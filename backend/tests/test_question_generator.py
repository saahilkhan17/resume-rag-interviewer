import pytest
from app.rag.question_generator import (
    generate_questions,
    get_generator,
    GroundedFallbackGenerator,
    GeminiQuestionGenerator,
    QuestionGenerationError,
)

# Sample chunk data structure similar to what VectorStore.search returns
sample_chunks = [
    {
        "chunk_id": "c1",
        "text": "You should know about gradient descent and its convergence.",
        "topics": ["gradient descent"],
        "heading": "# Gradient Descent",
        "roles": ["ai-ml-engineer"],
        "retrieval_query": "gradient descent",
    },
    {
        "chunk_id": "c2",
        "text": "Understanding REST APIs is crucial for backend development.",
        "topics": ["rest api"],
        "heading": "# REST APIs",
        "roles": ["backend-engineer"],
        "retrieval_query": "rest api",
    },
]

@pytest.mark.parametrize("api_key", [None, "dummy_key"])
def test_get_generator(api_key):
    gen = get_generator(api_key)
    if api_key:
        assert isinstance(gen, GeminiQuestionGenerator)
    else:
        assert isinstance(gen, GroundedFallbackGenerator)

def test_fallback_generator_basic():
    gen = GroundedFallbackGenerator()
    # Use only one chunk to test cycling
    questions = gen.generate(
        chunks=[sample_chunks[0]],
        parsed_profile={"skills": []},
        role="ai-ml-engineer",
        num_questions=3,
    )
    assert len(questions) == 3
    for q in questions:
        # source_chunks should point to the provided chunk id
        assert q["source_chunks"] == ["c1"]
        # retrieval_query present
        assert q["retrieval_query"] == "gradient descent"
        # text contains role wording
        assert "For this ai-ml-engineer interview" in q["text"]
        # topic derived from chunk topic
        assert q["topic"] in ["gradient descent", "ai-ml-engineer"]

def test_fallback_generator_skill_overlap():
    gen = GroundedFallbackGenerator()
    # Profile includes a skill that appears in chunk topics
    profile = {"skills": ["gradient descent", "docker"]}
    questions = gen.generate(
        chunks=[sample_chunks[0]],
        parsed_profile=profile,
        role="ai-ml-engineer",
        num_questions=1,
    )
    q = questions[0]
    # Best skill should be "gradient descent"
    assert "gradient descent" in q["text"].lower()

def test_fallback_generator_no_chunks_raises():
    gen = GroundedFallbackGenerator()
    with pytest.raises(QuestionGenerationError):
        gen.generate(chunks=[], parsed_profile={"skills": []}, role="backend-engineer", num_questions=2)

def test_generate_questions_uses_fallback_when_no_api_key(monkeypatch):
    # Ensure that passing api_key=None uses fallback and does not attempt Gemini call
    # Monkeypatch Gemini generator to raise if instantiated
    class DummyGemini:
        def __init__(self, *args, **kwargs):
            raise AssertionError("Gemini should not be instantiated")
    monkeypatch.setattr("app.rag.question_generator.GeminiQuestionGenerator", DummyGemini, raising=False)
    questions = generate_questions(
        chunks=[sample_chunks[1]],
        parsed_profile={"skills": []},
        role="backend-engineer",
        num_questions=2,
        api_key=None,
    )
    assert len(questions) == 2
    for q in questions:
        assert q["source_chunks"] == ["c2"]
