// src/screens/AnalyzerScreen.js
import React, { useEffect, useState } from "react";
import {
  ActivityIndicator,
  SafeAreaView,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from "react-native";
import ComplaintForm from "../components/ComplaintForm";
import EducationPanel from "../components/EducationPanel";
import FileUploader from "../components/FileUploader";
import MessageInput from "../components/MessageInput";
import ResultCard from "../components/ResultCard";
import TabBar from "../components/TabBar";
import { analyzeAudio, analyzeText } from "../services/api";

export default function AnalyzerScreen() {
  const [activeTab, setActiveTab] = useState("text");
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [toast, setToast] = useState(null);

  useEffect(() => {
    if (toast) {
      const t = setTimeout(() => setToast(null), 3500);
      return () => clearTimeout(t);
    }
  }, [toast]);

  const showToast = (message, type = "info") => setToast({ message, type });

  const handleAnalyze = async (text) => {
    setLoading(true);
    setResult(null);
    try {
      const data = await analyzeText(text);
      if (data.error) {
        showToast(data.error, "error");
        return;
      }
      setResult(data);
      showToast("Analysis complete!", "success");
    } catch {
      showToast("Backend connection failed.", "error");
    } finally {
      setLoading(false);
    }
  };

  const handleFileAnalyze = async (content) => {
    setLoading(true);
    setResult(null);
    try {
      const data = await analyzeText(content);
      if (data.error) {
        showToast(data.error, "error");
        return;
      }
      setResult(data);
      showToast("File analysis complete!", "success");
    } catch {
      showToast("Backend connection failed.", "error");
    } finally {
      setLoading(false);
    }
  };

  const handleAudioAnalyze = async (fileObj) => {
    setLoading(true);
    setResult(null);
    showToast("Transcribing audio... 20-40 sec", "info");
    try {
      const data = await analyzeAudio(
        fileObj.uri,
        fileObj.name,
        fileObj.mimeType,
      );
      if (data.error) {
        showToast(data.error, "error");
        return;
      }
      setResult(data);
      showToast("Audio analysis complete!", "success");
    } catch {
      showToast("Backend connection failed.", "error");
    } finally {
      setLoading(false);
    }
  };

  return (
    <SafeAreaView style={styles.safe}>
      <ScrollView
        contentContainerStyle={styles.container}
        keyboardShouldPersistTaps="handled"
      >
        <View style={styles.header}>
          <View style={styles.iconBadge}>
            <Text style={styles.iconEmoji}>🛡️</Text>
          </View>
          <Text style={styles.title}>
            FraudGuard <Text style={styles.titleGreen}>PK</Text>
          </Text>
          <Text style={styles.subtitle}>
            AI-powered scam detection for text, files & audio
          </Text>
          <View style={styles.badge}>
            <Text style={styles.badgeText}>PECA 2016 Compliant</Text>
          </View>
        </View>

        <TabBar activeTab={activeTab} onChange={setActiveTab} />

        {activeTab === "text" && (
          <MessageInput onAnalyze={handleAnalyze} loading={loading} />
        )}
        {activeTab === "file" && (
          <FileUploader
            onFileAnalyze={handleFileAnalyze}
            loading={loading}
            type="text"
          />
        )}
        {activeTab === "audio" && (
          <FileUploader
            onFileAnalyze={handleAudioAnalyze}
            loading={loading}
            type="audio"
          />
        )}

        {loading && (
          <View style={styles.loadingBox}>
            <ActivityIndicator size="large" color="#1d4ed8" />
            <Text style={styles.loadingText}>
              {activeTab === "audio"
                ? "Processing audio file..."
                : "AI analyzing message patterns..."}
            </Text>
          </View>
        )}

        {result && !loading && (
          <>
            <ResultCard result={result} />
            <EducationPanel items={result.education} />
            {result.complaint && <ComplaintForm text={result.complaint} />}
          </>
        )}

        {toast && (
          <View
            style={[
              styles.toast,
              toast.type === "error" && styles.toastError,
              toast.type === "success" && styles.toastSuccess,
            ]}
          >
            <Text style={styles.toastText}>{toast.message}</Text>
          </View>
        )}

        <Text style={styles.footer}>
          🔒 Your files are encrypted • Supports .txt, .mp3, .wav, .m4a
        </Text>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: "#f0f9ff" },
  container: { padding: 20, paddingBottom: 40 },
  header: { alignItems: "center", marginBottom: 20 },
  iconBadge: {
    backgroundColor: "#1d4ed8",
    padding: 14,
    borderRadius: 18,
    marginBottom: 12,
  },
  iconEmoji: { fontSize: 28 },
  title: { fontSize: 28, fontWeight: "800", color: "#1e3a8a" },
  titleGreen: { color: "#16a34a" },
  subtitle: {
    fontSize: 13,
    color: "#6b7280",
    marginTop: 6,
    textAlign: "center",
  },
  badge: {
    backgroundColor: "#dbeafe",
    borderRadius: 20,
    paddingHorizontal: 12,
    paddingVertical: 4,
    marginTop: 10,
  },
  badgeText: { fontSize: 11, color: "#1d4ed8", fontWeight: "600" },
  loadingBox: { alignItems: "center", paddingVertical: 30 },
  loadingText: { fontSize: 13, color: "#6b7280", marginTop: 10 },
  toast: {
    marginTop: 16,
    backgroundColor: "#374151",
    borderRadius: 10,
    padding: 12,
  },
  toastError: { backgroundColor: "#dc2626" },
  toastSuccess: { backgroundColor: "#16a34a" },
  toastText: { color: "#fff", fontSize: 12, textAlign: "center" },
  footer: {
    fontSize: 11,
    color: "#9ca3af",
    textAlign: "center",
    marginTop: 30,
  },
});
