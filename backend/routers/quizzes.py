import logging

from beanie import PydanticObjectId
from fastapi import APIRouter, HTTPException, Request

from limiter import limiter
from models import Quiz, Question, Option
from schemas import (
    QuizCreate, QuizUpdate, QuizSummary, QuizDetail, QuizPublic,
    QuestionPublic, OptionPublic, QuestionIn, ImportConfirm,
)

router = APIRouter(prefix="/api/quizzes", tags=["quizzes"])
logger = logging.getLogger("quizzy.quizzes")


def parse_id(id_str: str) -> PydanticObjectId:
    """Convert a string to a MongoDB ObjectId, returning 404 on invalid input."""
    try:
        return PydanticObjectId(id_str)
    except Exception:
        raise HTTPException(status_code=404, detail="Not found")


def quiz_to_summary(quiz: Quiz) -> QuizSummary:
    return QuizSummary(
        id=str(quiz.id),
        title=quiz.title,
        description=quiz.description,
        time_limit_minutes=quiz.time_limit_minutes,
        share_token=quiz.share_token,
        question_count=len(quiz.questions),
        created_at=quiz.created_at.isoformat(),
    )


def quiz_to_detail(quiz: Quiz) -> QuizDetail:
    return QuizDetail(
        id=str(quiz.id),
        title=quiz.title,
        description=quiz.description,
        time_limit_minutes=quiz.time_limit_minutes,
        share_token=quiz.share_token,
        created_at=quiz.created_at.isoformat(),
        questions=quiz.questions,
    )


def quiz_to_public(quiz: Quiz) -> QuizPublic:
    """Strip correct answers before sending the quiz to a participant."""
    return QuizPublic(
        id=str(quiz.id),
        title=quiz.title,
        description=quiz.description,
        time_limit_minutes=quiz.time_limit_minutes,
        questions=[
            QuestionPublic(
                id=q.id,
                text=q.text,
                question_type=q.question_type,
                options=[OptionPublic(id=o.id, text=o.text) for o in q.options],
                points=q.points,
                order_index=q.order_index,
            )
            for q in quiz.questions
        ],
    )


def question_from_input(data: QuestionIn, order_index: int) -> Question:
    options = [Option(text=o.text, is_correct=o.is_correct) for o in data.options]
    return Question(
        text=data.text,
        question_type=data.question_type,
        options=options,
        correct_answer=data.correct_answer,
        points=data.points,
        order_index=order_index,
    )


@router.get("/", response_model=list[QuizSummary])
@limiter.limit("60/minute")
async def list_quizzes(request: Request):
    quizzes = await Quiz.find().to_list()
    return [quiz_to_summary(q) for q in quizzes]


@router.post("/", response_model=QuizDetail, status_code=201)
@limiter.limit("10/minute")
async def create_quiz(request: Request, body: QuizCreate):
    quiz = Quiz(
        title=body.title,
        description=body.description,
        time_limit_minutes=body.time_limit_minutes,
    )
    await quiz.insert()
    logger.info("Quiz created: %s (id=%s)", quiz.title, quiz.id)
    return quiz_to_detail(quiz)


@router.get("/public/{share_token}", response_model=QuizPublic)
@limiter.limit("60/minute")
async def get_quiz_public(request: Request, share_token: str):
    quiz = await Quiz.find_one(Quiz.share_token == share_token)
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz not found")
    return quiz_to_public(quiz)


@router.get("/{quiz_id}", response_model=QuizDetail)
@limiter.limit("60/minute")
async def get_quiz(request: Request, quiz_id: str):
    quiz = await Quiz.get(parse_id(quiz_id))
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz not found")
    return quiz_to_detail(quiz)


@router.put("/{quiz_id}", response_model=QuizDetail)
@limiter.limit("20/minute")
async def update_quiz(request: Request, quiz_id: str, body: QuizUpdate):
    quiz = await Quiz.get(parse_id(quiz_id))
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz not found")
    if body.title is not None:
        quiz.title = body.title
    if body.description is not None:
        quiz.description = body.description
    if "time_limit_minutes" in body.model_fields_set:
        quiz.time_limit_minutes = body.time_limit_minutes
    await quiz.save()
    return quiz_to_detail(quiz)


@router.delete("/{quiz_id}", status_code=204)
@limiter.limit("10/minute")
async def delete_quiz(request: Request, quiz_id: str):
    quiz = await Quiz.get(parse_id(quiz_id))
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz not found")
    await quiz.delete()
    logger.info("Quiz deleted: id=%s", quiz_id)


# --- Question management ---

@router.post("/{quiz_id}/questions", response_model=QuizDetail, status_code=201)
@limiter.limit("30/minute")
async def add_question(request: Request, quiz_id: str, body: QuestionIn):
    quiz = await Quiz.get(parse_id(quiz_id))
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz not found")
    question = question_from_input(body, order_index=len(quiz.questions))
    quiz.questions.append(question)
    await quiz.save()
    return quiz_to_detail(quiz)


@router.put("/{quiz_id}/questions/{question_id}", response_model=QuizDetail)
@limiter.limit("30/minute")
async def update_question(request: Request, quiz_id: str, question_id: str, body: QuestionIn):
    quiz = await Quiz.get(parse_id(quiz_id))
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz not found")
    for i, q in enumerate(quiz.questions):
        if q.id == question_id:
            updated = question_from_input(body, q.order_index)
            updated.id = question_id
            quiz.questions[i] = updated
            await quiz.save()
            return quiz_to_detail(quiz)
    raise HTTPException(status_code=404, detail="Question not found")


@router.delete("/{quiz_id}/questions/{question_id}", response_model=QuizDetail)
@limiter.limit("30/minute")
async def delete_question(request: Request, quiz_id: str, question_id: str):
    quiz = await Quiz.get(parse_id(quiz_id))
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz not found")
    original_len = len(quiz.questions)
    quiz.questions = [q for q in quiz.questions if q.id != question_id]
    if len(quiz.questions) == original_len:
        raise HTTPException(status_code=404, detail="Question not found")
    for i, q in enumerate(quiz.questions):
        q.order_index = i
    await quiz.save()
    return quiz_to_detail(quiz)


@router.put("/{quiz_id}/questions/reorder", response_model=QuizDetail)
@limiter.limit("30/minute")
async def reorder_questions(request: Request, quiz_id: str, ordered_ids: list[str]):
    quiz = await Quiz.get(parse_id(quiz_id))
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz not found")
    question_map = {q.id: q for q in quiz.questions}
    reordered = []
    for i, qid in enumerate(ordered_ids):
        if qid not in question_map:
            raise HTTPException(status_code=400, detail=f"Unknown question id: {qid}")
        q = question_map[qid]
        q.order_index = i
        reordered.append(q)
    quiz.questions = reordered
    await quiz.save()
    return quiz_to_detail(quiz)


@router.post("/{quiz_id}/import", response_model=QuizDetail)
@limiter.limit("10/minute")
async def import_questions(request: Request, quiz_id: str, body: ImportConfirm):
    quiz = await Quiz.get(parse_id(quiz_id))
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz not found")
    start_index = len(quiz.questions)
    for i, q in enumerate(body.questions):
        question = question_from_input(QuestionIn(**q.model_dump()), start_index + i)
        quiz.questions.append(question)
    await quiz.save()
    logger.info("Imported %d questions into quiz id=%s", len(body.questions), quiz_id)
    return quiz_to_detail(quiz)
