import { api } from "./api.js";
import { initCalculator } from "./calculator.js";

initCalculator();

const params = new URLSearchParams(location.search);
const quizId = params.get("id");

const body = document.getElementById("leaderboard-body");
const lastUpdated = document.getElementById("last-updated");
const titleEl = document.getElementById("quiz-title");

if (!quizId) {
  body.innerHTML = '<tr><td colspan="6" class="text-danger">No quiz ID provided.</td></tr>';
  throw new Error("no quiz id");
}

// Load quiz name
api.getQuiz(quizId)
  .then((quiz) => {
    titleEl.textContent = `Leaderboard — ${quiz.title}`;
    document.title = `Quizzy — ${quiz.title} Leaderboard`;
  })
  .catch(() => {});

function rankEmoji(rank) {
  if (rank === 1) return "🥇";
  if (rank === 2) return "🥈";
  if (rank === 3) return "🥉";
  return rank;
}

function formatTime(secs) {
  if (secs == null) return "—";
  const m = Math.floor(secs / 60);
  const s = secs % 60;
  return m > 0 ? `${m}m ${s}s` : `${s}s`;
}

function formatDate(iso) {
  if (!iso) return "—";
  return new Date(iso).toLocaleString();
}

async function load() {
  try {
    const entries = await api.getLeaderboard(quizId);
    if (entries.length === 0) {
      body.innerHTML = '<tr><td colspan="6" style="text-align:center;color:var(--text-muted);padding:2rem">No completed attempts yet.</td></tr>';
      return;
    }
    body.innerHTML = entries.map((e) => `
      <tr>
        <td class="${e.rank <= 3 ? "rank-" + e.rank : ""}">${rankEmoji(e.rank)}</td>
        <td>${escHtml(e.participant_name)}</td>
        <td>${e.score} / ${e.max_score}</td>
        <td>${e.percentage}%</td>
        <td>${formatTime(e.time_taken_seconds)}</td>
        <td>${formatDate(e.completed_at)}</td>
      </tr>
    `).join("");
    lastUpdated.textContent = `Last updated: ${new Date().toLocaleTimeString()}`;
  } catch (err) {
    body.innerHTML = `<tr><td colspan="6" class="text-danger">Failed to load: ${escHtml(err.message)}</td></tr>`;
  }
}

document.getElementById("refresh-btn").addEventListener("click", load);

// Auto-refresh every 30s
load();
setInterval(load, 30000);

function escHtml(str) {
  const d = document.createElement("div");
  d.textContent = str || "";
  return d.innerHTML;
}
