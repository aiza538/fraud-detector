package expo.modules.callguard

import android.content.Context
import android.util.Log

/**
 * Aane wali phone call ka faisla aur alert. FraudCallScreeningService se chalta
 * hai (Android 10+). Pehle ye CallStateReceiver me tha, jo PHONE_STATE
 * broadcast + READ_CALL_LOG permission par chalta tha — Google Play is
 * permission par sabse sakht hai, aur Call Screening ko iski zarurat nahi.
 */
object CallAlert {
    fun handleIncoming(context: Context, number: String?) {
        Log.d("CallGuard", "incoming number raw=$number")

        // --- Saved contact: koi alert nahi ---------------------------------
        // Pehle `isSavedContact` Boolean tha aur READ_CONTACTS deny hone par
        // `false` return karta tha — yaani har SAVED contact bhi alert ho jata
        // tha. Ab teeno states alag hain aur cache load hota hai.
        if (!number.isNullOrEmpty()) {
            when (ContactLookup.lookupNumber(context, number)) {
                ContactLookup.Result.SAVED -> {
                    Log.d("CallGuard", "saved contact -> no alert")
                    return
                }
                // Permission nahi mili to number-level alert NAHI karenge —
                // warna har number "unknown" samajh ke alert hota. Text wale
                // rules permission se baal hain, wo chalti rahengi.
                ContactLookup.Result.UNKNOWN -> {
                    Log.d("CallGuard", "contacts unavailable -> skipping number alerts")
                    return
                }
                ContactLookup.Result.NOT_SAVED -> Unit
            }
        }

        val severity = if (number.isNullOrEmpty()) {
            // Hidden caller-ID: koi number hi nahi mila. Yeh genuine red flag
            // hai (banks caller ID chhupa kar call nahi karti) is liye UNKNOWN
            // par bhi ek alert — magar SIRF tab jab number khali hai.
            NumberRules.Severity.SUSPICIOUS
        } else {
            NumberRules.classify(number, context)
        }

        // Sirf scam/suspicious par alert. UNKNOWN = "pata nahi" — har personal
        // number UNKNOWN hai aur us par alert = pichla behaviour (noise).
        if (!NumberRules.shouldAlert(severity)) {
            Log.d("CallGuard", "severity=$severity -> no alert (unknown)")
            CallGuardModule.emitCallDetected(number.orEmpty(), severity.name.lowercase(), "phone", false)
            return
        }

        val subject = if (number.isNullOrEmpty()) "Hidden number" else number
        val label = when (severity) {
            NumberRules.Severity.SCAM ->
                "Impersonation or community-reported scam number. This is NOT a bank or government number."
            NumberRules.Severity.SUSPICIOUS ->
                if (number.isNullOrEmpty())
                    "Call from a hidden number. Banks and authorities never hide their caller ID. Verify before sharing an OTP or any details."
                else
                    "Unverified UAN-style number. Scammers fake official-looking bank numbers."
            else -> "Unknown incoming number"
        }
        Log.d("CallGuard", "classify -> $severity")
        FraudNotifier.show(context, subject, label, severity.name.lowercase())
        CallGuardModule.emitCallDetected(subject, severity.name.lowercase(), "phone", true)
    }
}
