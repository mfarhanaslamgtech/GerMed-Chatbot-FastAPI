import logging
from typing import Optional
from src.app.extensions.database import Database
from src.app.api.v1.models.user_model import UserDB
from src.app.exceptions.custom_exceptions import DatabaseException

class UserRepository:
    """
    Repository for User-related database operations.
    Uses Native Async PyMongo.
    """
    def __init__(self, db: Database, collection_name: str = "users"):
        self.collection = db.get_collection(collection_name)

    async def find_user_by_email(self, email: str) -> Optional[UserDB]:
        """Find a user by email (Async)."""
        try:
            user_data = await self.collection.find_one({"user_email": email})
            return UserDB(**user_data) if user_data else None
        except Exception as e:
            logging.error(f"❌ Error finding user by email {email}: {str(e)}")
            raise DatabaseException(f"Failed to fetch user by email: {email}")

    async def create_user(
        self, 
        user_email: str, 
        user_id: Optional[str] = None, 
        region: Optional[str] = None
    ) -> UserDB:
        """Create a new user with structured data (Async)."""
        try:
            user = UserDB(user_email=user_email, user_id=user_id, region=region) if user_id else UserDB(user_email=user_email, region=region)
            # Actually UserDB constructor handles Optional[user_id] fine because it has a default_factory.
            # If we pass None, Pydantic might use None instead of the factory if not careful.
            # But here we want to pass it if available.
            
            kwargs = {"user_email": user_email, "region": region}
            if user_id:
                kwargs["user_id"] = user_id
            
            user = UserDB(**kwargs)
            user_dict = user.model_dump(by_alias=True, exclude={"id"})
            
            result = await self.collection.insert_one(user_dict)
            user.id = str(result.inserted_id)
            
            logging.info(f"👤 User created successfully: {user_email}")
            return user
        except Exception as e:
            logging.error(f"❌ Error creating user: {str(e)}")
            raise DatabaseException("Failed to create user record")

    async def ensure_unique_email_index(self):
        """Standard Best Practice: Ensure email index exists."""
        try:
            await self.collection.create_index("user_email", unique=True)
            logging.info("📝 Unique index ensured for 'user_email'")
        except Exception as e:
            logging.error(f"❌ Failed to create user email index: {e}")
