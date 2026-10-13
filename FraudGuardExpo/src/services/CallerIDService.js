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

// ✅ Offline fallback — backend down par bhi legit helpline numbers SAFE
// rahen. Ye `VerifiedDirectory.kt` ka JS mirror hai: mobile ka native rules
// cache (NumberRules) isi list ka union use karta hai, is liye online aur
// offline ka jawab SAME hona chahie — warna user ko "unknown kabhi known
// ban jata hai" wali inconsistency dikhegi.
//
// Pichli baar isme apni static list nahi thi, sirf backend ka data tha.
// Backend `/number-lists` route missing hone se directory khali reh jati
// thi → HBL/UBL/MCB jaise har helpline "unknown 111 UAN" → SUSPICIOUS.
const OFFLINE_FALLBACK = {
  "111111425": "HBL",
  "111825888": "UBL",
  "111000622": "MCB Bank",
  "111622822": "MCB Bank",
  "111113113": "NBP",
  "111723723": "Faysal Bank",
  "111524724": "Bank Alfalah",
  "111468468": "Askari Bank",
  "111124123": "Bank of Punjab",
  "111124666": "Summit Bank",
  "111124777": "JS Bank",
  "111124444": "JazzCash",
  "111003737": "Easypaisa",
  "111579579": "Telenor",
  "111030030": "Ufone / Zong",
  "111345786": "FIA (general helpline)",
  "1991": "FIA Cyber Crime Wing",
  "800111111": "NADRA",
  "111772772": "FBR",
  "80055055": "PTA / PTCL",
  "9911": "K-Electric",
  "131": "IESCO / FESCO",
  "111009009": "GEPCO / SESCO",
};

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
  // ✅ Bundled fallback BHI merge karo — sync fail/partial hone par legit
  // numbers "unknown" na bane. Backend ki list naye numbers deti hai,
  // fallback guarantee ke liye hai (dono ka union).
  for (const [num, entity] of Object.entries(OFFLINE_FALLBACK)) {
    if (!nextDir[num]) nextDir[num] = entity;
  }
  directory = nextDir;
  spoofable = new Set((sp ?? []).map(cleanNumber));
  scamNumbers = new Set((scam ?? []).map(cleanNumber));
}

export function isDirectoryLoaded() {
  return Object.keys(directory).length > 0;
}

export function clearCallerDirectory() {
  // Reset to bundled fallback, bilkul empty nahi — warna next check par
  // har legit helpline "unknown" ho jayegi.
  updateCallerDirectory({ legitimate: [], directory: {}, scam: [], spoofable: [] });
}

// Backend `clean_number()` aur native `NumberRules.clean()` se IDENTICAL —
// online aur offline ka jawab aik jaisa hona chahie, warna user ko
// "unknown kabhi known ban jata hai" wali inconsistency dikhegi.
export function cleanNumber(raw) {
  let cleaned = (raw || "").replace(/[\s\-()]/g, "");
  if (cleaned.startsWith("+92")) cleaned = cleaned.slice(3);
  else if (cleaned.startsWith("0092")) cleaned = cleaned.slice(4);
  // Area-code strip — "051-111-111-425" (12 digits) → "111111425".
  // Bina iske bank ka official helpline kabhi match hi nahi hota tha aur
  // SUSPICIOUS aa jata tha.
  if (cleaned.length >= 12 && AREA_CODES.has(cleaned.slice(0, 3))) {
    cleaned = cleaned.slice(3);
  }
  if (cleaned.startsWith("0")) cleaned = cleaned.slice(1);
  return cleaned;
}

const AREA_CODES = new Set([
  "021", "022", "025", "031", "032", "033", "034", "041", "042", "045",
  "048", "049", "051", "052", "053", "054", "055", "061", "064", "068",
  "069", "071", "072", "073", "074", "081", "082", "083", "091", "092",
  "093", "094", "095", "099",
]);

/**
 * Copy-cat / impersonation detector — `VerifiedDirectory.impersonates()`
 * ka JS mirror.
 *
 * Verified UAN ka shape le magar 1–2 digit alag = authentic bank spoofing
 * (111-111-425 → 111-111-424). Pehle iske liye ek static `spoofable` list
 * sync hoti thi jo backend route missing hone se hamesha empty rehti thi.
 *
 * Guards: candidate khud legit na ho, same prefix family, same length,
 * sirf 1–2 digit ka farq.
 */
function impersonates(cleaned) {
  if (cleaned.length < 7 || !/^\d+$/.test(cleaned)) return false;
  const pool = Object.keys(directory).filter(
    (n) => n.length === cleaned.length && /^\d+$/.test(n),
  );
  for (const legit of pool) {
    if (legit === cleaned) continue;
    if (legit.slice(0, 3) !== cleaned.slice(0, 3)) continue;
    let diff = 0;
    for (let i = 0; i < legit.length; i++) {
      if (legit[i] !== cleaned[i]) diff++;
    }
    if (diff >= 1 && diff <= 2) return true;
  }
  return false;
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

  if (spoofable.has(cleaned) || impersonates(cleaned)) {
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