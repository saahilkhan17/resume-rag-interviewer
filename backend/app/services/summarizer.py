import re
from typing import List, Dict, Any

# ---------------------------------------------------------------------------
# Simple stopword set – can be extended as needed
# ---------------------------------------------------------------------------
STOPWORDS = {
    "the",
    "and",
    "or",
    "a",
    "an",
    "of",
    "in",
    "to",
    "for",
    "with",
    "on",
    "by",
    "as",
    "at",
    "is",
    "it",
    "this",
    "that",
    "from",
}


def _tokenise(text: str) -> set[str]:
    """Return a set of lowercase alphanumeric words, minus stopwords."""
    words = re.findall(r"[a-zA-Z0-9]+", text.lower())
    return {w for w in words if w not in STOPWORDS}


def key_points_from_text(text: str) -> List[str]:
    """Extract up to five salient sentences from *text*.

    Sentences are kept if their length falls between 40 and 250 characters.
    The function returns the first‑matching sentences after normalising whitespace.
    """
    if not text:
        return []
    # split on sentence terminators followed by whitespace
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    candidates = [s.strip() for s in sentences if 40 <= len(s.strip()) <= 250]
    return candidates[:5]


def assess_answer(question_text: str, answer_text: str, source_chunk_texts: List[str]) -> Dict[str, Any]:
    """Assess *answer_text* against *source_chunk_texts*.

    Returns a dictionary with an overall *assessment* string, a list of
    *key_points_covered* and a list of *key_points_missed*.
    """
    # Normalise answer
    answer = answer_text.strip()
    if not answer:
        # empty answer – everything is missed
        key_points = []
        for chunk in source_chunk_texts:
            key_points.extend(key_points_from_text(chunk))
        return {
            "assessment": "No answer provided.",
            "key_points_covered": [],
            "key_points_missed": key_points,
        }

    answer_tokens = _tokenise(answer)
    # Extract key points from each source chunk
    all_key_points: List[str] = []
    for chunk in source_chunk_texts:
        all_key_points.extend(key_points_from_text(chunk))

    covered: List[str] = []
    missed: List[str] = []
    for kp in all_key_points:
        kp_tokens = _tokenise(kp)
        if answer_tokens & kp_tokens:
            covered.append(kp)
        else:
            missed.append(kp)

    # Determine assessment tier
    if len(answer) < 20:
        tier = "Weak"
    elif covered and not missed:
        tier = "Strong"
    elif covered:
        tier = "Partial"
    else:
        tier = "Weak"

    if tier == "Strong":
        assessment = "Strong answer: covers the key ideas."
    elif tier == "Partial":
        assessment = (
            "Partial answer: covers some key ideas; misses "
            f"{', '.join(missed[:3])}{'...' if len(missed) > 3 else ''}."
        )
    else:
        assessment = "Weak / missing answer: does not address the key ideas."

    return {
        "assessment": assessment,
        "key_points_covered": covered,
        "key_points_missed": missed,
    }


def build_summary(
    session_role: str,
    questions: List[Dict[str, Any]],
    answers: Dict[str, str],
    chunk_texts_by_question: Dict[str, List[str]],
) -> Dict[str, Any]:
    """Construct a summary payload matching ``SummaryContent`` schema.

    *questions* is a list of dicts that contain at least ``id``, ``text`` and ``topic``.
    *answers* maps question ``id`` → answer text.
    *chunk_texts_by_question* maps question ``id`` → list of source chunk texts.
    """
    per_question: List[Dict[str, Any]] = []
    strengths: List[str] = []
    gaps: List[str] = []
    topics_covered_set: set[str] = set()

    for q in questions:
        qid = q.get("id")
        qtext = q.get("text", "")
        topic = q.get("topic", "")
        answer = answers.get(qid, "").strip()
        source_chunks = chunk_texts_by_question.get(qid, [])
        assessment_data = assess_answer(qtext, answer, source_chunks)
        assessment = assessment_data["assessment"]
        covered = assessment_data["key_points_covered"]
        missed = assessment_data["key_points_missed"]

        if assessment.startswith("Strong"):
            strengths.append(topic)
            topics_covered_set.add(topic)
        else:
            gaps.append(topic)

        per_question.append(
            {
                "question_id": qid,
                "question": qtext,
                "answer": answer,
                "assessment": assessment,
                "key_points_covered": covered,
                "key_points_missed": missed,
            }
        )

    # Overall assessment – a brief 2‑3 sentence summary
    total = len(questions)
    strong_cnt = len(strengths)
    overall = (
        f"The interview covered {total} questions for a {session_role} role. "
        f"{strong_cnt} of them were answered strongly, "
        f"with the remaining {total - strong_cnt} needing improvement."
    )

    # Recommended next steps – derive at least two actionable items from gaps
    recommended_next_steps: List[str] = []
    for topic in gaps[:2]:
        recommended_next_steps.append(
            f"Review the {topic} area and prepare concrete examples or projects to discuss."
        )
    if not recommended_next_steps:
        recommended_next_steps.append("Continue building on the strong topics and deepen knowledge where gaps were identified.")

    summary = {
        "overall_assessment": overall,
        "strengths": strengths,
        "gaps": gaps,
        "per_question": per_question,
        "topics_covered": list(topics_covered_set),
        "recommended_next_steps": recommended_next_steps,
    }
    return summary
