from fastapi import APIRouter, HTTPException
from beanie import PydanticObjectId
from models import Quiz, Question, Option
from schemas import (
    QuizCreate, QuizUpdate, QuizSummary, QuizDetail,
    QuestionIn, ImportConfirm
)

router = APIRouter(prefix="/api/quizzes", tags=["quizzes"])


def _quiz_to_summary(quiz: Quiz) -> QuizSummary:
    return QuizSummary(
        id=str(quiz.id),
        title=quiz.title,
        description=quiz.description,
        time_limit_minutes=quiz.time_limit_minutes,
        share_token=quiz.share_token,
        question_count=len(quiz.questions),
        created_at=quiz.created_at.isoformat(),
    )


def _quiz_to_detail(quiz: Quiz) -> QuizDetail:
    return QuizDetail(
        id=str(quiz.id),
        title=quiz.title,
        description=quiz.description,
        time_limit_minutes=quiz.time_limit_minutes,
        share_token=quiz.share_token,
        created_at=quiz.created_at.isoformat(),
        questions=quiz.questions,
    )


def _question_from_input(data: QuestionIn, order_index: int) -> Question:
    options = [
        Option(text=o.text, is_correct=o.is_correct)
        for o in data.options
    ]
    return Question(
        text=data.text,
        question_type=data.question_type,
        options=options,
        correct_answer=data.correct_answer,
        points=data.points,
        order_index=order_index,
    )


@router.get("/", response_model=list[QuizSummary])
async def list_quizzes():
    quizzes = await Quiz.find().to_list()
    return [_quiz_to_summary(q) for q in quizzes]


@router.post("/", response_model=QuizDetail, status_code=201)
async def create_quiz(body: QuizCreate):
    quiz = Quiz(
        title=body.title,
        description=body.description,
        time_limit_minutes=body.time_limit_minutes,
    )
    await quiz.insert()
    return _quiz_to_detail(quiz)


@router.get("/public/{share_token}", response_model=QuizDetail)
async def get_quiz_public(share_token: str):
    quiz = await Quiz.find_one(Quiz.share_token == share_token)
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz not found")
    # strip correct answers before sending to takers
    for q in quiz.questions:
        q.correct_answer = None
        for o in q.options:
            o.is_correct = False
    return _quiz_to_detail(quiz)


@router.get("/{quiz_id}", response_model=QuizDetail)
async def get_quiz(quiz_id: str):
    quiz = await Quiz.get(PydanticObjectId(quiz_id))
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz not found")
    return _quiz_to_detail(quiz)


@router.put("/{quiz_id}", response_model=QuizDetail)
async def update_quiz(quiz_id: str, body: QuizUpdate):
    quiz = await Quiz.get(PydanticObjectId(quiz_id))
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz not found")
    if body.title is not None:
        quiz.title = body.title
    if body.description is not None:
        quiz.description = body.description
    if body.time_limit_minutes is not None:
        quiz.time_limit_minutes = body.time_limit_minutes
    elif "time_limit_minutes" in body.model_fields_set:
        quiz.time_limit_minutes = None
    await quiz.save()
    return _quiz_to_detail(quiz)


@router.delete("/{quiz_id}", status_code=204)
async def delete_quiz(quiz_id: str):
    quiz = await Quiz.get(PydanticObjectId(quiz_id))
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz not found")
    await quiz.delete()


# --- Question management ---

@router.post("/{quiz_id}/questions", response_model=QuizDetail, status_code=201)
async def add_question(quiz_id: str, body: QuestionIn):
    quiz = await Quiz.get(PydanticObjectId(quiz_id))
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz not found")
    order_index = len(quiz.questions)
    question = _question_from_input(body, order_index)
    quiz.questions.append(question)
    await quiz.save()
    return _quiz_to_detail(quiz)


@router.put("/{quiz_id}/questions/{question_id}", response_model=QuizDetail)
async def update_question(quiz_id: str, question_id: str, body: QuestionIn):
    quiz = await Quiz.get(PydanticObjectId(quiz_id))
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz not found")
    for i, q in enumerate(quiz.questions):
        if q.id == question_id:
            updated = _question_from_input(body, q.order_index)
            updated.id = question_id
            quiz.questions[i] = updated
            await quiz.save()
            return _quiz_to_detail(quiz)
    raise HTTPException(status_code=404, detail="Question not found")


@router.delete("/{quiz_id}/questions/{question_id}", response_model=QuizDetail)
async def delete_question(quiz_id: str, question_id: str):
    quiz = await Quiz.get(PydanticObjectId(quiz_id))
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz not found")
    original_len = len(quiz.questions)
    quiz.questions = [q for q in quiz.questions if q.id != question_id]
    if len(quiz.questions) == original_len:
        raise HTTPException(status_code=404, detail="Question not found")
    # re-index
    for i, q in enumerate(quiz.questions):
        q.order_index = i
    await quiz.save()
    return _quiz_to_detail(quiz)


@router.put("/{quiz_id}/questions/reorder", response_model=QuizDetail)
async def reorder_questions(quiz_id: str, ordered_ids: list[str]):
    quiz = await Quiz.get(PydanticObjectId(quiz_id))
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
    return _quiz_to_detail(quiz)


@router.post("/{quiz_id}/import", response_model=QuizDetail)
async def import_questions(quiz_id: str, body: ImportConfirm):
    quiz = await Quiz.get(PydanticObjectId(quiz_id))
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz not found")
    start_index = len(quiz.questions)
    for i, q in enumerate(body.questions):
        question = _question_from_input(
            QuestionIn(**q.model_dump()),
            start_index + i,
        )
        quiz.questions.append(question)
    await quiz.save()
    return _quiz_to_detail(quiz)
