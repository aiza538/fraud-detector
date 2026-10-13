// src/services/fraudAlerts.js
// App ke andar fraud alert history ka local storage (document directory mein JSON file)
import { File, Paths } from "expo-file-system";

const MAX_ALERTS = 50;

// File har call par banti hai, module load par nahi: web par expo-file-system
// ka File bante hi crash karta hai, jis se poori app (web mode) khulti hi nahi thi.
const alertsFile = () => new File(Paths.document, "fraud-alerts.json");

export async function getAlerts() {
  try {
    const file = alertsFile();
    if (!file.exists) return [];
    const parsed = JSON.parse(file.textSync());
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

/** Is phone ki alert history hata do (account delete par). */
export async function clearAlerts() {
  try {
    const file = alertsFile();
    if (file.exists) file.delete();
  } catch {
    /* ignore */
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
    alertsFile().write(JSON.stringify(trimmed));
    return trimmed;
  } catch {
    return [];
  }
}
