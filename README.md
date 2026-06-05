# Quizzy

A quiz platform built with FastAPI and vanilla JavaScript.

## Features

- Create quizzes manually or import questions from CSV, Excel, or PDF
- MCQ and short-answer question types
- Shareable quiz links for participants
- Timed quizzes with auto-submit
- Leaderboards ranked by score and completion time
- Built-in floating calculator on all pages

## Project Structure

```
quizzy/
├── backend/
│   ├── main.py           # FastAPI app, serves frontend as static files
│   ├── models.py         # MongoDB documents (Quiz, Session)
│   ├── schemas.py        # Pydantic request/response shapes
│   ├── requirements.txt
│   └── routers/
│       ├── quizzes.py    # Quiz and question CRUD
│       ├── sessions.py   # Taking quizzes, scoring, leaderboard
│       └── imports.py    # CSV / Excel / PDF import
└── frontend/
    ├── index.html        # Dashboard
    ├── create.html       # Quiz builder
    ├── take.html         # Take a quiz (public, via share link)
    ├── leaderboard.html  # Leaderboard
    ├── style.css
    └── js/
        ├── api.js        # All API calls in one place
        ├── calculator.js # Floating calculator widget
        ├── timer.js      # Countdown timer
        ├── dashboard.js
        ├── create.js
        ├── take.js
        └── leaderboard.js
```

## Setup

### Requirements
- Python 3.10+
- A MongoDB Atlas cluster (free tier works fine)

### Install

```bash
cd backend
pip install -r requirements.txt
```

### Configure

Create `backend/.env` from the example:

```bash
cp backend/.env.example backend/.env
```

Edit `.env` and paste your MongoDB Atlas connection string:

```
MONGO_URL=mongodb+srv://<user>:<password>@<cluster>.mongodb.net/?retryWrites=true&w=majority
```

### Run

```bash
cd backend
uvicorn main:app --reload
```

Open [http://localhost:8000](http://localhost:8000).

## Import Format

### CSV / Excel

One question per row:

| question | type | option_a | option_b | option_c | option_d | correct | points |
|---|---|---|---|---|---|---|---|
| What is 2+2? | mcq | 3 | 4 | 5 | 6 | B | 1 |
| Explain gravity | short_answer | | | | | gravitational force | 2 |

`correct` for MCQ is the letter (A–F) of the correct option.

### PDF

The parser looks for:
- Lines starting with `1.` `2.` etc → question text
- Lines starting with `A)` `B)` `C)` `D)` → MCQ options
- Lines starting with `Answer:` → correct answer

Questions with no options are treated as short-answer.

## API

Interactive docs available at [http://localhost:8000/docs](http://localhost:8000/docs) when the server is running.

Key endpoints:

| Method | Path | Description |
|---|---|---|
| GET | `/api/quizzes/` | List all quizzes |
| POST | `/api/quizzes/` | Create a quiz |
| GET | `/api/quizzes/{id}` | Get quiz with questions |
| GET | `/api/quizzes/public/{token}` | Get quiz by share token (for takers) |
| POST | `/api/quizzes/{id}/questions` | Add a question |
| POST | `/api/sessions/` | Start a quiz session |
| POST | `/api/sessions/{id}/submit` | Submit answers and get score |
| GET | `/api/sessions/quiz/{id}/leaderboard` | Get leaderboard |
| POST | `/api/import/csv` | Parse a CSV file (preview) |
| POST | `/api/import/excel` | Parse an Excel file (preview) |
| POST | `/api/import/pdf` | Parse a PDF file (preview) |
| POST | `/api/quizzes/{id}/import` | Commit imported questions |
