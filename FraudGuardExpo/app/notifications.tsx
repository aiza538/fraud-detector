import React, { useCallback, useState } from "react";
import {
  FlatList,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { router } from "expo-router";
import { useFocusEffect } from "@react-navigation/native";
import { getAlerts } from "../src/services/fraudAlerts";

const LEVEL_COLORS: Record<string, string> = {
  scam: "#dc2626",
  suspicious: "#d97706",
  unknown: "#6b7280",
};

const SOURCE_EMOJI: Record<string, string> = {
  phone: "📞",
  whatsapp: "💬",
  telegram: "📨",
  sms: "📩",
  carrier: "📡",
};

type AlertItem = {
  id: string;
  number: string;
  message: string;
  level: string;
  source: string;
  time: string;
};

function formatTime(iso: string) {
  try {
    const d = new Date(iso);
    return d.toLocaleString("en-PK", {
      day: "numeric",
      month: "short",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return iso;
  }
}

export default function NotificationsScreen() {
  const [alerts, setAlerts] = useState<AlertItem[]>([]);

  useFocusEffect(
    useCallback(() => {
      let active = true;
      getAlerts().then((list) => {
        if (active) setAlerts(list as AlertItem[]);
      });
      return () => {
        active = false;
      };
    }, []),
  );

  const openAlert = (item: AlertItem) => {
    router.push({
      pathname: "/alert",
      params: {
        number: item.number,
        message: item.message,
        level: item.level,
        source: item.source,
        saved: "1",
      },
    });
  };

  return (
    <SafeAreaView style={styles.safe}>
      <View style={styles.header}>
        <TouchableOpacity onPress={() => router.back()}>
          <Text style={styles.back}>←</Text>
        </TouchableOpacity>
        <Text style={styles.title}>Fraud Alert History</Text>
        <View style={{ width: 24 }} />
      </View>

      <FlatList
        data={alerts}
        keyExtractor={(item) => item.id}
        contentContainerStyle={styles.list}
        ListEmptyComponent={
          <View style={styles.empty}>
            <Text style={styles.emptyEmoji}>🛡️</Text>
            <Text style={styles.emptyTitle}>Koi alerts nahi mile abhi tak</Text>
            <Text style={styles.emptyText}>
              Jab koi scam ya suspicious call aayegi, wo yahan list hogi.
            </Text>
          </View>
        }
        renderItem={({ item }) => (
          <TouchableOpacity style={styles.item} onPress={() => openAlert(item)}>
            <View
              style={[
                styles.dot,
                { backgroundColor: LEVEL_COLORS[item.level] ?? "#d97706" },
              ]}
            />
            <View style={styles.itemBody}>
              <Text style={styles.itemNumber} numberOfLines={1}>
                {SOURCE_EMOJI[item.source] ?? "📞"} {item.number}
              </Text>
              <Text style={styles.itemMessage} numberOfLines={2}>
                {item.message}
              </Text>
              <Text style={styles.itemTime}>{formatTime(item.time)}</Text>
            </View>
            <Text style={styles.chevron}>›</Text>
          </TouchableOpacity>
        )}
      />
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: "#f0f9ff" },
  header: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    paddingHorizontal: 16,
    paddingVertical: 12,
  },
  back: { fontSize: 24, color: "#1e3a8a", paddingHorizontal: 4 },
  title: { fontSize: 18, fontWeight: "800", color: "#1e3a8a" },
  list: { padding: 16, paddingTop: 4, flexGrow: 1 },
  empty: { alignItems: "center", marginTop: 80, paddingHorizontal: 30 },
  emptyEmoji: { fontSize: 44, marginBottom: 10 },
  emptyTitle: { fontSize: 16, fontWeight: "700", color: "#1e3a8a" },
  emptyText: {
    fontSize: 13,
    color: "#6b7280",
    textAlign: "center",
    marginTop: 6,
    lineHeight: 19,
  },
  item: {
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: "#fff",
    borderRadius: 12,
    padding: 14,
    marginBottom: 10,
    elevation: 1,
    shadowColor: "#000",
    shadowOpacity: 0.05,
    shadowRadius: 6,
    shadowOffset: { width: 0, height: 1 },
  },
  dot: { width: 10, height: 10, borderRadius: 5, marginRight: 12 },
  itemBody: { flex: 1 },
  itemNumber: { fontSize: 15, fontWeight: "700", color: "#1e3a8a" },
  itemMessage: { fontSize: 12, color: "#6b7280", marginTop: 2, lineHeight: 17 },
  itemTime: { fontSize: 11, color: "#9ca3af", marginTop: 4 },
  chevron: { fontSize: 22, color: "#9ca3af", marginLeft: 8 },
});
