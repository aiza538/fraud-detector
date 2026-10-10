// src/components/EducationPanel.js
import React from 'react';
import { View, Text, StyleSheet } from 'react-native';

export default function EducationPanel({ items }) {
  if (!items || items.length === 0) return null;

  return (
    <View style={styles.card}>
      <Text style={styles.title}>
        💡 How this scam works — protect yourself
      </Text>
      {items.map((item, i) => (
        <View key={i} style={styles.row}>
          <Text style={styles.bullet}>✓</Text>
          <Text style={styles.itemText}>{item}</Text>
        </View>
      ))}
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: '#fff',
    borderRadius: 16,
    padding: 20,
    marginTop: 16,
    borderWidth: 1,
    borderColor: '#dbeafe',
  },
  title: {
    fontWeight: '700',
    fontSize: 13,
    marginBottom: 10,
    color: '#374151',
  },
  row: { flexDirection: 'row', gap: 6, marginBottom: 6 },
  bullet: { color: '#3b82f6', marginTop: 1 },
  itemText: { fontSize: 13, color: '#6b7280', flex: 1 },
});
