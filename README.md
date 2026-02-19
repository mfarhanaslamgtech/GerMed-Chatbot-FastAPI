# GerMed ChatBot (FastAPI Production Ready)

This is a high-performance, asynchronous AI ChatBot built with **FastAPI**, designed for scalability and production use. It supports text and image queries using RAG (Retrieval-Augmented Generation) with OpenAI, Pinecone, and MongoDB.

---

## 🚀 Quick Start (Choose Your Path)

### Path A: I am a Developer (Local Coding)
*Use this if you want to write code and see changes instantly.*

1.  **Prerequisites**: Python 3.12+, Docker Desktop (for databases).
2.  **Environment Setup**:
    ```bash
    # 1. Create a virtual environment
    python -m venv .venv
    
    # 2. Activate it (Windows)
    .venv\Scripts\activate
    
    # 3. Install dependencies
    pip install -r requirements.txt
    ```
3.  **Start Databases (Docker)**:
    You need MongoDB and Redis running. We have a dedicated compose file for this:
    ```bash
    docker-compose -f docker-compose.db.yml up -d
    ```
4.  **Configure .env**:
    Copy `.env.example` to `.env` and set `DEBUG=True`.
5.  **Run the App (Hot Reload)**:
    ```bash
    uvicorn src.app.app:create_app --host 0.0.0.0 --port 8000 --reload
    ```
    *   **API Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)
    *   **Mongo Express**: [http://localhost:8081](http://localhost:8081)
    *   **Redis Commander**: [http://localhost:8082](http://localhost:8082)

---

### Path B: Production Deployment
*Use this for deploying to a live server (AWS, DigitalOcean, etc.).*

**Key Features of Production Mode:**
*   🔒 **Secure**: Internally restricted database ports (not exposed to internet).
*   🚀 **Scalable**: Uses **Gunicorn** with 4 concurrent workers (configurable).
*   🌐 **Nginx Proxy**: Handles SSL/TLS and static assets.
*   👤 **Non-Root User**: Runs inside container as secure `appuser`.

#### 1. Security First
*   **Update Passwords**: Open `.env` and `docker-compose.production.yml`. Replace ALL placeholder passwords (`CHANGE_ME_...`) with strong, random strings.
*   **Disable Debug**: Ensure `DEBUG=False` in `.env`.
*   **Allowed Origins**: Set `ALLOWED_ORIGINS` in `.env` to your frontend domain (e.g., `https://my-app.com`).

#### 2. Deploy
Run the full production stack:
```bash
docker-compose -f docker-compose.production.yml up --build -d
```

#### 3. Verify Deployment
*   The API is now hidden behind Nginx at **Port 80/443**.
*   Direct access to port `8000` is **BLOCKED**.
*   Direct access to Redis/Mongo ports (`6379`, `27017`) is **BLOCKED**.
*   **Health Check**: `curl http://localhost/health`

---

## 🛠️ Configuration Guide

### 1. `.env` File (Environment Variables)
This application uses Pydantic Settings for validation. Missing variables will prevent startup.

| Variable | Description | Example (Dev) | Production |
| :--- | :--- | :--- | :--- |
| `DEBUG` | Shows stack traces on error | `True` | `False` |
| `ALLOWED_ORIGINS` | CORS allowed domains | `*` | `https://domain.com` |
| `OPENAI_API_KEY` | Your OpenAI Key | `sk-...` | `sk-...` |
| `REDIS_PASSWORD` | Secure password for all Redis instances | `admin` | `StrongPass123!` |
| `JWT_SECRET_KEY` | key for signing tokens | `secret` | `LongRandomString` |

### 2. Gunicorn Configuration (`gunicorn_conf.py`)
Controls the application server workers.
*   **Workers**: Default is `4`.
*   **Memory Usage**: Each worker loads the AI models (~1.5GB RAM).
*   **Scaling**: To handle more traffic, increase workers (requires more RAM) or move AI models to a separate service.

---

## 📂 Project Structure
```
GerMed-Chatbot-FastAPI/
├── src/
│   └── app/
│       ├── api/             # Routes (Controllers)
│       ├── core/            # Database & Redis Connections
│       ├── services/        # Business Logic
│       ├── repositories/    # Database Access Layer
│       └── containers/      # Dependency Injection Setup
├── docker-compose.yml       # Local Development Stack
├── docker-compose.production.yml # Secure Production Stack
├── docker-compose.db.yml    # Databases Only (for local coding)
├── gunicorn_conf.py         # Production Server Config
├── nginx/                   # Nginx Proxy Config
└── Dockerfile               # Multi-stage Production Build
```

## 🧪 Testing
Run the test suite to ensure stability before deploying:
```bash
./run_tests.sh
```