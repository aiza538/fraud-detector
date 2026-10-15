// src/services/storage.js
// Chhoti values phone ki secure storage (Android Keystore) me. expo-secure-store
// web par nahi chalta — wahan (sirf development) localStorage.
import { Platform } from "react-native";
import * as SecureStore from "expo-secure-store";

export const storage =
  Platform.OS === "web"
    ? {
        get: async (key) => globalThis.localStorage?.getItem(key) ?? null,
        set: async (key, value) => globalThis.localStorage?.setItem(key, value),
        remove: async (key) => globalThis.localStorage?.removeItem(key),
      }
    : {
        get: (key) => SecureStore.getItemAsync(key),
        set: (key, value) => SecureStore.setItemAsync(key, value),
        remove: (key) => SecureStore.deleteItemAsync(key),
      };
