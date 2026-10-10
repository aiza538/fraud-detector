// src/components/FileUploader.js
import * as DocumentPicker from "expo-document-picker";
// import * as FileSystem from "expo-file-system/legacy";
import React, { useState } from "react";
import {
  ActivityIndicator,
  Alert,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from "react-native";

export default function FileUploader({ onFileAnalyze, loading, type }) {
  const [file, setFile] = useState(null);

  const pickFile = async () => {
    try {
      const result = await DocumentPicker.getDocumentAsync({
        type:
          type === "text"
            ? "text/plain"
            : [
                "audio/mpeg",
                "audio/mp4",
                "audio/wav",
                "audio/x-wav",
                "audio/*",
              ],
        copyToCacheDirectory: true,
      });

      if (result.canceled) return;
      const picked = result.assets[0];
      setFile(picked);
    } catch (e) {
      Alert.alert("Error", "Could not open file picker");
    }
  };

  const handleAnalyze = async () => {
    if (!file) {
      Alert.alert("No file", "Please select a file first");
      return;
    }
    if (type === "text") {
      try {
        const response = await fetch(file.uri);
        const content = await response.text();
        onFileAnalyze(content);
      } catch (e) {
        Alert.alert("Error", "Could not read file content");
      }
    } else {
      onFileAnalyze({
        uri: file.uri,
        name: file.name,
        mimeType: file.mimeType,
      });
    }
  };

  return (
    <View style={styles.card}>
      <Text style={styles.title}>
        {type === "text" ? "📄 Upload Text File" : "🎤 Upload Audio File"}
      </Text>
      <Text style={styles.subtitle}>
        {type === "text"
          ? "Select a .txt file"
          : "Select .mp3, .wav, .m4a (max 10MB) — tap ☰ menu in picker to browse folders"}
      </Text>
      <TouchableOpacity style={styles.dropZone} onPress={pickFile}>
        <Text style={styles.dropIcon}>⬆️</Text>
        <Text style={styles.dropText}>
          {file ? file.name : "Tap to browse files"}
        </Text>
      </TouchableOpacity>

      <TouchableOpacity
        style={[styles.button, (loading || !file) && styles.buttonDisabled]}
        onPress={handleAnalyze}
        disabled={loading || !file}
      >
        {loading ? (
          <ActivityIndicator color="#fff" />
        ) : (
          <Text style={styles.buttonText}>Detect Fraud</Text>
        )}
      </TouchableOpacity>
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: "#fff",
    borderRadius: 16,
    padding: 20,
    shadowColor: "#000",
    shadowOpacity: 0.08,
    shadowRadius: 10,
    shadowOffset: { width: 0, height: 4 },
    elevation: 3,
  },
  title: { fontSize: 16, fontWeight: "700", color: "#374151" },
  subtitle: { fontSize: 12, color: "#9ca3af", marginTop: 2, marginBottom: 14 },
  dropZone: {
    borderWidth: 2,
    borderColor: "#d1d5db",
    borderStyle: "dashed",
    borderRadius: 12,
    paddingVertical: 30,
    alignItems: "center",
    backgroundColor: "#f9fafb",
  },
  dropIcon: { fontSize: 26, marginBottom: 8 },
  dropText: {
    fontSize: 13,
    color: "#4b5563",
    paddingHorizontal: 20,
    textAlign: "center",
  },
  button: {
    backgroundColor: "#1d4ed8",
    borderRadius: 12,
    paddingVertical: 12,
    alignItems: "center",
    marginTop: 16,
  },
  buttonDisabled: { opacity: 0.5 },
  buttonText: { color: "#fff", fontWeight: "700", fontSize: 15 },
});
