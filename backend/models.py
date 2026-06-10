from datetime import datetime, timezone
from typing import Literal, Optional

import uuid
from beanie import Document
from pydantic import BaseModel, Field
from pymongo import ASCENDING, IndexModel


def utcnow() -> datetime:
    """Return the current UTC time as a naive datetime (compatible with MongoDB storage)."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


class Option(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    text: str
    is_correct: bool = False


class Question(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    text: str
    question_type: Literal["mcq", "short_answer"]
    options: list[Option] = []
    correct_answer: Optional[str] = None  # only used for short_answer
    points: int = 1
    order_index: int = 0


class Quiz(Document):
    title: str
    description: str = ""
    time_limit_minutes: Optional[int] = None  # None means untimed
    share_token: str = Field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = Field(default_factory=utcnow)
    questions: list[Question] = []

    class Settings:
        name = "quizzes"
        indexes = [
            # Fast lookup by share token (used every time someone opens a quiz link)
            IndexModel([("share_token", ASCENDING)], unique=True),
        ]


class AnswerRecord(BaseModel):
    question_id: str
    selected_option_id: Optional[str] = None  # MCQ
    text_answer: Optional[str] = None          # short_answer
    is_correct: bool = False
    points_earned: int = 0


class Session(Document):
    quiz_id: str
    participant_name: str
    started_at: datetime = Field(default_factory=utcnow)
    completed_at: Optional[datetime] = None
    score: int = 0
    max_score: int = 0
    time_taken_seconds: Optional[int] = None
    answers: list[AnswerRecord] = []

    class Settings:
        name = "sessions"
        indexes = [
            # Leaderboard query filters and sorts by quiz_id + completed_at
            IndexModel([("quiz_id", ASCENDING), ("completed_at", ASCENDING)]),
        ]
