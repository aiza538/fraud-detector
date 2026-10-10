import React, { useEffect, useState } from "react";
import {
  ScrollView,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { router, useLocalSearchParams } from "expo-router";
import * as Linking from "expo-linking";
import { saveAlert } from "../src/services/fraudAlerts";
import { reportNumber } from "../src/services/api";
import { syncRules } from "../src/services/callMonitor";
import {
  FIA_PORTAL_URL,
  buildEmailLink,
} from "../src/services/fiaLinks";

const LEVEL_COLORS: Record<string, string> = {
  scam: "#dc2626",
  suspicious: "#d97706",
  // "unknown" alert history me nahi likha jata, magar purani entries ya
  // native event me aa sakta hai — usay laal/amber na dikhayein.
  unknown: "#6b7280",
};

const SOURCE_LABELS: Record<string, string> = {
  phone: "📞 Incoming Phone Call",
  whatsapp: "💬 WhatsApp",
  telegram: "📨 Telegram",
  sms: "📩 SMS",
  carrier: "📡 Carrier Verification Signal",
};

export default function AlertScreen() {
  const params = useLocalSearchParams<{
    number?: string;
    message?: string;
    level?: string;
    source?: string;
    saved?: string;
  }>();

  const number = params.number ?? "Unknown number";
  const message =
    params.message ?? "This number matched a known fraud pattern.";
  const level = params.level ?? "suspicious";
  const source = params.source ?? "phone";

  const [reported, setReported] = useState(level === "scam");
  const [reportError, setReportError] = useState(false);

  useEffect(() => {
    // History se kholne par dobara save na ho — sirf naye alerts save karo
    if (params.saved !== "1") {
      saveAlert({ number, message, level, source });
    }
  }, []);

  const handleReport = async () => {
    try {
      // Backend ab consensus use karta hai — ek report number turant block
      // nahi karti. `syncRules()` sirf tab chahiye jab number actually confirm
      // ho, warna ye useless call hai (aur pehle har report pe native rules
      // push hote thay, jo consensus ke saath galat hota).
      const res = await reportNumber(number);
      setReported(true);
      setReportError(false);
      if (res?.status === "confirmed") syncRules();
    } catch {
      setReportError(true);
    }
  };

  // FIA tak complaint ka official rasta — portal aur email dono.
  const openFia = async (url: string) => {
    try {
      if (await Linking.canOpenURL(url)) await Linking.openURL(url);
    } catch {
      setReportError(true);
    }
  };

  const accent = LEVEL_COLORS[level] ?? LEVEL_COLORS.suspicious;
  const isScam = level === "scam";

  return (
    <SafeAreaView style={styles.safe}>
      <ScrollView contentContainerStyle={styles.container}>
        <View style={[styles.banner, { backgroundColor: accent }]}>
          <Text style={styles.bannerEmoji}>{isScam ? "🚨" : "⚠️"}</Text>
          <Text style={styles.bannerTitle}>
            {isScam ? "Scam Call Detected" : "Suspicious Call Detected"}
          </Text>
          <Text style={styles.bannerSource}>
            {SOURCE_LABELS[source] ?? SOURCE_LABELS.phone}
          </Text>
        </View>

        <View style={styles.card}>
          <Text style={styles.label}>CALLER NUMBER</Text>
          <Text style={styles.number}>{number}</Text>

          <Text style={[styles.label, { marginTop: 16 }]}>RISK ANALYSIS</Text>
          <Text style={styles.message}>{message}</Text>

          <View style={[styles.levelBadge, { borderColor: accent }]}>
            <Text style={[styles.levelText, { color: accent }]}>
              {level.toUpperCase()} RISK
            </Text>
          </View>
        </View>

        <View style={styles.tipsCard}>
          <Text style={styles.tipsTitle}>🛡️ Safety Tips</Text>
          <Text style={styles.tip}>• Banks kabhi OTP ya PIN nahi maangte</Text>
          <Text style={styles.tip}>
            • JazzCash/Easypaisa ka staff passwords nahi poochta
          </Text>
          <Text style={styles.tip}>
            • Pareshan mat hon — call kaat dein aur 1991 pe report karein
          </Text>
        </View>

        {/* FIA Cyber Wing tak shikayat — ye app ka asal maqsad hai. Alert
            screen pe user ka sabse zyada kaam yahi hona chahie: number aur
            message FIA tak pohoncha do. */}
        <View style={styles.fiaCard}>
          <Text style={styles.fiaTitle}>🚔 FIA Cyber Crime Wing</Text>
          <Text style={styles.fiaText}>
            Complaint darj karne ke liye number aur details FIA tak bhejni
            hongi. Official helpline 1991 (Mon–Fri 8am–4pm).
          </Text>
          <TouchableOpacity
            style={[styles.button, styles.fiaButton]}
            onPress={() => openFia(FIA_PORTAL_URL)}>
            <Text style={styles.buttonText}>🚔 FIA par complaint karein</Text>
          </TouchableOpacity>
          <TouchableOpacity
            style={[styles.button, styles.fiaEmailButton]}
            onPress={() =>
              openFia(buildEmailLink({ number, message, channel: source }))
            }>
            <Text style={styles.buttonText}>
              ✉️ Email se FIA ko bhejein
            </Text>
          </TouchableOpacity>
        </View>

        {!reported ? (
          <TouchableOpacity
            style={[styles.button, styles.reportButton]}
            onPress={handleReport}>
            <Text style={styles.buttonText}>🚩 Community mein report karein</Text>
          </TouchableOpacity>
        ) : (
          <View style={[styles.button, styles.reportedButton]}>
            <Text style={styles.buttonText}>✓ Community report darj</Text>
          </View>
        )}

        <Text style={styles.consensusNote}>
          Community report se number tab block hota hai jab 5 alag users
          report karein — taake ek galti se koi number block na ho.
        </Text>

        {reportError && (
          <Text style={styles.errorText}>
            Report nahi ja saka — backend se connect karein aur dobara try
            karein.
          </Text>
        )}

        <TouchableOpacity
          style={[styles.button, styles.historyButton]}
          onPress={() => router.push("/notifications")}>
          <Text style={styles.buttonText}>📋 Alert History</Text>
        </TouchableOpacity>

        <TouchableOpacity onPress={() => router.push("/")}>
          <Text style={styles.backText}>← Back to Home</Text>
        </TouchableOpacity>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: "#f0f9ff" },
  container: { padding: 20, paddingBottom: 40 },
  banner: {
    borderRadius: 16,
    padding: 24,
    alignItems: "center",
    marginBottom: 16,
  },
  bannerEmoji: { fontSize: 40 },
  bannerTitle: {
    color: "#fff",
    fontSize: 20,
    fontWeight: "800",
    marginTop: 8,
    textAlign: "center",
  },
  bannerSource: { color: "#ffe4e6", fontSize: 12, marginTop: 4 },
  card: {
    backgroundColor: "#fff",
    borderRadius: 14,
    padding: 18,
    marginBottom: 14,
    elevation: 2,
    shadowColor: "#000",
    shadowOpacity: 0.06,
    shadowRadius: 8,
    shadowOffset: { width: 0, height: 2 },
  },
  label: { fontSize: 11, fontWeight: "700", color: "#9ca3af", letterSpacing: 1 },
  number: { fontSize: 24, fontWeight: "800", color: "#1e3a8a", marginTop: 4 },
  message: { fontSize: 14, color: "#374151", marginTop: 4, lineHeight: 21 },
  levelBadge: {
    alignSelf: "flex-start",
    borderWidth: 1.5,
    borderRadius: 20,
    paddingHorizontal: 12,
    paddingVertical: 4,
    marginTop: 14,
  },
  levelText: { fontSize: 11, fontWeight: "800" },
  tipsCard: {
    backgroundColor: "#eff6ff",
    borderRadius: 14,
    padding: 16,
    marginBottom: 18,
  },
  fiaCard: {
    backgroundColor: "#fef2f2",
    borderRadius: 14,
    padding: 16,
    marginBottom: 16,
    borderWidth: 1,
    borderColor: "#fecaca",
  },
  fiaTitle: {
    fontSize: 15,
    fontWeight: "800",
    color: "#991b1b",
    marginBottom: 6,
  },
  fiaText: {
    fontSize: 12.5,
    color: "#7f1d1d",
    marginBottom: 12,
    lineHeight: 19,
  },
  fiaButton: { backgroundColor: "#b91c1c" },
  fiaEmailButton: { backgroundColor: "#7f1d1d" },
  consensusNote: {
    fontSize: 11,
    color: "#6b7280",
    lineHeight: 16,
    marginBottom: 14,
    marginTop: -6,
  },
  tipsTitle: { fontSize: 14, fontWeight: "700", color: "#1e3a8a", marginBottom: 8 },
  tip: { fontSize: 12.5, color: "#374151", marginBottom: 4, lineHeight: 19 },
  button: {
    borderRadius: 12,
    paddingVertical: 14,
    alignItems: "center",
    marginBottom: 12,
  },
  reportButton: { backgroundColor: "#1d4ed8" },
  reportedButton: { backgroundColor: "#16a34a" },
  historyButton: { backgroundColor: "#0e7490" },
  buttonText: { color: "#fff", fontSize: 15, fontWeight: "700" },
  errorText: { color: "#dc2626", fontSize: 12, textAlign: "center", marginBottom: 10 },
  backText: {
    textAlign: "center",
    color: "#6b7280",
    fontSize: 14,
    marginTop: 6,
  },
});
