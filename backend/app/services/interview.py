import json
from typing import List, Dict, Any

from sqlalchemy.orm import Session as DBSession

from app import models
from app.services import summarizer, context_builder
from app.rag.question_generator import generate_questions, QuestionGenerationError
from app.rag.retriever import Retriever
from app.rag.vector_store import VectorStore
from app.config import settings


def create_session(db: DBSession, role: str, parsed_profile: dict) -> models.InterviewSession:
    """Create a new InterviewSession with status ``created``.

    ``parsed_profile`` is stored as JSON in the ``parsed_profile`` column.
    """
    session = models.InterviewSession(
        role=role,
        parsed_profile=parsed_profile,
        status="created",
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def get_session(db: DBSession, session_id: str) -> models.InterviewSession | None:
    return db.query(models.InterviewSession).filter(models.InterviewSession.id == session_id).first()


def list_sessions(db: DBSession) -> List[models.InterviewSession]:
    return (
        db.query(models.InterviewSession)
        .order_by(models.InterviewSession.created_at.desc())
        .all()
    )


def delete_session(db: DBSession, session_id: str) -> bool:
    sess = get_session(db, session_id)
    if not sess:
        return False
    db.delete(sess)
    db.commit()
    return True


def start_interview(
    db: DBSession,
    session: models.InterviewSession,
    retriever: Retriever,
    api_key: str | None = None,
    num_questions: int = 5,
) -> List[models.Question]:
    """Generate interview questions for a session.

    Idempotent – if questions already exist for the session, they are returned.
    """
    if session.status == "completed":
        raise ValueError("session already completed")

    if session.questions:
        # Already started – return existing questions
        return list(session.questions)

    # Build retrieval context
    context = context_builder.build_context(
        parsed_profile=session.parsed_profile or {},
        role=session.role,
        retriever=retriever,
    )
    chunks = context.get("chunks", [])

    # Generate grounded questions
    try:
        generated = generate_questions(
            chunks=chunks,
            parsed_profile=session.parsed_profile or {},
            role=session.role,
            num_questions=num_questions,
            api_key=api_key,
        )
    except QuestionGenerationError as exc:
        raise exc

    if not generated:
        raise QuestionGenerationError("No questions could be generated for this session")

    # Persist Question rows
    for idx, qdict in enumerate(generated):
        question = models.Question(
            session_id=session.id,
            text=qdict.get("text", ""),
            topic=qdict.get("topic", ""),
            difficulty=qdict.get("difficulty", "medium"),
            source_chunk_ids=qdict.get("source_chunks", []),
            retrieval_query=qdict.get("retrieval_query"),
            order_index=idx,
        )
        db.add(question)
    # Update session status
    session.status = "in_progress"
    db.commit()
    # Refresh to get question objects with IDs
    db.refresh(session)
    return list(session.questions)


def store_answer(
    db: DBSession,
    session: models.InterviewSession,
    question_id: str,
    answer_text: str,
) -> models.Answer:
    """Store or update an answer for a given question in a session."""
    if session.status != "in_progress":
        raise ValueError("cannot store answer when session status is not in_progress")

    # Verify question belongs to session
    question = (
        db.query(models.Question)
        .filter(models.Question.id == question_id, models.Question.session_id == session.id)
        .first()
    )
    if not question:
        raise LookupError(f"question {question_id} not found in session {session.id}")

    stripped = answer_text.strip()
    if not stripped:
        raise ValueError("answer_text must not be empty or whitespace only")

    # Upsert Answer
    answer = (
        db.query(models.Answer)
        .filter(models.Answer.question_id == question_id, models.Answer.session_id == session.id)
        .first()
    )
    if answer:
        answer.answer_text = stripped
        # stored_at will be updated automatically via default if we set onupdate; here we manually set
        from app.models import utc_now

        answer.stored_at = utc_now()
    else:
        answer = models.Answer(
            session_id=session.id,
            question_id=question_id,
            answer_text=stripped,
        )
        db.add(answer)
    db.commit()
    db.refresh(answer)
    return answer


def complete_interview(
    db: DBSession,
    session: models.InterviewSession,
) -> Dict[str, Any]:
    """Finalize the interview, building a summary and marking the session completed."""
    if session.status != "in_progress":
        raise ValueError("session must be in_progress to complete")
    if not session.answers:
        raise ValueError("at least one answer is required to complete the interview")

    # Ensure vector store is loaded for chunk text lookup
    vector_store = VectorStore(index_dir=settings.backend_dir / "data" / "vector_store")
    if not vector_store.load():
        # Attempt to build index if missing – this mirrors Retriever.ensure_loaded logic
        from app.rag.ingestion import build_index

        vector_store = build_index(kb_dir=settings.kb_dir_path, index_dir=vector_store.index_dir)

    # Prepare data structures for summary
    questions = list(session.questions)  # already ordered by order_index due to relationship ordering
    answers_dict = {ans.question_id: ans.answer_text for ans in session.answers}
    chunk_texts_by_question: Dict[str, List[str]] = {}
    for q in questions:
        texts: List[str] = []
        for cid in q.source_chunk_ids or []:
            txt = vector_store.get_chunk_text(cid)
            if txt:
                texts.append(txt)
        chunk_texts_by_question[q.id] = texts

    summary_content = summarizer.build_summary(
        session_role=session.role,
        questions=[{"id": q.id, "text": q.text, "topic": q.topic} for q in questions],
        answers=answers_dict,
        chunk_texts_by_question=chunk_texts_by_question,
    )

    # Persist Summary (replace existing if any)
    if session.summary:
        db.delete(session.summary)
        db.flush()
    summary = models.Summary(session_id=session.id, content=summary_content)
    db.add(summary)
    session.status = "completed"
    db.commit()
    return summary_content


def get_summary(db: DBSession, session: models.InterviewSession) -> Dict[str, Any] | None:
    if session.summary:
        return session.summary.content
    return None
