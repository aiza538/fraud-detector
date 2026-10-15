import { Stack } from "expo-router";
import React, { useEffect } from "react";
import { Platform } from "react-native";
import { SafeAreaProvider } from "react-native-safe-area-context";
import { StatusBar } from "expo-status-bar";
import { ensureNotificationsReady } from "../src/services/notifications";
import { startCallMonitor } from "../src/services/callMonitor";
// Background sync ka task app ke start hote hi define hona chahiye.
import { registerBackgroundSync } from "../src/services/backgroundSync";

export default function RootLayout() {
  useEffect(() => {
    if (Platform.OS === "web") return;
    ensureNotificationsReady();
    startCallMonitor();
    registerBackgroundSync();
  }, []);

  return (
    <SafeAreaProvider>
      <StatusBar style="dark" />
      <Stack screenOptions={{ headerShown: false }} />
    </SafeAreaProvider>
  );
}
