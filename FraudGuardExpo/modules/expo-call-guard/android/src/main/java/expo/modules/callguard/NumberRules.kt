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
     * +92 / 0092 hatao, area-code hatao, aur leading zero EK hi hatao taake
     * 0300…, +92300…, 92300…, 051-111-111-425 — sab ek hi number ban jayein.
     *
     * NOTE: leading zero EK hi hatao. `trimStart('0')` poora zero-strip kar
     * deta tha — 0800-55055 (PTA) jaise short UANs tab bhi theek rehte thay
     * kyunke wo ek hi zero se start hote hain, magar "00" se start hone wale
     * number galat normalize hote the.
     *
     * AREA-CODE strip: Pakistani banks helpline "021-111-825-888" (Karachi)
     * aur "051-111-111-425" (Islamabad) ke roop me advertise karte hain.
     * Ye 12-digit number backend ke "111111425" se kabhi match hi nahi hota
     * tha → official bank helpline UNKNOWN → SUSPICIOUS. Yaani bank ka apna
     * number scam alert bana raha tha.
     */
    fun clean(raw: String): String {
        var c = raw.replace(" ", "").replace("-", "")
            .replace("(", "").replace(")", "")
        if (c.startsWith("+92")) c = c.substring(3)
        else if (c.startsWith("0092")) c = c.substring(4)
        // "051111111425" → "111111425". Sirf jab pehle 3 digits area code hon
        // — 10-digit mobile numbers kabhi affected nahi hote.
        if (c.length >= 12) {
            val area = c.substring(0, 3)
            if (area.all { it.isDigit() } && AREA_CODES.contains(area)) c = c.substring(3)
        }
        if (c.startsWith("0")) c = c.drop(1)
        return c
    }

    private val AREA_CODES = setOf(
        "021", "022", "025", "031", "032", "033", "034", "041", "042",
        "045", "048", "049", "051", "052", "053", "054", "055", "061",
        "064", "068", "069", "071", "072", "073", "074", "081", "082",
        "083", "091", "092", "093", "094", "095", "099",
    )

    /**
     * Backend `/check-number` ka offline mirror — wahi 4-level tree:
     *   1. community-reported scam       -> SCAM
     *   2. verified official number      -> SAFE
     *   3. verified UAN ka copy-cat spoof -> SCAM
     *   4. unknown 9-digit 111… UAN      -> SUSPICIOUS
     *   5. baqi sab                     -> UNKNOWN (koi alert nahi)
     *
     * ✅ "UNKNOWN = pata nahi, alert nahi" — ye rule hi poori FP control ki
     * backbone hai. Personal mobiles (300-999), landlines aur short codes
     * Pakistan me POORE Jazz/Zong/Tenor/Ufone + delivery + govt helplines ka
     * range hain; inhe "suspicious" kehlaana user ko har dost, har rider
     * aur har bank par amber alert de raha tha.
     *
     * ✅ Legit list AB KABHI khali nahi hoti:
     *   Pehle sirf backend-synced set use hota tha. `/number-lists` route
     *   backend me missing tha → sync fail → empty prefs → HBL 111-111-425
     *   bhi "list me nahi" → `111` prefix rule → SUSPICIOUS. Ab synced list
     *   ke saath BUNDLED [VerifiedDirectory] ka union use hota hai, is liye
     *   backend down hone par bhi asli helpline SAFE rehti hai.
     */
    fun classify(raw: String, context: Context): Severity {
        val number = clean(raw)
        if (number.isEmpty()) return Severity.UNKNOWN

        val prefs = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
        val syncedLegit = prefs.getStringSet(KEY_LEGIT, emptySet()) ?: emptySet()
        val scam = prefs.getStringSet(KEY_SCAM, emptySet()) ?: emptySet()
        val spoofable = prefs.getStringSet(KEY_SPOOFABLE, emptySet()) ?: emptySet()

        // Union: backend ki fresh list + offline fallback. Kabhi khali nahi.
        val legit: Set<String> =
            if (syncedLegit.isEmpty()) VerifiedDirectory.numbers()
            else syncedLegit + VerifiedDirectory.numbers()

        // 1. Community-reported scam — sab se authoritative.
        if (scam.contains(number)) return Severity.SCAM
        // 2. Verified official — bank/govt/wallet helpline. Lists PEHLE
        //    check hoti hain, length guard se pehle (NADRA "1700", FIA
        //    "1991" jaise short codes bhi official hain).
        if (legit.contains(number)) return Severity.SAFE
        // 3. Chhote random numbers — koi matlab nahi, koi alert nahi.
        if (number.length < 7) return Severity.UNKNOWN
        // 4. Copy-cat / impersonation: verified UAN se 1-2 digit door.
        if (spoofable.contains(number)) return Severity.SCAM
        if (VerifiedDirectory.impersonates(number, legit)) return Severity.SCAM
        // 5. Bank-style UAN shape jo verified list me nahi. Sirf AMBER —
        //    paka scam nahi (koi bhi private company 111-prefix UAN use
        //    kar sakti hai).
        if (number.length == 9 && number.startsWith("111")) return Severity.SUSPICIOUS
        // 6. Personal mobile, landline, short code → UNKNOWN. Koi alert nahi.
        return Severity.UNKNOWN
    }

    /** Sirf wahi numbers jo ALERT deserve karte hain. */
    fun shouldAlert(severity: Severity): Boolean =
        severity == Severity.SCAM || severity == Severity.SUSPICIOUS
}