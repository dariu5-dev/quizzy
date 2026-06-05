from datetime import datetime
from fastapi import APIRouter, HTTPException
from beanie import PydanticObjectId
from models import Quiz, Session, AnswerRecord
from schemas import (
    SessionStart, SessionSubmit, SessionResult,
    AnswerResult, LeaderboardEntry
)

router = APIRouter(prefix="/api/sessions", tags=["sessions"])


def _score_answer(question, answer_in) -> tuple[bool, int, str | None]:
    """Returns (is_correct, points_earned, correct_answer_text)."""
    if question.question_type == "mcq":
        correct_option = next((o for o in question.options if o.is_correct), None)
        is_correct = (
            correct_option is not None
            and answer_in.selected_option_id == correct_option.id
        )
        correct_text = correct_option.text if correct_option else None
        return is_correct, question.points if is_correct else 0, correct_text

    # short_answer: case-insensitive strip match
    if question.correct_answer and answer_in.text_answer:
        is_correct = (
            answer_in.text_answer.strip().lower()
            == question.correct_answer.strip().lower()
        )
        return is_correct, question.points if is_correct else 0, question.correct_answer

    return False, 0, question.correct_answer


@router.post("/", status_code=201)
async def start_session(body: SessionStart):
    quiz = await Quiz.get(PydanticObjectId(body.quiz_id))
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz not found")
    session = Session(
        quiz_id=body.quiz_id,
        participant_name=body.participant_name,
        max_score=sum(q.points for q in quiz.questions),
    )
    await session.insert()
    return {"session_id": str(session.id)}


@router.post("/{session_id}/submit", response_model=SessionResult)
async def submit_session(session_id: str, body: SessionSubmit):
    session = await Session.get(PydanticObjectId(session_id))
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.completed_at is not None:
        raise HTTPException(status_code=400, detail="Session already submitted")

    quiz = await Quiz.get(PydanticObjectId(session.quiz_id))
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz not found")

    question_map = {q.id: q for q in quiz.questions}
    answer_records = []
    answer_results = []
    total_score = 0

    for answer_in in body.answers:
        question = question_map.get(answer_in.question_id)
        if not question:
            continue
        is_correct, points, correct_text = _score_answer(question, answer_in)
        total_score += points
        answer_records.append(AnswerRecord(
            question_id=answer_in.question_id,
            selected_option_id=answer_in.selected_option_id,
            text_answer=answer_in.text_answer,
            is_correct=is_correct,
            points_earned=points,
        ))
        answer_results.append(AnswerResult(
            question_id=answer_in.question_id,
            is_correct=is_correct,
            points_earned=points,
            correct_answer=correct_text,
        ))

    session.answers = answer_records
    session.score = total_score
    session.completed_at = datetime.utcnow()
    session.time_taken_seconds = body.time_taken_seconds
    await session.save()

    max_score = sum(q.points for q in quiz.questions)
    percentage = round((total_score / max_score * 100) if max_score > 0 else 0, 1)

    return SessionResult(
        session_id=str(session.id),
        score=total_score,
        max_score=max_score,
        percentage=percentage,
        answers=answer_results,
    )


@router.get("/quiz/{quiz_id}/leaderboard", response_model=list[LeaderboardEntry])
async def get_leaderboard(quiz_id: str):
    sessions = await Session.find(
        Session.quiz_id == quiz_id,
        Session.completed_at != None,
    ).to_list()

    # sort: highest score first, then fastest time
    sessions.sort(key=lambda s: (-s.score, s.time_taken_seconds or 999999))

    entries = []
    for rank, s in enumerate(sessions, start=1):
        percentage = round((s.score / s.max_score * 100) if s.max_score > 0 else 0, 1)
        entries.append(LeaderboardEntry(
            rank=rank,
            participant_name=s.participant_name,
            score=s.score,
            max_score=s.max_score,
            percentage=percentage,
            time_taken_seconds=s.time_taken_seconds,
            completed_at=s.completed_at.isoformat() if s.completed_at else None,
        ))
    return entries
