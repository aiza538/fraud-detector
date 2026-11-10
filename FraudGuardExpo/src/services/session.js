// src/services/session.js
// App ka apna token — koi login screen nahi. Pehli request par server ek
// anonymous account banata hai; token phone ki secure storage (Android
// Keystore) me rehta hai aur har request ke saath jata hai.
import { storage } from "./storage";

const API_BASE = process.env.EXPO_PUBLIC_API_URL;
const KEY = "fraudguard.session";
// Token 30 din ka hota hai; aakhri hafte me app khule to naya le lo, taake
// rozana use karne wale ka account kabhi expire na ho.
const REFRESH_WINDOW_SECONDS = 7 * 86400;

let session; // undefined = abhi storage se parha nahi; null = koi session nahi
let pending = null; // ek waqt me ek hi signup/refresh, chahe 3 requests saath aayein

async function load() {
  if (session === undefined) {
    try {
      const raw = await storage.get(KEY);
      session = raw ? JSON.parse(raw) : null;
    } catch {
      session = null;
    }
  }
  return session;
}

/** Server ka `{ token, expires_at, verified }` jawab yaad rakho. */
export async function saveSession(next) {
  session = next;
  try {
    await storage.set(KEY, JSON.stringify(next));
  } catch {
    // Storage fail ho to bhi app chalti rahe — token is run ke liye memory me hai.
  }
}

export async function clearSession() {
  session = null;
  try {
    await storage.remove(KEY);
  } catch {
    /* ignore */
  }
}

async function authCall(path, token) {
  let response;
  try {
    response = await fetch(`${API_BASE}/v1/auth/${path}`, {
      method: "POST",
      headers: token ? { Authorization: `Bearer ${token}` } : undefined,
    });
  } catch {
    throw new Error("Backend connection failed.");
  }
  return response;
}

async function signUp() {
  const response = await authCall("anonymous");
  const body = await response.json().catch(() => ({}));
  if (!response.ok || !body.token) {
    throw new Error(body.message || "Backend connection failed.");
  }
  await saveSession(body);
  return body;
}

async function refresh(current) {
  const response = await authCall("refresh", current.token);
  if (response.status === 401) return signUp();
  if (!response.ok) return current;
  const body = await response.json();
  await saveSession(body);
  return body;
}

async function resolve() {
  const current = await load();
  if (!current) return signUp();
  if (current.expires_at - Date.now() / 1000 < REFRESH_WINDOW_SECONDS) {
    // Refresh fail ho (offline) to purana token hi chalne do.
    return refresh(current).catch(() => current);
  }
  return current;
}

/** Abhi ka session; zarurat ho to naya anonymous account bana kar. */
export function getSession() {
  if (!pending) {
    pending = resolve().finally(() => {
      pending = null;
    });
  }
  return pending;
}
