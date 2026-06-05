import io
import re
from fastapi import APIRouter, UploadFile, File, HTTPException
from schemas import ImportPreview, ImportedQuestion, OptionIn

router = APIRouter(prefix="/api/import", tags=["import"])


def _parse_csv_or_excel(content: bytes, filename: str) -> ImportPreview:
    import pandas as pd

    try:
        if filename.endswith(".csv"):
            df = pd.read_csv(io.BytesIO(content))
        else:
            df = pd.read_excel(io.BytesIO(content))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Could not parse file: {e}")

    questions = []
    errors = []
    required_cols = {"question", "type"}
    actual_cols = {c.lower().strip() for c in df.columns}

    if not required_cols.issubset(actual_cols):
        raise HTTPException(
            status_code=400,
            detail=f"File must have at least columns: question, type. Found: {list(df.columns)}"
        )

    # normalise column names to lowercase
    df.columns = [c.lower().strip() for c in df.columns]

    option_cols = ["option_a", "option_b", "option_c", "option_d", "option_e", "option_f"]

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
            points = int(row.get("points", 1))
        except (ValueError, TypeError):
            pass

        if q_type == "mcq":
            # read options A-F
            options_text = []
            for col in option_cols:
                val = str(row.get(col, "")).strip()
                if val and val != "nan":
                    options_text.append(val)

            correct_raw = str(row.get("correct", "")).strip().upper()
            # correct can be "B" or "option_b" or the option text itself
            correct_index = None
            letter_map = {"A": 0, "B": 1, "C": 2, "D": 3, "E": 4, "F": 5}
            if correct_raw in letter_map:
                correct_index = letter_map[correct_raw]

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
            if correct_answer == "nan":
                correct_answer = ""
            questions.append(ImportedQuestion(
                text=q_text,
                question_type="short_answer",
                correct_answer=correct_answer or None,
                points=points,
            ))

    return ImportPreview(questions=questions, errors=errors)


def _parse_pdf(content: bytes) -> ImportPreview:
    try:
        import pdfplumber
    except ImportError:
        raise HTTPException(status_code=500, detail="pdfplumber not installed")

    try:
        with pdfplumber.open(io.BytesIO(content)) as pdf:
            lines = []
            for page in pdf.pages:
                text = page.extract_text() or ""
                lines.extend(text.splitlines())
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Could not read PDF: {e}")

    questions = []
    errors = []

    current_question = None
    current_options: list[OptionIn] = []
    correct_letter = None

    option_pattern = re.compile(r"^([A-Fa-f])[).]\s+(.+)$")
    question_pattern = re.compile(r"^\d+[.)]\s+(.+)$")
    answer_pattern = re.compile(r"^[Aa]nswer[:\s]+([A-Fa-f]|.+)$")

    def flush_question():
        if current_question is None:
            return
        if current_options:
            correct_index = None
            if correct_letter:
                letter_map = {"a": 0, "b": 1, "c": 2, "d": 3, "e": 4, "f": 5}
                correct_index = letter_map.get(correct_letter.lower())
            opts = [
                OptionIn(text=o.text, is_correct=(i == correct_index))
                for i, o in enumerate(current_options)
            ]
            questions.append(ImportedQuestion(
                text=current_question,
                question_type="mcq",
                options=opts,
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

        ans_match = answer_pattern.match(line)
        if ans_match:
            correct_letter = ans_match.group(1).strip()
            continue

        opt_match = option_pattern.match(line)
        if opt_match:
            current_options.append(OptionIn(text=opt_match.group(2).strip()))
            continue

        q_match = question_pattern.match(line)
        if q_match:
            flush_question()
            current_question = q_match.group(1).strip()
            current_options = []
            correct_letter = None
            continue

    flush_question()
    return ImportPreview(questions=questions, errors=errors)


@router.post("/csv", response_model=ImportPreview)
async def import_csv(file: UploadFile = File(...)):
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Expected a .csv file")
    content = await file.read()
    return _parse_csv_or_excel(content, file.filename)


@router.post("/excel", response_model=ImportPreview)
async def import_excel(file: UploadFile = File(...)):
    if not file.filename.endswith((".xlsx", ".xls")):
        raise HTTPException(status_code=400, detail="Expected an .xlsx or .xls file")
    content = await file.read()
    return _parse_csv_or_excel(content, file.filename)


@router.post("/pdf", response_model=ImportPreview)
async def import_pdf(file: UploadFile = File(...)):
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Expected a .pdf file")
    content = await file.read()
    return _parse_pdf(content)
