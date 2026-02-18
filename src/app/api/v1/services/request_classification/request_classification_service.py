import json
import logging
import re
from typing import List, Any
from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import JsonOutputParser

from src.app.helpers.prompt import request_classify_prompt_template
from src.app.exceptions.custom_exceptions import APIException

class RequestClassificationService:
    """
    Service to classify user queries using LangChain and OpenAI.
    Determines if a query is for 'text_product_search' or 'faqs_search'.
    """
    
    def __init__(self, openai_llm: ChatOpenAI):
        self.llm = openai_llm
        self.prompt = request_classify_prompt_template()
        # 🎓 PRO TIP: Using LCEL (LangChain Expression Language) for clean chains
        self.chain = self.prompt | self.llm

    async def classify_request(self, text_query: str, chat_history: List[Any] = []) -> str:
        """
        Asynchronously classifies the incoming query.
        """
        try:
            # Format history for the prompt if it's a list of BaseMessages
            # Otherwise assume it's already a string or formatted history
            history_str = self._format_history(chat_history)
            
            # Invoke the chain (LCEL is async-friendly)
            response = await self.chain.ainvoke({
                "text_query": text_query,
                "chat_history": history_str
            })
            
            content = response.content.strip()
            
            # 🔹 Extract and parse JSON
            classification = self._extract_json(content)
            
            label = classification.get("label")
            if label not in {"text_product_search", "faqs_search"}:
                logging.error(f"⚠️ Unexpected label from LLM: {label}")
                # Default fallback
                return "faqs_search"

            logging.info(f"🎯 Query Classified: {label}")
            return label

        except Exception as e:
            logging.error(f"❌ Classification failed: {e}")
            # Safe Fallback: Assume FAQ/Support if classification fails
            return "faqs_search"

    def _format_history(self, history: List[Any]) -> str:
        """Converts LangChain message objects to a string for prompt consumption."""
        if not history:
            return "No previous history."
        
        formatted = []
        for msg in history:
            role = "User" if msg.type == "human" else "AI"
            formatted.append(f"{role}: {msg.content}")
        return "\n".join(formatted[-5:]) # Last 5 messages for context

    def _extract_json(self, text: str) -> dict:
        """Safely extracts JSON from LLM response text."""
        try:
            # Look for the first JSON object block
            match = re.search(r"\{.*?\}", text, re.DOTALL)
            if match:
                return json.loads(match.group(0))
            return json.loads(text)
        except Exception:
            logging.warning(f"Could not parse classification JSON: {text}")
            return {"label": "faqs_search"}
