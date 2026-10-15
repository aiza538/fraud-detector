// src/services/backgroundSync.js
// App khole baghair bhi naye confirmed scam numbers aur scanner rules phone
// tak pohanchein. Android ka WorkManager is task ko taqreeban har 12 ghante
// chalata hai (battery ke hisaab se thora aage peeche).
import { Platform } from "react-native";
import * as BackgroundTask from "expo-background-task";
import * as TaskManager from "expo-task-manager";
import { syncRules } from "./callMonitor";

const TASK = "fraudguard-sync";

// Task ki definition module ke top level par honi zaroori hai: Android app ko
// band halat me background me jagata hai, aur tab bhi ye file load hoti hai
// (app/_layout.tsx ise import karta hai).
TaskManager.defineTask(TASK, async () => {
  try {
    await syncRules();
    return BackgroundTask.BackgroundTaskResult.Success;
  } catch {
    return BackgroundTask.BackgroundTaskResult.Failed;
  }
});

export async function registerBackgroundSync() {
  if (Platform.OS !== "android") return;
  try {
    if ((await BackgroundTask.getStatusAsync()) !== BackgroundTask.BackgroundTaskStatus.Available) return;
    if (await TaskManager.isTaskRegisteredAsync(TASK)) return;
    await BackgroundTask.registerTaskAsync(TASK, { minimumInterval: 12 * 60 }); // minutes
  } catch {
    // Expo Go me ye native module nahi hota — app baqi sab kuch karti rehti hai.
  }
}
