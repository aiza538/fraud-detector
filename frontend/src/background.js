// src/background.js
const API_BASE = "http://localhost:5000"; // Change this to your deployed Render URL later

chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === "analyzeText") {
    fetch(`${API_BASE}/analyze/text`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text: request.text })
    })
    .then(res => res.json())
    .then(data => sendResponse({ success: true, data }))
    .catch(error => sendResponse({ success: false, error: error.message }));
    
    return true; // Keep the message channel open for async fetch
  }
});
