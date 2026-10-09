// src/components/ComplaintForm.js
import * as Linking from "expo-linking";
import { File, Paths } from "expo-file-system";
import * as Sharing from "expo-sharing";
import { useState } from "react";
import { Alert, StyleSheet, Text, TouchableOpacity, View } from "react-native";
import {
  FIA_CYBER_HELPLINE,
  FIA_GENERAL_HELPLINE,
  FIA_PORTAL_URL,
  buildEmailLink,
} from "../services/fiaLinks";

export default function ComplaintForm({ text, number, channel }) {
  const [busy, setBusy] = useState(false);
  if (!text) return null;

  const open = async (url) => {
    try {
      if (await Linking.canOpenURL(url)) {
        await Linking.openURL(url);
      } else {
        Alert.alert("Link nahi khul saka", url);
      }
    } catch {
      Alert.alert("Error", "Link nahi khul saka");
    }
  };

  const downloadComplaint = async () => {
    try {
      const file = new File(Paths.document, "FIA_Complaint.txt");
      file.write(text);

      if (await Sharing.isAvailableAsync()) {
        await Sharing.shareAsync(file.uri);
      } else {
        Alert.alert("Saved", `File saved to: ${file.uri}`);
      }
    } catch (_e) {
      Alert.alert("Error", "Could not save complaint file");
    }
  };

  // Sabse important action: complaint seedha FIA portal par bhej de. Email
  // tab user ke email app me khulega (user khud bhejta hai — hum apne taraf
  // se kuch bhejte nahi), wo backup ke liye hai.
  const fileFiaComplaint = async () => {
    setBusy(true);
    await open(FIA_PORTAL_URL);
    setBusy(false);
  };

  const emailFiaComplaint = async () => {
    setBusy(true);
    await open(
      buildEmailLink({
        number,
        message: text.split("\n")[0],
        channel,
      }),
    );
    setBusy(false);
  };

  const callHelpline = async () => {
    setBusy(true);
    await open(`tel:${FIA_CYBER_HELPLINE}`);
    setBusy(false);
  };

  return (
    <View style={styles.card}>
      <View style={styles.header}>
        <Text style={styles.title}>📄 FIA Complaint (PECA 2016)</Text>
        <TouchableOpacity style={styles.button} onPress={downloadComplaint}>
          <Text style={styles.buttonText}>Save</Text>
        </TouchableOpacity>
      </View>

      <Text style={styles.intro}>
        Ye complaint FIA Cyber Crime Wing tak bhejni hogi. Neeche se seedha
        official portal ya email par bhej sakte hain.
      </Text>

      <View style={styles.actions}>
        <TouchableOpacity
          style={[styles.primary, busy && styles.disabled]}
          onPress={fileFiaComplaint}
          disabled={busy}>
          <Text style={styles.primaryText}>
            🚔 FIA par complaint karein
          </Text>
        </TouchableOpacity>

        <TouchableOpacity
          style={[styles.secondary, busy && styles.disabled]}
          onPress={emailFiaComplaint}
          disabled={busy}>
          <Text style={styles.secondaryText}>
            ✉️ Email se bhejein (helpdesk.cyber@fia.gov.pk)
          </Text>
        </TouchableOpacity>

        <TouchableOpacity
          style={[styles.secondary, busy && styles.disabled]}
          onPress={callHelpline}
          disabled={busy}>
          <Text style={styles.secondaryText}>
            📞 Cyber helpline {FIA_CYBER_HELPLINE} (8am–4pm)
          </Text>
        </TouchableOpacity>
      </View>

      <View style={styles.textBox}>
        <Text style={styles.text}>{text}</Text>
      </View>

      <Text style={styles.disclaimer}>
        Call/Facebook/in-person: Cyber Crime HQ, National Police Foundation
        Building, Sector G-10/4, Islamabad. 15 CCRC centres hain — nearest one
        in-person sab se tez rasta hai. General FIA helpline{" "}
        {FIA_GENERAL_HELPLINE}.
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: "#fff",
    borderRadius: 16,
    padding: 20,
    marginTop: 16,
    borderWidth: 1,
    borderStyle: "dashed",
    borderColor: "#bfdbfe",
  },
  header: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: 10,
  },
  title: { fontSize: 13, fontWeight: "700", color: "#374151" },
  button: {
    backgroundColor: "#eff6ff",
    borderWidth: 1,
    borderColor: "#bfdbfe",
    borderRadius: 8,
    paddingHorizontal: 12,
    paddingVertical: 6,
  },
  buttonText: { fontSize: 11, color: "#1d4ed8", fontWeight: "600" },
  intro: {
    fontSize: 12,
    color: "#4b5563",
    lineHeight: 18,
    marginBottom: 12,
  },
  actions: { gap: 8, marginBottom: 12 },
  primary: {
    backgroundColor: "#1d4ed8",
    borderRadius: 12,
    paddingVertical: 13,
    alignItems: "center",
  },
  primaryText: { color: "#fff", fontSize: 14, fontWeight: "700" },
  secondary: {
    borderWidth: 1,
    borderColor: "#bfdbfe",
    borderRadius: 12,
    paddingVertical: 11,
    alignItems: "center",
  },
  secondaryText: { color: "#1d4ed8", fontSize: 13, fontWeight: "600" },
  disabled: { opacity: 0.5 },
  textBox: { backgroundColor: "#f9fafb", borderRadius: 10, padding: 12 },
  text: { fontSize: 11, color: "#6b7280", fontFamily: "monospace" },
  disclaimer: {
    fontSize: 10,
    color: "#9ca3af",
    marginTop: 10,
    lineHeight: 15,
  },
});
