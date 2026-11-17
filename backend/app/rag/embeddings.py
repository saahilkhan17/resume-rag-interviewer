from typing import Any


class TfidfEmbedder:
    def __init__(self, stop_words: str = "english", max_features: int = 5000):
        self.stop_words = stop_words
        self.max_features = max_features
        self.vectorizer: Any = None

    def fit(self, texts: list[str]) -> "TfidfEmbedder":
        if not texts:
            raise ValueError("texts cannot be empty")
        from sklearn.feature_extraction.text import TfidfVectorizer

        self.vectorizer = TfidfVectorizer(
            stop_words=self.stop_words,
            max_features=self.max_features,
        )
        self.vectorizer.fit(texts)
        return self

    def transform(self, texts: list[str]) -> Any:
        if self.vectorizer is None:
            raise RuntimeError("TfidfEmbedder must be fit before transforming")
        if not texts:
            raise ValueError("texts cannot be empty")
        return self.vectorizer.transform(texts)

    def fit_transform(self, texts: list[str]) -> Any:
        if not texts:
            raise ValueError("texts cannot be empty")
        from sklearn.feature_extraction.text import TfidfVectorizer

        self.vectorizer = TfidfVectorizer(
            stop_words=self.stop_words,
            max_features=self.max_features,
        )
        return self.vectorizer.fit_transform(texts)


def cosine_similarity_scores(query_vec: Any, doc_matrix: Any) -> list[float]:
    if doc_matrix is None or (hasattr(doc_matrix, "shape") and doc_matrix.shape[0] == 0):
        return []
    from sklearn.metrics.pairwise import cosine_similarity

    sim = cosine_similarity(query_vec, doc_matrix)
    if sim.ndim == 2 and sim.shape[0] > 0:
        return [float(x) for x in sim[0]]
    return [float(x) for x in sim.flatten()]


class GeminiEmbedder:
    def __init__(self, api_key: str = "", model: str = "models/text-embedding-004"):
        self.api_key = api_key
        self.model = model

    def _ensure_configured(self) -> None:
        if not self.api_key:
            raise RuntimeError("GEMINI_API_KEY is required to use GeminiEmbedder")
        import google.generativeai as genai

        genai.configure(api_key=self.api_key)

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        self._ensure_configured()
        import google.generativeai as genai

        result = genai.embed_content(
            model=self.model,
            content=texts,
            task_type="retrieval_document",
        )
        return result.get("embedding", [])

    def embed_query(self, query: str) -> list[float]:
        self._ensure_configured()
        import google.generativeai as genai

        result = genai.embed_content(
            model=self.model,
            content=query,
            task_type="retrieval_query",
        )
        return result.get("embedding", [])
