import os
import sys
import tempfile
import importlib
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

@pytest.fixture(scope="session")
def tmp_db_path():
    """Create a temporary SQLite DB file path."""
    tmp_dir = tempfile.mkdtemp()
    db_path = Path(tmp_dir) / "test.db"
    return db_path

@pytest.fixture(scope="session")
def client(tmp_db_path):
    """Create a TestClient with a temporary database.

    Re-imports the application modules after setting the DATABASE_URL
    environment variable to point to a temporary SQLite file.
    """
    # Set env before import
    os.environ["DATABASE_URL"] = f"sqlite:///{tmp_db_path}"

    # Ensure fresh imports of config, database, and main
    modules_to_reload = ["app.config", "app.database", "app.main"]
    for mod in modules_to_reload:
        if mod in sys.modules:
            del sys.modules[mod]

    # Reload config to pick up new env var
    import app.config as config
    importlib.reload(config)

    # Import and reload database to re-create engine with temp path
    import app.database as database
    importlib.reload(database)

    # Initialise DB schema
    database.init_db()

    # Import the FastAPI app
    import app.main as main
    importlib.reload(main)

    # Create TestClient
    client = TestClient(main.app)
    yield client
    # Cleanup will be handled by pytest temporary dir removal

@pytest.fixture
def sample_resume_bytes():
    fixture_path = Path(__file__).parent / "fixtures" / "sample_resume.txt"
    return fixture_path.read_bytes()

@pytest.fixture
def kb_chunks():
    from app.rag.ingestion import load_kb
    from app.config import settings
    return load_kb(settings.kb_dir_path)

@pytest.fixture
def retriever(kb_chunks):
    from app.rag.vector_store import VectorStore
    from app.rag.retriever import Retriever
    import tempfile
    # Temporary index directory
    idx_dir = Path(tempfile.mkdtemp())
    store = VectorStore(index_dir=idx_dir)
    store.build(kb_chunks)
    retr = Retriever(vector_store=store)
    # Ensure loaded (should already be built)
    retr.ensure_loaded()
    return retr
