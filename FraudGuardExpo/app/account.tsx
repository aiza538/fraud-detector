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

type Account = { verified: boolean };

export default function AccountScreen() {
  const [account, setAccount] = useState<Account | null>(null);
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
        .catch((err: any) => active && setError(err?.message || "Load nahi ho saka."));
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
      setError(err?.message || "Delete nahi ho saka — dobara try karein.");
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
            <Text style={styles.cardTitle}>Account delete ho gaya</Text>
            <Text style={styles.text}>
              Aapka account, reports aur is phone ki alert history hata di gayi
              hai. App istemal karte rahne par ek naya anonymous account khud
              ban jayega.
            </Text>
            <TouchableOpacity style={styles.button} onPress={() => router.replace("/")}>
              <Text style={styles.buttonText}>Home par jayein</Text>
            </TouchableOpacity>
          </View>
        ) : (
          <>
            <View style={styles.card}>
              <Text style={styles.cardTitle}>Aapka account</Text>
              {account === null && !error ? (
                <ActivityIndicator color="#1d4ed8" style={{ marginTop: 12 }} />
              ) : account?.verified ? (
                <Text style={[styles.status, styles.verified]}>✓ Email verified</Text>
              ) : (
                <>
                  <Text style={styles.status}>Anonymous — email verify nahi hua</Text>
                  <Text style={styles.text}>
                    Message aur number check karne ke liye kuch nahi chahiye.
                    Sirf scam number report karne ke liye email verify karna
                    hota hai.
                  </Text>
                  <TouchableOpacity
                    style={styles.button}
                    onPress={() => router.push("/verify-email")}>
                    <Text style={styles.buttonText}>Email verify karein</Text>
                  </TouchableOpacity>
                </>
              )}
            </View>

            <View style={styles.card}>
              <Text style={styles.cardTitle}>Account delete karein</Text>
              <Text style={styles.text}>
                Is se aapka account, aapki reports aur is phone ki alert
                history hamesha ke liye hat jati hai.
              </Text>
              {!confirming ? (
                <TouchableOpacity
                  style={[styles.button, styles.dangerOutline]}
                  onPress={() => setConfirming(true)}>
                  <Text style={styles.dangerText}>Account delete karein</Text>
                </TouchableOpacity>
              ) : (
                <>
                  <Text style={styles.confirmText}>
                    Pakka delete karna hai? Ye wapas nahi ho sakta.
                  </Text>
                  <TouchableOpacity
                    style={[styles.button, styles.danger]}
                    onPress={handleDelete}
                    disabled={deleting}>
                    {deleting ? (
                      <ActivityIndicator color="#fff" size="small" />
                    ) : (
                      <Text style={styles.buttonText}>Haan, delete karein</Text>
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
