import { StatusBar } from "expo-status-bar";
import React from "react";
import { SafeAreaProvider } from "react-native-safe-area-context";
import AnalyzerScreen from "../src/screens/AnalyzerScreen";

export default function RootLayout() {
  return (
    <SafeAreaProvider>
      <StatusBar style="dark" />
      <AnalyzerScreen />
    </SafeAreaProvider>
  );
}
