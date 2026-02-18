import re
import logging
from typing import Dict, Any, List, Optional

from langchain_openai import ChatOpenAI
from langchain_core.messages import BaseMessage

from src.app.api.v1.repositories.chat_repository import ChatRepository
from src.app.helpers.prompt import get_audio_qa_prompt, condense_question_prompt

class AudioCallService:
    """
    Service for handling Voice/Audio-based queries.
    Focuses on natural, concise, speech-friendly responses.
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
        self.qa_prompt = get_audio_qa_prompt()
        self.condense_prompt = condense_question_prompt()

    async def answer_question(
        self, 
        user_id: str, 
        user_email: str, 
        question: str, 
        history: List[BaseMessage] = []
    ) -> str:
        """
        Flow designed for Text-to-Speech compatibility.
        """
        try:
            # 1. Context Retrieval
            retriever = self.vector_store.as_retriever(search_kwargs={"k": 3})
            docs = await retriever.ainvoke(question)
            context = "\n\n".join([d.page_content for d in docs])

            # 2. History Formatting
            history_str = self._format_history(history)

            # 3. Generate Speech-Friendly Answer
            chain = self.qa_prompt | self.llm
            response = await chain.ainvoke({
                "context": context,
                "chat_history": history_str,
                "question": question
            })

            answer = response.content.strip()

            # 4. Clean for TTS (No markdown, no bracketed links)
            answer = self._clean_for_speech(answer)

            return answer

        except Exception as e:
            logging.error(f"❌ AudioCallService Error: {e}")
            return "I'm sorry, I'm having a bit of trouble connecting to my knowledge base. How else can I help you?"

    def _format_history(self, history: List[BaseMessage]) -> str:
        if not history:
            return "No previous history."
        return "\n".join([f"{'User' if m.type == 'human' else 'AI'}: {m.content}" for m in history[-3:]])

    def _clean_for_speech(self, text: str) -> str:
        """Removes markdown and formats URLs for better TTS reading."""
        # Remove markdown bold/italics
        text = text.replace("**", "").replace("_", "")
        # Replace [title](url) with "title (url)"
        text = re.sub(r'\[([^\]]+)\]\((https?://[^\)]+)\)', r'\1 (\2)', text)
        return text
