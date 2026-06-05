from datetime import datetime
from typing import Literal, Optional
from beanie import Document
from pydantic import BaseModel, Field
import uuid


class Option(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    text: str
    is_correct: bool = False


class Question(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    text: str
    question_type: Literal["mcq", "short_answer"]
    options: list[Option] = []
    correct_answer: Optional[str] = None  # for short_answer
    points: int = 1
    order_index: int = 0


class Quiz(Document):
    title: str
    description: str = ""
    time_limit_minutes: Optional[int] = None  # None means untimed
    share_token: str = Field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = Field(default_factory=datetime.utcnow)
    questions: list[Question] = []

    class Settings:
        name = "quizzes"


class AnswerRecord(BaseModel):
    question_id: str
    selected_option_id: Optional[str] = None  # MCQ
    text_answer: Optional[str] = None          # short_answer
    is_correct: bool = False
    points_earned: int = 0


class Session(Document):
    quiz_id: str
    participant_name: str
    started_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    score: int = 0
    max_score: int = 0
    time_taken_seconds: Optional[int] = None
    answers: list[AnswerRecord] = []

    class Settings:
        name = "sessions"
