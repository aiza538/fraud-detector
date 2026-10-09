// src/services/api.js
import { Platform } from "react-native";

const API_BASE = process.env.EXPO_PUBLIC_API_URL;

export async function analyzeText(text, channel) {
  const response = await fetch(`${API_BASE}/analyze/text`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text, channel }),
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

/**
 * `isSavedContact` true bhejne se backend number ko "safe / Saved contact"
 * dega. Ye zaroori hai warna user apne hi dost ke number par "suspicious" dekh
 * leta hai (personal mobiles pehle "suspicious, high confidence" hote thay).
 */
export async function checkNumber(number, isSavedContact = false) {
  const response = await fetch(`${API_BASE}/check-number`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ number, saved_contact: isSavedContact }),
  });
  return response.json();
}

export async function reportNumber(number, note) {
  const response = await fetch(`${API_BASE}/report-number`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ number, note }),
  });
  // Backend verified number par report reject karta hai (400) — UI ko error
  // message dikhani hai, is liye status check zaroori hai.
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body.message || `Report failed (${response.status})`);
  }
  // { status: "pending" | "confirmed", report_count, reports_needed, message }
  return response.json();
}

/**
 * Appeal path — number owner ya admin ke liye. Pehle koi un-report route
 * nahi tha, is liye ek baar block hua number hamesha ke liye block rehta tha.
 */
export async function unreportNumber(number) {
  const response = await fetch(`${API_BASE}/unreport-number`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ number }),
  });
  const body = await response.json().catch(() => ({}));
  if (!response.ok && response.status !== 404) {
    throw new Error(body.message || `Appeal failed (${response.status})`);
  }
  return body;
}

export async function getNumberLists() {
  const response = await fetch(`${API_BASE}/number-lists`);
  return response.json();
}
