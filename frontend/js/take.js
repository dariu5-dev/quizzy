import { api } from "./api.js";
import { initCalculator } from "./calculator.js";
import { createTimer } from "./timer.js";

initCalculator();

const params = new URLSearchParams(location.search);
const token = params.get("token");

if (!token) {
  document.body.innerHTML = '<div class="page"><p class="text-danger">No quiz token provided.</p></div>';
  throw new Error("no token");
}

let quiz = null;
let sessionId = null;
let timer = null;
let timerStarted = false;

// --- Elements ---
const nameScreen = document.getElementById("name-screen");
const quizScreen = document.getElementById("quiz-screen");
const resultsScreen = document.getElementById("results-screen");
const nameInput = document.getElementById("participant-name");
const startBtn = document.getElementById("start-btn");
const timerDisplay = document.getElementById("timer-display");
const progressLabel = document.getElementById("progress-label");
const progressBarFill = document.getElementById("progress-bar-fill");
const questionsContainer = document.getElementById("questions-container");
const submitRow = document.getElementById("submit-row");
const submitBtn = document.getElementById("submit-btn");

// --- Load quiz ---
try {
  quiz = await api.getQuizPublic(token);
  document.getElementById("quiz-title-name").textContent = quiz.title;
  document.title = `Quizzy — ${quiz.title}`;

  if (quiz.description) {
    document.getElementById("quiz-desc-name").textContent = quiz.description;
  }

  const meta = document.getElementById("quiz-meta-name");
  const qCount = quiz.questions.length;
  const timeStr = quiz.time_limit_minutes ? `${quiz.time_limit_minutes} minute limit` : "Untimed";
  meta.innerHTML = `
    <span class="tag tag-blue">${qCount} question${qCount !== 1 ? "s" : ""}</span>
    &nbsp;
    <span class="tag tag-gray">${timeStr}</span>
  `;
} catch (err) {
  document.body.innerHTML = `<div class="page"><p class="text-danger">Could not load quiz: ${err.message}</p></div>`;
  throw err;
}

// --- Start quiz ---
startBtn.addEventListener("click", async () => {
  const name = nameInput.value.trim();
  if (!name) { nameInput.focus(); return; }

  startBtn.disabled = true;
  try {
    const res = await api.startSession(quiz.id, name);
    sessionId = res.session_id;
    showQuizScreen();
  } catch (err) {
    alert("Could not start quiz: " + err.message);
    startBtn.disabled = false;
  }
});

nameInput.addEventListener("keydown", (e) => {
  if (e.key === "Enter") startBtn.click();
});

function showQuizScreen() {
  nameScreen.style.display = "none";
  quizScreen.style.display = "";

  document.getElementById("quiz-title-take").textContent = quiz.title;

  const sorted = [...quiz.questions].sort((a, b) => a.order_index - b.order_index);
  renderQuestions(sorted);
  updateProgress(sorted.length);
  submitRow.style.display = "";

  if (quiz.time_limit_minutes) {
    const totalSeconds = quiz.time_limit_minutes * 60;
    timerDisplay.style.display = "";

    timer = createTimer(
      totalSeconds,
      (formatted, remaining) => {
        timerDisplay.textContent = formatted;
        timerDisplay.className = "timer";
        if (remaining <= 60) timerDisplay.classList.add("danger");
        else if (remaining <= 180) timerDisplay.classList.add("warning");
      },
      () => {
        // time's up — auto submit
        submitQuiz(true);
      }
    );
    timer.start();
    timerStarted = true;
  }
}

function renderQuestions(questions) {
  questionsContainer.innerHTML = "";
  for (const q of questions) {
    questionsContainer.appendChild(buildQuestionCard(q));
  }

  // Update progress when any answer changes
  questionsContainer.addEventListener("change", () => {
    updateProgress(questions.length);
  });
  questionsContainer.addEventListener("input", () => {
    updateProgress(questions.length);
  });
}

function buildQuestionCard(q) {
  const card = document.createElement("div");
  card.className = "question-card";
  card.dataset.qid = q.id;

  const num = q.order_index + 1;
  card.innerHTML = `
    <div class="q-number">Question ${num}</div>
    <div class="q-text">${escHtml(q.text)}</div>
    <div class="q-answer-area"></div>
  `;

  const answerArea = card.querySelector(".q-answer-area");

  if (q.question_type === "mcq") {
    for (const opt of q.options) {
      const label = document.createElement("label");
      label.className = "option-choice";
      label.innerHTML = `
        <input type="radio" name="q-${q.id}" value="${opt.id}" />
        <span>${escHtml(opt.text)}</span>
      `;
      label.querySelector("input").addEventListener("change", () => {
        card.querySelectorAll(".option-choice").forEach((l) => l.classList.remove("selected"));
        label.classList.add("selected");
      });
      answerArea.appendChild(label);
    }
  } else {
    const textarea = document.createElement("textarea");
    textarea.rows = 3;
    textarea.placeholder = "Type your answer here…";
    textarea.dataset.qid = q.id;
    answerArea.appendChild(textarea);
  }

  return card;
}

function updateProgress(total) {
  let answered = 0;
  const cards = questionsContainer.querySelectorAll(".question-card");
  for (const card of cards) {
    const qid = card.dataset.qid;
    const radio = card.querySelector(`input[type="radio"]:checked`);
    const textarea = card.querySelector("textarea");
    if (radio || (textarea && textarea.value.trim())) answered++;
  }
  const pct = total > 0 ? Math.round((answered / total) * 100) : 0;
  progressBarFill.style.width = pct + "%";
  progressLabel.textContent = `${answered} / ${total} answered`;
}

// --- Submit ---
submitBtn.addEventListener("click", () => submitQuiz(false));

async function submitQuiz(autoSubmit) {
  if (!autoSubmit && !confirm("Submit your answers?")) return;

  submitBtn.disabled = true;
  if (timer) timer.stop();
  const timeTaken = timer ? timer.elapsed() : null;

  const answers = [];
  for (const card of questionsContainer.querySelectorAll(".question-card")) {
    const qid = card.dataset.qid;
    const radio = card.querySelector(`input[type="radio"]:checked`);
    const textarea = card.querySelector("textarea");

    if (radio) {
      answers.push({ question_id: qid, selected_option_id: radio.value });
    } else if (textarea) {
      answers.push({ question_id: qid, text_answer: textarea.value.trim() });
    } else {
      answers.push({ question_id: qid });
    }
  }

  try {
    const result = await api.submitSession(sessionId, answers, timeTaken);
    showResults(result);
  } catch (err) {
    alert("Submit failed: " + err.message);
    submitBtn.disabled = false;
    if (timer && timerStarted) timer.start();
  }
}

function showResults(result) {
  quizScreen.style.display = "none";
  resultsScreen.style.display = "";

  const pct = result.percentage;
  const passed = pct >= 50;
  const banner = document.getElementById("result-banner");
  banner.className = `result-banner mb-4 ${passed ? "pass" : "fail"}`;
  document.getElementById("result-score").textContent = `${result.score} / ${result.max_score}`;
  document.getElementById("result-label").textContent = `${pct}% — ${passed ? "Well done!" : "Keep practising!"}`;

  const reviewEl = document.getElementById("answers-review");
  const sorted = [...quiz.questions].sort((a, b) => a.order_index - b.order_index);

  reviewEl.innerHTML = "<h2>Answer Review</h2>";
  for (const q of sorted) {
    const answer = result.answers.find((a) => a.question_id === q.id);
    if (!answer) continue;
    const div = document.createElement("div");
    div.className = `card answer-review mt-4 ${answer.is_correct ? "correct" : "wrong"}`;
    div.innerHTML = `
      <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:1rem">
        <p><strong>Q${q.order_index + 1}.</strong> ${escHtml(q.text)}</p>
        <span style="font-size:1.25rem">${answer.is_correct ? "✅" : "❌"}</span>
      </div>
      ${answer.correct_answer
        ? `<p class="text-muted mt-2" style="font-size:0.875rem">Correct answer: <strong>${escHtml(answer.correct_answer)}</strong></p>`
        : ""}
    `;
    reviewEl.appendChild(div);
  }

  document.getElementById("leaderboard-link").href =
    `/leaderboard.html?id=${quiz.id}`;
}

function escHtml(str) {
  const d = document.createElement("div");
  d.textContent = str || "";
  return d.innerHTML;
}
