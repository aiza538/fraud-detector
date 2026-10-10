// src/services/api.js
// Same backend your web app (frontend/src/services/api.js) already talks to.
const API_BASE = 'https://l-law-liet-fraudguard-pk-backend.hf.space';

export async function analyzeText(text) {
  const response = await fetch(`${API_BASE}/analyze/text`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ text }),
  });

  if (!response.ok) {
    // Backend returns { error: "..." } with a non-200 status sometimes
    const body = await response.json().catch(() => ({}));
    throw new Error(body.error || `Request failed (${response.status})`);
  }

  return response.json();
}
