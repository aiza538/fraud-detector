import React, { useCallback, useEffect, useState } from "react";
import {
  ActivityIndicator,
  AppState,
  ScrollView,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { router } from "expo-router";
import {
  getProtectionStatus,
  markWelcomeDone,
  requestCalls,
  requestContacts,
  requestMessages,
  requestNotifications,
} from "../src/services/protection";

type Key = "notifications" | "contacts" | "calls" | "messages";
type Status = Record<Key, boolean | null>;

// Har permission se PEHLE user ko saaf batana: kya chahiye, kyun, aur data
// kahan jata hai. Google Play is disclosure ke baghair notification access /
// call screening wali app reject kar deta hai.
const STEPS: { key: Key; icon: string; title: string; why: string; privacy: string; button: string }[] = [
  {
    key: "notifications",
    icon: "🔔",
    title: "Show alerts",
    why: "When a scam call or message is caught, FraudGuard tells you straight away with a notification.",
    privacy: "No data leaves your phone for this.",
    button: "Allow notifications",
  },
  {
    key: "contacts",
    icon: "👥",
    title: "No false alarms for people you know",
    why: "FraudGuard reads your contacts only to check whether a call or message comes from someone you have saved, so family and friends never trigger an alert.",
    privacy: "Your contacts stay on your phone. They are never sent to our server.",
    button: "Allow contacts",
  },
  {
    key: "calls",
    icon: "📞",
    title: "Check incoming calls",
    why: "Set FraudGuard as your \"caller ID & spam\" app so every incoming call can be checked against scam and impersonation lists.",
    privacy: "Numbers are checked on your phone. FraudGuard never blocks a call; it only shows a warning.",
    button: "Set as caller ID app",
  },
  {
    key: "messages",
    icon: "💬",
    title: "Scan WhatsApp and SMS",
    why: "FraudGuard reads the notifications of new WhatsApp, SMS and Telegram messages to spot scams. On the next screen, turn FraudGuard AI on, then come back.",
    privacy: "Messages are checked on your phone. They are never sent to our server and never stored.",
    button: "Open notification access",
  },
];

const REQUEST: Record<Key, () => Promise<void>> = {
  notifications: requestNotifications,
  contacts: requestContacts,
  calls: requestCalls,
  messages: requestMessages,
};

export default function WelcomeScreen() {
  const [status, setStatus] = useState<Status | null>(null);
  const [index, setIndex] = useState(-1); // -1 = intro
  const [busy, setBusy] = useState(false);

  const refresh = useCallback(async () => setStatus(await getProtectionStatus()), []);

  // Settings screen ya system dialog se wapas aane par haal dobara dekho.
  useEffect(() => {
    refresh();
    const sub = AppState.addEventListener("change", (state) => {
      if (state === "active") refresh();
    });
    return () => sub.remove();
  }, [refresh]);

  // Jo permission is phone par mumkin hi nahi (null), us ka step nahi dikhta.
  const steps = status ? STEPS.filter((s) => status[s.key] !== null) : [];
  const step = index >= 0 ? steps[index] : undefined;
  const granted = step && status ? status[step.key] === true : false;

  const next = async () => {
    if (index + 1 < steps.length) {
      setIndex(index + 1);
    } else {
      await markWelcomeDone();
      router.replace("/");
    }
  };

  const allow = async () => {
    if (!step) return;
    setBusy(true);
    try {
      await REQUEST[step.key]();
    } finally {
      await refresh();
      setBusy(false);
    }
  };

  if (!status) {
    return (
      <SafeAreaView style={[styles.safe, styles.center]}>
        <ActivityIndicator color="#1d4ed8" />
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={styles.safe}>
      <ScrollView contentContainerStyle={styles.container}>
        {index === -1 ? (
          <View style={styles.card}>
            <Text style={styles.bigIcon}>🛡️</Text>
            <Text style={styles.title}>FraudGuard AI</Text>
            <Text style={styles.text}>
              FraudGuard spots scam calls and scam messages right on your phone
              and warns you straight away.
            </Text>
            {steps.length > 0 ? (
              <Text style={styles.text}>
                It needs {steps.length} permissions, and before each one we explain
                why. You can tap “Not now” on any of them and turn it on later
                from the Account screen.
              </Text>
            ) : null}
            <TouchableOpacity style={styles.button} onPress={next}>
              <Text style={styles.buttonText}>Get started</Text>
            </TouchableOpacity>
          </View>
        ) : step ? (
          <View style={styles.card}>
            <Text style={styles.progress}>
              {index + 1} / {steps.length}
            </Text>
            <Text style={styles.bigIcon}>{step.icon}</Text>
            <Text style={styles.title}>{step.title}</Text>
            <Text style={styles.text}>{step.why}</Text>
            <View style={styles.privacyBox}>
              <Text style={styles.privacyText}>🔒 {step.privacy}</Text>
            </View>

            {granted ? (
              <>
                <Text style={styles.done}>✓ Turned on</Text>
                <TouchableOpacity style={styles.button} onPress={next}>
                  <Text style={styles.buttonText}>Next</Text>
                </TouchableOpacity>
              </>
            ) : (
              <>
                <TouchableOpacity style={styles.button} onPress={allow} disabled={busy}>
                  {busy ? (
                    <ActivityIndicator color="#fff" size="small" />
                  ) : (
                    <Text style={styles.buttonText}>{step.button}</Text>
                  )}
                </TouchableOpacity>
                <TouchableOpacity onPress={next} disabled={busy}>
                  <Text style={styles.link}>Not now</Text>
                </TouchableOpacity>
              </>
            )}
          </View>
        ) : null}
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: "#f0f9ff" },
  center: { alignItems: "center", justifyContent: "center" },
  container: { padding: 20, paddingTop: 40, paddingBottom: 40 },
  card: {
    backgroundColor: "#fff",
    borderRadius: 16,
    padding: 22,
    elevation: 2,
    shadowColor: "#000",
    shadowOpacity: 0.06,
    shadowRadius: 8,
    shadowOffset: { width: 0, height: 2 },
  },
  progress: { fontSize: 12, color: "#6b7280", textAlign: "right" },
  bigIcon: { fontSize: 44, textAlign: "center", marginVertical: 8 },
  title: { fontSize: 20, fontWeight: "800", color: "#1e3a8a", textAlign: "center", marginBottom: 10 },
  text: { fontSize: 14, color: "#374151", lineHeight: 21, marginBottom: 10 },
  privacyBox: { backgroundColor: "#f0fdf4", borderRadius: 10, padding: 12, marginTop: 4 },
  privacyText: { fontSize: 13, color: "#166534", lineHeight: 19 },
  done: { fontSize: 15, fontWeight: "800", color: "#16a34a", textAlign: "center", marginTop: 16 },
  button: {
    backgroundColor: "#1d4ed8",
    borderRadius: 12,
    paddingVertical: 14,
    alignItems: "center",
    marginTop: 16,
  },
  buttonText: { color: "#fff", fontSize: 15, fontWeight: "700" },
  link: { color: "#475569", fontSize: 14, fontWeight: "600", textAlign: "center", marginTop: 16 },
});
