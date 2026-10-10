// src/services/CallerIDService.js
// Client-side Caller ID directory — backend /check-number ka offline mirror.
// Jab backend unreachable ho tab bhi number verify/report flow kaam kare.
//
// IMPORTANT: isme apni KOI static whitelist list nahi hai. Pehle yahan ek
// VERIFIED_AUTHORITIES object hardcoded tha (UBL "111-825-825", MCB
// "111-622-822") jo backend ke numbers se DRIFT kar chuka tha — backend par
// UBL "111-825-888" aur MCB "111-000-622" hain. Offline fallback aur online
// check alag jawab de rahe the, jo user ko "unknown kabhi known ban jata hai"
// wali inconsistency deta tha.
//
// Ab whitelist SIRF backend se aati hai (syncRules → /number-lists) aur memory
// me rehti hai. Backend se kabhi contact na aaya ho to `checkCallerID`
// `unknown` deta hai — guess nahi karta.

let directory = {};   // normalized number -> entity name
let spoofable = new Set();
let scamNumbers = new Set();

/** Backend /number-lists ke data se in-memory directory update karo. */
export function updateCallerDirectory({ legitimate, directory: dir, scam, spoofable: sp }) {
  const nextDir = {};
  for (const [num, entity] of Object.entries(dir ?? {})) {
    nextDir[cleanNumber(num)] = entity;
  }
  // Kuch clients `legitimate` list bhi bhejte hain entity ke baghair —
  // unko bhi directory me daalo taake caller-ID naam dikh sake.
  for (const num of legitimate ?? []) {
    const n = cleanNumber(num);
    if (n && !nextDir[n]) nextDir[n] = "Verified official";
  }
  directory = nextDir;
  spoofable = new Set((sp ?? []).map(cleanNumber));
  scamNumbers = new Set((scam ?? []).map(cleanNumber));
}

export function isDirectoryLoaded() {
  return Object.keys(directory).length > 0;
}

export function clearCallerDirectory() {
  directory = {};
  spoofable = new Set();
  scamNumbers = new Set();
}

// Backend clean_number() se identical — leading zero EK hatana hai,
// poora `replace(/^0+/, "")` se short UAN (0800-55055) galat normalize hote the.
export function cleanNumber(raw) {
  let cleaned = (raw || "").replace(/[\s\-()]/g, "");
  if (cleaned.startsWith("+92")) cleaned = cleaned.slice(3);
  else if (cleaned.startsWith("0092")) cleaned = cleaned.slice(4);
  if (cleaned.startsWith("0")) cleaned = cleaned.slice(1);
  return cleaned;
}

/**
 * Chaar level ka verdict — backend /check-number ke saath align:
 *   scam | safe | suspicious | unknown
 *
 * `unknown` ka matlab "pata nahi" hai, scam ya suspicious NAHI.
 */
export function checkCallerID(incomingNumber, { isSavedContact = false } = {}) {
  const cleaned = cleanNumber(incomingNumber);
  if (!cleaned) return { status: "unknown" };

  if (scamNumbers.has(cleaned)) {
    return {
      status: "scam",
      warning: "Ye number community me fraudulent report kiya gaya hai.",
    };
  }

  if (directory[cleaned]) {
    return { status: "safe", authority: directory[cleaned] };
  }

  if (isSavedContact) {
    return { status: "safe", authority: "Saved contact" };
  }

  // Lists check hone ke baad length guard — NADRA "1700" / FIA "1717" jaise
  // 4-digit verified short codes bhi official hain.
  if (cleaned.length < 7) return { status: "unknown" };

  if (spoofable.has(cleaned)) {
    return {
      status: "scam",
      warning: "Ye number kisi verified bank/sarkari helpline se bahut milta hai — impersonation scam hai.",
    };
  }

  if (cleaned.length === 9 && cleaned.startsWith("111")) {
    return {
      status: "suspicious",
      warning: "UAN-style number jo verified list me nahi — verify karein.",
    };
  }

  // Personal mobiles (300-999), landlines, short codes — teeno UNKNOWN.
  // Pehle yahan bhi koi heuristic nahi tha, magar NumberChecker UI inhe
  // "suspicious" dikhata tha. Ab koi alert nahi.
  return { status: "unknown" };
}

export function getCallerName(number, opts) {
  const result = checkCallerID(number, opts);
  return result.status === "safe" ? result.authority : null;
}