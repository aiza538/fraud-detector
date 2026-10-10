package expo.modules.callguard

import android.content.Context
import android.content.Intent
import android.net.Uri
import android.provider.Settings
import expo.modules.kotlin.modules.Module
import expo.modules.kotlin.modules.ModuleDefinition

class CallGuardModule : Module() {
    init {
        instance = this
    }

    override fun definition() = ModuleDefinition {
        Name("CallGuard")

        AsyncFunction("setRules") { rules: Map<String, Any?> ->
            val context = appContext.reactContext
            if (context != null) {
                @Suppress("UNCHECKED_CAST")
                NumberRules.save(
                    context,
                    rules["legitimate"] as? List<String> ?: emptyList(),
                    rules["scam"] as? List<String> ?: emptyList(),
                    // Backend `/number-lists` se aata hai: verified UAN ke 1-2
                    // digit door ke numbers. Inhe impersonation samajhna hai
                    // bina network ke.
                    rules["spoofable"] as? List<String> ?: emptyList(),
                )
            }
            Unit
        }

        // Number lists change hone par phonebook cache refresh karo, taake
        // rules sync ke baad saved-contact detection turant theek ho.
        AsyncFunction("refreshContactCache") {
            val context = appContext.reactContext
            if (context != null) ContactLookup.invalidate()
            Unit
        }

        Function("hasContactsPermission") {
            val context = appContext.reactContext ?: return@Function false
            ContactLookup.hasPermission(context)
        }

        /**
         * Manual "Check Number" tab ke liye phonebook lookup.
         * Return: "saved" | "not_saved" | "unknown" — "unknown" ka matlab
         * READ_CONTACTS nahi mili, verified number nahi hai.
         */
        Function("checkContact") { number: String ->
            val context = appContext.reactContext
                ?: return@Function ContactLookup.Result.UNKNOWN.name.lowercase()
            when (ContactLookup.lookupNumber(context, number)) {
                ContactLookup.Result.SAVED -> "saved"
                ContactLookup.Result.NOT_SAVED -> "not_saved"
                ContactLookup.Result.UNKNOWN -> "unknown"
            }
        }

        Function("hasNotificationAccess") {
            val context = appContext.reactContext ?: return@Function false
            isNotificationServiceEnabled(context)
        }

        AsyncFunction("requestNotificationAccess") {
            val context = appContext.reactContext
            if (context != null) {
                val intent = Intent(Settings.ACTION_NOTIFICATION_LISTENER_SETTINGS)
                    .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
                context.startActivity(intent)
            }
            Unit
        }

        Events("onCallDetected", "onMessageDetected")
    }

    private fun isNotificationServiceEnabled(context: Context): Boolean {
        val flat = Settings.Secure.getString(context.contentResolver, "enabled_notification_listeners")
        return flat?.contains(context.packageName) == true ||
            flat?.contains("expo.modules.callguard") == true
    }

    companion object {
        @Volatile
        private var instance: CallGuardModule? = null

        fun emitCallDetected(number: String, status: String, source: String, alerted: Boolean) {
            instance?.sendEvent(
                "onCallDetected",
                mapOf(
                    "number" to number,
                    "status" to status,
                    "source" to source,
                    // false = user ko notification NAHI mili (unknown = pata nahi).
                    // JS is flag se alert history me bhi entry banata hai ya nahi.
                    "alerted" to alerted,
                ),
            )
        }

        fun emitMessageDetected(subject: String, message: String, source: String, level: String) {
            instance?.sendEvent(
                "onMessageDetected",
                mapOf("subject" to subject, "message" to message, "source" to source, "level" to level),
            )
        }
    }
}
