import logging
from typing import Optional
from openai import OpenAI, AsyncOpenAI
from langchain_openai import ChatOpenAI
from src.app.config.settings import settings

class OpenAIClient:
    """
    Utility class to manage OpenAI configuration and initialization.
    
    🎓 FASTAPI MIGRATION NOTE:
    We now provide both synchronous and asynchronous OpenAI clients.
    FastAPI works best with AsyncOpenAI for non-blocking I/O.
    """
    
    _logger = logging.getLogger(__name__)

    @staticmethod
    def get_openai_client(is_async: bool = True):
        """Initialize OpenAI client."""
        try:
            api_key = settings.openai.OPENAI_API_KEY
            if is_async:
                client = AsyncOpenAI(api_key=api_key)
                OpenAIClient._logger.info("✅ AsyncOpenAI client initialized.")
            else:
                client = OpenAI(api_key=api_key)
                OpenAIClient._logger.info("✅ Sync OpenAI client initialized.")
            return client
        except Exception as e:
            OpenAIClient._logger.error(f"❌ Failed to initialize OpenAI client: {e}")
            raise

    @staticmethod
    def get_openai_llm() -> ChatOpenAI:
        """Initialize LangChain ChatOpenAI instance."""
        try:
            llm = ChatOpenAI(
                api_key=settings.openai.OPENAI_API_KEY, # In newest langchain-openai it's api_key, not openai_api_key (though both work)
                model=settings.openai.MODEL_NAME,
                temperature=settings.openai.OPENAI_TEMPERATURE,
                max_tokens=settings.openai.MAX_TOKENS,
                timeout=settings.openai.REQUEST_TIMEOUT
            )
            OpenAIClient._logger.info(f"✅ ChatOpenAI initialized with model: {settings.openai.MODEL_NAME}")
            return llm
        except Exception as e:
            OpenAIClient._logger.error(f"❌ Failed to initialize ChatOpenAI: {e}")
            raise

    @staticmethod
    async def check_health() -> bool:
        """Simple health check for OpenAI API."""
        try:
            client = AsyncOpenAI(api_key=settings.openai.OPENAI_API_KEY)
            await client.models.list()
            return True
        except Exception:
            return False

if __name__ == "__main__":
    import asyncio
    async def main():
        logging.basicConfig(level=logging.INFO)
        print("🔍 Checking OpenAI Config...")
        try:
            openai = OpenAIClient()
            print("✅ OpenAI.py: Connection Successful!")
        except Exception as e:
            print(f"❌ OpenAI.py: Connection Failed -> {e}")
    asyncio.run(main())
