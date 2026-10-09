package expo.modules.callguard

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.telephony.TelephonyManager
import android.util.Log

class CallStateReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent) {
        if (intent.action != TelephonyManager.ACTION_PHONE_STATE_CHANGED) return
        val state = intent.getStringExtra(TelephonyManager.EXTRA_STATE)
        Log.d("CallGuard", "PHONE_STATE: $state")
        if (state != TelephonyManager.EXTRA_STATE_RINGING) return

        val number = intent.getStringExtra(TelephonyManager.EXTRA_INCOMING_NUMBER)
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

        val subject = if (number.isNullOrEmpty()) "Hidden/Unknown number" else number
        val label = when (severity) {
            NumberRules.Severity.SCAM ->
                "Impersonation / community-reported scam number — ye number bank ya sarkari idare ka NAHI hai"
            NumberRules.Severity.SUSPICIOUS ->
                if (number.isNullOrEmpty())
                    "Hidden caller-ID se call — banks/authorities kabhi caller ID chhupa kar call nahi karte. OTP/info share se pehle verify karein."
                else
                    "Unverified UAN-style number — scammers official-looking bank numbers spoof karte hain"
            else -> "Unknown incoming number"
        }
        Log.d("CallGuard", "classify -> $severity")
        FraudNotifier.show(context, subject, label, severity.name.lowercase())
        CallGuardModule.emitCallDetected(subject, severity.name.lowercase(), "phone", true)
    }
}