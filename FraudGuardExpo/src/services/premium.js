// src/services/premium.js
// Premium plan — Google Play subscription, RevenueCat SDK ke zariye.
//
// Phone sirf khareedari karta hai. Premium hai ya nahi, ye faisla SERVER
// karta hai (wo khud RevenueCat se poochta hai) — is liye har khareedari /
// restore ke baad `refreshPremium()` server ko batata hai ke dobara check kare.
import { Platform } from "react-native";
import Purchases from "react-native-purchases";
import { getAccount, refreshPremium } from "./api";

const ANDROID_KEY = process.env.EXPO_PUBLIC_REVENUECAT_ANDROID_KEY;
// RevenueCat dashboard me entitlement ka identifier (server ke
// REVENUECAT_ENTITLEMENT ke barabar).
const ENTITLEMENT = "premium";

export const MANAGE_URL =
  "https://play.google.com/store/account/subscriptions?package=com.fraudguard.ai";

let configuredFor = null;

/** Store se khareedari mumkin hai? (Android + key set; web/iOS par abhi nahi.) */
export function storeAvailable() {
  return Platform.OS === "android" && !!ANDROID_KEY;
}

/** RevenueCat ko is install ke account id ke saath tayyar karo. Account id
 *  hi RevenueCat ka "app user id" hai — server isi id se entitlement poochta hai. */
async function ensureConfigured(accountId) {
  if (!storeAvailable()) return false;
  if (configuredFor === null) {
    Purchases.configure({ apiKey: ANDROID_KEY, appUserID: accountId });
    configuredFor = accountId;
  } else if (configuredFor !== accountId) {
    // Account badla (delete ke baad naya, ya email se purana wapas aaya).
    await Purchases.logIn(accountId);
    configuredFor = accountId;
  }
  return true;
}

function hasEntitlement(customerInfo) {
  return !!customerInfo?.entitlements?.active?.[ENTITLEMENT];
}

/**
 * App khulne par: agar Google Play ke hisaab se premium hai magar server ko
 * abhi pata nahi (jaise khareedne ke baad internet chala gaya), server ko
 * dobara check karwao. Kabhi error nahi phenkta — ye background kaam hai.
 */
export async function syncPremium() {
  try {
    const account = await getAccount();
    if (!(await ensureConfigured(account.id))) return account;
    const info = await Purchases.getCustomerInfo();
    if (hasEntitlement(info) !== account.premium) {
      return await refreshPremium();
    }
    return account;
  } catch (err) {
    if (__DEV__) console.log("[premium] sync skipped:", err?.message);
    return null;
  }
}

/** Paywall ke packages (monthly / yearly), Google Play ki local price ke saath. */
export async function loadPackages(accountId) {
  if (!(await ensureConfigured(accountId))) return [];
  const offerings = await Purchases.getOfferings();
  return offerings.current?.availablePackages ?? [];
}

/**
 * Khareedo, phir server se confirm karwao. Wapas: naya account
 * (`premium` true/false), ya null agar user ne khud cancel kiya.
 */
export async function buy(pkg) {
  try {
    await Purchases.purchasePackage(pkg);
  } catch (err) {
    if (err?.userCancelled) return null;
    throw err;
  }
  return refreshPremium();
}

/** Naye phone / reinstall par purani subscription wapas lao. */
export async function restore(accountId) {
  if (!(await ensureConfigured(accountId))) return null;
  await Purchases.restorePurchases();
  return refreshPremium();
}
