const API_BASE = "http://localhost:5000";

export const analyzeText = async (text) => {
  const response = await fetch(`${API_BASE}/analyze/text`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text }),
  });
  return response.json();
};

export const analyzeAudio = async (audioFile) => {
  const formData = new FormData();
  formData.append("file", audioFile);
  const response = await fetch(`${API_BASE}/analyze/audio`, {
    method: "POST",
    body: formData,
  });
  return response.json();
};