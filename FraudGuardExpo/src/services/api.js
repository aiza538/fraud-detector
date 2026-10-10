// src/services/api.js
import { Platform } from "react-native";

const API_BASE = process.env.EXPO_PUBLIC_API_URL;

export async function analyzeText(text) {
  const response = await fetch(`${API_BASE}/analyze/text`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text }),
  });
  return response.json();
}

export async function analyzeAudio(fileUri, fileName, mimeType) {
  const formData = new FormData();

  if (Platform.OS === "web") {
    // Web: uri ko actual Blob mein convert karo
    const fileResponse = await fetch(fileUri);
    const blob = await fileResponse.blob();
    formData.append("file", blob, fileName || "audio.mp3");
  } else {
    // Native (Android/iOS): RN ka special object format
    formData.append("file", {
      uri: fileUri,
      name: fileName || "audio.mp3",
      type: mimeType || "audio/mpeg",
    });
  }

  const response = await fetch(`${API_BASE}/analyze/audio`, {
    method: "POST",
    body: formData,
    // Content-Type header MAT dena — fetch khud boundary ke sath set karega
  });
  return response.json();
}
