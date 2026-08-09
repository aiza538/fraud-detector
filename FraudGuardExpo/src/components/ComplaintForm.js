// src/components/ComplaintForm.js
import * as FileSystem from "expo-file-system";
import * as Sharing from "expo-sharing";
import { Alert, StyleSheet, Text, TouchableOpacity, View } from "react-native";

export default function ComplaintForm({ text }) {
  if (!text) return null;

  const downloadComplaint = async () => {
    try {
      const fileUri = FileSystem.documentDirectory + "FIA_Complaint.txt";
      await FileSystem.writeAsStringAsync(fileUri, text);

      if (await Sharing.isAvailableAsync()) {
        await Sharing.shareAsync(fileUri);
      } else {
        Alert.alert("Saved", `File saved to: ${fileUri}`);
      }
    } catch (e) {
      Alert.alert("Error", "Could not save complaint file");
    }
  };

  return (
    <View style={styles.card}>
      <View style={styles.header}>
        <Text style={styles.title}>📄 Auto-generated FIA Complaint</Text>
        <TouchableOpacity style={styles.button} onPress={downloadComplaint}>
          <Text style={styles.buttonText}>Download</Text>
        </TouchableOpacity>
      </View>
      <View style={styles.textBox}>
        <Text style={styles.text}>{text}</Text>
      </View>
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
  textBox: { backgroundColor: "#f9fafb", borderRadius: 10, padding: 12 },
  text: { fontSize: 11, color: "#6b7280", fontFamily: "monospace" },
});
