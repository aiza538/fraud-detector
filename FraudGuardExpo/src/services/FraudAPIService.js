const BACKEND_URL = process.env.EXPO_PUBLIC_API_URL;

export async function scanMessage({ text, source, sender }) {
  try {
    const res = await fetch(`${BACKEND_URL}/analyze/text`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text, source, sender }),
    });
    return await res.json();
  } catch (e) {
    console.error("FraudGuard API error:", e);
    return null;
  }
}
