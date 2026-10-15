import React, { useState } from "react";
import {
  ActivityIndicator,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { router } from "expo-router";
import { requestEmailCode, verifyEmailCode } from "../src/services/api";

// Number report karne se pehle ek baar email verify hota hai — is ke baghair
// koi bhi 5 naye accounts bana kar kisi ka number scam mark karwa sakta tha.
export default function VerifyEmailScreen() {
  const [step, setStep] = useState<"email" | "code" | "done">("email");
  const [email, setEmail] = useState("");
  const [code, setCode] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  const run = async (action: () => Promise<void>) => {
    setBusy(true);
    setError("");
    setNotice("");
    try {
      await action();
    } catch (err: any) {
      // Server ke messages (galat code, thora intezar, limit) seedhe dikhao.
      setError(err?.message || "Something went wrong. Please try again.");
    } finally {
      setBusy(false);
    }
  };

  const sendCode = (resend = false) =>
    run(async () => {
      await requestEmailCode(email.trim());
      setCode("");
      setStep("code");
      if (resend) setNotice("A new code has been sent.");
    });

  const confirmCode = () =>
    run(async () => {
      await verifyEmailCode(code.trim());
      setStep("done");
    });

  return (
    <SafeAreaView style={styles.safe}>
      <View style={styles.header}>
        <TouchableOpacity onPress={() => router.back()}>
          <Text style={styles.back}>←</Text>
        </TouchableOpacity>
        <Text style={styles.title}>Verify Your Email</Text>
        <View style={{ width: 24 }} />
      </View>

      <ScrollView
        contentContainerStyle={styles.container}
        keyboardShouldPersistTaps="handled">
        {step === "email" && (
          <View style={styles.card}>
            <Text style={styles.text}>
              To report a number, you need to verify an email once. This stops
              anyone from getting a real number blocked with fake reports.
            </Text>
            <Text style={styles.small}>
              We never store your email address, only a scrambled form of it
              that cannot be turned back into the address.
            </Text>
            <TextInput
              style={styles.input}
              value={email}
              onChangeText={setEmail}
              placeholder="you@example.com"
              placeholderTextColor="#9ca3af"
              keyboardType="email-address"
              autoCapitalize="none"
              autoCorrect={false}
              editable={!busy}
              onSubmitEditing={() => sendCode()}
            />
            <TouchableOpacity
              style={[styles.button, (!email.trim() || busy) && styles.disabled]}
              onPress={() => sendCode()}
              disabled={!email.trim() || busy}>
              {busy ? (
                <ActivityIndicator color="#fff" size="small" />
              ) : (
                <Text style={styles.buttonText}>Send code</Text>
              )}
            </TouchableOpacity>
          </View>
        )}

        {step === "code" && (
          <View style={styles.card}>
            <Text style={styles.text}>
              We sent a 6-digit code to {email.trim()}. It is valid for 10
              minutes.
            </Text>
            <TextInput
              style={[styles.input, styles.codeInput]}
              value={code}
              onChangeText={(value) => setCode(value.replace(/\D/g, ""))}
              placeholder="000000"
              placeholderTextColor="#9ca3af"
              keyboardType="number-pad"
              maxLength={6}
              editable={!busy}
              onSubmitEditing={confirmCode}
            />
            <TouchableOpacity
              style={[styles.button, (code.length !== 6 || busy) && styles.disabled]}
              onPress={confirmCode}
              disabled={code.length !== 6 || busy}>
              {busy ? (
                <ActivityIndicator color="#fff" size="small" />
              ) : (
                <Text style={styles.buttonText}>Verify</Text>
              )}
            </TouchableOpacity>
            <TouchableOpacity onPress={() => sendCode(true)} disabled={busy}>
              <Text style={styles.link}>Send a new code</Text>
            </TouchableOpacity>
            <TouchableOpacity onPress={() => setStep("email")} disabled={busy}>
              <Text style={styles.link}>Change email</Text>
            </TouchableOpacity>
          </View>
        )}

        {step === "done" && (
          <View style={styles.card}>
            <Text style={styles.doneEmoji}>✅</Text>
            <Text style={styles.doneTitle}>Email verified</Text>
            <Text style={styles.text}>
              You can now report scam numbers. Reports from a newly verified
              account start counting after 48 hours.
            </Text>
            <TouchableOpacity style={styles.button} onPress={() => router.back()}>
              <Text style={styles.buttonText}>Go back</Text>
            </TouchableOpacity>
          </View>
        )}

        {!!notice && <Text style={styles.notice}>{notice}</Text>}
        {!!error && <Text style={styles.error}>{error}</Text>}
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: "#f0f9ff" },
  header: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    paddingHorizontal: 20,
    paddingVertical: 14,
  },
  back: { fontSize: 24, color: "#1e3a8a", width: 24 },
  title: { fontSize: 18, fontWeight: "800", color: "#1e3a8a" },
  container: { padding: 20, paddingBottom: 40 },
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
  text: { fontSize: 14, color: "#374151", lineHeight: 21 },
  small: { fontSize: 12, color: "#6b7280", lineHeight: 18, marginTop: 8 },
  input: {
    borderWidth: 1.5,
    borderColor: "#dbeafe",
    borderRadius: 12,
    paddingHorizontal: 12,
    paddingVertical: 11,
    fontSize: 15,
    color: "#1f2937",
    backgroundColor: "#f8fafc",
    marginTop: 14,
  },
  codeInput: { fontSize: 22, letterSpacing: 8, textAlign: "center" },
  button: {
    backgroundColor: "#1d4ed8",
    borderRadius: 12,
    paddingVertical: 13,
    alignItems: "center",
    marginTop: 14,
  },
  disabled: { opacity: 0.5 },
  buttonText: { color: "#fff", fontSize: 14, fontWeight: "700" },
  link: { color: "#1d4ed8", fontSize: 13, fontWeight: "600", textAlign: "center", marginTop: 14 },
  doneEmoji: { fontSize: 40, textAlign: "center" },
  doneTitle: {
    fontSize: 17,
    fontWeight: "800",
    color: "#16a34a",
    textAlign: "center",
    marginVertical: 8,
  },
  notice: { color: "#16a34a", fontSize: 13, textAlign: "center", marginTop: 14 },
  error: { color: "#dc2626", fontSize: 13, textAlign: "center", marginTop: 14 },
});
