import { Stack } from "expo-router";
import React, { useEffect } from "react";
import { Platform } from "react-native";
import { SafeAreaProvider } from "react-native-safe-area-context";
import { StatusBar } from "expo-status-bar";
import { ensureNotificationsReady } from "../src/services/notifications";
import { startCallMonitor } from "../src/services/callMonitor";

export default function RootLayout() {
  useEffect(() => {
    if (Platform.OS === "web") return;
    ensureNotificationsReady();
    startCallMonitor();
  }, []);

  return (
    <SafeAreaProvider>
      <StatusBar style="dark" />
      <Stack screenOptions={{ headerShown: false }} />
    </SafeAreaProvider>
  );
}
