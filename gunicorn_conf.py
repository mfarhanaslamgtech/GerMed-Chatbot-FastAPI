import multiprocessing

# ------------------------------------------------------------------------------
# Gunicorn Configuration for Production Scalability
# ------------------------------------------------------------------------------
#
# To handle "thousands" of users on a single server:
# 1. We use Uvicorn workers (uvicorn.workers.UvicornWorker) for async performance.
# 2. We use multiple workers to utilize all CPU cores.
# 3. We keep heavy AI models either:
#    a) Loaded per worker (if RAM allows - current implementation)
#    b) Offloaded to a separate service (future optimization)
#
# ------------------------------------------------------------------------------

# 1. Bind Address
bind = "0.0.0.0:8000"

# 2. Worker Class & Concurrency
# Uvicorn workers are essential for FastAPI's async capabilities.
worker_class = "uvicorn.workers.UvicornWorker"

# 3. Number of Workers
# Formula: (2 x num_cores) + 1
# However, since we load Heavy ML Models (CLIP/SentenceTransformers) in each worker:
# - Each worker eats ~1-2GB RAM.
# - If you have 32GB RAM + 16 cores, use: workers = 4-8 (monitor RAM!)
# - If you have 8GB RAM + 4 cores, use: workers = 2 (to avoid OOM crashes)
# default to 2 workers to be safe for typical cloud instances.
workers = 4  
# threads = 2  # threads doesn't apply to Uvicorn workers (async loop handles concurrency)

# 4. Timeout
# AI models can take time to load or process complex queries.
# Increase timeout to prevent Gunicorn from killing workers prematurely.
timeout = 120  # 2 minutes
keepalive = 5

# 5. Logging
accesslog = "-"  # stdout
errorlog = "-"   # stderr
loglevel = "info"

# 6. Preloading
# Preloading application code before forking workers can save RAM (Copy-on-Write).
# However, with PyTorch/TensorFlow, this can sometimes cause deadlocks with CUDA.
# Test carefully. For CPU-only inference, preload_app = True usually helps save RAM.
preload_app = False 
