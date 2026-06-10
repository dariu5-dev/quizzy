import io
import logging
import re

import pandas as pd
import pdfplumber
from fastapi import APIRouter, File, HTTPException, Request, UploadFile

from limiter import limiter
from schemas import ImportPreview, ImportedQuestion, OptionIn

router = APIRouter(prefix="/api/import", tags=["import"])
logger = logging.getLogger("quizzy.imports")

MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB

# File magic bytes — used to verify the actual file type, not just the extension
PDF_MAGIC = b"%PDF-"
XLSX_MAGIC = b"PK\x03\x04"  # .xlsx is a ZIP archive


def check_size(content: bytes, filename: str) -> None:
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail=f"File too large (max {MAX_FILE_SIZE // (1024 * 1024)} MB)")


def check_magic(content: bytes, expected: bytes, label: str) -> None:
    if not content.startswith(expected):
        raise HTTPException(status_code=400, detail=f"File does not appear to be a valid {label}")


def parse_csv_or_excel(content: bytes, filename: str) -> ImportPreview:
    try:
        if filename.endswith(".csv"):
            df = pd.read_csv(io.BytesIO(content))
        else:
            df = pd.read_excel(io.BytesIO(content))
    except Exception as exc:
        logger.warning("Failed to parse file %s: %s", filename, exc)
        raise HTTPException(status_code=400, detail="Could not parse file — check the format and try again")

    questions: list[ImportedQuestion] = []
    errors: list[str] = []

    required_cols = {"question", "type"}
    actual_cols = {c.lower().strip() for c in df.columns}
    if not required_cols.issubset(actual_cols):
        raise HTTPException(
            status_code=400,
            detail=f"File must have at least columns: question, type. Found: {list(df.columns)}",
        )

    df.columns = [c.lower().strip() for c in df.columns]
    option_cols = ["option_a", "option_b", "option_c", "option_d", "option_e", "option_f"]
    letter_map = {"A": 0, "B": 1, "C": 2, "D": 3, "E": 4, "F": 5}

    for row_num, row in df.iterrows():
        q_text = str(row.get("question", "")).strip()
        q_type = str(row.get("type", "")).strip().lower()

        if not q_text or q_text == "nan":
            errors.append(f"Row {row_num + 2}: empty question, skipped")
            continue
        if q_type not in ("mcq", "short_answer"):
            errors.append(f"Row {row_num + 2}: unknown type '{q_type}', skipped")
            continue

        points = 1
        try:
            points = max(1, min(100, int(row.get("points", 1))))
        except (ValueError, TypeError):
            pass

        if q_type == "mcq":
            options_text = [
                str(row.get(col, "")).strip()
                for col in option_cols
                if str(row.get(col, "")).strip() not in ("", "nan")
            ]
            correct_raw = str(row.get("correct", "")).strip().upper()
            correct_index = letter_map.get(correct_raw)

            if not options_text:
                errors.append(f"Row {row_num + 2}: MCQ has no options, skipped")
                continue

            options = [
                OptionIn(text=t, is_correct=(i == correct_index))
                for i, t in enumerate(options_text)
            ]
            questions.append(ImportedQuestion(
                text=q_text,
                question_type="mcq",
                options=options,
                points=points,
            ))
        else:
            correct_answer = str(row.get("correct", "")).strip()
            questions.append(ImportedQuestion(
                text=q_text,
                question_type="short_answer",
                correct_answer=correct_answer if correct_answer and correct_answer != "nan" else None,
                points=points,
            ))

    return ImportPreview(questions=questions, errors=errors)


def parse_pdf(content: bytes) -> ImportPreview:
    try:
        with pdfplumber.open(io.BytesIO(content)) as pdf:
            lines = []
            for page in pdf.pages:
                text = page.extract_text() or ""
                lines.extend(text.splitlines())
    except Exception as exc:
        logger.warning("Failed to parse PDF: %s", exc)
        raise HTTPException(status_code=400, detail="Could not read PDF — it may be encrypted or corrupted")

    questions: list[ImportedQuestion] = []
    errors: list[str] = []

    current_question: str | None = None
    current_options: list[OptionIn] = []
    correct_letter: str | None = None

    option_re = re.compile(r"^([A-Fa-f])[).]\s+(.+)$")
    question_re = re.compile(r"^\d+[.)]\s+(.+)$")
    answer_re = re.compile(r"^[Aa]nswer[:\s]+([A-Fa-f]|.+)$")
    letter_map = {"a": 0, "b": 1, "c": 2, "d": 3, "e": 4, "f": 5}

    def flush():
        if current_question is None:
            return
        if current_options:
            correct_idx = letter_map.get(correct_letter.lower()) if correct_letter else None
            questions.append(ImportedQuestion(
                text=current_question,
                question_type="mcq",
                options=[
                    OptionIn(text=o.text, is_correct=(i == correct_idx))
                    for i, o in enumerate(current_options)
                ],
            ))
        else:
            questions.append(ImportedQuestion(
                text=current_question,
                question_type="short_answer",
            ))

    for line in lines:
        line = line.strip()
        if not line:
            continue

        if m := answer_re.match(line):
            correct_letter = m.group(1).strip()
            continue

        if m := option_re.match(line):
            current_options.append(OptionIn(text=m.group(2).strip()))
            continue

        if m := question_re.match(line):
            flush()
            current_question = m.group(1).strip()
            current_options = []
            correct_letter = None
            continue

    flush()
    return ImportPreview(questions=questions, errors=errors)


@router.post("/csv", response_model=ImportPreview)
@limiter.limit("5/minute")
async def import_csv(request: Request, file: UploadFile = File(...)):
    if not file.filename or not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Expected a .csv file")
    content = await file.read()
    check_size(content, file.filename)
    return parse_csv_or_excel(content, file.filename)


@router.post("/excel", response_model=ImportPreview)
@limiter.limit("5/minute")
async def import_excel(request: Request, file: UploadFile = File(...)):
    if not file.filename or not file.filename.endswith((".xlsx", ".xls")):
        raise HTTPException(status_code=400, detail="Expected an .xlsx or .xls file")
    content = await file.read()
    check_size(content, file.filename)
    if file.filename.endswith(".xlsx"):
        check_magic(content, XLSX_MAGIC, "Excel file")
    return parse_csv_or_excel(content, file.filename)


@router.post("/pdf", response_model=ImportPreview)
@limiter.limit("5/minute")
async def import_pdf(request: Request, file: UploadFile = File(...)):
    if not file.filename or not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Expected a .pdf file")
    content = await file.read()
    check_size(content, file.filename)
    check_magic(content, PDF_MAGIC, "PDF file")
    return parse_pdf(content)
