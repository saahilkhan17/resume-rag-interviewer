import re
import io
from typing import List, Dict, Any, Set
from pypdf import PdfReader

# ---------------------------------------------------------------------------
# Lexicon definitions
# ---------------------------------------------------------------------------
SKILL_LEXICON: Dict[str, List[str]] = {
    "python": ["python"],
    "java": ["java"],
    "javascript": ["javascript", "js"],
    "typescript": ["typescript", "ts"],
    "sql": ["sql"],
    "fastapi": ["fastapi"],
    "django": ["django"],
    "flask": ["flask"],
    "react": ["react"],
    "node.js": ["node.js", "nodejs", "node"],
    "machine learning": ["machine learning", "ml"],
    "deep learning": ["deep learning", "dl"],
    "tensorflow": ["tensorflow", "tf"],
    "pytorch": ["pytorch", "torch"],
    "scikit-learn": ["scikit-learn", "sklearn"],
    "pandas": ["pandas"],
    "numpy": ["numpy"],
    "natural language processing": ["natural language processing", "nlp"],
    "computer vision": ["computer vision", "cv"],
    "docker": ["docker"],
    "kubernetes": ["kubernetes", "k8s"],
    "aws": ["aws", "amazon web services"],
    "postgresql": ["postgresql", "postgres"],
    "mysql": ["mysql"],
    "mongodb": ["mongodb"],
    "redis": ["redis"],
    "git": ["git"],
    "rest api": ["rest api", "restful api"],
    "graphql": ["graphql"],
    "langchain": ["langchain"],
    "transformers": ["transformers"],
    "data analysis": ["data analysis", "data analytics"],
    "statistics": ["statistics"],
    "spark": ["spark"],
    "airflow": ["airflow"],
    "linux": ["linux"],
    "html": ["html"],
    "css": ["css"],
    "c++": ["c++"],
    "go": ["go"],
    "rust": ["rust"],
}

DOMAIN_KEYWORDS: Dict[str, List[str]] = {
    "machine learning": ["machine learning", "ml", "model", "training", "prediction"],
    "data science": ["data science", "statistics", "analysis", "data mining"],
    "backend development": ["backend", "api", "server", "database", "rest"],
    "web development": ["web", "frontend", "react", "html", "css", "javascript"],
    "natural language processing": ["nlp", "natural language processing", "text", "token"],
    "computer vision": ["computer vision", "cv", "image", "object detection"],
    "devops/cloud": ["docker", "kubernetes", "aws", "ci/cd", "cloud"],
    "databases": ["sql", "postgresql", "mysql", "mongodb", "redis", "database"],
}

TECHNOLOGIES: Set[str] = {
    "fastapi",
    "django",
    "flask",
    "react",
    "node.js",
    "tensorflow",
    "pytorch",
    "scikit-learn",
    "pandas",
    "numpy",
    "docker",
    "kubernetes",
    "aws",
    "postgresql",
    "mysql",
    "mongodb",
    "redis",
    "git",
    "langchain",
    "transformers",
    "spark",
    "airflow",
}

# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def extract_text_from_bytes(data: bytes, filename: str) -> str:
    """Extract plain text from a binary resume file.

    Supported extensions:
        - .pdf  – extracted via pypdf's PdfReader
        - .txt  – UTF‑8 decoded (replace errors)
        - .md   – same as txt
    """
    ext = filename.lower().rsplit(".", 1)[-1]
    if ext == "pdf":
        # PdfReader accepts a file‑like object.
        reader = PdfReader(io.BytesIO(data))
        pages = [page.extract_text() or "" for page in reader.pages]
        return "\n".join(pages)
    if ext in {"txt", "md"}:
        return data.decode("utf-8", errors="replace")
    raise ValueError("unsupported file type")

# ---------------------------------------------------------------------------
# Core parsing logic
# ---------------------------------------------------------------------------

def _find_skills(text: str) -> List[str]:
    lowered = text.lower()
    found: Set[str] = set()
    for canonical, aliases in SKILL_LEXICON.items():
        for alias in aliases:
            # Word‑boundary regex ensures we don't match substrings.
            pattern = rf"\b{re.escape(alias)}\b"
            if re.search(pattern, lowered):
                found.add(canonical)
                break
    return sorted(found)

def _find_domains(text: str) -> List[str]:
    lowered = text.lower()
    domains: List[str] = []
    for domain, keywords in DOMAIN_KEYWORDS.items():
        if any(re.search(rf"\b{re.escape(kw)}\b", lowered) for kw in keywords):
            domains.append(domain)
    return domains

def _extract_years_experience(text: str) -> Any:
    # Look for patterns like "3 years experience", "2+ years", "5 yrs".
    match = re.search(r"(\d+)\s*\+?\s*(?:years?|yrs?)\s+experience", text, re.IGNORECASE)
    if match:
        return int(match.group(1))
    return None

def parse_resume_text(text: str) -> Dict[str, Any]:
    if not text:
        return {
            "skills": [],
            "technologies": [],
            "domains": [],
            "years_experience_hint": None,
        }
    skills = _find_skills(text)
    technologies = [s for s in skills if s in TECHNOLOGIES]
    domains = _find_domains(text)
    years = _extract_years_experience(text)
    return {
        "skills": skills,
        "technologies": technologies,
        "domains": domains,
        "years_experience_hint": years,
    }

def parse_resume_file(data: bytes, filename: str) -> Dict[str, Any]:
    raw_text = extract_text_from_bytes(data, filename)
    parsed = parse_resume_text(raw_text)
    parsed.update({
        "raw_text": raw_text[:20000],
        "text_length": len(raw_text),
    })
    return parsed
