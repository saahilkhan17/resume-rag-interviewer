# Tests for data persistence across FastAPI client instances

import pytest
from fastapi.testclient import TestClient

# conftest provides a `client` fixture (session scoped) that uses a temporary SQLite DB.

def test_session_persists_across_clients(client, sample_resume_bytes):
    """Create a session, start interview, answer a question, then verify data is
    visible from a freshly imported FastAPI app and directly via the DB.
    """
    # Create a new interview session
    files = {"resume": ("sample_resume.txt", sample_resume_bytes, "text/plain")}
    create_resp = client.post("/api/sessions", data={"role": "backend-engineer"}, files=files)
    assert create_resp.status_code == 201
    session_id = create_resp.json()["session_id"]

    # Start the interview to generate questions
    start_resp = client.post(f"/api/sessions/{session_id}/start")
    assert start_resp.status_code == 200
    questions = start_resp.json()["questions"]
    assert questions
    first_q = questions[0]
    qid = first_q["id"]

    # Answer the first question
    ans_resp = client.post(
        f"/api/sessions/{session_id}/answers",
        json={"question_id": qid, "answer_text": "My answer"},
    )
    assert ans_resp.status_code == 201

    # ---- Fresh client via re‑imported app ----
    # Import the app after the fixture has already performed its reloads
    from app.main import app as fresh_app
    fresh_client = TestClient(fresh_app)
    fresh_q_resp = fresh_client.get(f"/api/sessions/{session_id}/questions")
    assert fresh_q_resp.status_code == 200
    # The previously answered question should still be present
    fresh_questions = fresh_q_resp.json()
    assert any(q["id"] == qid for q in fresh_questions)

    # ---- Direct DB verification ----
    from app.database import SessionLocal
    db = SessionLocal()
    try:
        from app.models import Answer, InterviewSession
        # Verify the session exists
        sess = db.query(InterviewSession).filter(InterviewSession.id == session_id).one_or_none()
        assert sess is not None
        # Verify exactly one answer linked to the session
        answers = db.query(Answer).filter(Answer.session_id == session_id).all()
        assert len(answers) == 1
        assert answers[0].question_id == qid
    finally:
        db.close()

def test_multiple_answers_persist(client, sample_resume_bytes):
    """Create a session, answer all questions, then ensure DB contains all answers."""
    files = {"resume": ("sample_resume.txt", sample_resume_bytes, "text/plain")}
    create_resp = client.post("/api/sessions", data={"role": "ai-ml-engineer"}, files=files)
    assert create_resp.status_code == 201
    session_id = create_resp.json()["session_id"]
    start_resp = client.post(f"/api/sessions/{session_id}/start")
    assert start_resp.status_code == 200
    qids = [q["id"] for q in start_resp.json()["questions"]]
    for qid in qids:
        ans = client.post(
            f"/api/sessions/{session_id}/answers",
            json={"question_id": qid, "answer_text": "answer"},
        )
        assert ans.status_code == 201
    # Verify via DB
    from app.database import SessionLocal
    from app.models import Answer
    db = SessionLocal()
    try:
        answers = db.query(Answer).filter(Answer.session_id == session_id).all()
        assert len(answers) == len(qids)
    finally:
        db.close()
