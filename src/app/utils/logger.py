"""
╔══════════════════════════════════════════════════════════════════════════╗
║                      GerMed ChatBot — Logger Setup                     ║
╠══════════════════════════════════════════════════════════════════════════╣
║                                                                        ║
║  🎓 WHAT YOU'RE LEARNING HERE:                                         ║
║                                                                        ║
║  Logging is the same in Flask and FastAPI — Python's built-in          ║
║  `logging` module works everywhere. The key insight is:                ║
║                                                                        ║
║  1. Configure logging ONCE at startup (in create_app / lifespan)       ║
║  2. Use `logging.getLogger(__name__)` in every module                  ║
║  3. The logger name automatically matches the module path              ║
║     e.g., "src.app.api.v1.services.text_search.text_search_service"   ║
║                                                                        ║
║  This is identical to the Flask version — logging is framework-        ║
║  agnostic. We just port it directly.                                   ║
║                                                                        ║
╚══════════════════════════════════════════════════════════════════════════╝
"""

import logging
import sys
from pathlib import Path


def setup_logging(log_level: str = "INFO", log_dir: str = "logs") -> None:
    """
    Configure application-wide logging with both console and file handlers.

    Args:
        log_level: Minimum log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_dir: Directory for log files (created if it doesn't exist)
    """
    # Ensure log directory exists
    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)

    # Define log format
    log_format = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # Root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))

    # Clear existing handlers to avoid duplicates on reload
    root_logger.handlers.clear()

    # Console handler — colored output for dev experience
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(log_format)
    console_handler.setLevel(logging.DEBUG)
    root_logger.addHandler(console_handler)

    # File handler — persistent logs
    file_handler = logging.FileHandler(log_path / "app.log", encoding="utf-8")
    file_handler.setFormatter(log_format)
    file_handler.setLevel(logging.INFO)
    root_logger.addHandler(file_handler)

    # Suppress noisy third-party loggers
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)

    logging.info("📋 Logging initialized successfully.")
