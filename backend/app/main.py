"""FastAPI application entry point for Resume RAG Interviewer.

This module defines a `create_app` factory that configures the FastAPI
instance, registers CORS middleware, includes API routers, and provides a
simple health check endpoint. During startup it initializes the database
and performs a best‑effort warm‑up of the RAG retriever.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Import routers
from app.api import roles, sessions

# Import utilities for startup
from app.database import init_db

# Retrieve the Retriever helper; fallback to direct construction if needed
try:
    from app.api.sessions import get_retriever  # noqa: F401
except Exception:
    # If the helper is unavailable, we'll construct a Retriever manually later
    get_retriever = None

# Optional imports for manual Retriever construction
if get_retriever is None:
    from app.rag.retriever import Retriever
    from app.rag.vector_store import VectorStore
    from app.config import settings


def create_app() -> FastAPI:
    """Create and configure the FastAPI application.

    Returns
    -------
    FastAPI
        Configured FastAPI app instance.
    """
    app = FastAPI(title="Resume RAG Interviewer", version="0.1.0")
    # Ensure database tables are created immediately (tests may not trigger startup events)
    from app.database import init_db
    init_db()


    # CORS configuration
    origins = ["http://localhost:5173", "http://127.0.0.1:5173"]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include API routers
    app.include_router(roles.router)
    app.include_router(sessions.router)

    @app.get("/health")
    async def health_check():
        return {"status": "ok"}

    # Startup event: initialize DB and warm‑up retriever
    @app.on_event("startup")
    async def startup_event():
        # Initialise database tables
        init_db()
        # Warm‑up the vector store / retriever – best effort, ignore any errors
        try:
            if get_retriever is not None:
                retriever = get_retriever()
                # Retriever has an `ensure_loaded` method to lazily build the index
                if hasattr(retriever, "ensure_loaded"):
                    retriever.ensure_loaded()
            else:
                # Manual construction fallback
                default_index_dir = settings.backend_dir / "data" / "vector_store"
                vector_store = VectorStore(index_dir=default_index_dir)
                retriever = Retriever(vector_store=vector_store)
                if hasattr(retriever, "ensure_loaded"):
                    retriever.ensure_loaded()
        except Exception as exc:  # pragma: no cover – defensive
            print(f"[startup] Retriever warm‑up warning: {exc}")

    return app


# Create a module‑level app instance for ASGI servers
app = create_app()


if __name__ == "__main__":
    # Import uvicorn lazily to avoid unnecessary dependency load when imported as a module
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
