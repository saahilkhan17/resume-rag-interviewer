from typing import Any, Optional
from app.config import settings
from app.rag.vector_store import VectorStore


class Retriever:
    def __init__(self, vector_store: Optional[VectorStore] = None):
        if vector_store is None:
            default_index_dir = settings.backend_dir / "data" / "vector_store"
            self.vector_store = VectorStore(index_dir=default_index_dir)
        else:
            self.vector_store = vector_store

    def ensure_loaded(self) -> None:
        if self.vector_store.is_empty:
            if not self.vector_store.load() or self.vector_store.is_empty:
                from app.rag.ingestion import build_index

                self.vector_store = build_index(
                    kb_dir=settings.kb_dir_path,
                    index_dir=self.vector_store.index_dir,
                )

    def retrieve(
        self,
        query: str,
        role: str,
        top_k: int = 5,
    ) -> list[dict[str, Any]]:
        self.ensure_loaded()
        if not query or not query.strip():
            return []
        roles = [role] if role else None
        return self.vector_store.search(query=query, top_k=top_k, roles=roles)

    def retrieve_for_topics(
        self,
        topics: list[str],
        role: str,
        top_k_per_topic: int = 2,
    ) -> list[dict[str, Any]]:
        self.ensure_loaded()
        if not topics:
            return []

        deduped: list[dict[str, Any]] = []
        seen_chunk_ids: set[str] = set()

        for topic in topics:
            if not topic or not topic.strip():
                continue
            topic_results = self.retrieve(
                query=topic,
                role=role,
                top_k=top_k_per_topic,
            )
            for chunk in topic_results:
                cid = chunk.get("chunk_id", "")
                if cid and cid not in seen_chunk_ids:
                    seen_chunk_ids.add(cid)
                    deduped.append(chunk)

        return deduped
