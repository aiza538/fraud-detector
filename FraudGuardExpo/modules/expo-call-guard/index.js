import { Platform } from "react-native";
import { requireNativeModule } from "expo-modules-core";

let CallGuard = null;
if (Platform.OS === "android") {
  try {
    CallGuard = requireNativeModule("CallGuard");
  } catch {
    CallGuard = null;
  }
}

export function isCallGuardAvailable() {
  return CallGuard != null;
}

export async function setNativeRules(legitimate, scam, spoofable = []) {
  if (!CallGuard) return;
  await CallGuard.setRules({ legitimate, scam, spoofable });
}

/** Server ki rules file (JSON text) phone ke message scanner par lagao.
 *  false = file ghalat thi; phone par pehle wali rules chalti rahti hain. */
export async function setTextRules(json) {
  if (!CallGuard) return false;
  return CallGuard.setTextRules(json);
}

/** Phone par lagi downloaded rules ka version, ya null (app ki apni copy). */
export function getTextRulesVersion() {
  if (!CallGuard) return null;
  try {
    return CallGuard.getTextRulesVersion() ?? null;
  } catch {
    return null;
  }
}

/** Phonebook cache refresh — READ_CONTACTS milne ke baad call karein. */
export async function refreshContactCache() {
  if (!CallGuard) return;
  try {
    await CallGuard.refreshContactCache();
  } catch {
    /* module installed nahi — ignore */
  }
}

export function hasContactsPermission() {
  if (!CallGuard) return false;
  try {
    return CallGuard.hasContactsPermission();
  } catch {
    return false;
  }
}

/**
 * "saved" | "not_saved" | "unknown" — "unknown" ka matlab READ_CONTACTS
 * nahi mili (tab number ko "suspicious" nahi kehna chahiye).
 */
export function checkContact(number) {
  if (!CallGuard || !number) return "unknown";
  try {
    return CallGuard.checkContact(String(number));
  } catch {
    return "unknown";
  }
}

/** Android 10+: kya FraudGuard "caller ID & spam" app hai (call alerts ke liye zaroori). */
export function hasCallScreeningRole() {
  if (!CallGuard) return false;
  try {
    return CallGuard.hasCallScreeningRole();
  } catch {
    return false;
  }
}

/** System ka dialog dikhata hai. false = is phone par Call Screening mumkin nahi. */
export async function requestCallScreeningRole() {
  if (!CallGuard) return false;
  try {
    return await CallGuard.requestCallScreeningRole();
  } catch {
    return false;
  }
}

export function hasNotificationAccess() {
  if (!CallGuard) return false;
  try {
    return CallGuard.hasNotificationAccess();
  } catch {
    return false;
  }
}

export async function requestNotificationAccess() {
  if (!CallGuard) return;
  await CallGuard.requestNotificationAccess();
}

export function addCallDetectedListener(handler) {
  if (!CallGuard) return () => {};
  return CallGuard.addListener("onCallDetected", handler);
}

export function addMessageDetectedListener(handler) {
  if (!CallGuard) return () => {};
  return CallGuard.addListener("onMessageDetected", handler);
}
