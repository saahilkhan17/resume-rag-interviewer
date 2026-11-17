from datetime import datetime
from typing import Any
from pydantic import BaseModel, ConfigDict, Field, field_validator


class ParsedProfile(BaseModel):
    skills: list[str] = Field(default_factory=list)
    technologies: list[str] = Field(default_factory=list)
    domains: list[str] = Field(default_factory=list)
    years_experience_hint: int | None = None

    model_config = ConfigDict(from_attributes=True)


# Added back SessionCreateResponse
class SessionCreateResponse(BaseModel):
    session_id: str
    role: str
    parsed_profile: ParsedProfile
    status: str
    model_config = ConfigDict(from_attributes=True)


class SessionDetailResponse(BaseModel):
    session_id: str
    role: str
    parsed_profile: ParsedProfile
    status: str
    question_count: int
    answer_count: int
    created_at: str

    model_config = ConfigDict(from_attributes=True)
    @field_validator("created_at", mode="before")
    @classmethod
    def serialize_created_at(cls, v: Any) -> str:
        if isinstance(v, datetime):
            return v.isoformat()
        return str(v)


class QuestionOut(BaseModel):
    id: str
    text: str
    topic: str
    difficulty: str = "medium"
    source_chunks: list[str] = Field(default_factory=list)
    trace: dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(from_attributes=True)


class StartResponse(BaseModel):
    status: str
    questions: list[QuestionOut]

    model_config = ConfigDict(from_attributes=True)


class AnswerCreate(BaseModel):
    question_id: str
    answer_text: str

    @field_validator("answer_text")
    @classmethod
    def validate_non_empty(cls, v: str) -> str:
        stripped = v.strip() if v else ""
        if not stripped:
            raise ValueError("answer_text must not be empty or whitespace only")
        return stripped


class AnswerResponse(BaseModel):
    answer_id: str
    question_id: str
    stored_at: str

    model_config = ConfigDict(from_attributes=True)
    @field_validator("stored_at", mode="before")
    @classmethod
    def serialize_stored_at(cls, v: Any) -> str:
        if isinstance(v, datetime):
            return v.isoformat()
        return str(v)


class PerQuestionSummary(BaseModel):
    question_id: str
    question: str
    answer: str
    assessment: str
    key_points_covered: list[str] = Field(default_factory=list)
    key_points_missed: list[str] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class SummaryContent(BaseModel):
    overall_assessment: str
    strengths: list[str] = Field(default_factory=list)
    gaps: list[str] = Field(default_factory=list)
    per_question: list[PerQuestionSummary] = Field(default_factory=list)
    topics_covered: list[str] = Field(default_factory=list)
    recommended_next_steps: list[str] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class CompleteResponse(BaseModel):
    status: str
    summary: SummaryContent

    model_config = ConfigDict(from_attributes=True)


class RoleOut(BaseModel):
    id: str
    label: str
    description: str
    kb_chunks: int

    model_config = ConfigDict(from_attributes=True)


class SessionListItem(BaseModel):
    session_id: str
    role: str
    status: str
    created_at: str

    model_config = ConfigDict(from_attributes=True)
    @field_validator("created_at", mode="before")
    @classmethod
    def serialize_created_at(cls, v: Any) -> str:
        if isinstance(v, datetime):
            return v.isoformat()
        return str(v)
