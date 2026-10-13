// src/services/api.js
// Backend ka /v1 API — har request token ke saath jati hai (session.js).
import { Platform } from "react-native";
import { clearSession, getSession, saveSession } from "./session";

const API_BASE = process.env.EXPO_PUBLIC_API_URL;

/** Server ne request reject ki. `code` server ka error code hai
 *  (jaise "daily_limit", "email_verification_required"); `status` 0 = network. */
export class ApiError extends Error {
  constructor(status, code, message) {
    super(message);
    this.status = status;
    this.code = code;
  }
}

async function send(path, options, token) {
  try {
    return await fetch(`${API_BASE}/v1${path}`, {
      ...options,
      headers: { ...options.headers, Authorization: `Bearer ${token}` },
    });
  } catch {
    throw new ApiError(0, "network", "Backend connection failed.");
  }
}

async function request(path, options = {}) {
  let session;
  try {
    session = await getSession();
  } catch (err) {
    throw new ApiError(0, "network", err.message);
  }
  let response = await send(path, options, session.token);
  if (response.status === 401) {
    // Token expire/revoke ho chuka — naya anonymous account lo, ek baar dobara.
    await clearSession();
    session = await getSession();
    response = await send(path, options, session.token);
  }
  if (response.status === 204) return null;
  const body = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new ApiError(
      response.status,
      body.error ?? "error",
      body.message ?? `Server error (${response.status})`,
    );
  }
  return body;
}

function post(path, json) {
  return request(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(json),
  });
}

export function analyzeText(text, channel) {
  return post("/analyze/text", { text, channel });
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

  // Content-Type header MAT dena — fetch khud boundary ke sath set karega
  return request("/analyze/audio", { method: "POST", body: formData });
}

/**
 * `isSavedContact` true bhejne se backend number ko "safe / Saved contact"
 * dega. Ye zaroori hai warna user apne hi dost ke number par "suspicious" dekh
 * leta hai (personal mobiles pehle "suspicious, high confidence" hote thay).
 */
export function checkNumber(number, isSavedContact = false) {
  return post("/check-number", { number, saved_contact: isSavedContact });
}

/**
 * Sirf email-verified user report kar sakta hai — warna `ApiError` jis ka
 * `code` "email_verification_required" hota hai (UI verify screen kholta hai).
 * Jawab: { status: "pending" | "confirmed", report_count, reports_needed, message }
 */
export function reportNumber(number, note) {
  return post("/report-number", { number, note });
}

export function getNumberLists() {
  return request("/number-lists");
}

export function requestEmailCode(email) {
  return post("/auth/email/start", { email });
}

/** Code sahi ho to server verified session deta hai (ya purana account wapas). */
export async function verifyEmailCode(code) {
  const session = await post("/auth/email/verify", { code });
  await saveSession(session);
  return session;
}

/** { verified, admin, created_at } */
export function getAccount() {
  return request("/account");
}

export async function deleteAccount() {
  await request("/account", { method: "DELETE" });
  await clearSession();
}
