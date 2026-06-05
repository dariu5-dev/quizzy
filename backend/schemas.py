from typing import Literal, Optional
from pydantic import BaseModel
from models import Question


# --- Quiz schemas ---

class OptionIn(BaseModel):
    text: str
    is_correct: bool = False


class QuestionIn(BaseModel):
    text: str
    question_type: Literal["mcq", "short_answer"]
    options: list[OptionIn] = []
    correct_answer: Optional[str] = None
    points: int = 1
    order_index: int = 0


class QuizCreate(BaseModel):
    title: str
    description: str = ""
    time_limit_minutes: Optional[int] = None


class QuizUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    time_limit_minutes: Optional[int] = None


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


# --- Session schemas ---

class AnswerIn(BaseModel):
    question_id: str
    selected_option_id: Optional[str] = None
    text_answer: Optional[str] = None


class SessionStart(BaseModel):
    quiz_id: str
    participant_name: str


class SessionSubmit(BaseModel):
    answers: list[AnswerIn]
    time_taken_seconds: Optional[int] = None


class AnswerResult(BaseModel):
    question_id: str
    is_correct: bool
    points_earned: int
    correct_answer: Optional[str] = None  # shown after submit


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
    text: str
    question_type: Literal["mcq", "short_answer"]
    options: list[OptionIn] = []
    correct_answer: Optional[str] = None
    points: int = 1


class ImportPreview(BaseModel):
    questions: list[ImportedQuestion]
    errors: list[str] = []


class ImportConfirm(BaseModel):
    questions: list[ImportedQuestion]
