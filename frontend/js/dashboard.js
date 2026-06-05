import { api } from "./api.js";
import { initCalculator } from "./calculator.js";

initCalculator();

const grid = document.getElementById("quiz-grid");

function shareUrl(token) {
  return `${location.origin}/take.html?token=${token}`;
}

function formatTime(mins) {
  if (!mins) return "Untimed";
  return mins >= 60 ? `${Math.floor(mins / 60)}h ${mins % 60}m` : `${mins}m`;
}

function renderQuiz(quiz) {
  const card = document.createElement("div");
  card.className = "quiz-card";
  const url = shareUrl(quiz.share_token);

  card.innerHTML = `
    <div>
      <h3>${escHtml(quiz.title)}</h3>
      <p class="meta">
        ${quiz.question_count} question${quiz.question_count !== 1 ? "s" : ""} &nbsp;·&nbsp;
        ${formatTime(quiz.time_limit_minutes)}
      </p>
      ${quiz.description ? `<p class="text-muted mt-2">${escHtml(quiz.description)}</p>` : ""}
    </div>
    <div class="share-link-box">
      <span title="${url}">${url}</span>
      <button class="btn btn-ghost btn-sm copy-btn" data-url="${url}">Copy</button>
    </div>
    <div class="actions">
      <a href="/create.html?id=${quiz.id}" class="btn btn-ghost btn-sm">Edit</a>
      <a href="/leaderboard.html?id=${quiz.id}" class="btn btn-ghost btn-sm">Leaderboard</a>
      <button class="btn btn-danger btn-sm delete-btn" data-id="${quiz.id}">Delete</button>
    </div>
  `;

  card.querySelector(".copy-btn").addEventListener("click", async (e) => {
    const btn = e.currentTarget;
    await navigator.clipboard.writeText(btn.dataset.url).catch(() => {});
    btn.textContent = "Copied!";
    setTimeout(() => btn.textContent = "Copy", 2000);
  });

  card.querySelector(".delete-btn").addEventListener("click", async (e) => {
    if (!confirm(`Delete "${quiz.title}"? This cannot be undone.`)) return;
    const btn = e.currentTarget;
    btn.disabled = true;
    try {
      await api.deleteQuiz(quiz.id);
      card.remove();
      if (!grid.querySelector(".quiz-card")) showEmpty();
    } catch (err) {
      alert("Delete failed: " + err.message);
      btn.disabled = false;
    }
  });

  return card;
}

function showEmpty() {
  grid.innerHTML = `
    <div class="empty-state">
      <p>No quizzes yet.</p>
      <a href="/create.html" class="btn btn-primary">Create your first quiz</a>
    </div>`;
}

function escHtml(str) {
  const d = document.createElement("div");
  d.textContent = str;
  return d.innerHTML;
}

async function load() {
  try {
    const quizzes = await api.listQuizzes();
    grid.innerHTML = "";
    if (quizzes.length === 0) {
      showEmpty();
      return;
    }
    for (const q of quizzes) {
      grid.appendChild(renderQuiz(q));
    }
  } catch (err) {
    grid.innerHTML = `<div class="empty-state text-danger">Failed to load: ${err.message}</div>`;
  }
}

load();
