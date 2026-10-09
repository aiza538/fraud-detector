// src/services/fraudAlerts.js
// App ke andar fraud alert history ka local storage (document directory mein JSON file)
import { File, Paths } from "expo-file-system";

const alertsFile = new File(Paths.document, "fraud-alerts.json");
const MAX_ALERTS = 50;

export async function getAlerts() {
  try {
    if (!alertsFile.exists) return [];
    const raw = alertsFile.textSync();
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

export async function saveAlert(alert) {
  try {
    const alerts = await getAlerts();
    alerts.unshift({
      ...alert,
      id: Date.now().toString(),
      time: new Date().toISOString(),
    });
    const trimmed = alerts.slice(0, MAX_ALERTS);
    alertsFile.write(JSON.stringify(trimmed));
    return trimmed;
  } catch {
    return [];
  }
}
