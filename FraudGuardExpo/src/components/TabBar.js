// src/components/TabBar.js
import React from "react";
import { StyleSheet, Text, TouchableOpacity, View } from "react-native";

const TABS = [
  { id: "text", label: "Paste Text", icon: "💬" },
  { id: "file", label: "Upload File", icon: "📄" },
  { id: "audio", label: "Upload Audio", icon: "🎤" },
];

export default function TabBar({ activeTab, onChange }) {
  return (
    <View style={styles.wrapper}>
      {TABS.map((tab) => (
        <TouchableOpacity
          key={tab.id}
          onPress={() => onChange(tab.id)}
          activeOpacity={0.8}
          style={[styles.tab, activeTab === tab.id && styles.tabActive]}
        >
          <Text style={styles.icon}>{tab.icon}</Text>
          <Text
            numberOfLines={1}
            style={[styles.label, activeTab === tab.id && styles.labelActive]}
          >
            {tab.label}
          </Text>
        </TouchableOpacity>
      ))}
    </View>
  );
}

const styles = StyleSheet.create({
  wrapper: {
    flexDirection: "row",
    backgroundColor: "rgba(255,255,255,0.65)",
    borderRadius: 16,
    padding: 5,
    gap: 6,
    marginBottom: 18,
    shadowColor: "#000",
    shadowOpacity: 0.04,
    shadowRadius: 6,
    shadowOffset: { width: 0, height: 2 },
  },
  tab: {
    flex: 1,
    alignItems: "center",
    justifyContent: "center",
    paddingVertical: 11,
    borderRadius: 12,
  },
  tabActive: {
    backgroundColor: "#1d4ed8",
    shadowColor: "#1d4ed8",
    shadowOpacity: 0.3,
    shadowRadius: 8,
    shadowOffset: { width: 0, height: 3 },
    elevation: 4,
  },
  icon: { fontSize: 15 },
  label: { fontSize: 10, color: "#6b7280", marginTop: 3, fontWeight: "600" },
  labelActive: { color: "#fff" },
});
