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
import * as Linking from "expo-linking";
import { useFocusEffect } from "@react-navigation/native";
import type { PurchasesPackage } from "react-native-purchases";
import { getAccount } from "../src/services/api";
import { buy, loadPackages, MANAGE_URL, restore, storeAvailable } from "../src/services/premium";

type Account = {
  id: string;
  premium: boolean;
  premium_until: number | null;
  limits: { analyze_text: number; analyze_audio: number };
};

// Server ki limits (config.py) — sirf dikhane ke liye; asal limit server lagata hai.
const FREE = { text: 5, voice: 1 };
const PREMIUM = { text: 60, voice: 10 };

const PERIODS: Record<string, string> = {
  MONTHLY: "per month",
  ANNUAL: "per year",
  SIX_MONTH: "every 6 months",
  THREE_MONTH: "every 3 months",
  WEEKLY: "per week",
};

export default function PremiumScreen() {
  const [account, setAccount] = useState<Account | null>(null);
  const [packages, setPackages] = useState<PurchasesPackage[] | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  useFocusEffect(
    useCallback(() => {
      let active = true;
      setError("");
      getAccount()
        .then(async (data: Account) => {
          if (!active) return;
          setAccount(data);
          if (!data.premium && storeAvailable()) {
            const list = await loadPackages(data.id);
            if (active) setPackages(list);
          }
        })
        .catch((err: any) => active && setError(err?.message || "Could not load plans."));
      return () => {
        active = false;
      };
    }, []),
  );

  const finish = (updated: Account | null, okMessage: string, noneMessage: string) => {
    if (!updated) return;
    setAccount(updated);
    if (updated.premium) setNotice(okMessage);
    else setError(noneMessage);
  };

  const handleBuy = async (pkg: PurchasesPackage) => {
    setBusy(pkg.identifier);
    setError("");
    setNotice("");
    try {
      finish(
        await buy(pkg),
        "Welcome to Premium! Your higher limits are active now.",
        "The payment went through but we could not confirm it yet. Tap “Restore purchases” in a minute.",
      );
    } catch (err: any) {
      setError(err?.message || "The purchase could not be completed.");
    } finally {
      setBusy(null);
    }
  };

  const handleRestore = async () => {
    if (!account) return;
    setBusy("restore");
    setError("");
    setNotice("");
    try {
      finish(
        await restore(account.id),
        "Your Premium plan has been restored.",
        "No active subscription was found for this Google account.",
      );
    } catch (err: any) {
      setError(err?.message || "Could not restore purchases. Please try again.");
    } finally {
      setBusy(null);
    }
  };

  const until =
    account?.premium_until && account.premium_until < 4102444800
      ? new Date(account.premium_until * 1000).toLocaleDateString()
      : null;

  return (
    <SafeAreaView style={styles.safe}>
      <View style={styles.header}>
        <TouchableOpacity onPress={() => router.back()}>
          <Text style={styles.back}>←</Text>
        </TouchableOpacity>
        <Text style={styles.title}>FraudGuard AI Premium</Text>
        <View style={{ width: 24 }} />
      </View>

      <ScrollView contentContainerStyle={styles.container}>
        <View style={styles.card}>
          <Text style={styles.cardTitle}>Always free</Text>
          <Text style={styles.text}>
            ✓ Scam call alerts{"\n"}✓ WhatsApp and SMS scanning{"\n"}✓ Number
            checks and scam reports
          </Text>
        </View>

        <View style={styles.card}>
          <Text style={styles.cardTitle}>AI checks per day</Text>
          <View style={styles.row}>
            <Text style={[styles.cell, styles.cellLabel]} />
            <Text style={[styles.cell, styles.head]}>Free</Text>
            <Text style={[styles.cell, styles.head, styles.premiumText]}>Premium</Text>
          </View>
          <View style={styles.row}>
            <Text style={[styles.cell, styles.cellLabel]}>Message checks</Text>
            <Text style={styles.cell}>{FREE.text}</Text>
            <Text style={[styles.cell, styles.premiumText]}>{PREMIUM.text}</Text>
          </View>
          <View style={styles.row}>
            <Text style={[styles.cell, styles.cellLabel]}>Voice note checks</Text>
            <Text style={styles.cell}>{FREE.voice}</Text>
            <Text style={[styles.cell, styles.premiumText]}>{PREMIUM.voice}</Text>
          </View>
        </View>

        {account === null && !error ? (
          <ActivityIndicator color="#1d4ed8" style={{ marginTop: 12 }} />
        ) : account?.premium ? (
          <View style={styles.card}>
            <Text style={[styles.cardTitle, styles.premiumText]}>✓ You have Premium</Text>
            <Text style={styles.text}>
              {until ? `Your plan renews or ends on ${until}.` : "Your plan is active."}
            </Text>
            <TouchableOpacity style={styles.outline} onPress={() => Linking.openURL(MANAGE_URL)}>
              <Text style={styles.outlineText}>Manage subscription</Text>
            </TouchableOpacity>
          </View>
        ) : account && !storeAvailable() ? (
          <View style={styles.card}>
            <Text style={styles.text}>
              Premium can only be bought in the FraudGuard AI app installed
              from Google Play.
            </Text>
          </View>
        ) : account ? (
          <View style={styles.card}>
            <Text style={styles.cardTitle}>Choose a plan</Text>
            {packages === null ? (
              <ActivityIndicator color="#1d4ed8" style={{ marginTop: 12 }} />
            ) : packages.length === 0 ? (
              <Text style={styles.text}>
                Plans are not available right now. Please try again later.
              </Text>
            ) : (
              packages.map((pkg) => (
                <TouchableOpacity
                  key={pkg.identifier}
                  style={styles.button}
                  disabled={busy !== null}
                  onPress={() => handleBuy(pkg)}>
                  {busy === pkg.identifier ? (
                    <ActivityIndicator color="#fff" size="small" />
                  ) : (
                    <Text style={styles.buttonText}>
                      {pkg.product.priceString} {PERIODS[pkg.packageType] ?? ""}
                    </Text>
                  )}
                </TouchableOpacity>
              ))
            )}
            <TouchableOpacity onPress={handleRestore} disabled={busy !== null}>
              {busy === "restore" ? (
                <ActivityIndicator color="#475569" size="small" style={{ marginTop: 14 }} />
              ) : (
                <Text style={styles.link}>Restore purchases</Text>
              )}
            </TouchableOpacity>
            <Text style={styles.fineprint}>
              Payment is charged to your Google Play account. Subscriptions
              renew automatically until cancelled. Cancel anytime in Google
              Play → Payments & subscriptions → Subscriptions.
            </Text>
          </View>
        ) : null}

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
    marginBottom: 16,
    elevation: 2,
    shadowColor: "#000",
    shadowOpacity: 0.06,
    shadowRadius: 8,
    shadowOffset: { width: 0, height: 2 },
  },
  cardTitle: { fontSize: 16, fontWeight: "800", color: "#1e3a8a", marginBottom: 8 },
  text: { fontSize: 13, color: "#374151", lineHeight: 22 },
  row: { flexDirection: "row", paddingVertical: 6 },
  cell: { flex: 1, fontSize: 14, color: "#374151", textAlign: "center" },
  cellLabel: { flex: 2, textAlign: "left" },
  head: { fontWeight: "800" },
  premiumText: { color: "#16a34a", fontWeight: "800" },
  button: {
    backgroundColor: "#1d4ed8",
    borderRadius: 12,
    paddingVertical: 14,
    alignItems: "center",
    marginTop: 12,
  },
  buttonText: { color: "#fff", fontSize: 15, fontWeight: "700" },
  outline: {
    borderWidth: 1.5,
    borderColor: "#1d4ed8",
    borderRadius: 12,
    paddingVertical: 13,
    alignItems: "center",
    marginTop: 14,
  },
  outlineText: { color: "#1d4ed8", fontSize: 14, fontWeight: "700" },
  link: { color: "#475569", fontSize: 13, fontWeight: "600", textAlign: "center", marginTop: 14 },
  fineprint: { fontSize: 11, color: "#6b7280", lineHeight: 16, marginTop: 14 },
  notice: { color: "#16a34a", fontSize: 13, textAlign: "center", fontWeight: "700" },
  error: { color: "#dc2626", fontSize: 13, textAlign: "center", marginTop: 4 },
});
