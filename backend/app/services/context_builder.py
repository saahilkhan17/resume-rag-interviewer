import re
from typing import List, Dict, Any

# ---------------------------------------------------------------------------
# Role definitions
# ---------------------------------------------------------------------------
ROLE_TOPICS: Dict[str, List[str]] = {
    "ai-ml-engineer": [
        "machine learning",
        "deep learning",
        "neural networks",
        "gradient descent",
        "evaluation metrics",
        "overfitting",
        "RAG",
        "NLP embeddings",
    ],
    "data-science": [
        "supervised learning",
        "decision trees",
        "evaluation metrics",
        "unsupervised clustering",
        "overfitting",
        "statistics",
    ],
    "backend-engineer": [
        "REST APIs",
        "FastAPI",
        "databases",
        "SQL",
        "authentication",
        "JWT",
        "async queues",
        "caching",
    ],
}

ROLE_LABELS: Dict[str, str] = {
    "ai-ml-engineer": "AI/ML Engineer",
    "data-science": "Data Science / Applied ML",
    "backend-engineer": "Backend Engineer",
}

# ---------------------------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------------------------

def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().lower())

def build_queries(parsed_profile: Dict[str, Any], role: str, max_queries: int = 5) -> List[str]:
    """Create a list of retrieval queries based on resume skills and role topics.

    - Order skills by relevance to the role's topics before pairing.
    - Pair each top skill with each role‑specific topic.
    - Add pure topic‑only queries.
    - Deduplicate and truncate to ``max_queries``.
    """
    skills = parsed_profile.get("skills", [])
    topics = ROLE_TOPICS.get(role, [])

    # Tokenise helper (ignore generic words)
    ignore_words = {"learning", "data", "api"}
    def tokenize(txt: str) -> List[str]:
        return [t for t in re.split(r"\W+", txt.lower()) if len(t) >= 2 and t not in ignore_words]

    # Score each skill by overlap with role topics
    skill_scores = []
    for skill in skills:
        score = 0
        skill_tokens = set(tokenize(skill))
        for topic in topics:
            topic_tokens = set(tokenize(topic))
            score += len(skill_tokens & topic_tokens)
        skill_scores.append((score, skill))
    # Stable sort by descending score (keep original order for ties)
    skill_scores.sort(key=lambda x: -x[0])
    ordered_skills = [s for _, s in skill_scores]

    queries: List[str] = []
    if ordered_skills:
        for skill in ordered_skills[:5]:  # limit to top few skills for brevity
            for topic in topics:
                queries.append(f"{skill} {topic}")
    # topic‑only queries
    queries.extend(topics)

    # deduplicate while preserving order
    seen = set()
    unique_queries = []
    for q in queries:
        norm = _normalize(q)
        if norm not in seen:
            seen.add(norm)
            unique_queries.append(q)
        if len(unique_queries) >= max_queries:
            break
    return unique_queries

    """Create a list of retrieval queries based on resume skills and role topics.

    - Pair each top skill with each role‑specific topic.
    - Add pure topic‑only queries.
    - Deduplicate and truncate to ``max_queries``.
    """
    skills = parsed_profile.get("skills", [])
    topics = ROLE_TOPICS.get(role, [])
    queries: List[str] = []

    if skills:
        for skill in skills[:5]:  # limit to top few skills for brevity
            for topic in topics:
                queries.append(f"{skill} {topic}")
    # topic‑only queries
    queries.extend(topics)

    # deduplicate while preserving order
    seen = set()
    unique_queries = []
    for q in queries:
        norm = _normalize(q)
        if norm not in seen:
            seen.add(norm)
            unique_queries.append(q)
        if len(unique_queries) >= max_queries:
            break
    return unique_queries

def select_topics(parsed_profile: Dict[str, Any], role: str) -> List[str]:
    """Select up to five topics that best match the resume.

    Preference order:
        1. Topics whose keywords intersect with resume ``skills`` or ``domains``.
        2. Remaining role topics in defined order.
    """
    topics = ROLE_TOPICS.get(role, [])
    skills = set(parsed_profile.get("skills", []))
    domains = set(parsed_profile.get("domains", []))
    selected: List[str] = []

    # First pass – relevance
    for t in topics:
        tokens = set(_normalize(t).split())
        if tokens & skills or tokens & domains:
            selected.append(t)
        if len(selected) >= 5:
            return selected
    # Second pass – fill up
    for t in topics:
        if t not in selected:
            selected.append(t)
        if len(selected) >= 5:
            break
    return selected

def build_context(
    parsed_profile: Dict[str, Any],
    role: str,
    retriever: Any,
    top_k_per_query: int = 2,
) -> Dict[str, Any]:
    """Retrieve knowledge‑base chunks and assemble a context dict.

    The ``retriever`` is expected to expose a ``retrieve(query: str, top_k: int)``
    method returning a list of dicts, each containing at least ``chunk_id`` and
    ``content``.
    """
    queries = build_queries(parsed_profile, role)
    topics = select_topics(parsed_profile, role)
    seen_ids = set()
    chunks: List[Dict[str, Any]] = []
    for q in queries:
        for chunk in retriever.retrieve(q, role, top_k=top_k_per_query):
            # Stamp the retrieval query onto the chunk for traceability
            chunk_copy = dict(chunk)
            chunk_copy["retrieval_query"] = q
            cid = chunk_copy.get("chunk_id")
            if cid and cid not in seen_ids:
                seen_ids.add(cid)
                chunks.append(chunk_copy)
    return {"queries": queries, "topics": topics, "chunks": chunks}
