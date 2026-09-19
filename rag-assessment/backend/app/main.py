
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.dependencies import get_embedder, get_vector_store
from app.routers import upload, query, documents

# Initialize FastAPI application
app = FastAPI(
    title="RAG Assessment API",
    description="Retrieval-Augmented Generation API with Document Ingestion, Hybrid/Vector Retrieval, and Groq LLM streaming.",
    version="1.0.0",
)

# CORS Middleware setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize core services once at module level so models/stores are ready
embedder = get_embedder()
vector_store = get_vector_store()

# Store singletons on app.state for additional access patterns
app.state.embedder = embedder
app.state.vector_store = vector_store

# Include routers
app.include_router(upload.router, prefix="", tags=["Upload"])
app.include_router(query.router, prefix="", tags=["Query"])
app.include_router(documents.router, prefix="", tags=["Documents"])


@app.get("/", tags=["Health"])
async def root_health():
    """Root health check endpoint."""
    return {"status": "ok"}


@app.get("/health", tags=["Health"])
async def health_check():
    """Dedicated health check endpoint."""
    return {"status": "ok"}
