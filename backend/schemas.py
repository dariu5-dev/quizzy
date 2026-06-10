from typing import Literal, Optional
from pydantic import BaseModel, Field
from models import Question


# --- Quiz schemas ---

class OptionIn(BaseModel):
    text: str = Field(..., min_length=1, max_length=500)
    is_correct: bool = False


class QuestionIn(BaseModel):
    text: str = Field(..., min_length=1, max_length=2000)
    question_type: Literal["mcq", "short_answer"]
    options: list[OptionIn] = Field(default=[], max_length=6)
    correct_answer: Optional[str] = Field(None, max_length=1000)
    points: int = Field(1, ge=1, le=100)
    order_index: int = Field(0, ge=0)


class QuizCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    description: str = Field("", max_length=1000)
    time_limit_minutes: Optional[int] = Field(None, ge=1, le=600)


class QuizUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    time_limit_minutes: Optional[int] = Field(None, ge=1, le=600)


class QuizSummary(BaseModel):
    id: str
    title: str
    description: str
    time_limit_minutes: Optional[int]
    share_token: str
    question_count: int
    created_at: str


class QuizDetail(BaseModel):
    id: str
    title: str
    description: str
    time_limit_minutes: Optional[int]
    share_token: str
    created_at: str
    questions: list[Question]


# --- Public quiz schemas (correct answers excluded) ---
# These are used when serving the quiz to participants.

class OptionPublic(BaseModel):
    """MCQ option shown to the quiz taker — no is_correct flag."""
    id: str
    text: str


class QuestionPublic(BaseModel):
    """Question shown to the quiz taker — no correct answer exposed."""
    id: str
    text: str
    question_type: Literal["mcq", "short_answer"]
    options: list[OptionPublic]
    points: int
    order_index: int


class QuizPublic(BaseModel):
    """Quiz served to participants via the share link."""
    id: str
    title: str
    description: str
    time_limit_minutes: Optional[int]
    questions: list[QuestionPublic]


# --- Session schemas ---

class AnswerIn(BaseModel):
    question_id: str = Field(..., min_length=1, max_length=100)
    selected_option_id: Optional[str] = Field(None, max_length=100)
    text_answer: Optional[str] = Field(None, max_length=5000)


class SessionStart(BaseModel):
    quiz_id: str = Field(..., min_length=1, max_length=100)
    participant_name: str = Field(..., min_length=1, max_length=100)


class SessionSubmit(BaseModel):
    answers: list[AnswerIn] = Field(..., max_length=500)
    time_taken_seconds: Optional[int] = Field(None, ge=0, le=86400)


class AnswerResult(BaseModel):
    question_id: str
    is_correct: bool
    points_earned: int
    correct_answer: Optional[str] = None  # revealed after submit


class SessionResult(BaseModel):
    session_id: str
    score: int
    max_score: int
    percentage: float
    answers: list[AnswerResult]


# --- Leaderboard ---

class LeaderboardEntry(BaseModel):
    rank: int
    participant_name: str
    score: int
    max_score: int
    percentage: float
    time_taken_seconds: Optional[int]
    completed_at: Optional[str]


# --- Import preview ---

class ImportedQuestion(BaseModel):
    text: str = Field(..., min_length=1, max_length=2000)
    question_type: Literal["mcq", "short_answer"]
    options: list[OptionIn] = Field(default=[], max_length=6)
    correct_answer: Optional[str] = Field(None, max_length=1000)
    points: int = Field(1, ge=1, le=100)


class ImportPreview(BaseModel):
    questions: list[ImportedQuestion]
    errors: list[str] = []


class ImportConfirm(BaseModel):
    questions: list[ImportedQuestion] = Field(..., max_length=500)
