"""Sessions API router implementing the interview workflow.
"""

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session as DBSession
from typing import List
import threading
import os

from app import schemas
from app.services import interview
from app.database import get_db
from app.services import resume_parser
from app.rag.retriever import Retriever
from app.config import settings

router = APIRouter()

# Singleton retriever with lazy initialization and thread‑safety
_retriever_instance: Retriever | None = None
_retriever_lock = threading.Lock()

def get_retriever() -> Retriever:
    global _retriever_instance
    if _retriever_instance is None:
        with _retriever_lock:
            if _retriever_instance is None:
                _retriever_instance = Retriever()
    return _retriever_instance

# Helper to validate role
def _valid_role(role: str) -> bool:
    from . import roles as role_mod
    return any(r["id"] == role for r in role_mod.ROLES)

@router.get("/api/sessions", response_model=List[schemas.SessionListItem])
def list_sessions(db: DBSession = Depends(get_db)):
    sessions = interview.list_sessions(db)
    return [
        schemas.SessionListItem(
            session_id=s.id,
            role=s.role,
            status=s.status,
            created_at=s.created_at,
        )
        for s in sessions
    ]

@router.post(
    "/api/sessions",
    response_model=schemas.SessionCreateResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_session(
    resume: UploadFile = File(...),
    role: str = Form(...),
    db: DBSession = Depends(get_db),
):
    # Role validation
    if not _valid_role(role):
        raise HTTPException(status_code=422, detail="Unknown role")
    # File type validation
    ext = os.path.splitext(resume.filename)[1].lower()
    if ext not in {".pdf", ".txt", ".md"}:
        raise HTTPException(status_code=415, detail="Unsupported file type")
    data = await resume.read()
    try:
        parsed = resume_parser.parse_resume_file(data, resume.filename)
    except Exception as exc:
        # Treat parsing errors as unsupported content
        raise HTTPException(status_code=415, detail=str(exc))
    # Strip large raw fields before storing
    parsed_to_store = {
        k: v for k, v in parsed.items() if k not in {"raw_text", "text_length"}
    }
    session = interview.create_session(db, role=role, parsed_profile=parsed_to_store)
    response = schemas.SessionCreateResponse(
        session_id=session.id,
        role=session.role,
        parsed_profile=schemas.ParsedProfile(**parsed_to_store),
        status=session.status,
    )
    return response

@router.get("/api/sessions/{session_id}", response_model=schemas.SessionDetailResponse)
def get_session_detail(session_id: str, db: DBSession = Depends(get_db)):
    sess = interview.get_session(db, session_id)
    if not sess:
        raise HTTPException(status_code=404, detail="Session not found")
    return schemas.SessionDetailResponse(
        session_id=sess.id,
        role=sess.role,
        parsed_profile=schemas.ParsedProfile(**(sess.parsed_profile or {})),
        status=sess.status,
        question_count=len(sess.questions),
        answer_count=len(sess.answers),
        created_at=sess.created_at,
    )

@router.post("/api/sessions/{session_id}/start", response_model=schemas.StartResponse)
def start_interview(session_id: str, db: DBSession = Depends(get_db)):
    sess = interview.get_session(db, session_id)
    if not sess:
        raise HTTPException(status_code=404, detail="Session not found")
    try:
        questions = interview.start_interview(
            db=db,
            session=sess,
            retriever=get_retriever(),
            api_key=settings.gemini_api_key or None,
            num_questions=settings.num_questions,
        )
    except ValueError as ve:
        raise HTTPException(status_code=422, detail=str(ve))
    except LookupError as le:
        raise HTTPException(status_code=404, detail=str(le))
    except Exception as exc:
        # Expect QuestionGenerationError for 503
        from app.rag.question_generator import QuestionGenerationError
        if isinstance(exc, QuestionGenerationError):
            raise HTTPException(status_code=503, detail=str(exc))
        raise HTTPException(status_code=500, detail=str(exc))
    # Convert to response schema
    q_out = [
        schemas.QuestionOut(
            id=q.id,
            text=q.text,
            topic=q.topic,
            difficulty=q.difficulty,
            source_chunks=q.source_chunk_ids or [],
            trace={"query": q.retrieval_query, "chunk_ids": q.source_chunk_ids},
        )
        for q in questions
    ]
    return schemas.StartResponse(status="in_progress", questions=q_out)

@router.get("/api/sessions/{session_id}/questions", response_model=List[schemas.QuestionOut])
def get_questions(session_id: str, db: DBSession = Depends(get_db)):
    sess = interview.get_session(db, session_id)
    if not sess:
        raise HTTPException(status_code=404, detail="Session not found")
    return [
        schemas.QuestionOut(
            id=q.id,
            text=q.text,
            topic=q.topic,
            difficulty=q.difficulty,
            source_chunks=q.source_chunk_ids or [],
            trace={"query": q.retrieval_query, "chunk_ids": q.source_chunk_ids},
        )
        for q in sess.questions
    ]

@router.post(
    "/api/sessions/{session_id}/answers",
    response_model=schemas.AnswerResponse,
    status_code=status.HTTP_201_CREATED,
)
def submit_answer(
    session_id: str,
    answer: schemas.AnswerCreate,
    db: DBSession = Depends(get_db),
):
    sess = interview.get_session(db, session_id)
    if not sess:
        raise HTTPException(status_code=404, detail="Session not found")
    try:
        ans = interview.store_answer(db, sess, answer.question_id, answer.answer_text)
    except ValueError as ve:
        raise HTTPException(status_code=422, detail=str(ve))
    except LookupError as le:
        raise HTTPException(status_code=404, detail=str(le))
    return schemas.AnswerResponse(
        answer_id=ans.id,
        question_id=ans.question_id,
        stored_at=ans.stored_at,
    )

@router.post(
    "/api/sessions/{session_id}/complete",
    response_model=schemas.CompleteResponse,
)
def complete(session_id: str, db: DBSession = Depends(get_db)):
    sess = interview.get_session(db, session_id)
    if not sess:
        raise HTTPException(status_code=404, detail="Session not found")
    try:
        summary_content = interview.complete_interview(db, sess)
    except ValueError as ve:
        raise HTTPException(status_code=422, detail=str(ve))
    return schemas.CompleteResponse(status="completed", summary=summary_content)

@router.get("/api/sessions/{session_id}/summary", response_model=schemas.SummaryContent)
def get_summary(session_id: str, db: DBSession = Depends(get_db)):
    sess = interview.get_session(db, session_id)
    if not sess:
        raise HTTPException(status_code=404, detail="Session not found")
    summary = interview.get_summary(db, sess)
    if not summary:
        raise HTTPException(status_code=404, detail="Summary not available")
    return summary

@router.delete("/api/sessions/{session_id}")
def delete_session(session_id: str, db: DBSession = Depends(get_db)):
    success = interview.delete_session(db, session_id)
    if not success:
        raise HTTPException(status_code=404, detail="Session not found")
    return JSONResponse(content={"deleted": True, "session_id": session_id})
