const BACKEND_URL = 'https://l-law-liet-fraudguard-pk-backend.hf.space'; // Your HuggingFace URL

export async function scanMessage({ text, source, sender }) {
  try {
    const res = await fetch(`${BACKEND_URL}/analyze`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text, source, sender }),
    });
    return await res.json();
  } catch (e) {
    console.error('FraudGuard API error:', e);
    return null;
  }
}