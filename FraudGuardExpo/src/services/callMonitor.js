// src/services/callMonitor.js
// Android native monitoring ko JS se bridge karta hai:
// rules sync (backend se) + call/message events ko alert history mein save.
import { Platform, PermissionsAndroid, Alert } from "react-native";
import { getNumberLists } from "./api";
import { updateCallerDirectory } from "./CallerIDService";
import {
  isCallGuardAvailable,
  setNativeRules,
  refreshContactCache,
  hasContactsPermission,
  addCallDetectedListener,
  addMessageDetectedListener,
  hasNotificationAccess,
  requestNotificationAccess,
} from "../../modules/expo-call-guard";
import { saveAlert } from "./fraudAlerts";

const CALL_MESSAGES = {
  scam: "Impersonation ya community-reported scam number. Bank/sarkari idare apna aam number chhupa kar call nahi karte.",
  suspicious:
    "Unverified UAN-style number — scammers official-looking bank numbers spoof kar sakte hain. OTP ya paisa maange to block karein.",
};

// Unknown number = "pata nahi", scam nahi. Is par koi alert history entry
// nahi banti — warna har personal number app ka notification ban jata tha.
//
// "cooldown" native dedupe ka signal hai: same number par 12 ghante ke andar
// dobara notification nahi bheji gayi. Ye bhi history me entry nahi banata,
// warna ek hi scammer ki 5 calls par 5 duplicate rows.
const ALERTED_LEVELS = new Set(["scam", "suspicious"]);

export async function syncRules() {
  if (!isCallGuardAvailable()) return;
  try {
    const data = await getNumberLists();
    if (!data || typeof data !== "object") return;
    await setNativeRules(
      data.legitimate ?? [],
      data.scam ?? [],
      data.spoofable ?? [],
    );
    // Offline caller-ID bhi backend ki hi directory se chalta hai, taake
    // online aur offline ka jawab ek jaisa ho.
    updateCallerDirectory(data);
  } catch {
    // Backend offline / route missing — native rules cached (ya bundled
    // fallback) hi chalte rahenge.
    //
    // ✅ Ye silent-fail pehle ASLI problem thi: `/number-lists` backend me
    // MISSING tha → sync hamesha fail → native legit list KHAALI → HBL
    // 111-111-425 jaise real helpline numbers bhi "unknown 111 UAN" par
    // SUSPICIOUS aa jate thay. Ab: (a) backend route exist karta hai,
    // (b) native `NumberRules` VERIFIED_DIRECTORY ka union use karta hai,
    // (c) JS `CallerIDService` me bhi OFFLINE_FALLBACK merge hota hai —
    // teenon layers par legit helpline KABHI unknown nahi hogi.
    updateCallerDirectory({ legitimate: [], directory: {}, scam: [], spoofable: [] });
  }
}

async function ensureContactsPermission() {
  if (!isCallGuardAvailable()) return false;
  const already = hasContactsPermission();
  if (already) return true;
  const res = await PermissionsAndroid.request(
    PermissionsAndroid.PERMISSIONS.READ_CONTACTS,
  );
  const granted = res === PermissionsAndroid.RESULTS.GRANTED;
  if (granted) {
    // Native cache turant refresh karo warna pehla lookup "denied" cache
    // kar lega aur poori app lifetime tak har saved contact unknown lagega.
    await refreshContactCache();
  }
  return granted;
}

export async function startCallMonitor() {
  if (Platform.OS !== "android") return () => {};
  if (!isCallGuardAvailable()) return () => {};

  await PermissionsAndroid.request(
    PermissionsAndroid.PERMISSIONS.READ_PHONE_STATE,
  );
  // Caller number read karne ke liye (Android 9+)
  await PermissionsAndroid.request(
    PermissionsAndroid.PERMISSIONS.READ_CALL_LOG ?? "android.permission.READ_CALL_LOG",
  );
  // Saved contacts detect karne ke liye — bina iske saved logon ke numbers
  // "unknown" samajh ke alert hote thay.
  const contactsGranted = await ensureContactsPermission();
  if (!contactsGranted) {
    // Bina READ_CONTACTS ke saved-contact detection kaam nahi karta. Text wale
    // rules phir bhi chalti hain, magar number-level alerts chup ho jate hain —
    // ye user ko batana zaroori hai warna "app kaam nahi kar raha" lagega.
    Alert.alert(
      "Contacts permission nahi mili",
      "Bina contacts ke FraudGuard saved numbers pehchan nahi kar pata, is liye unknown numbers par alert nahi aayenge. Settings → App permissions → Contacts → Allow karein.",
    );
  }

  await syncRules();

  // WhatsApp/SMS/Telegram incoming scanner native notification listener se
  // chalta hai — uske liye notification access zaroori hai
  if (!hasNotificationAccess()) {
    await requestNotificationAccess();
  }

  const callSub = addCallDetectedListener(
    ({ number, status, source, alerted }) => {
      if (!alerted || !ALERTED_LEVELS.has(status)) return;
      saveAlert({
        number,
        message:
          source === "whatsapp"
            ? "Incoming WhatsApp call from an unverified number — banks and government agencies never call on WhatsApp."
            : CALL_MESSAGES[status] ?? "Suspicious number detected.",
        level: status,
        source: source ?? "phone",
      });
    },
  );

  const msgSub = addMessageDetectedListener(
    ({ subject, message, source, level }) => {
      if (!ALERTED_LEVELS.has(level)) return;
      saveAlert({
        number: subject,
        message,
        level,
        source: source ?? "whatsapp",
      });
    },
  );

  return () => {
    callSub?.remove?.();
    msgSub?.remove?.();
  };
}