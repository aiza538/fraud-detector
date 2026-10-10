export const API_URL = process.env.EXPO_PUBLIC_API_URL;

export async function checkFraud(text: string) {
  try {
    const response = await fetch(`${API_URL}/analyze/text`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text }),
    });

    if (!response.ok) {
      throw new Error(`Server error: ${response.status}`);
    }

    const result = await response.json();
    return result;
  } catch (error) {
    console.error("Connection error:", error);
    throw error;
  }
}