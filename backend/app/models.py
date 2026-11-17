from datetime import datetime, timezone
import uuid
from sqlalchemy import Column, DateTime, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import relationship
from app.database import Base


def generate_uuid() -> str:
    return uuid.uuid4().hex


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class InterviewSession(Base):
    __tablename__ = "interview_sessions"

    id = Column(String(64), primary_key=True, default=generate_uuid)
    role = Column(String(128), nullable=False)
    status = Column(String(64), nullable=False, default="created")
    parsed_profile = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    questions = relationship(
        "Question",
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="Question.order_index",
    )
    answers = relationship(
        "Answer",
        back_populates="session",
        cascade="all, delete-orphan",
    )
    summary = relationship(
        "Summary",
        back_populates="session",
        uselist=False,
        cascade="all, delete-orphan",
    )


class Question(Base):
    __tablename__ = "questions"

    id = Column(String(64), primary_key=True, default=generate_uuid)
    session_id = Column(
        String(64),
        ForeignKey("interview_sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    text = Column(Text, nullable=False)
    topic = Column(String(256), nullable=False)
    difficulty = Column(String(64), nullable=False, default="medium")
    source_chunk_ids = Column(JSON, nullable=False, default=list)
    retrieval_query = Column(Text, nullable=True)
    order_index = Column(Integer, nullable=False, default=0)

    session = relationship("InterviewSession", back_populates="questions")
    answers = relationship(
        "Answer",
        back_populates="question",
        cascade="all, delete-orphan",
    )


class Answer(Base):
    __tablename__ = "answers"

    id = Column(String(64), primary_key=True, default=generate_uuid)
    session_id = Column(
        String(64),
        ForeignKey("interview_sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    question_id = Column(
        String(64),
        ForeignKey("questions.id", ondelete="CASCADE"),
        nullable=False,
    )
    answer_text = Column(Text, nullable=False)
    stored_at = Column(DateTime, default=utc_now, nullable=False)

    session = relationship("InterviewSession", back_populates="answers")
    question = relationship("Question", back_populates="answers")


class Summary(Base):
    __tablename__ = "summaries"

    id = Column(String(64), primary_key=True, default=generate_uuid)
    session_id = Column(
        String(64),
        ForeignKey("interview_sessions.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    content = Column(JSON, nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)

    session = relationship("InterviewSession", back_populates="summary")
