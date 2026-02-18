import logging
from sentence_transformers import SentenceTransformer
from transformers import CLIPProcessor, CLIPModel
from typing import Optional, Dict, Any
from src.app.config.settings import settings

class TextEmbeddingModel:
    """
    Singleton class to manage SentenceTransformer Embedding Model.
    """
    _instance: Optional[SentenceTransformer] = None

    @classmethod
    def get_instance(cls) -> SentenceTransformer:
        if cls._instance is None:
            try:
                model_name = settings.embedding_models.TRANSFORMERS_EMBEDDING_MODEL
                logging.info(f"💾 Loading SentenceTransformer: {model_name}")
                cls._instance = SentenceTransformer(model_name)
                logging.info("✅ SentenceTransformer loaded.")
            except Exception as e:
                logging.error(f"❌ Failed to load SentenceTransformer: {e}")
                raise
        return cls._instance

class ImageEmbeddingModel:
    """
    Singleton for managing CLIP model + processor.
    """
    _instance: Optional[Dict[str, Any]] = None

    @classmethod
    def get_instance(cls) -> Dict[str, Any]:
        if cls._instance is None:
            try:
                model_name = settings.embedding_models.IMAGE_EMBEDDING_MODEL
                device = "cpu" # Defaulting to CPU for now
                
                logging.info(f"💾 Loading CLIP: {model_name} on {device}")
                processor = CLIPProcessor.from_pretrained(model_name)
                model = CLIPModel.from_pretrained(model_name).to(device)

                cls._instance = {
                    "model": model,
                    "processor": processor,
                    "device": device
                }
                logging.info("✅ CLIP model loaded.")
            except Exception as e:
                logging.error(f"❌ Failed to load CLIP: {e}")
                raise
        return cls._instance

if __name__ == "__main__":
    import asyncio
    async def main():
        logging.basicConfig(level=logging.INFO)
        print("🔍 Checking Embedding Model Config...")
        try:
            text_embedding_model = TextEmbeddingModel.get_instance()
            image_embedding_model = ImageEmbeddingModel.get_instance()
            print("✅ Embedding Model.py: Connection Successful!")
        except Exception as e:
            print(f"❌ Embedding Model.py: Connection Failed -> {e}")
    asyncio.run(main())
