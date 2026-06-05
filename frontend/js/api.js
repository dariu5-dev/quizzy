const BASE = "";  // same origin

async function request(method, path, body = null) {
  const opts = {
    method,
    headers: body ? { "Content-Type": "application/json" } : {},
  };
  if (body) opts.body = JSON.stringify(body);
  const res = await fetch(BASE + path, opts);
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || res.statusText);
  }
  if (res.status === 204) return null;
  return res.json();
}

async function uploadFile(path, file) {
  const form = new FormData();
  form.append("file", file);
  const res = await fetch(BASE + path, { method: "POST", body: form });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || res.statusText);
  }
  return res.json();
}

// --- Quizzes ---
export const api = {
  listQuizzes: () => request("GET", "/api/quizzes/"),
  createQuiz: (data) => request("POST", "/api/quizzes/", data),
  getQuiz: (id) => request("GET", `/api/quizzes/${id}`),
  updateQuiz: (id, data) => request("PUT", `/api/quizzes/${id}`, data),
  deleteQuiz: (id) => request("DELETE", `/api/quizzes/${id}`),
  getQuizPublic: (token) => request("GET", `/api/quizzes/public/${token}`),

  addQuestion: (quizId, data) => request("POST", `/api/quizzes/${quizId}/questions`, data),
  updateQuestion: (quizId, qId, data) => request("PUT", `/api/quizzes/${quizId}/questions/${qId}`, data),
  deleteQuestion: (quizId, qId) => request("DELETE", `/api/quizzes/${quizId}/questions/${qId}`),
  reorderQuestions: (quizId, orderedIds) => request("PUT", `/api/quizzes/${quizId}/questions/reorder`, orderedIds),
  importQuestions: (quizId, data) => request("POST", `/api/quizzes/${quizId}/import`, data),

  // --- Sessions ---
  startSession: (quizId, participantName) =>
    request("POST", "/api/sessions/", { quiz_id: quizId, participant_name: participantName }),
  submitSession: (sessionId, answers, timeTakenSeconds) =>
    request("POST", `/api/sessions/${sessionId}/submit`, { answers, time_taken_seconds: timeTakenSeconds }),
  getLeaderboard: (quizId) => request("GET", `/api/sessions/quiz/${quizId}/leaderboard`),

  // --- Imports ---
  importCsv: (file) => uploadFile("/api/import/csv", file),
  importExcel: (file) => uploadFile("/api/import/excel", file),
  importPdf: (file) => uploadFile("/api/import/pdf", file),
};
