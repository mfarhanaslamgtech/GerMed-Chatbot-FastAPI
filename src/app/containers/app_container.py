from dependency_injector import containers, providers

# Infrastructure / Extensions
from src.app.extensions.database import Database
from src.app.core.redis_connector import RedisConnection
from src.app.core.assets.asset_uploader import LocalAssetUploader

# Utils
from src.app.utils.logger import setup_logging
from src.app.utils.openai_client import OpenAIClient
from src.app.utils.embedding_model import TextEmbeddingModel, ImageEmbeddingModel
from src.app.utils.vector_store import initialize_vector_store

# Repositories (Layer 3)
from src.app.api.v1.repositories.user_repository import UserRepository
from src.app.api.v1.repositories.token_repository import TokenRepository
from src.app.api.v1.repositories.chat_repository import ChatRepository

# Services (Layer 5)
from src.app.api.v1.services.request_classification.request_classification_service import RequestClassificationService
from src.app.api.v1.services.text_search.text_search_service import TextSearchService
from src.app.api.v1.services.faqs.faq_service import FaqService
from src.app.api.v1.services.audio_call.audio_call_service import AudioCallService
from src.app.api.v1.services.geo.geo_service import GeoService
from src.app.api.v1.services.auth.auth_service import AuthService
from src.app.api.v1.services.visual_search.visual_search_service import VisualSearchService
from src.app.api.v1.services.catalog.catalog_service import CatalogService
from src.app.api.v1.services.vector_sync.sync_manager import SyncManager

# Controllers (Layer 4)
from src.app.api.v1.controllers.chat.text_query_handler import TextQueryHandler
from src.app.api.v1.controllers.chat.image_query_handler import ImageQueryHandler
from src.app.api.v1.controllers.chat.chat_controller import ChatController
from src.app.api.v1.controllers.auth.auth_controller import AuthController

class AppContainer(containers.DeclarativeContainer):
    """
    Dependency Injection Container for the GerMed FastAPI application.
    
    🎓 FASTAPI MIGRATION NOTE:
    This container links our Phase 2 Infrastructure (Database, Redis, etc.)
    so they can be injected into Repositories and Services in future phases.
    """
    
    # We will configure wiring as we add controllers
    # wiring_config = containers.WiringConfiguration(...)

    # 1. Base Providers
    logger = providers.Callable(setup_logging)
    
    # 2. Database (Async)
    database = providers.Singleton(Database)

    # 3. Redis Clients (Singletons)
    # 🎓 PRO TIP: We inject the client directly. 
    # Connection verification (PING) is handled in the App Lifespan.
    redis_textbot = providers.Singleton(RedisConnection.get_textbot_client)
    redis_imagebot = providers.Singleton(RedisConnection.get_imagebot_client)
    redis_rate_limit = providers.Singleton(RedisConnection.get_rate_limit_client)
    redis_token_manager = providers.Singleton(RedisConnection.get_token_manager_client)

    # 4. Storage / Assets
    asset_uploader = providers.Singleton(LocalAssetUploader)

    # 5. AI Models (Singletons)
    text_embedding_model = providers.Singleton(TextEmbeddingModel.get_instance)
    image_embedding_model = providers.Singleton(ImageEmbeddingModel.get_instance)
    
    # 6. Third Party Clients
    openai_client = providers.Singleton(OpenAIClient.get_openai_client, is_async=True)
    openai_llm = providers.Singleton(OpenAIClient.get_openai_llm)
    
    # 7. Vector Database (Pinecone)
    vector_store = providers.Singleton(initialize_vector_store)

    # 8. Repositories (Layer 3)
    user_repository = providers.Singleton(
        UserRepository, 
        db=database
    )
    
    token_repository = providers.Singleton(
        TokenRepository, 
        redis_conn=redis_token_manager
    )

    chat_repository = providers.Singleton(
        ChatRepository, 
        db=database
    )

    # 9. Services (Layer 5)
    classification_service = providers.Singleton(
        RequestClassificationService,
        openai_llm=openai_llm
    )
    
    text_search_service = providers.Singleton(
        TextSearchService,
        redis_client=redis_textbot,
        embedding_model=text_embedding_model,
        openai_llm=openai_llm,
        chat_repository=chat_repository
    )
    
    faq_service = providers.Singleton(
        FaqService,
        vector_store=vector_store,
        openai_llm=openai_llm,
        chat_repository=chat_repository
    )

    audio_call_service = providers.Singleton(
        AudioCallService,
        vector_store=vector_store,
        openai_llm=openai_llm,
        chat_repository=chat_repository
    )

    # 10. Visual Search (Layer 8)
    visual_search_service = providers.Singleton(
        VisualSearchService,
        redis_client=redis_imagebot,
        processor=providers.Callable(lambda clip: clip["processor"], image_embedding_model),
        model=providers.Callable(lambda clip: clip["model"], image_embedding_model),
        device=providers.Callable(lambda clip: clip["device"], image_embedding_model),
        asset_uploader=asset_uploader,
        repository=chat_repository,
        openai_client=openai_client
    )

    # 11. Handlers & Controllers (Layer 4)
    text_query_handler = providers.Singleton(
        TextQueryHandler,
        chat_repository=chat_repository,
        classification_service=classification_service,
        text_search_service=text_search_service,
        faqs_service=faq_service
    )

    image_query_handler = providers.Singleton(
        ImageQueryHandler,
        visual_search_service=visual_search_service
    )

    chat_controller = providers.Singleton(
        ChatController,
        text_handler=text_query_handler,
        image_handler=image_query_handler
    )

    # 12. Auth Stack (Layer 6)
    geo_service = providers.Singleton(GeoService)

    auth_service = providers.Singleton(
        AuthService,
        token_repository=token_repository,
        user_repository=user_repository,
        geo_service=geo_service
    )

    auth_controller = providers.Singleton(
        AuthController,
        auth_service=auth_service
    )

    # 13. Catalog Service (Layer 9 — Background task)
    catalog_service = providers.Factory(
        CatalogService,
        redis_conn=redis_textbot
    )

    # 14. Embeddings Sync (Migration Logic)
    embeddings_sync_manager = providers.Singleton(
        SyncManager,
        text_redis=redis_textbot,
        image_redis=redis_imagebot
    )
