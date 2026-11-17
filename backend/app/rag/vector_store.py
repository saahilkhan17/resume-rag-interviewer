import json
from pathlib import Path
import pickle
from typing import Any
from app.rag.chunker import Chunk
from app.rag.embeddings import TfidfEmbedder, cosine_similarity_scores


class VectorStore:
    def __init__(self, index_dir: Path):
        self.index_dir = Path(index_dir)
        self.index_file = self.index_dir / "index.json"
        self.tfidf_file = self.index_dir / "tfidf.pkl"
        self.chunks: list[dict[str, Any]] = []
        self.vectorizer: Any = None
        self.doc_matrix: Any = None

    def build(self, chunks: list[Chunk]) -> None:
        self.index_dir.mkdir(parents=True, exist_ok=True)
        if not chunks:
            self.chunks = []
            self.vectorizer = None
            self.doc_matrix = None
            self.index_file.write_text("[]", encoding="utf-8")
            if self.tfidf_file.exists():
                self.tfidf_file.unlink()
            return

        texts = [c.text for c in chunks]
        embedder = TfidfEmbedder()
        self.doc_matrix = embedder.fit_transform(texts)
        self.vectorizer = embedder.vectorizer

        self.chunks = [
            {
                "chunk_id": c.id,
                "text": c.text,
                "source": c.source,
                "heading": c.heading,
                "roles": c.roles,
                "topics": c.topics,
            }
            for c in chunks
        ]

        self.index_file.write_text(
            json.dumps(self.chunks, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        with open(self.tfidf_file, "wb") as f:
            pickle.dump(
                {"vectorizer": self.vectorizer, "doc_matrix": self.doc_matrix},
                f,
            )

    def load(self) -> bool:
        if not self.index_file.exists() or not self.tfidf_file.exists():
            return False
        try:
            with open(self.index_file, "r", encoding="utf-8") as f:
                self.chunks = json.load(f)
            with open(self.tfidf_file, "rb") as f:
                data = pickle.load(f)
                self.vectorizer = data.get("vectorizer")
                self.doc_matrix = data.get("doc_matrix")
            if (
                not isinstance(self.chunks, list)
                or self.vectorizer is None
                or self.doc_matrix is None
            ):
                return False
            return True
        except Exception:
            return False

    @property
    def is_empty(self) -> bool:
        return (
            len(self.chunks) == 0
            or self.vectorizer is None
            or self.doc_matrix is None
        )

    @property
    def chunk_count(self) -> int:
        return len(self.chunks)

    def search(
        self,
        query: str,
        top_k: int = 5,
        roles: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        if self.is_empty or not query or not query.strip():
            return []

        query_vec = self.vectorizer.transform([query])
        scores = cosine_similarity_scores(query_vec, self.doc_matrix)

        roles_filter = set(roles) if roles else None

        candidates = []
        for i, chunk in enumerate(self.chunks):
            if roles_filter:
                chunk_roles = set(chunk.get("roles", []))
                if not chunk_roles.intersection(roles_filter):
                    continue

            score = float(scores[i]) if i < len(scores) else 0.0
            candidates.append(
                {
                    "chunk_id": chunk["chunk_id"],
                    "text": chunk["text"],
                    "source": chunk["source"],
                    "heading": chunk["heading"],
                    "topics": chunk.get("topics", []),
                    "roles": chunk.get("roles", []),
                    "score": score,
                }
            )

        candidates.sort(key=lambda x: x["score"], reverse=True)
        return candidates[:top_k]

    def get_chunk_text(self, chunk_id: str) -> str:
        """Retrieve the raw text for a given chunk ID.

        Returns an empty string if the chunk is not found.
        """
        for chunk in self.chunks:
            if chunk.get("chunk_id") == chunk_id:
                return chunk.get("text", "")
        return ""
