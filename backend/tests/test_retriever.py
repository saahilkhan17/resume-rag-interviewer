import pytest
from app.rag.retriever import Retriever
from app.rag.vector_store import VectorStore
from app.rag.ingestion import load_kb
from app.config import settings
import tempfile

@pytest.fixture
def retriever_with_kb(kb_chunks):
    # Build index in temporary directory
    idx_dir = tempfile.mkdtemp()
    store = VectorStore(index_dir=idx_dir)
    store.build(kb_chunks)
    retr = Retriever(vector_store=store)
    retr.ensure_loaded()
    return retr

def test_retrieve_top_result(retriever_with_kb):
    # Assuming gradient-descent.md exists in KB and contains "gradient descent"
    results = retriever_with_kb.retrieve("gradient descent", role="ai-ml-engineer", top_k=5)
    assert results, "Should return at least one result"
    top = results[0]
    assert "gradient descent" in top["text"].lower()
    assert top["score"] >= results[-1]["score"]

def test_role_scoping(retriever_with_kb):
    # Backend role should not retrieve ai-ml specific chunks (e.g., gradient descent)
    ml_results = retriever_with_kb.retrieve("gradient descent", role="backend-engineer", top_k=5)
    # Ensure none of the results have role "ai-ml-engineer" only if chunk_roles include that role
    # Ensure every result includes 'backend-engineer' role
    for r in ml_results:
        roles = r.get("roles", [])
        # Must have backend-engineer in roles
        assert "backend-engineer" in roles
        # Must not be a chunk with only ai-ml-engineer role
        if set(roles) == {"ai-ml-engineer"}:
            pytest.fail(f"Chunk {r.get('chunk_id')} incorrectly scoped to only ai-ml-engineer")
def test_empty_kb_dir(tmp_path, monkeypatch):
    empty_dir = tmp_path / "empty_kb"
    empty_dir.mkdir()
    # Monkeypatch settings.kb_dir to point to empty_dir
    monkeypatch.setattr(settings, "kb_dir", str(empty_dir))
    # Build a retriever with empty KB
    store = VectorStore(index_dir=tmp_path / "empty_index")
    store.build([])
    retr = Retriever(vector_store=store)
    results = retr.retrieve("anything", role="ai-ml-engineer", top_k=3)
    assert results == []

def test_retrieve_for_topics_deduplication(retriever_with_kb):
    # Pick two topics that will likely retrieve same chunk
    topics = ["gradient descent", "gradient"]
    results = retriever_with_kb.retrieve_for_topics(topics, role="ai-ml-engineer", top_k_per_topic=2)
    ids = [r["chunk_id"] for r in results]
    # Ensure no duplicate ids
    assert len(ids) == len(set(ids))
