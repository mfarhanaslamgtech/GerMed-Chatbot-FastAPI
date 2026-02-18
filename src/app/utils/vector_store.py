import logging
import os
from pinecone import Pinecone, ServerlessSpec
from langchain_openai import OpenAIEmbeddings
from langchain_pinecone import PineconeVectorStore
from src.app.config.settings import settings

def initialize_vector_store() -> PineconeVectorStore:
    """
    Initializes Pinecone and returns a LangChain PineconeVectorStore.
    
    🎓 FASTAPI MIGRATION NOTE:
    We use the settings class instead of os.environ directly.
    """
    try:
        api_key = settings.pinecone.PINECONE_API_KEY
        index_name = settings.pinecone.PINECONE_INDEX_NAME
        namespace = settings.pinecone.PINECONE_NAMESPACE
        
        # 1. Initialize Pinecone Client
        pc = Pinecone(api_key=api_key)

        # 2. Check/Create Index
        # Note: In production, we usually do this once outside the app, 
        # but here we follow the Gervet logic.
        if index_name not in pc.list_indexes().names():
            logging.info(f"🏗️ Creating Pinecone index: {index_name}")
            pc.create_index(
                name=index_name,
                dimension=3072, # dimension for text-embedding-3-large
                metric="cosine",
                spec=ServerlessSpec(cloud="aws", region="us-east-1")
            )
        else:
            logging.info(f"✅ Pinecone index {index_name} already exists")

        # 3. Initialize OpenAI Embeddings
        embeddings_model = OpenAIEmbeddings(
            model=settings.embedding_models.OPENAI_EMBEDDING_MODEL,
            api_key=settings.openai.OPENAI_API_KEY
        )

        # 4. Return Vector Store
        # 🎓 PRO TIP: We pass the API key explicitly because LangChain components
        # sometimes fail to find it in the environment when using Pydantic Settings.
        vectorstore = PineconeVectorStore(
            index_name=index_name,
            embedding=embeddings_model,
            namespace=namespace,
            pinecone_api_key=api_key
        )
        
        logging.info(f"✅ Connected to Pinecone index: {index_name}")
        return vectorstore
    except Exception as e:
        if "FORBIDDEN" in str(e) or "403" in str(e):
            logging.error(f"❌ Pinecone Limit Error: You have reached the maximum number of indexes (5). "
                          f"Please delete an unused index at app.pinecone.io or use an existing index name in .env.")
        else:
            logging.error(f"❌ Failed to initialize Vector Store: {e}")
        raise

if __name__ == "__main__":
    import asyncio
    async def main():
        logging.basicConfig(level=logging.INFO)
        print("🔍 Checking Vector Store Config...")
        try:
            if settings.pinecone.PINECONE_API_KEY:
                vectorstore = initialize_vector_store()
                print("✅ Vector Store.py: Connection Successful!")
            else:
                print("❌ Vector Store.py: Pinecone API Key not found")
        except Exception as e:
            print(f"❌ Vector Store.py: Connection Failed -> {e}")
    asyncio.run(main())
                

