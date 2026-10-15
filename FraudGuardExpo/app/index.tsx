import React, { useEffect, useState } from "react";
import { Platform } from "react-native";
import { Redirect } from "expo-router";
import AnalyzerScreen from "../src/screens/AnalyzerScreen";
import { isWelcomeDone } from "../src/services/protection";

// Pehli baar app khule to welcome screen, jo har permission se pehle us ki
// wajah batati hai. Android ke siwa koi permission nahi, to wahan seedha home.
export default function Home() {
  const [welcomeDone, setWelcomeDone] = useState<boolean | null>(
    Platform.OS === "android" ? null : true,
  );

  useEffect(() => {
    if (welcomeDone === null) isWelcomeDone().then(setWelcomeDone);
  }, [welcomeDone]);

  if (welcomeDone === null) return null;
  if (!welcomeDone) return <Redirect href="/welcome" />;
  return <AnalyzerScreen />;
}
