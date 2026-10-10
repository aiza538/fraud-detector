package expo.modules.callguard

import android.app.Notification
import android.provider.Telephony
import android.service.notification.NotificationListenerService
import android.service.notification.StatusBarNotification
import android.util.Log

class FraudNotificationListener : NotificationListenerService() {

    companion object {
        // WhatsApp, SMS aur Telegram messages scan karte hain
        private val TARGET_PACKAGES = setOf(
            "com.whatsapp",
            "com.whatsapp.w4b",
            "com.android.mms",
            "org.telegram.messenger",
        )
        private val WHATSAPP_PACKAGES = setOf("com.whatsapp", "com.whatsapp.w4b")

        // WhatsApp INCOMING aur MISSED calls ki notifications: "Incoming voice
        // call" / "Missed voice call". Outgoing "Calling…" match NAHI karti.
        private val INCOMING_CALL_REGEX =
            Regex("(incoming|missed)\\s+(voice|video)\\s+call", RegexOption.IGNORE_CASE)
        private val NUMBER_REGEX = Regex("""\+?\d[\d\s\-()]{6,}""")

        // WhatsApp group notifications ka prefix: "Family (30 messages)"
        private val GROUP_COUNT_REGEX =
            Regex("""\(\d+\s*(messages?|new messages?)\)""", RegexOption.IGNORE_CASE)

        private const val DEDUP_WINDOW_MS = 60_000L
        private var lastAlertKey: String? = null
        private var lastAlertMs = 0L

        private fun shouldDedupe(key: String): Boolean {
            val now = System.currentTimeMillis()
            if (key == lastAlertKey && now - lastAlertMs < DEDUP_WINDOW_MS) return true
            lastAlertKey = key
            lastAlertMs = now
            return false
        }
    }

    override fun onNotificationPosted(sbn: StatusBarNotification?) {
        val n = sbn ?: return
        if (!isTargetPackage(n.packageName)) return

        val extras = n.notification?.extras ?: return
        val title = extras.getCharSequence(Notification.EXTRA_TITLE)?.toString().orEmpty()
        val body = extras.getCharSequence(Notification.EXTRA_TEXT)?.toString().orEmpty()
        val subText = extras.getCharSequence(Notification.EXTRA_SUB_TEXT)?.toString().orEmpty()
        val bigText = extras.getCharSequence(Notification.EXTRA_BIG_TEXT)?.toString().orEmpty()
        if (title.isEmpty() && body.isEmpty()) return

        val isWhatsapp = WHATSAPP_PACKAGES.any { n.packageName.startsWith(it) }
        Log.d("CallGuard", "notif pkg=${n.packageName} title='$title' body='$body'")

        if (isWhatsapp && (INCOMING_CALL_REGEX.containsMatchIn(body) ||
                INCOMING_CALL_REGEX.containsMatchIn(subText))
        ) {
            Log.d("CallGuard", "matched WhatsApp call regex, title='$title'")
            handleIncomingWhatsAppCall(title)
            return
        }

        // Sender ka trust determine karo.
        //
        // PEHLE: `sender.isNotEmpty() && isTrustedSender(sender)` — ek hi
        // condition, aur `isTrustedSender` me SQL `LIKE` substring match tha.
        // Do buri consequences:
        //   1. Saved logon ki NORMAL baat (family emergency, "paise bhej do")
        //      par rule engine fire ho jata tha — anchors ab isay rokta hai.
        //   2. `LIKE` wildcard ki wajah se group title / SMS header kisi bhi
        //      saved contact se "match" ho jata tha → ASLI bank/lottery scam
        //      SMS silently skip ho jati thi.
        // AB: number ho to phonebook me exact number lookup; naam ho to exact
        // (case-insensitive) naam lookup. Groups alag se handle hote hain.
        val parsed = parseSender(title)
        val trusted = isTrustedSender(parsed)

        // Group/preview notifications ka poora text aksar BIG_TEXT mein hota hai
        val scanText = listOf(body, bigText).filter { it.isNotBlank() }.joinToString("\n")
        val verdict = TextRules.classifyMessageWithSeverity(
            title = title,
            body = scanText,
            context = applicationContext,
            trustedSender = trusted,
            // Group me sender ki identity available nahi hoti (title group ka
            // naam hota hai) — is liye link analysis wahan chalti hi nahi.
            // Sirf text-based scam: OTP mangna, prize/lottery, bank impersonation.
            isGroup = parsed.isGroup,
        )
        if (verdict == null) {
            Log.d("CallGuard", "message classified SAFE (no alert): sender='$title'")
            return
        }
        val source = sourceFor(n.packageName)

        val subject = title.ifEmpty { "New message" }
        // Severity TextRules ka apni hai — "scam" par laal, "suspicious" par amber.
        FraudNotifier.show(this, subject, verdict.first, verdict.second)
        CallGuardModule.emitMessageDetected(subject, verdict.first, source, verdict.second)
    }

    private fun handleIncomingWhatsAppCall(title: String) {
        // Title caller ka number ho ya contact ka naam.
        val number = extractNumber(title)
        if (number != null) {
            when (ContactLookup.lookupNumber(applicationContext, number)) {
                ContactLookup.Result.SAVED -> return
                // Contacts available nahi to number par alert nahi — warna har
                // number alert ho jayega. Ye WhatsApp-call ka UNKNOWN case hai.
                ContactLookup.Result.UNKNOWN -> return
                ContactLookup.Result.NOT_SAVED -> Unit
            }
        } else if (ContactLookup.lookupName(applicationContext, title) == ContactLookup.Result.SAVED) {
            // Title me number nahi → saved contact ka naam
            return
        }
        if (shouldDedupe("whatsapp-call:${number ?: title}")) return

        val severity = if (number == null) {
            // Na number, na saved naam — WhatsApp ne contact resolve nahi kiya.
            // Koi rule match nahi hua to koi signal hi nahi.
            return
        } else {
            NumberRules.classify(number, applicationContext)
        }

        if (!NumberRules.shouldAlert(severity)) {
            Log.d("CallGuard", "whatsapp call severity=$severity -> no alert")
            CallGuardModule.emitCallDetected(number, severity.name.lowercase(), "whatsapp", false)
            return
        }

        val label = when (severity) {
            NumberRules.Severity.SCAM ->
                "Community-reported scam number ne WhatsApp se call ki — bank/authority kabhi WhatsApp par call nahi karta."
            else ->
                "Unverified UAN-style number ne WhatsApp se call kiya — banks/authorities WhatsApp par call nahi karti. OTP ya paisa maange to scam hai."
        }
        FraudNotifier.show(this, number, label, severity.name.lowercase())
        CallGuardModule.emitCallDetected(number, severity.name.lowercase(), "whatsapp", true)
    }

    /**
     * Title ka format:
     *   - group:  "Family (30 messages)"   → [Group] "Family" marker
     *   - 1:1:    "Sender" ya "+92 300 1234567"
     *
     * Pehle sirf `title.substringBefore(':')` kiya jata tha. Ab group prefix
     * alag se pehchan karte hain kyunki group ke members unknown hote hain —
     * unke messages bhi anchor-gated rules se guzarte hain.
     */
    private data class Sender(val identity: String, val isGroup: Boolean)

    private fun parseSender(title: String): Sender {
        val isGroup = GROUP_COUNT_REGEX.containsMatchIn(title)
        val identity = title
            .substringBefore(':')
            .replace(GROUP_COUNT_REGEX, "")
            .replace(Regex("""\(\d+\)"""), "")
            .replace("~", "")
            .trim()
        return Sender(identity, isGroup)
    }

    private fun isTrustedSender(parsed: Sender): Boolean {
        if (parsed.identity.isEmpty()) return false
        // WhatsApp/Telegram GROUP kabhi trusted nahi — group aik insaan nahi hai,
        // usme bhi unknown log lottery/OTP scam drop karte hain. Group ka naam
        // phonebook se match ho to bhi scan karo.
        //
        // Group me bhi ASLI scam pakdi jati hai — magar sirf text-based signals
        // (OTP mangna, prize/lottery, bank impersonation), link nahi. Text rules
        // anchors-gated hain, is liye FP bojh kam hai, aur sender ki identity
        // na hone ki wajah se link par faisla lagana galat hota ( asli course/job
        // ads roz aati hain). Link check `classifyMessageWithSeverity(isGroup=true)`
        // se skip hoti hai.
        if (parsed.isGroup) return false
        if (NUMBER_REGEX.containsMatchIn(parsed.identity)) {
            val number = extractNumber(parsed.identity) ?: return false
            return ContactLookup.isSavedContact(applicationContext, number)
        }
        return ContactLookup.hasContactNamed(applicationContext, parsed.identity)
    }

    private fun isTargetPackage(pkg: String): Boolean {
        if (TARGET_PACKAGES.contains(pkg)) return true
        // vivo/Samsung ka messaging app com.android.mms na bhi ho sakta hai
        return try {
            Telephony.Sms.getDefaultSmsPackage(applicationContext) == pkg
        } catch (_: Exception) {
            false
        }
    }

    private fun extractNumber(identity: String): String? {
        val match = NUMBER_REGEX.find(identity) ?: return null
        val cleaned = NumberRules.clean(match.value)
        return if (cleaned.length >= 7) cleaned else null
    }

    private fun sourceFor(pkg: String): String = when {
        pkg.startsWith("com.whatsapp") -> "whatsapp"
        pkg == "org.telegram.messenger" -> "telegram"
        else -> "sms"
    }

    override fun onNotificationRemoved(sbn: StatusBarNotification?) {}
}