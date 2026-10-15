// src/services/protection.js
// Har protection ki permission ka haal, aur maangne ke helpers. Permissions
// sirf welcome screen (app/welcome.tsx) se maangi jati hain — har ek se pehle
// user ko bataya jata hai ke kyun chahiye aur data kahan jata hai (Google Play
// is "prominent disclosure" ko zaroori kehta hai).
import { PermissionsAndroid, Platform } from "react-native";
import * as Notifications from "expo-notifications";
import {
  isCallGuardAvailable,
  hasContactsPermission,
  refreshContactCache,
  hasCallScreeningRole,
  requestCallScreeningRole,
  hasNotificationAccess,
  requestNotificationAccess,
} from "../../modules/expo-call-guard";
import { storage } from "./storage";

const WELCOME_KEY = "fraudguard.welcome_done";

export async function isWelcomeDone() {
  try {
    return (await storage.get(WELCOME_KEY)) === "1";
  } catch {
    return false;
  }
}

export async function markWelcomeDone() {
  try {
    await storage.set(WELCOME_KEY, "1");
  } catch {
    /* ignore — agli baar welcome dobara dikh jayega */
  }
}

/**
 * Har protection: true = chal rahi hai, false = permission nahi mili,
 * null = is phone/app par mumkin hi nahi (jaise Expo Go, ya Android 9 par calls).
 */
export async function getProtectionStatus() {
  const native = Platform.OS === "android" && isCallGuardAvailable();
  let notifications = null;
  try {
    notifications = (await Notifications.getPermissionsAsync()).status === "granted";
  } catch {
    notifications = null;
  }
  return {
    notifications,
    contacts: native ? hasContactsPermission() : null,
    calls: native && Platform.Version >= 29 ? hasCallScreeningRole() : null,
    messages: native ? hasNotificationAccess() : null,
  };
}

export async function requestNotifications() {
  try {
    await Notifications.requestPermissionsAsync();
  } catch {
    /* ignore */
  }
}

export async function requestContacts() {
  const res = await PermissionsAndroid.request(PermissionsAndroid.PERMISSIONS.READ_CONTACTS);
  if (res === PermissionsAndroid.RESULTS.GRANTED) {
    // Native cache turant refresh karo warna pehla lookup "denied" cache
    // kar lega aur poori app lifetime tak har saved contact unknown lagega.
    await refreshContactCache();
  }
}

/** System ka "caller ID & spam app" dialog. */
export async function requestCalls() {
  await requestCallScreeningRole();
}

/** Android settings ki "Notification access" screen kholta hai. */
export async function requestMessages() {
  await requestNotificationAccess();
}
