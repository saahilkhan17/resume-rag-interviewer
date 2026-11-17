# Tests for summarizer service functions

import pytest
from app.services.summarizer import assess_answer, build_summary

# Helper chunk texts with identifiable key points
def sample_chunks():
    return [
        "The system uses a vector store to retrieve relevant documents. It supports fast search.",
        "Embedding generation is performed using transformer models. These models produce dense vectors.",
    ]

def test_assess_answer_strong_and_weak():
    # Strong: answer includes all key points (simple exact copy)
    source = sample_chunks()
    # Combine key sentences to ensure coverage
    answer_strong = " ".join(source)
    result_strong = assess_answer("question", answer_strong, source)
    assert result_strong["assessment"].startswith("Strong")
    assert result_strong["key_points_covered"]
    assert not result_strong["key_points_missed"]

    # Weak: empty answer
    result_weak = assess_answer("question", "", source)
    assert result_weak["assessment"].startswith(("Weak", "No answer"))
    # All key points should be missed
    total_kps = sum(len([kp for kp in assess_answer("q", "", [c])["key_points_missed"]]) for c in source)
    # Since assess_answer returns all key points when answer empty, we compare lengths
    assert len(result_weak["key_points_missed"]) > 0
    assert not result_weak["key_points_covered"]

def test_assess_answer_partial():
    source = sample_chunks()
    # Provide only the first sentence of the first chunk
    partial_answer = "The system uses a vector store to retrieve relevant documents."
    result = assess_answer("question", partial_answer, source)
    # Should be Partial (covered some but missed others)
    assert result["assessment"].startswith("Partial")
    assert result["key_points_covered"]
    assert result["key_points_missed"]

def test_build_summary_structure_and_empty_answers():
    # Define three questions with topics
    questions = [
        {"id": "q1", "text": "Q1?", "topic": "topic1"},
        {"id": "q2", "text": "Q2?", "topic": "topic2"},
        {"id": "q3", "text": "Q3?", "topic": "topic3"},
    ]
    # Provide answers for only first two, third empty
    answers = {
        "q1": "Answer covering all key points.",
        "q2": "",  # empty answer
        "q3": "Partial answer.",
    }
    # Use same chunks for each question for simplicity
    chunk_texts_by_question = {
        "q1": sample_chunks(),
        "q2": sample_chunks(),
        "q3": sample_chunks(),
    }
    summary = build_summary("candidate", questions, answers, chunk_texts_by_question)
    # Verify overall keys exist
    for key in [
        "overall_assessment",
        "strengths",
        "gaps",
        "per_question",
        "topics_covered",
        "recommended_next_steps",
    ]:
        assert key in summary
    # per_question length should match number of questions
    assert len(summary["per_question"]) == len(questions)
    # strengths should contain topic1 if assessment was Strong, else not
    # We'll infer based on our dummy answer – it likely results in Weak/Partial, so strengths may be empty
    # Ensure gaps include topics with non‑strong assessments
    assert set(summary["gaps"]).issuperset({"topic1", "topic2", "topic3"})
    # recommended_next_steps should be non‑empty
    assert summary["recommended_next_steps"]

def test_build_summary_all_empty_answers():
    questions = [
        {"id": "q1", "text": "Q1?", "topic": "t1"},
        {"id": "q2", "text": "Q2?", "topic": "t2"},
    ]
    answers = {"q1": "", "q2": ""}
    chunk_texts_by_question = {"q1": sample_chunks(), "q2": sample_chunks()}
    summary = build_summary("candidate", questions, answers, chunk_texts_by_question)
    # All topics should appear in gaps because no strong answers
    assert set(summary["gaps"]) == {"t1", "t2"}
    # Strengths should be empty
    assert not summary["strengths"]
    # recommended_next_steps should still contain at least two items derived from gaps
    assert len(summary["recommended_next_steps"]) >= 2
