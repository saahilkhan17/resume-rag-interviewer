"""Roles API router.
Provides GET /api/roles endpoint returning available roles with KB chunk counts.
"""

from fastapi import APIRouter, HTTPException
from functools import lru_cache
from typing import List

from app import schemas
from app.config import settings
from app.rag import ingestion

router = APIRouter()

# Define static role data
ROLES = [
    {
        "id": "ai-ml-engineer",
        "label": "AI/ML Engineer",
        "description": "Interviews on machine learning, deep learning and applied ML.",
    },
    {
        "id": "data-science",
        "label": "Data Science / Applied ML",
        "description": "Interviews on statistics, modelling and evaluation.",
    },
    {
        "id": "backend-engineer",
        "label": "Backend Engineer",
        "description": "Interviews on APIs, databases and backend systems.",
    },
]

@lru_cache(maxsize=1)
def _load_chunks() -> List[dict]:
    """Load KB chunks once, caching the result.
    Returns an empty list on any exception to keep the API alive.
    """
    try:
        return ingestion.load_kb(settings.kb_dir_path)
    except Exception as exc:
        # Log warning (print) and return empty list
        print(f"[roles] Warning while loading KB: {exc}")
        return []

def _count_chunks_by_role(role_id: str) -> int:
    """Count chunks that have the given role in their metadata.
    Handles both dicts and dataclass Chunk objects.
    """
    chunks = _load_chunks()
    count = 0
    for c in chunks:
        # Try attribute first (dataclass), fallback to dict
        roles = getattr(c, "roles", None)
        if roles is None and isinstance(c, dict):
            roles = c.get("roles", [])
        if roles and role_id in roles:
            count += 1
    return count

@router.get("/api/roles", response_model=List[schemas.RoleOut])
def list_roles() -> List[schemas.RoleOut]:
    """Return the list of roles with the number of KB chunks for each role.
    Any loading error results in a count of 0 for all roles.
    """
    result: List[schemas.RoleOut] = []
    for r in ROLES:
        try:
            cnt = _count_chunks_by_role(r["id"])
        except Exception:
            cnt = 0
        result.append(
            schemas.RoleOut(
                id=r["id"],
                label=r["label"],
                description=r["description"],
                kb_chunks=cnt,
            )
        )
    return result
