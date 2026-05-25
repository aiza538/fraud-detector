const BASE_URL = "http://localhost:8000";

export async function analyzeText(text) {
  const res = await fetch(`${BASE_URL}/analyze`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text }),
  });
  return res.json();
}

export async function analyzeAudio(file) {
  const form = new FormData();
  form.append("file", file);
  const res = await fetch(`${BASE_URL}/analyze-audio`, {
    method: "POST",
    body: form,
  });
  return res.json();
}

export async function getHistory() {
  const res = await fetch(`${BASE_URL}/history`);
  return res.json();
}
