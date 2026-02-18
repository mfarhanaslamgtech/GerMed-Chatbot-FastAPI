"""
╔════════════════════════════════════════════════════════════════════════╗
║                  GerMed ChatBot — Entry Point (Uvicorn)                ║
╠════════════════════════════════════════════════════════════════════════╣
║                                                                        ║
║  🎓 WHAT YOU'RE LEARNING HERE:                                         ║
║                                                                        ║
║  WSGI vs ASGI — The fundamental difference:                            ║
║                                                                        ║
║  Flask = WSGI (Web Server Gateway Interface)                           ║
║   - Synchronous: One request blocks until it's done                    ║
║   - Uses Gunicorn or Werkzeug as the server                            ║
║   - app.run(host, port)                                                ║
║                                                                        ║
║  FastAPI = ASGI (Asynchronous Server Gateway Interface)                ║
║   - Asynchronous: Multiple requests handled concurrently               ║
║   - Uses Uvicorn (or Hypercorn) as the server                          ║
║   - uvicorn.run(app, host, port)                                       ║
║                                                                        ║
║  WHY ASYNC MATTERS for a ChatBot:                                      ║
║   - OpenAI API calls take 1-10 seconds. With Flask, that thread is     ║
║     blocked. With FastAPI + async, other requests are served while     ║
║     waiting for OpenAI to respond.                                     ║
║   - Same for MongoDB queries, Redis lookups, and embedding generation. ║
║                                                                        ║
║  Flask version (run.py):                                               ║
║      app = create_app()                                                ║
║      app.run(debug=True, host='0.0.0.0', port=5000)                    ║
║                                                                        ║
║  FastAPI version (this file):                                          ║
║      app = create_app()                                                ║
║      uvicorn.run("main:app", host='0.0.0.0', port=8000, reload=True)   ║
║                                                                        ║
║  NOTE: "main:app" is a string reference. Uvicorn imports the `app`     ║
║  object from the `main` module. This enables hot-reloading — when you  ║
║  save a file, the server restarts automatically.                       ║
║                                                                        ║
╚════════════════════════════════════════════════════════════════════════╝
"""

from src.app.app import create_app
from src.app.config.config import Config

# Create the application instance
# Uvicorn needs this at module level to reference it as "main:app"
app = create_app()


if __name__ == "__main__":
    import uvicorn

    # 🎓 Uvicorn options explained:
    #
    # "main:app"  → Import path: module_name:variable_name
    # host        → Same as Flask: "0.0.0.0" = listen on all interfaces
    # port        → 8000 is the FastAPI convention (Flask uses 5000)
    # reload      → Auto-restart on file changes (like Flask's debug=True)
    # log_level   → Uvicorn's own logging (separate from our app logger)
    # workers     → Number of worker processes (for production, use > 1)
    #               In dev, keep at 1 with reload=True

    uvicorn.run(
        "main:app",                    # String reference for hot-reload
        host=Config.HOST,
        port=Config.PORT,
        reload=Config.DEBUG,           # Auto-reload in dev mode
        log_level="info",
    )
