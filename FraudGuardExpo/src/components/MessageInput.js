// src/components/MessageInput.js
import React, { useState } from "react";
import {
  ActivityIndicator,
  Alert,
  StyleSheet,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from "react-native";

export default function MessageInput({ onAnalyze, loading }) {
  const [text, setText] = useState("");

  const handleSubmit = () => {
    if (!text.trim()) {
      Alert.alert("Empty message", "Please paste a message to analyze");
      return;
    }
    if (text.trim().length < 20) {
      Alert.alert(
        "Too short",
        "Message seems too short. Please paste the complete message",
      );
      return;
    }
    onAnalyze(text);
  };

  return (
    <View style={styles.card}>
      <Text style={styles.title}>Paste Suspicious Message</Text>
      <Text style={styles.subtitle}>
        SMS, WhatsApp, or social media messages
      </Text>

      <TextInput
        style={styles.textArea}
        multiline
        numberOfLines={6}
        value={text}
        onChangeText={setText}
        placeholder={`Paste suspicious message here...\n\nExample: "Assalam-o-Alaikum, main HBL security team se bol raha hoon. Aap ka account block ho raha hai. Fooran OTP share karein..."`}
        placeholderTextColor="#9ca3af"
      />

      <Text style={styles.charCount}>{text.length} characters</Text>

      <TouchableOpacity
        style={[
          styles.button,
          (loading || !text.trim()) && styles.buttonDisabled,
        ]}
        onPress={handleSubmit}
        disabled={loading || !text.trim()}
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
  subtitle: { fontSize: 12, color: "#9ca3af", marginTop: 2, marginBottom: 12 },
  textArea: {
    borderWidth: 1,
    borderColor: "#e5e7eb",
    borderRadius: 12,
    padding: 14,
    fontSize: 14,
    color: "#374151",
    backgroundColor: "#f9fafb",
    minHeight: 130,
    textAlignVertical: "top",
  },
  charCount: {
    fontSize: 10,
    color: "#9ca3af",
    textAlign: "right",
    marginTop: 6,
    marginBottom: 12,
  },
  button: {
    backgroundColor: "#1d4ed8",
    borderRadius: 12,
    paddingVertical: 12,
    alignItems: "center",
    shadowColor: "#1d4ed8",
    shadowOpacity: 0.3,
    shadowRadius: 8,
    shadowOffset: { width: 0, height: 3 },
    elevation: 4,
  },
  buttonDisabled: { backgroundColor: "#93b4f0", shadowOpacity: 0 },
  buttonDisabled: { opacity: 0.5 },
  buttonText: { color: "#fff", fontWeight: "700", fontSize: 15 },
});
