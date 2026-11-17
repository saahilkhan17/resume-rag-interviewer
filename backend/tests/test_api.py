import pytest
from app import schemas

# Use the provided client fixture for most tests

def test_health_check(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

def test_get_roles(client):
    response = client.get("/api/roles")
    assert response.status_code == 200
    roles = response.json()
    assert isinstance(roles, list)
    assert len(roles) == 3
    for role in roles:
        assert "id" in role and "kb_chunks" in role
        # All roles have at least one chunk in the provided KB
        assert role["kb_chunks"] > 0

def test_create_session_invalid_role(client):
    files = {"resume": ("sample.txt", b"dummy", "text/plain")}
    response = client.post("/api/sessions", data={"role": "unknown-role"}, files=files)
    assert response.status_code == 422
    assert "Unknown role" in response.text

def test_create_session_unsupported_file(client):
    files = {"resume": ("bad.exe", b"binarydata", "application/octet-stream")}
    response = client.post("/api/sessions", data={"role": "backend-engineer"}, files=files)
    assert response.status_code == 415
    assert "Unsupported file type" in response.text

def test_full_flow(client, sample_resume_bytes):
    # Create session
    files = {"resume": ("sample_resume.txt", sample_resume_bytes, "text/plain")}
    create_resp = client.post("/api/sessions", data={"role": "ai-ml-engineer"}, files=files)
    assert create_resp.status_code == 201
    data = create_resp.json()
    session_id = data["session_id"]
    # Parsed profile should contain non‑empty skills list
    parsed = data["parsed_profile"]
    assert "skills" in parsed and isinstance(parsed["skills"], list) and parsed["skills"]

    # Start interview
    start_resp = client.post(f"/api/sessions/{session_id}/start")
    assert start_resp.status_code == 200
    start_data = start_resp.json()
    assert start_data["status"] == "in_progress"
    questions = start_data["questions"]
    assert len(questions) == 5
    qids = [q["id"] for q in questions]
    for q in questions:
        assert q["source_chunks"]
        assert q["trace"]["query"]
        assert q["trace"]["chunk_ids"]

    # GET questions endpoint should match
    get_q = client.get(f"/api/sessions/{session_id}/questions")
    assert get_q.status_code == 200
    assert get_q.json() == questions

    # Answer each question
    for qid in qids:
        ans_resp = client.post(
            f"/api/sessions/{session_id}/answers",
            json={"question_id": qid, "answer_text": "My answer"},
        )
        assert ans_resp.status_code == 201
        ans_data = ans_resp.json()
        assert ans_data["question_id"] == qid
        assert ans_data["answer_id"]

    # Complete interview
    comp_resp = client.post(f"/api/sessions/{session_id}/complete")
    assert comp_resp.status_code == 200
    comp_data = comp_resp.json()
    summary = comp_data["summary"]
    # Validate summary structure
    for key in ["overall_assessment", "strengths", "gaps", "per_question", "topics_covered", "recommended_next_steps"]:
        assert key in summary
    assert len(summary["per_question"]) == 5

    # GET summary endpoint
    sum_resp = client.get(f"/api/sessions/{session_id}/summary")
    assert sum_resp.status_code == 200
    assert sum_resp.json() == summary

    # Session detail reflects counts
    detail_resp = client.get(f"/api/sessions/{session_id}")
    assert detail_resp.status_code == 200
    detail = detail_resp.json()
    assert detail["question_count"] == 5
    assert detail["answer_count"] == 5

    # Delete session
    del_resp = client.delete(f"/api/sessions/{session_id}")
    assert del_resp.status_code == 200
    # Subsequent GET should 404
    after_del = client.get(f"/api/sessions/{session_id}")
    assert after_del.status_code == 404

def test_start_idempotent(client, sample_resume_bytes):
    files = {"resume": ("sample_resume.txt", sample_resume_bytes, "text/plain")}
    create = client.post("/api/sessions", data={"role": "backend-engineer"}, files=files)
    session_id = create.json()["session_id"]
    first = client.post(f"/api/sessions/{session_id}/start").json()["questions"]
    second = client.post(f"/api/sessions/{session_id}/start").json()["questions"]
    assert [q["id"] for q in first] == [q["id"] for q in second]

def test_error_handling_invalid_question(client, sample_resume_bytes):
    files = {"resume": ("sample_resume.txt", sample_resume_bytes, "text/plain")}
    sess = client.post("/api/sessions", data={"role": "backend-engineer"}, files=files).json()["session_id"]
    client.post(f"/api/sessions/{sess}/start")
    # Use a random UUID as bad question id
    bad_id = "nonexistent-id"
    resp = client.post(
        f"/api/sessions/{sess}/answers",
        json={"question_id": bad_id, "answer_text": "test"},
    )
    assert resp.status_code == 404

def test_error_complete_before_answers(client, sample_resume_bytes):
    files = {"resume": ("sample_resume.txt", sample_resume_bytes, "text/plain")}
    sess = client.post("/api/sessions", data={"role": "backend-engineer"}, files=files).json()["session_id"]
    client.post(f"/api/sessions/{sess}/start")
    resp = client.post(f"/api/sessions/{sess}/complete")
    assert resp.status_code == 422

def test_error_summary_before_complete(client, sample_resume_bytes):
    files = {"resume": ("sample_resume.txt", sample_resume_bytes, "text/plain")}
    sess = client.post("/api/sessions", data={"role": "backend-engineer"}, files=files).json()["session_id"]
    client.post(f"/api/sessions/{sess}/start")
    resp = client.get(f"/api/sessions/{sess}/summary")
    assert resp.status_code == 404
