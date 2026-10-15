// src/services/callMonitor.js
// Android native monitoring ko JS se bridge karta hai:
// rules sync (backend se) + call/message events ko alert history mein save.
import { Platform } from "react-native";
import { getNumberLists, getRules } from "./api";
import { updateCallerDirectory } from "./CallerIDService";
import {
  isCallGuardAvailable,
  setNativeRules,
  setTextRules,
  getTextRulesVersion,
  addCallDetectedListener,
  addMessageDetectedListener,
} from "../../modules/expo-call-guard";
import { saveAlert } from "./fraudAlerts";

const CALL_MESSAGES = {
  scam: "Impersonation or community-reported scam number. Banks and government offices do not call from hidden or look-alike numbers.",
  suspicious:
    "Unverified UAN-style number — scammers fake official-looking bank numbers. If they ask for an OTP or money, block them.",
};

// Unknown number = "pata nahi", scam nahi. Is par koi alert history entry
// nahi banti — warna har personal number app ka notification ban jata tha.
const ALERTED_LEVELS = new Set(["scam", "suspicious"]);

export async function syncRules() {
  if (!isCallGuardAvailable()) return;
  try {
    const data = await getNumberLists();
    await setNativeRules(
      data.legitimate ?? [],
      data.scam ?? [],
      data.spoofable ?? [],
    );
    // Offline caller-ID bhi backend ki hi directory se chalta hai, taake
    // online aur offline ka jawab ek jaisa ho.
    updateCallerDirectory(data);
  } catch {
    // Backend offline — purane cached rules hi chalte rahenge.
    // NOTE: pehle yahan rules stale rehne par bhi app UNKNOWN numbers ko
    // "suspicious" bana deta tha. Ab unknown pe koi alert nahi hota, is liye
    // stale rules se sirf verified banks ka naam hi stale reh sakta hai.
  }
  try {
    // WhatsApp/SMS scanner ki rules — sirf tab download jab server par nayi
    // version ho (warna server khali 304 bhejta hai).
    const rules = await getRules(getTextRulesVersion());
    if (rules) {
      const applied = await setTextRules(JSON.stringify(rules));
      if (__DEV__) console.log(`[rules] version ${rules.version} applied: ${applied}`);
    } else if (__DEV__) {
      console.log("[rules] unchanged (server sent 304)");
    }
  } catch {
    // Offline — phone par pehle se lagi rules (ya app ki apni copy) chalti rahengi.
  }
}

export async function startCallMonitor() {
  if (Platform.OS !== "android") return () => {};
  if (!isCallGuardAvailable()) return () => {};

  // Permissions yahan nahi maangi jatin — welcome screen (app/welcome.tsx)
  // har ek se pehle wajah batakar maangti hai. Yahan sirf rules sync aur
  // native events sunna.
  await syncRules();

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