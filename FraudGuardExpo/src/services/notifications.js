// src/services/notifications.js
// expo-notifications setup + fraud alert notification helper
import * as Notifications from "expo-notifications";
import { Platform } from "react-native";

export const FRAUD_CHANNEL_ID = "fraud-alerts";

// App foreground mein bhi notification dikhaye
Notifications.setNotificationHandler({
  handleNotification: async () => ({
    shouldPlaySound: true,
    shouldSetBadge: false,
    shouldShowBanner: true,
    shouldShowList: true,
  }),
});

export async function ensureNotificationsReady() {
  if (Platform.OS === "android") {
    await Notifications.setNotificationChannelAsync(FRAUD_CHANNEL_ID, {
      name: "Fraud Alerts",
      importance: Notifications.AndroidImportance.MAX,
      vibrationPattern: [0, 250, 250, 250],
      lightColor: "#dc2626",
    });
  }
  const { status } = await Notifications.getPermissionsAsync();
  if (status !== "granted") {
    await Notifications.requestPermissionsAsync();
  }
}

const LEVEL_TITLES = {
  scam: "🚨 Scam call detected",
  suspicious: "⚠️ Suspicious call detected",
};

export async function showFraudAlertNotification({ number, message, level }) {
  const content = {
    title: LEVEL_TITLES[level] ?? LEVEL_TITLES.suspicious,
    body: `${number}\n${message}`,
    data: { number, message, level, source: "phone", saved: "1" },
  };
  await Notifications.scheduleNotificationAsync({
    content,
    trigger:
      Platform.OS === "android"
        ? { channelId: FRAUD_CHANNEL_ID }
        : null,
  });
}
