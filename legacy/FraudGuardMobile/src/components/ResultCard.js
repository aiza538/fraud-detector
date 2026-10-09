// src/components/ResultCard.js
import React from 'react';
import { View, Text, StyleSheet } from 'react-native';

export default function ResultCard({ result }) {
  if (!result) return null;

  if (result.error) {
    return (
      <View style={[styles.card, styles.errorBanner]}>
        <Text style={styles.errorTitle}>Analysis Failed</Text>
        <Text style={styles.errorText}>{result.error}</Text>
      </View>
    );
  }

  const tactics = result.tactics || [];
  const stats = [
    { label: 'Attack Type', value: result.type || 'Unknown' },
    { label: 'Legal Reference', value: result.peca || 'N/A' },
    { label: 'Language', value: result.language || 'Unknown' },
  ];

  return (
    <View style={styles.card}>
      <View
        style={[
          styles.banner,
          result.fraud ? styles.bannerDanger : styles.bannerSafe,
        ]}
      >
        <Text
          style={[
            styles.bannerTitle,
            result.fraud ? styles.textDanger : styles.textSafe,
          ]}
        >
          {result.fraud ? '⚠️ Fraud Detected' : '✅ Safe Message'}
        </Text>
        <Text style={styles.bannerSub}>
          Confidence: {result.confidence ?? 0}% • FIA Verified
        </Text>
      </View>

      <View style={styles.statsRow}>
        {stats.map(stat => (
          <View key={stat.label} style={styles.statBox}>
            <Text style={styles.statLabel}>{stat.label}</Text>
            <Text style={styles.statValue}>{stat.value}</Text>
          </View>
        ))}
      </View>

      {tactics.length > 0 && (
        <View style={styles.section}>
          <Text style={styles.sectionLabel}>
            ⚡ Manipulation Tactics Detected
          </Text>
          <View style={styles.tagRow}>
            {tactics.map(tactic => (
              <View key={tactic} style={styles.tag}>
                <Text style={styles.tagText}>{tactic}</Text>
              </View>
            ))}
          </View>
        </View>
      )}

      {result.target && (
        <View style={styles.targetBox}>
          <Text style={styles.targetText}>🎯 Targeted: {result.target}</Text>
        </View>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: '#fff',
    borderRadius: 16,
    padding: 20,
    marginTop: 16,
    shadowColor: '#000',
    shadowOpacity: 0.08,
    shadowRadius: 10,
    shadowOffset: { width: 0, height: 4 },
    elevation: 3,
  },
  errorBanner: {
    borderWidth: 1,
    borderColor: '#fecaca',
    backgroundColor: '#fef2f2',
  },
  errorTitle: { color: '#b91c1c', fontWeight: '700', fontSize: 16 },
  errorText: { color: '#ef4444', fontSize: 13, marginTop: 4 },
  banner: { borderRadius: 12, padding: 14, borderWidth: 1 },
  bannerDanger: { backgroundColor: '#fef2f2', borderColor: '#fecaca' },
  bannerSafe: { backgroundColor: '#f0fdf4', borderColor: '#bbf7d0' },
  bannerTitle: { fontSize: 18, fontWeight: '700' },
  textDanger: { color: '#b91c1c' },
  textSafe: { color: '#15803d' },
  bannerSub: { fontSize: 12, color: '#6b7280', marginTop: 4 },
  statsRow: { flexDirection: 'row', gap: 8, marginTop: 14 },
  statBox: {
    flex: 1,
    backgroundColor: '#f9fafb',
    borderRadius: 10,
    padding: 10,
  },
  statLabel: { fontSize: 9, color: '#9ca3af', textTransform: 'uppercase' },
  statValue: {
    fontSize: 12,
    fontWeight: '600',
    color: '#374151',
    marginTop: 4,
  },
  section: { marginTop: 16 },
  sectionLabel: { fontSize: 12, color: '#9ca3af', marginBottom: 8 },
  tagRow: { flexDirection: 'row', flexWrap: 'wrap', gap: 8 },
  tag: {
    backgroundColor: '#fee2e2',
    borderColor: '#fecaca',
    borderWidth: 1,
    borderRadius: 20,
    paddingHorizontal: 12,
    paddingVertical: 6,
  },
  tagText: { fontSize: 11, color: '#b91c1c' },
  targetBox: {
    marginTop: 14,
    backgroundColor: '#fefce8',
    borderColor: '#fde68a',
    borderWidth: 1,
    borderRadius: 10,
    padding: 10,
  },
  targetText: { fontSize: 12, color: '#a16207' },
});
