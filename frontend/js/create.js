import { api } from "./api.js";
import { initCalculator } from "./calculator.js";

initCalculator();

const params = new URLSearchParams(location.search);
let quizId = params.get("id");  // null if creating new

let currentQuiz = null;
let importedQuestions = [];

// --- Elements ---
const pageTitle = document.getElementById("page-title");
const titleInput = document.getElementById("title");
const descInput = document.getElementById("description");
const timeLimitInput = document.getElementById("time-limit");
const saveMetaBtn = document.getElementById("save-meta-btn");
const saveStatus = document.getElementById("save-status");
const importSection = document.getElementById("import-section");
const questionsSection = document.getElementById("questions-section");
const questionsList = document.getElementById("questions-list");
const noQuestions = document.getElementById("no-questions");

// --- Load existing quiz if editing ---
if (quizId) {
  pageTitle.textContent = "Edit Quiz";
  api.getQuiz(quizId).then((quiz) => {
    currentQuiz = quiz;
    titleInput.value = quiz.title;
    descInput.value = quiz.description || "";
    timeLimitInput.value = quiz.time_limit_minutes || "";
    showQuizSections();
    renderQuestions(quiz.questions);
  }).catch((err) => alert("Failed to load quiz: " + err.message));
}

// --- Save quiz metadata ---
saveMetaBtn.addEventListener("click", async () => {
  const title = titleInput.value.trim();
  if (!title) { alert("Title is required."); return; }

  const data = {
    title,
    description: descInput.value.trim(),
    time_limit_minutes: timeLimitInput.value ? parseInt(timeLimitInput.value) : null,
  };

  saveMetaBtn.disabled = true;
  saveStatus.textContent = "Saving…";

  try {
    if (quizId) {
      currentQuiz = await api.updateQuiz(quizId, data);
    } else {
      currentQuiz = await api.createQuiz(data);
      quizId = currentQuiz.id;
      history.replaceState(null, "", `?id=${quizId}`);
    }
    saveStatus.textContent = "Saved!";
    pageTitle.textContent = "Edit Quiz";
    showQuizSections();
    renderQuestions(currentQuiz.questions);
  } catch (err) {
    saveStatus.textContent = "Error: " + err.message;
  } finally {
    saveMetaBtn.disabled = false;
    setTimeout(() => saveStatus.textContent = "", 3000);
  }
});

function showQuizSections() {
  importSection.style.display = "";
  questionsSection.style.display = "";
}

// --- Render questions ---
function renderQuestions(questions) {
  questionsList.innerHTML = "";
  const sorted = [...questions].sort((a, b) => a.order_index - b.order_index);
  if (sorted.length === 0) {
    noQuestions.style.display = "";
  } else {
    noQuestions.style.display = "none";
    for (const q of sorted) {
      questionsList.appendChild(buildQuestionEl(q));
    }
  }
}

function buildQuestionEl(question) {
  const el = document.createElement("div");
  el.className = "question-item";
  el.dataset.id = question.id;

  const typeLabel = question.question_type === "mcq" ? "MCQ" : "Short Answer";
  const typeCls = question.question_type === "mcq" ? "mcq" : "short-answer";

  el.innerHTML = `
    <div class="q-header">
      <span class="q-badge ${typeCls}">${typeLabel}</span>
      <span style="flex:1;font-weight:500">${escHtml(question.text)}</span>
      <button class="btn btn-ghost btn-sm edit-btn">Edit</button>
      <button class="btn btn-danger btn-sm delete-btn">Delete</button>
    </div>
    <div class="q-body">
      ${renderQuestionPreview(question)}
    </div>
    <div class="q-edit-form" style="display:none"></div>
  `;

  el.querySelector(".delete-btn").addEventListener("click", async () => {
    if (!confirm("Delete this question?")) return;
    try {
      const updated = await api.deleteQuestion(quizId, question.id);
      currentQuiz = updated;
      renderQuestions(updated.questions);
    } catch (err) {
      alert("Delete failed: " + err.message);
    }
  });

  el.querySelector(".edit-btn").addEventListener("click", () => {
    const formDiv = el.querySelector(".q-edit-form");
    const bodyDiv = el.querySelector(".q-body");
    if (formDiv.style.display === "none") {
      formDiv.style.display = "";
      bodyDiv.style.display = "none";
      formDiv.innerHTML = "";
      formDiv.appendChild(buildEditForm(question, async (updated) => {
        try {
          const result = await api.updateQuestion(quizId, question.id, updated);
          currentQuiz = result;
          renderQuestions(result.questions);
        } catch (err) {
          alert("Save failed: " + err.message);
        }
      }, () => {
        formDiv.style.display = "none";
        bodyDiv.style.display = "";
      }));
    } else {
      formDiv.style.display = "none";
      bodyDiv.style.display = "";
    }
  });

  return el;
}

function renderQuestionPreview(q) {
  if (q.question_type === "mcq") {
    const opts = q.options.map((o) =>
      `<div class="option-row">
        <span style="color:${o.is_correct ? "var(--success)" : "var(--text-muted)"}">
          ${o.is_correct ? "✓" : "○"}
        </span>
        <span>${escHtml(o.text)}</span>
      </div>`
    ).join("");
    return opts || "<span class='text-muted'>No options yet</span>";
  }
  return `<span class="text-muted">Expected answer: ${escHtml(q.correct_answer || "—")}</span>`;
}

function buildEditForm(question, onSave, onCancel) {
  const wrapper = document.createElement("div");
  const isMcq = question.question_type === "mcq";

  wrapper.innerHTML = `
    <div class="form-group">
      <label>Question Text</label>
      <textarea class="q-text-input" rows="2">${escHtml(question.text)}</textarea>
    </div>
    <div class="form-group">
      <label>Points</label>
      <input type="number" class="q-points-input" value="${question.points}" min="1" style="max-width:100px" />
    </div>
    ${isMcq ? buildMcqOptionsHtml(question.options) : buildShortAnswerHtml(question.correct_answer)}
    <div style="display:flex;gap:0.5rem;margin-top:0.75rem">
      <button class="btn btn-primary btn-sm save-edit-btn">Save</button>
      <button class="btn btn-ghost btn-sm cancel-edit-btn">Cancel</button>
    </div>
  `;

  if (isMcq) initOptionButtons(wrapper);

  wrapper.querySelector(".save-edit-btn").addEventListener("click", () => {
    const text = wrapper.querySelector(".q-text-input").value.trim();
    const points = parseInt(wrapper.querySelector(".q-points-input").value) || 1;
    if (!text) { alert("Question text required"); return; }

    if (isMcq) {
      const optRows = wrapper.querySelectorAll(".mcq-option-row");
      const options = [];
      let hasCorrect = false;
      for (const row of optRows) {
        const t = row.querySelector("input[type='text']").value.trim();
        const correct = row.querySelector("input[type='radio']").checked;
        if (t) { options.push({ text: t, is_correct: correct }); if (correct) hasCorrect = true; }
      }
      if (options.length < 2) { alert("MCQ needs at least 2 options"); return; }
      if (!hasCorrect) { alert("Mark one option as correct"); return; }
      onSave({ text, question_type: "mcq", options, points });
    } else {
      const correct_answer = wrapper.querySelector(".q-correct-input").value.trim();
      onSave({ text, question_type: "short_answer", correct_answer, points });
    }
  });

  wrapper.querySelector(".cancel-edit-btn").addEventListener("click", onCancel);
  return wrapper;
}

function buildMcqOptionsHtml(existingOptions = []) {
  const rows = existingOptions.length > 0
    ? existingOptions.map((o, i) => mcqOptionRowHtml(i, o.text, o.is_correct)).join("")
    : mcqOptionRowHtml(0, "", false) + mcqOptionRowHtml(1, "", false);

  return `
    <div class="form-group">
      <label>Options (select the correct one)</label>
      <div class="mcq-options-container">
        ${rows}
      </div>
      <button type="button" class="btn btn-ghost btn-sm add-option-btn mt-2">+ Add Option</button>
    </div>`;
}

function mcqOptionRowHtml(index, text = "", isCorrect = false) {
  return `
    <div class="option-row mcq-option-row">
      <input type="radio" name="correct-option" ${isCorrect ? "checked" : ""} />
      <input type="text" value="${escHtml(text)}" placeholder="Option ${index + 1}" />
      <button type="button" class="btn btn-danger btn-sm remove-option-btn">✕</button>
    </div>`;
}

function buildShortAnswerHtml(correctAnswer = "") {
  return `
    <div class="form-group">
      <label>Expected Answer (case-insensitive match)</label>
      <input type="text" class="q-correct-input" value="${escHtml(correctAnswer || "")}" placeholder="Correct answer" />
    </div>`;
}

function initOptionButtons(container) {
  container.querySelector(".add-option-btn").addEventListener("click", () => {
    const optContainer = container.querySelector(".mcq-options-container");
    const count = optContainer.querySelectorAll(".mcq-option-row").length;
    if (count >= 6) { alert("Maximum 6 options"); return; }
    const div = document.createElement("div");
    div.innerHTML = mcqOptionRowHtml(count);
    const row = div.firstElementChild;
    row.querySelector(".remove-option-btn").addEventListener("click", () => row.remove());
    optContainer.appendChild(row);
  });

  container.querySelectorAll(".remove-option-btn").forEach((btn) => {
    btn.addEventListener("click", () => btn.closest(".mcq-option-row").remove());
  });
}

// --- Add question buttons ---
function startAddQuestion(type) {
  if (!quizId) { alert("Save quiz details first."); return; }

  const skeleton = type === "mcq"
    ? { id: null, text: "", question_type: "mcq", options: [], points: 1, order_index: 999 }
    : { id: null, text: "", question_type: "short_answer", correct_answer: "", points: 1, order_index: 999 };

  const wrapper = document.createElement("div");
  wrapper.className = "question-item";
  wrapper.style.borderColor = "var(--primary)";

  const form = buildEditForm(skeleton, async (data) => {
    try {
      const updated = await api.addQuestion(quizId, data);
      currentQuiz = updated;
      wrapper.remove();
      renderQuestions(updated.questions);
    } catch (err) {
      alert("Failed to add: " + err.message);
    }
  }, () => wrapper.remove());

  wrapper.appendChild(form);
  questionsList.prepend(wrapper);
  noQuestions.style.display = "none";
}

document.getElementById("add-mcq-btn").addEventListener("click", () => startAddQuestion("mcq"));
document.getElementById("add-sa-btn").addEventListener("click", () => startAddQuestion("short_answer"));

// --- Import ---
function setupImportInput(inputEl, apiFn) {
  inputEl.addEventListener("change", async () => {
    const file = inputEl.files[0];
    if (!file) return;
    inputEl.value = "";
    try {
      const preview = await apiFn(file);
      showImportPreview(preview);
    } catch (err) {
      alert("Import failed: " + err.message);
    }
  });
}

setupImportInput(document.getElementById("import-csv"), api.importCsv);
setupImportInput(document.getElementById("import-excel"), api.importExcel);
setupImportInput(document.getElementById("import-pdf"), api.importPdf);

function showImportPreview(preview) {
  importedQuestions = preview.questions;
  const previewDiv = document.getElementById("import-preview");
  const list = document.getElementById("preview-list");
  const countEl = document.getElementById("preview-count");
  const errorsEl = document.getElementById("import-errors");

  countEl.textContent = preview.questions.length;
  list.innerHTML = preview.questions.map((q, i) => {
    const type = q.question_type === "mcq" ? "MCQ" : "Short Answer";
    const opts = q.options && q.options.length
      ? `<div class="text-muted" style="font-size:0.8rem">${q.options.map((o) => (o.is_correct ? "✓ " : "○ ") + o.text).join(" &nbsp; ")}</div>`
      : "";
    return `
      <div class="import-preview-item">
        <strong>Q${i + 1}</strong> <span class="q-badge ${q.question_type === "mcq" ? "mcq" : "short-answer"}">${type}</span>
        ${escHtml(q.text)}
        ${opts}
        ${q.correct_answer ? `<div class="text-muted" style="font-size:0.8rem">Answer: ${escHtml(q.correct_answer)}</div>` : ""}
      </div>`;
  }).join("");

  errorsEl.innerHTML = preview.errors && preview.errors.length
    ? preview.errors.map((e) => `<div>${escHtml(e)}</div>`).join("")
    : "";

  previewDiv.style.display = "";
}

document.getElementById("confirm-import-btn").addEventListener("click", async () => {
  if (!quizId) { alert("Save quiz details first."); return; }
  try {
    const updated = await api.importQuestions(quizId, { questions: importedQuestions });
    currentQuiz = updated;
    renderQuestions(updated.questions);
    document.getElementById("import-preview").style.display = "none";
    importedQuestions = [];
  } catch (err) {
    alert("Import failed: " + err.message);
  }
});

document.getElementById("cancel-import-btn").addEventListener("click", () => {
  document.getElementById("import-preview").style.display = "none";
  importedQuestions = [];
});

function escHtml(str) {
  const d = document.createElement("div");
  d.textContent = str || "";
  return d.innerHTML;
}
