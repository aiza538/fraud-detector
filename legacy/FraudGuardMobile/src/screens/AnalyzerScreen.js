// src/screens/AnalyzerScreen.js
import React, { useState } from 'react';
import {
  View,
  Text,
  ScrollView,
  StyleSheet,
  ActivityIndicator,
  SafeAreaView,
} from 'react-native';
import MessageInput from '../components/MessageInput';
import ResultCard from '../components/ResultCard';
import EducationPanel from '../components/EducationPanel';
import { analyzeText } from '../services/api';

export default function AnalyzerScreen() {
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);

  const handleAnalyze = async text => {
    setLoading(true);
    setResult(null);
    try {
      const data = await analyzeText(text);
      setResult(data);
    } catch (err) {
      setResult({ error: err.message || 'Backend connection failed.' });
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
            AI-powered scam detection for text messages
          </Text>
        </View>

        <MessageInput onAnalyze={handleAnalyze} loading={loading} />

        {loading && (
          <View style={styles.loadingBox}>
            <ActivityIndicator size="large" color="#1d4ed8" />
            <Text style={styles.loadingText}>
              AI analyzing message patterns...
            </Text>
          </View>
        )}

        {result && !loading && (
          <>
            <ResultCard result={result} />
            <EducationPanel items={result.education} />
          </>
        )}

        <Text style={styles.footer}>
          🔒 Your messages are analyzed securely
        </Text>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: '#f0f9ff' },
  container: { padding: 20, paddingBottom: 40 },
  header: { alignItems: 'center', marginBottom: 24 },
  iconBadge: {
    backgroundColor: '#1d4ed8',
    padding: 14,
    borderRadius: 18,
    marginBottom: 12,
  },
  iconEmoji: { fontSize: 28 },
  title: { fontSize: 28, fontWeight: '800', color: '#1e3a8a' },
  titleGreen: { color: '#16a34a' },
  subtitle: { fontSize: 14, color: '#6b7280', marginTop: 6 },
  loadingBox: { alignItems: 'center', paddingVertical: 30 },
  loadingText: { fontSize: 13, color: '#6b7280', marginTop: 10 },
  footer: {
    fontSize: 11,
    color: '#9ca3af',
    textAlign: 'center',
    marginTop: 30,
  },
});
