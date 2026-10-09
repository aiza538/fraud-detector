package expo.modules.callguard

import android.content.Context

object NumberRules {

    /**
     * Chaar level ka faisla. "UNKNOWN" ka matlab hai "pata nahi" — scam ya
     * suspicious NAHI. Receiver is par ALERT NAHI banata, sirf history me log
     * karta hai.
     *
     * Pehle sirf String return hota tha aur CallStateReceiver ka
     * `classified ?: "suspicious"` har unknown number ko "suspicious" bana
     * deta tha — yaani poori duniya ka har personal number alert kar raha tha.
     */
    enum class Severity { SCAM, SAFE, SUSPICIOUS, UNKNOWN }

    private const val PREFS = "call_guard_rules"
    private const val KEY_LEGIT = "legitimate"
    private const val KEY_SCAM = "scam"
    private const val KEY_SPOOFABLE = "spoofable"

    fun save(context: Context, legitimate: List<String>, scam: List<String>, spoofable: List<String> = emptyList()) {
        context.getSharedPreferences(PREFS, Context.MODE_PRIVATE).edit()
            .putStringSet(KEY_LEGIT, legitimate.toSet())
            .putStringSet(KEY_SCAM, scam.toSet())
            .putStringSet(KEY_SPOOFABLE, spoofable.toSet())
            .apply()
    }

    /**
     * +92 / 0092 hatao aur leading zeros nipta do taake 0300…, +92300…, 92300…
     * sab ek hi number ban jayein.
     *
     * NOTE: leading zero EK hi hatao. `trimStart('0')` poora zero-strip kar
     * deta tha — 0800-55055 (PTA) jaise short UANs tab bhi theek rehte the
     * kyunke wo ek hi zero se start hote hain, magar "00" se start hone wale
     * number galat normalize hote the.
     */
    fun clean(raw: String): String {
        var c = raw.replace(" ", "").replace("-", "")
            .replace("(", "").replace(")", "")
        if (c.startsWith("+92")) c = c.substring(3)
        else if (c.startsWith("0092")) c = c.substring(4)
        if (c.startsWith("0")) c = c.substring(1)
        return c
    }

    /**
     * Backend /check-number ka offline mirror — wahi 4-level tree, wahi order:
     *   1. community-reported scam  -> SCAM
     *   2. verified official number -> SAFE
     *   3. saved contact           -> SAFE (receiver pehle check karta hai)
     *   4. verified UAN ka spoof    -> SCAM
     *   5. unknown 111… UAN         -> SUSPICIOUS
     *   6. baqi sab                -> UNKNOWN (koi alert nahi)
     *
     * Personal mobiles (300-999) jaan bujh kar UNKNOWN hain: Pakistan me ye
     * POORE Jazz/Zong/Tenor/Ufone ka range hai, inhe "suspicious" kehlaana
     * har dost aur har delivery rider ko alert karta tha.
     */
    fun classify(raw: String, context: Context): Severity {
        val number = clean(raw)
        if (number.isEmpty()) return Severity.UNKNOWN

        val prefs = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
        val legit = prefs.getStringSet(KEY_LEGIT, emptySet()) ?: emptySet()
        val scam = prefs.getStringSet(KEY_SCAM, emptySet()) ?: emptySet()
        val spoofable = prefs.getStringSet(KEY_SPOOFABLE, emptySet()) ?: emptySet()

        // Lists ko PEHLE check karo, length guard se pehle — NADRA "1700",
        // FIA "1717" jaise 4-digit verified short codes bhi official hain.
        if (scam.contains(number)) return Severity.SCAM
        if (legit.contains(number)) return Severity.SAFE
        // Baqi ke liye 7-digit minimum: chhote random numbers ka koi matlab nahi.
        if (number.length < 7) return Severity.UNKNOWN
        // Backend `/number-lists` se sync hua: verified UAN se 1-2 digit door ke
        // numbers. Ye impersonation ke ASLI patterns hain.
        if (spoofable.contains(number)) return Severity.SCAM
        if (number.length == 9 && number.startsWith("111")) return Severity.SUSPICIOUS
        return Severity.UNKNOWN
    }

    /** Sirf wahi numbers jo ALERT deserve karte hain. */
    fun shouldAlert(severity: Severity): Boolean =
        severity == Severity.SCAM || severity == Severity.SUSPICIOUS
}