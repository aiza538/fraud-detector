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
