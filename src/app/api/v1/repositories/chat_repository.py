import logging
import json
from typing import Optional, List, Union
from datetime import datetime
from pymongo import ASCENDING, DESCENDING
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage

from src.app.extensions.database import Database
from src.app.api.v1.models.chat_model import (
    ChatMessages, RoleEnum, UserContent, AssistantContent
)
from src.app.exceptions.custom_exceptions import DatabaseException

class ChatRepository:
    """
    Handles chat message storage and history retrieval using Native Async PyMongo.
    Includes complex aggregation for cleaning history for LLM consumption.
    """

    def __init__(self, db: Database, collection_name: str = "messages"):
        self.collection = db.get_collection(collection_name)

    async def ensure_indexes(self):
        """Create indexes for performance optimization."""
        try:
            await self.collection.create_index([("user_id", ASCENDING)])
            await self.collection.create_index([("user_email", ASCENDING)])
            await self.collection.create_index([("created_at", DESCENDING)])
            await self.collection.create_index([("content", "text")])
            logging.info("📝 Chat indexes ensured successfully.")
        except Exception as e:
            logging.error(f"❌ Failed to create chat indexes: {e}")

    async def save_message(
        self, 
        user_id: Optional[str], 
        user_email: str, 
        role: RoleEnum, 
        content: Union[UserContent, AssistantContent]
    ) -> ChatMessages:
        """Save a single chat message (Async)."""
        try:
            message = ChatMessages(
                user_id=user_id,
                user_email=user_email,
                role=role,
                content=content
            )
            # model_dump is the new dict() in Pydantic v2
            message_dict = message.model_dump(by_alias=True, exclude={"id"})
            result = await self.collection.insert_one(message_dict)
            message.id = str(result.inserted_id)
            
            logging.info(f"💾 Message saved | user={user_email} role={role}")
            return message
        except Exception as e:
            logging.error(f"❌ Error saving message: {e}")
            raise DatabaseException("Failed to save chat message")

    async def save_bulk_messages(self, messages: List[ChatMessages]) -> None:
        """Bulk insert messages for high-performance logging."""
        try:
            dicts = [m.model_dump(by_alias=True, exclude={"id"}) for m in messages]
            await self.collection.insert_many(dicts)
            logging.info(f"📊 Bulk saved {len(messages)} messages.")
        except Exception as e:
            logging.error(f"❌ Bulk save failed: {e}")
            raise DatabaseException("Bulk message save failed")

    async def get_clean_chat_history(self, user_email: str, limit: int = 5) -> List[BaseMessage]:
        """
        Retrieves formatted chat history for LangChain using an optimized aggregation pipeline.
        
        🎓 PRO TIP: We use aggregation to handle legacy vs new nested content structures 
        directly in the database, reducing Python CPU overhead.
        """
        try:
            pipeline = [
                {"$match": {"user_email": user_email}},
                {"$sort": {"created_at": -1}},
                {"$limit": limit},
                {
                    "$project": {
                        "role": 1,
                        "question_text": "$content.question.text",
                        "question_image": "$content.question.image",
                        "answer_content": "$content.answer",
                        "_id": 0
                    }
                }
            ]

            cursor = await self.collection.aggregate(pipeline)
            messages = []
            
            # Motor/PyMongo Async cursors use async for
            async for doc in cursor:
                role = doc.get("role")
                
                if role == RoleEnum.user:
                    parts = []
                    if doc.get("question_text"):
                        parts.append(str(doc["question_text"]))
                    if doc.get("question_image"):
                        parts.append(f"[Image: {doc['question_image']}]")
                    
                    content_str = " ".join(parts).strip()
                    if content_str:
                        messages.append(HumanMessage(content=content_str))

                elif role == RoleEnum.assistant:
                    ans = doc.get("answer_content")
                    if ans:
                        content_str = json.dumps(ans, ensure_ascii=False) if isinstance(ans, dict) else str(ans)
                        messages.append(AIMessage(content=content_str))

            # Reverse to Chronological order (LLMs expect earliest message first)
            messages.reverse()
            return messages

        except Exception as e:
            logging.error(f"❌ Error fetching chat history for {user_email}: {e}")
            return []
