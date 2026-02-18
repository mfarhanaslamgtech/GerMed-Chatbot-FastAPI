# GerMed ChatBot (FastAPI Migration)

This project has been migrated from Flask to FastAPI for improved performance, async support, and modern features.

## 🚀 Key Features
- **FastAPI**: Modern, fast (high-performance) web framework.
- **Asynchronous**: Built-in async/await support for I/O operations.
- **Dependency Injection**: Modular and testable architecture using `dependency-injector`.
- **Auto-Documentation**: interactive API docs at `/docs` (Swagger UI) and `/redoc`.
- **Dockerized**: Easy setup with Docker Compose.

## 🛠️ Setup & Installation

### Prerequisites
- Python 3.12+
- Docker & Docker Compose (optional but recommended)

### Local Setup (Without Docker)
1. **Create Virtual Environment**:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```
2. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```
3. **Configure Environment**:
   - Copy `.env.example` to `.env` (a `.env` with dummy values is created for you)
   - Update `.env` with real API keys (OpenAI, Pinecone, etc.)
4. **Run the Application**:
   ```bash
   uvicorn src.app.app:create_app --host 0.0.0.0 --port 8000 --reload
   ```

### 🐳 Docker Scenarios

Choose the scenario that fits your current task:

#### Scenario A: Databases Only (Fastest for Local Coding)
Use this if you want to run the FastAPI app locally (`uvicorn`) but need the databases (Redis Stack, MongoDB) running in Docker.
1. **Start Databases**:
   ```bash
   docker-compose -f docker-compose.db.yml up -d
   ```
2. **Run App Locally**:
   ```bash
   uvicorn main:app --reload
   ```

#### Scenario B: Full Stack (App + Databases)
Use this to test the entire system as a production-like containerized environment.
1. **Build and Run**:
   ```bash
   docker-compose up --build -d
   ```

### 🖥️ Admin Dashboards (After starting Docker)
- **MongoDB UI**: [http://localhost:8081](http://localhost:8081)
- **Redis UI**: [http://localhost:8082](http://localhost:8082)
- **API Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)

## 🧪 Running Tests
To run all unit and integration tests:
```bash
./run_tests.sh
```
(Ensure you created the script or run `pytest` if configured, or use the loop command provided in development logs).

## 📂 Project Structure
- `src/app/api`: Routers, Controllers, Services, Repositories.
- `src/app/core`: Core infrastructure (Redis, Logging).
- `src/app/extensions`: Database connections.
- `src/app/containers`: Dependency Injection Container.
- `src/app/middlewares`: Authentication and others.
- `tests/`: Unit and integration tests for all layers.

## 🔑 Authentication
- **Login**: `POST /v1/auth/login`
- **Refresh**: `POST /v1/auth/refresh_token`
- **Logout**: `POST /v1/auth/logout`
Protected routes require `Authorization: Bearer <token>`.

## 📦 Deployment
The application is containerized. Use the provided `Dockerfile` and `docker-compose.yml` for deployment.