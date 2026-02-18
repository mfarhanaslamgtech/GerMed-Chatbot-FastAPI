import json
import logging
import re
from typing import Dict, Any, List, Optional

from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.messages import BaseMessage

from src.app.api.v1.repositories.chat_repository import ChatRepository
from src.app.api.v1.models.chat_model import ChatMessages, RoleEnum, UserContent, AssistantContent
from src.app.helpers.prompt import get_faqs_qa_prompt, condense_question_prompt
from src.app.exceptions.custom_exceptions import APIException

class FaqService:
    """
    Asynchronous FAQ RAG Service.
    Uses Pinecone Vector DB to retrieve context and OpenAI to generate answers.
    """

    def __init__(
        self, 
        vector_store: Any, 
        openai_llm: ChatOpenAI, 
        chat_repository: ChatRepository
    ):
        self.vector_store = vector_store
        self.llm = openai_llm
        self.repository = chat_repository
        self.qa_prompt = get_faqs_qa_prompt()
        self.condense_prompt = condense_question_prompt()

    async def answer_question(
        self, 
        user_id: str, 
        user_email: str, 
        question: str, 
        history: List[BaseMessage]
    ) -> Dict[str, Any]:
        """
        Main RAG flow: 
        1. Condense question (if needed)
        2. Retrieve context from Pinecone
        3. Generate JSON answer via LLM
        4. Save to DB in background
        """
        try:
            # 1. Condense Question for search (Async)
            history_str = self._format_history(history)
            standalone_question = await self._get_standalone_question(question, history_str)
            logging.info(f"🔍 Standalone Question: {standalone_question}")

            # 2. Retrieve Documents (Async friendly wrapper)
            # PineconeVectorStore.as_retriever() is what we usually use
            retriever = self.vector_store.as_retriever(search_kwargs={"k": 5})
            docs = await retriever.ainvoke(standalone_question)
            context = "\n\n".join([d.page_content for d in docs])

            # 3. Generate Answer (Async LCEL)
            chain = self.qa_prompt | self.llm
            response = await chain.ainvoke({
                "context": context,
                "chat_history": history_str,
                "question": question
            })

            # 4. Safe Parse JSON
            raw_answer = response.content.strip()
            parsed_answer = self._safe_parse_json(raw_answer)

            # 5. Background Save (Fire and Forget)
            # In FastAPI, we usually use BackgroundTasks, but here we'll 
            # just trigger the task since we're in an async method.
            await self._save_chat(user_id, user_email, question, parsed_answer)

            return parsed_answer

        except Exception as e:
            logging.error(f"❌ FaqService Error: {e}", exc_info=True)
            return self._fallback_response()

    async def _get_standalone_question(self, question: str, history_str: str) -> str:
        """Rephrases the question to be standalone if context exists."""
        if not history_str or history_str == "No previous history.":
            return question
            
        try:
            chain = self.condense_prompt | self.llm
            response = await chain.ainvoke({"chat_history": history_str, "question": question})
            return response.content.strip()
        except:
            return question

    def _format_history(self, history: List[BaseMessage]) -> str:
        if not history:
            return "No previous history."
        return "\n".join([f"{'User' if m.type == 'human' else 'AI'}: {m.content}" for m in history[-5:]])

    def _safe_parse_json(self, text: str) -> Dict[str, Any]:
        """Robust JSON cleaning and parsing."""
        try:
            # Remove markdown blocks
            text = re.sub(r"```json|```", "", text).strip()
            match = re.search(r"\{.*\}", text, re.DOTALL)
            if match:
                return json.loads(match.group(0))
            return json.loads(text)
        except:
            logging.warning(f"⚠️ JSON Parse failed for FAQ response: {text[:100]}...")
            return self._fallback_response()

    async def _save_chat(self, user_id: str, user_email: str, question: str, answer: Dict[str, Any]):
        """Persists the interaction to MongoDB."""
        try:
            messages = [
                ChatMessages(
                    user_id=user_id, user_email=user_email, role=RoleEnum.user,
                    content=UserContent.create(text=question)
                ),
                ChatMessages(
                    user_id=user_id, user_email=user_email, role=RoleEnum.assistant,
                    content=AssistantContent.create(answer=answer)
                )
            ]
            await self.repository.save_bulk_messages(messages)
        except Exception as e:
            logging.error(f"Failed to save FAQ chat: {e}")

    def _fallback_response(self) -> Dict[str, Any]:
        return {
            "start_message": "I'm here to help, but I'm having trouble retrieving details right now.",
            "core_message": {"steps": ["Please visit https://www.gervetusa.com for assistance.", "Or contact us at sales@gervetusa.com"]},
            "end_message": "How else can I help you?",
            "more_prompt": None
        }
