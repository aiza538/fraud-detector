// src/components/NumberChecker.js
import React, { useState } from "react";
import {
  ActivityIndicator,
  StyleSheet,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from "react-native";
import { useRouter } from "expo-router";
import * as Linking from "expo-linking";
import { checkNumber, reportNumber } from "../services/api";
import { checkCallerID } from "../services/CallerIDService";
import { checkContact } from "../../modules/expo-call-guard";
import { syncRules } from "../services/callMonitor";

// Wrongly reported number ka owner yahan removal maangta hai. Team ise
// expo.dev par EXPO_PUBLIC_SUPPORT_EMAIL ke naam se set karti hai; set na ho to
// button nahi dikhta.
const SUPPORT_EMAIL = process.env.EXPO_PUBLIC_SUPPORT_EMAIL;

function appealLink(number) {
  const subject = `Removal request: ${number}`;
  const body =
    `My number ${number} is marked as a scam in FraudGuard AI, but it belongs to me. ` +
    "Please review it.\n\nMy name:\nWhy this number is mine:\n";
  return `mailto:${SUPPORT_EMAIL}?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`;
}

// UNKNOWN = "kisi list me nahi, koi signal nahi". Grey label + koi red
// "suspicious" warning nahi. Pehle unknown bhi amber "SUSPICIOUS" dikhata
// tha, jo user ko galat tension deta tha.
const STATUS_STYLES = {
  safe: { color: "#16a34a", bg: "#f0fdf4", label: "✓ VERIFIED SAFE" },
  scam: { color: "#dc2626", bg: "#fef2f2", label: "🚩 SCAM / IMPERSONATION" },
  suspicious: { color: "#d97706", bg: "#fffbeb", label: "⚠️ SUSPICIOUS" },
  unknown: { color: "#6b7280", bg: "#f9fafb", label: "ℹ️ NO MATCH — NO ALERT" },
};

// Backend offline ho to synced client-side directory se fallback answer.
// Directory ab backend se aati hai (syncRules), is liye online aur offline
// ka jawab ek jaisa hota hai — pehle yahan apni alag hardcoded list thi
// jo backend se drift kar chuki thi.
function localCheck(rawNumber) {
  const id = checkCallerID(rawNumber);
  if (id.status === "safe") {
    return {
      status: "safe",
      entity: id.authority,
      message: `Verified — ${id.authority} (offline directory).`,
      confidence: "high",
      offline: true,
    };
  }
  if (id.status === "scam") {
    return {
      status: "scam",
      message: id.warning,
      confidence: "high",
      offline: true,
    };
  }
  if (id.status === "suspicious") {
    return {
      status: "suspicious",
      message: id.warning,
      confidence: "medium",
      offline: true,
    };
  }
  return { status: "unknown", message: "Not on any list — no alert.", confidence: "low", offline: true };
}

export default function NumberChecker({ onToast }) {
  const router = useRouter();
  const [number, setNumber] = useState("");
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [reporting, setReporting] = useState(false);
  const [reported, setReported] = useState(false);

  const handleCheck = async () => {
    const trimmed = number.trim();
    if (!trimmed) {
      onToast?.("Please enter a number", "error");
      return;
    }
    setLoading(true);
    setResult(null);
    setReported(false);
    try {
      // Native module se phonebook check: "saved" / "not_saved" / "unknown".
      // "unknown" (permission nahi mili) ko `false` bhejna chahiye — is case me
      // number ko saved na samjhein, magar use "unknown" bhi na karein.
      const isSaved = checkContact(trimmed) === "saved";
      const data = await checkNumber(trimmed, isSaved);
      if (data.status === "error") {
        onToast?.(data.message ?? "Invalid number", "error");
        return;
      }
      setResult({ ...data, rawNumber: trimmed });
    } catch (err) {
      // Server ne khud mana kiya (jaise daily limit) — wahi message dikhao.
      if (err.status) {
        onToast?.(err.message, "error");
        return;
      }
      // Backend unreachable — synced directory se jawab dein. Hamesha kuch
      // return karta hai (unknown bhi) taake user ko "kuch bhi nahi mila"
      // ki jagah clear "no match, no alert" mile.
      setResult({ ...localCheck(trimmed), rawNumber: trimmed });
    } finally {
      setLoading(false);
    }
  };

  const handleReport = async () => {
    setReporting(true);
    try {
      const res = await reportNumber(result.rawNumber);
      setReported(true);
      // Backend ab consensus use karta hai — ek report number ko turant
      // block nahi karti. UI ko honest status dikhana zaroori hai, warna user
      // sochta hai jab block ho gaya hoga. (Pehle yahan turant "scam" set ho
      // jata tha jab tak backend flatten list me daalta.)
      if (res.status === "confirmed") {
        setResult((r) => ({ ...r, status: "scam", report_count: res.report_count }));
        syncRules();
        onToast?.("This number is now confirmed as a scam.", "success");
      } else {
        onToast?.(res.message || "Report recorded.", "info");
      }
    } catch (err) {
      // Report sirf email-verified user kar sakta hai — verify screen kholo;
      // wapas aa kar user dobara Report dabata hai.
      if (err.code === "email_verification_required") {
        onToast?.("Please verify your email before reporting.", "info");
        router.push("/verify-email");
        return;
      }
      // Backend verified number par report reject karta hai (400) — user ko
      // clear message dikhana zaroori hai warna "silently kuch nahi hua".
      onToast?.(err.message || "Could not send the report. Please try again.", "error");
    } finally {
      setReporting(false);
    }
  };

  // Appeal sirf community reports par — spoof (lookalike) verdict kisi report se nahi aata.
  const handleAppeal = async () => {
    try {
      await Linking.openURL(appealLink(result.rawNumber));
    } catch {
      onToast?.(`Please email ${SUPPORT_EMAIL} to request a review.`, "info");
    }
  };

  const style = result ? STATUS_STYLES[result.status] ?? STATUS_STYLES.unknown : null;
  // Report button `unknown` par bhi rahega — scammer asal me personal mobile
  // se call karta hai (jo ab jaan bujh kar "unknown" hai), aur user ke paas
  // usse report karne ka koi aur tareeqa nahi. `safe` aur already-`scam` par
  // button nahi (backend verified numbers par report reject karta hai).
  const canReport =
    result && (result.status === "suspicious" || result.status === "unknown") && !result.offline;

  return (
    <View style={styles.card}>
      <Text style={styles.title}>📞 Phone Number Check</Text>
      <Text style={styles.hint}>
        If someone calls pretending to be a bank or an authority, check
        their number here.
      </Text>

      <View style={styles.inputRow}>
        <TextInput
          style={styles.input}
          value={number}
          onChangeText={setNumber}
          placeholder="e.g. 0300-1234567 or 111-111-425"
          placeholderTextColor="#9ca3af"
          keyboardType="phone-pad"
          autoCapitalize="none"
          onSubmitEditing={handleCheck}
        />
        <TouchableOpacity
          style={styles.checkButton}
          onPress={handleCheck}
          disabled={loading}>
          {loading ? (
            <ActivityIndicator color="#fff" size="small" />
          ) : (
            <Text style={styles.checkButtonText}>Check</Text>
          )}
        </TouchableOpacity>
      </View>

      {result && style && (
        <View style={[styles.resultBox, { backgroundColor: style.bg }]}>
          <Text style={[styles.statusText, { color: style.color }]}>
            {style.label}
          </Text>
          {result.entity && (
            <Text style={[styles.entityText, { color: style.color }]}>
              {result.status === "safe"
                ? `🏦 ${result.entity} — Official helpline`
                : `🎭 Impersonating ${result.entity}`}
            </Text>
          )}
          <Text style={styles.message}>{result.message}</Text>
          {result.report_count != null && result.status === "scam" && (
            <Text style={styles.provenance}>
              {result.report_count} independent reports
              {result.source && result.source !== "community"
                ? ` • source: ${result.source.replace(/_/g, " ")}`
                : ""}
            </Text>
          )}
          {result.confidence && (
            <Text style={styles.confidence}>
              Confidence: {result.confidence}
              {result.offline ? " • offline directory" : ""}
            </Text>
          )}
        </View>
      )}

      {canReport && (
        <TouchableOpacity
          style={[styles.reportButton, reported && styles.reportedButton]}
          onPress={handleReport}
          disabled={reporting || reported}>
          {reporting ? (
            <ActivityIndicator color="#fff" size="small" />
          ) : (
            <Text style={styles.reportButtonText}>
              {reported ? "✓ Report recorded" : "🚩 Report as Scam"}
            </Text>
          )}
        </TouchableOpacity>
      )}

      {reported && (
        <Text style={styles.consensusNote}>
          A number is blocked for everyone only after {5} different users
          report it. One report alone never triggers an alert, so a single
          mistake cannot block a number.
        </Text>
      )}

      {SUPPORT_EMAIL && result?.status === "scam" && result.source === "community" && (
        <TouchableOpacity style={styles.appealButton} onPress={handleAppeal}>
          <Text style={styles.appealText}>This is my number — request removal</Text>
        </TouchableOpacity>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: "#fff",
    borderRadius: 16,
    padding: 18,
    elevation: 2,
    shadowColor: "#000",
    shadowOpacity: 0.06,
    shadowRadius: 8,
    shadowOffset: { width: 0, height: 2 },
  },
  title: { fontSize: 16, fontWeight: "800", color: "#1e3a8a" },
  hint: { fontSize: 12, color: "#6b7280", marginTop: 4, marginBottom: 12, lineHeight: 18 },
  inputRow: { flexDirection: "row", gap: 8 },
  input: {
    flex: 1,
    borderWidth: 1.5,
    borderColor: "#dbeafe",
    borderRadius: 12,
    paddingHorizontal: 12,
    paddingVertical: 10,
    fontSize: 15,
    color: "#1f2937",
    backgroundColor: "#f8fafc",
  },
  checkButton: {
    backgroundColor: "#1d4ed8",
    borderRadius: 12,
    paddingHorizontal: 18,
    justifyContent: "center",
    alignItems: "center",
  },
  checkButtonText: { color: "#fff", fontWeight: "700", fontSize: 14 },
  resultBox: {
    borderRadius: 12,
    padding: 14,
    marginTop: 14,
  },
  statusText: { fontSize: 14, fontWeight: "800", marginBottom: 6 },
  entityText: { fontSize: 13, fontWeight: "700", marginBottom: 6 },
  message: { fontSize: 13, color: "#374151", lineHeight: 19 },
  provenance: { fontSize: 11, color: "#991b1b", marginTop: 8, fontWeight: "600" },
  confidence: { fontSize: 11, color: "#6b7280", marginTop: 8 },
  consensusNote: { fontSize: 11, color: "#6b7280", marginTop: 8, lineHeight: 16 },
  appealButton: {
    marginTop: 12,
    borderWidth: 1,
    borderColor: "#cbd5e1",
    borderRadius: 12,
    paddingVertical: 11,
    alignItems: "center",
  },
  appealText: { color: "#475569", fontSize: 13, fontWeight: "600" },
  reportButton: {
    backgroundColor: "#dc2626",
    borderRadius: 12,
    paddingVertical: 13,
    alignItems: "center",
    marginTop: 14,
  },
  reportedButton: { backgroundColor: "#16a34a" },
  reportButtonText: { color: "#fff", fontSize: 14, fontWeight: "700" },
});
