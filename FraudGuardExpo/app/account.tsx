import React, { useCallback, useState } from "react";
import {
  ActivityIndicator,
  ScrollView,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { router } from "expo-router";
import { useFocusEffect } from "@react-navigation/native";
import { deleteAccount, getAccount } from "../src/services/api";
import { clearAlerts } from "../src/services/fraudAlerts";
import { getProtectionStatus } from "../src/services/protection";

type Account = { verified: boolean };
type Protection = Awaited<ReturnType<typeof getProtectionStatus>>;

const PROTECTIONS: { key: keyof Protection; label: string }[] = [
  { key: "notifications", label: "Alert notifications" },
  { key: "contacts", label: "Recognise saved contacts" },
  { key: "calls", label: "Check incoming calls" },
  { key: "messages", label: "Scan WhatsApp and SMS" },
];

export default function AccountScreen() {
  const [account, setAccount] = useState<Account | null>(null);
  const [protection, setProtection] = useState<Protection | null>(null);
  const [error, setError] = useState("");
  const [confirming, setConfirming] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [deleted, setDeleted] = useState(false);

  // Focus par dobara load — verify screen se wapas aane par status naya ho.
  useFocusEffect(
    useCallback(() => {
      let active = true;
      setError("");
      getAccount()
        .then((data: Account) => active && setAccount(data))
        .catch((err: any) => active && setError(err?.message || "Could not load your account."));
      getProtectionStatus().then((data) => active && setProtection(data));
      return () => {
        active = false;
      };
    }, []),
  );

  const handleDelete = async () => {
    setDeleting(true);
    setError("");
    try {
      await deleteAccount();
      await clearAlerts();
      setDeleted(true);
    } catch (err: any) {
      setError(err?.message || "Could not delete the account. Please try again.");
    } finally {
      setDeleting(false);
      setConfirming(false);
    }
  };

  return (
    <SafeAreaView style={styles.safe}>
      <View style={styles.header}>
        <TouchableOpacity onPress={() => router.back()}>
          <Text style={styles.back}>←</Text>
        </TouchableOpacity>
        <Text style={styles.title}>Account</Text>
        <View style={{ width: 24 }} />
      </View>

      <ScrollView contentContainerStyle={styles.container}>
        {deleted ? (
          <View style={styles.card}>
            <Text style={styles.cardTitle}>Account deleted</Text>
            <Text style={styles.text}>
              Your account, your reports and the alert history on this phone
              have been removed. If you keep using the app, a new anonymous
              account is created automatically.
            </Text>
            <TouchableOpacity style={styles.button} onPress={() => router.replace("/")}>
              <Text style={styles.buttonText}>Go to home</Text>
            </TouchableOpacity>
          </View>
        ) : (
          <>
            <View style={styles.card}>
              <Text style={styles.cardTitle}>Your account</Text>
              {account === null && !error ? (
                <ActivityIndicator color="#1d4ed8" style={{ marginTop: 12 }} />
              ) : account?.verified ? (
                <Text style={[styles.status, styles.verified]}>✓ Email verified</Text>
              ) : (
                <>
                  <Text style={styles.status}>Anonymous — email not verified</Text>
                  <Text style={styles.text}>
                    You do not need anything to check messages and numbers.
                    An email is only needed to report a scam number.
                  </Text>
                  <TouchableOpacity
                    style={styles.button}
                    onPress={() => router.push("/verify-email")}>
                    <Text style={styles.buttonText}>Verify email</Text>
                  </TouchableOpacity>
                </>
              )}
            </View>

            {protection && (
              <View style={styles.card}>
                <Text style={styles.cardTitle}>Protection</Text>
                {PROTECTIONS.map(({ key, label }) => (
                  <View key={key} style={styles.protectionRow}>
                    <Text style={styles.text}>{label}</Text>
                    <Text
                      style={[
                        styles.protectionState,
                        protection[key] === true && styles.verified,
                        protection[key] === false && styles.off,
                      ]}>
                      {protection[key] === true
                        ? "✓ On"
                        : protection[key] === false
                          ? "✗ Off"
                          : "Not available on this phone"}
                    </Text>
                  </View>
                ))}
                <TouchableOpacity style={styles.button} onPress={() => router.push("/welcome")}>
                  <Text style={styles.buttonText}>Open protection setup</Text>
                </TouchableOpacity>
              </View>
            )}

            <View style={styles.card}>
              <Text style={styles.cardTitle}>Delete account</Text>
              <Text style={styles.text}>
                This permanently removes your account, your reports and
                the alert history on this phone.
              </Text>
              {!confirming ? (
                <TouchableOpacity
                  style={[styles.button, styles.dangerOutline]}
                  onPress={() => setConfirming(true)}>
                  <Text style={styles.dangerText}>Delete account</Text>
                </TouchableOpacity>
              ) : (
                <>
                  <Text style={styles.confirmText}>
                    Are you sure? This cannot be undone.
                  </Text>
                  <TouchableOpacity
                    style={[styles.button, styles.danger]}
                    onPress={handleDelete}
                    disabled={deleting}>
                    {deleting ? (
                      <ActivityIndicator color="#fff" size="small" />
                    ) : (
                      <Text style={styles.buttonText}>Yes, delete</Text>
                    )}
                  </TouchableOpacity>
                  <TouchableOpacity onPress={() => setConfirming(false)} disabled={deleting}>
                    <Text style={styles.link}>Cancel</Text>
                  </TouchableOpacity>
                </>
              )}
            </View>
          </>
        )}

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
    marginBottom: 16,
    elevation: 2,
    shadowColor: "#000",
    shadowOpacity: 0.06,
    shadowRadius: 8,
    shadowOffset: { width: 0, height: 2 },
  },
  cardTitle: { fontSize: 16, fontWeight: "800", color: "#1e3a8a", marginBottom: 6 },
  status: { fontSize: 14, fontWeight: "700", color: "#6b7280", marginBottom: 6 },
  verified: { color: "#16a34a" },
  off: { color: "#dc2626" },
  protectionRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    paddingVertical: 6,
  },
  protectionState: { fontSize: 13, fontWeight: "700", color: "#6b7280" },
  text: { fontSize: 13, color: "#374151", lineHeight: 20 },
  button: {
    backgroundColor: "#1d4ed8",
    borderRadius: 12,
    paddingVertical: 13,
    alignItems: "center",
    marginTop: 14,
  },
  buttonText: { color: "#fff", fontSize: 14, fontWeight: "700" },
  dangerOutline: { backgroundColor: "#fff", borderWidth: 1.5, borderColor: "#dc2626" },
  dangerText: { color: "#dc2626", fontSize: 14, fontWeight: "700" },
  danger: { backgroundColor: "#dc2626" },
  confirmText: { fontSize: 13, color: "#991b1b", fontWeight: "700", marginTop: 14 },
  link: { color: "#475569", fontSize: 13, fontWeight: "600", textAlign: "center", marginTop: 14 },
  error: { color: "#dc2626", fontSize: 13, textAlign: "center", marginTop: 4 },
});
