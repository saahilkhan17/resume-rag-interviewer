import json
import re
from typing import List, Dict, Any

# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------
class QuestionGenerationError(Exception):
    """Raised when question generation cannot produce any grounded questions."""

# ---------------------------------------------------------------------------
# Helper to extract key propositions from a chunk of text
# ---------------------------------------------------------------------------
def extract_key_propositions(chunk_text: str, max_points: int = 3) -> List[str]:
    """Return up to ``max_points`` salient sentences from ``chunk_text``.

    Sentences are scored primarily by length (prefer 60‑220 characters) and
    heuristically by the presence of domain‑specific keywords.
    """
    # Simple sentence splitter – split on punctuation followed by space
    sentences = re.split(r"(?<=[.!?])\s+", chunk_text.strip())
    keywords = [
        "model",
        "algorithm",
        "trade‑off",
        "error",
        "rate",
        "loss",
        "index",
        "query",
        "token",
        "layer",
        "training",
        "prediction",
        "performance",
    ]
    def score(sent: str) -> int:
        length = len(sent)
        if 60 <= length <= 220:
            length_score = 10
        elif length < 60:
            length_score = 5
        else:
            length_score = 2
        kw_score = sum(1 for kw in keywords if re.search(rf"\\b{re.escape(kw)}\\b", sent, re.IGNORECASE))
        return length_score + kw_score * 2
    scored = sorted(((score(s), s) for s in sentences if s), reverse=True)
    top = [s.strip().lstrip("# ").strip() for _, s in scored[:max_points]]
    return top

# ---------------------------------------------------------------------------
# Grounded fallback generator – produces questions without LLM
# ---------------------------------------------------------------------------
class GroundedFallbackGenerator:
    def __init__(self):
        self.difficulty_cycle = ["medium", "medium", "hard", "easy", "medium"]
        self.cycle_index = 0

    def _next_difficulty(self) -> str:
        d = self.difficulty_cycle[self.cycle_index % len(self.difficulty_cycle)]
        self.cycle_index += 1
        return d

    def generate(
        self,
        chunks: List[Dict[str, Any]],
        parsed_profile: Dict[str, Any],
        role: str,
        num_questions: int = 5,
    ) -> List[Dict[str, Any]]:
        if not chunks:
            raise QuestionGenerationError(
                "No relevant knowledge-base content found for this role and resume; cannot generate grounded questions."
            )
        skills = parsed_profile.get("skills", [])
        skill_or_role = skills if skills else [role]
        questions: List[Dict[str, Any]] = []
        for i in range(num_questions):
            chunk = chunks[i % len(chunks)]
            chunk_id = chunk.get("chunk_id")
            chunk_text = chunk.get("text", "") or ""
            propositions = extract_key_propositions(chunk_text, max_points=1)
            proposition = propositions[0] if propositions else ""
            topics = chunk.get("topics") or []
            # --- skill relevance scoring ---
            ignore_words = {"learning", "data", "api"}
            def tokenize(txt: str) -> List[str]:
                return [t for t in re.split(r"\W+", txt.lower()) if len(t) >= 2 and t not in ignore_words]
            # Build searchable text from chunk text, topics, and heading
            search_parts = [chunk_text]
            if topics:
                search_parts.append(" ".join(topics))
            else:
                heading = chunk.get("heading", "")
                search_parts.append(heading)
            search_text = " ".join(search_parts).lower()
            search_tokens = set(tokenize(search_text))
            best_skill = None
            best_score = -1
            for skill_candidate in skill_or_role:
                skill_tokens = tokenize(skill_candidate)
                score = sum(1 for tok in skill_tokens if tok in search_tokens)
                if score > best_score:
                    best_score = score
                    best_skill = skill_candidate
            if best_score == 0:
                best_skill = None
            # Determine concept/topic for the question
            if topics:
                concept = topics[0]
            else:
                heading = chunk.get("heading", "")
                concept = heading.lstrip("#").strip() if heading else role
            skill_placeholder = best_skill if best_skill is not None else role
            # Alternate question forms by chunk index
            if i % 2 == 0:
                # Form A
                if proposition:
                    text = f"For this {role} interview: {proposition} — how would you apply this in a real project?"
                else:
                    text = f"For this {role} interview: Explain {concept} and how you would apply it in a real project."
            else:
                # Form B – explain style
                if proposition:
                    text = f"For this {role} interview: Explain this idea in your own words and give an example: {proposition}"
                else:
                    text = f"For this {role} interview: Explain {concept} in your own words."
            topic_val = concept
            questions.append({
                "text": text,
                "topic": topic_val,
                "difficulty": self._next_difficulty(),
                "source_chunks": [chunk_id] if chunk_id else [],
                "retrieval_query": chunk.get("retrieval_query", ""),
            })
        return questions

# ---------------------------------------------------------------------------
# Gemini‑based generator – uses Google Gemini if API key provided
# ---------------------------------------------------------------------------
class GeminiQuestionGenerator:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self._gemini = None

    def _ensure_client(self):
        if self._gemini is None:
            import google.generativeai as genai
            genai.configure(api_key=self.api_key)
            self._gemini = genai.GenerativeModel("gemini-1.5-flash")

    def generate(
        self,
        chunks: List[Dict[str, Any]],
        parsed_profile: Dict[str, Any],
        role: str,
        num_questions: int = 5,
    ) -> List[Dict[str, Any]]:
        self._ensure_client()
        if not chunks:
            raise QuestionGenerationError(
                "No relevant knowledge-base content found for this role and resume; cannot generate grounded questions."
            )
        # Build prompt
        skills = ", ".join(parsed_profile.get("skills", [])) or "(none)"
        chunk_strs = []
        for idx, chunk in enumerate(chunks[: num_questions * 2]):
            cid = chunk.get("chunk_id", f"c{idx}")
            txt = chunk.get("text", "")
            chunk_strs.append(f"<chunk id='{cid}'>\n{txt}\n</chunk>")
        chunk_section = "\n\n".join(chunk_strs)
        prompt = (
            f"You are given several knowledge‑base chunks and a candidate's resume skills. "
            f"Produce exactly {num_questions} JSON objects, each with keys: text, topic, difficulty, source_chunks (list of chunk ids), retrieval_query (use the query that retrieved the chunk). "
            f"The questions must be grounded: each must reference at least one skill from the resume (or the role name) and at least one concept from a chunk. "
            f"Vary the question forms and difficulty levels (easy, medium, hard). Return a JSON array without any surrounding markdown.\n\n"
            f"Resume skills: {skills}\nRole: {role}\n\nChunks:\n{chunk_section}\n"
        )
        response = self._gemini.generate_content(prompt)
        text = response.text.strip()
        if text.startswith("```json"):
            text = text[len("```json"):].strip()
        if text.startswith("```"):
            text = text[len("```"):].strip()
        if text.endswith("```"):
            text = text[: -len("```")].strip()
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError as e:
            raise QuestionGenerationError(f"Failed to parse Gemini response as JSON: {e}\nRaw response: {text}")
        # Validate items
        valid = []
        chunk_ids = {c.get("chunk_id") for c in chunks}
        for item in parsed:
            if not isinstance(item, dict):
                continue
            src = item.get("source_chunks", [])
            if not src or not any(s in chunk_ids for s in src):
                continue
            if all(k in item for k in ("text", "topic", "difficulty", "source_chunks", "retrieval_query")):
                valid.append(item)
        if len(valid) < 1:
            raise QuestionGenerationError("Gemini did not return any valid grounded questions.")
        return valid[:num_questions]

def get_generator(api_key: str | None):
    if api_key:
        return GeminiQuestionGenerator(api_key)
    return GroundedFallbackGenerator()

def generate_questions(
    chunks: List[Dict[str, Any]],
    parsed_profile: Dict[str, Any],
    role: str,
    num_questions: int = 5,
    api_key: str | None = None,
) -> List[Dict[str, Any]]:
    generator = get_generator(api_key)
    try:
        return generator.generate(chunks, parsed_profile, role, num_questions)
    except Exception as exc:
        if isinstance(generator, GeminiQuestionGenerator):
            fallback = GroundedFallbackGenerator()
            try:
                return fallback.generate(chunks, parsed_profile, role, num_questions)
            except QuestionGenerationError:
                raise
        raise