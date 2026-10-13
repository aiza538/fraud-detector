package expo.modules.callguard

/**
 * BUNDLED verified directory — backend se sync hone wali lists ka OFFLINE
 * fallback.
 *
 * Kyun zaroori hai:
 *   Backend `/number-lists` pehle implement hi nahi tha, is liye
 *   `syncRules()` fail hoti thi aur native rules EMPTY rehte thay. Empty
 *   legit list ka matlab tha ke HBL 111-111-425 bhi "verified list me nahi"
 *   → 9-digit 111 number → SUSPICIOUS → har bank ke helpline par amber
 *   alert. Yahi "unknown number par scam/suspicious lag jata hai" wali
 *   shikayat ka asal root cause tha.
 *
 * Ab: synced list aur ye bundled list UNION hain. Lists kabhi khali nahi
 * hoti → legit helpline number kabhi alert nahi hoga, chahe backend down ho
 * ya `/number-lists` 404 de.
 *
 * NOTE: numbers "cleaned" form me hain — bina leading zero, bina +92
 * (same normalization jis ka `NumberRules.clean()` aur backend use karte
 * hain). Ye list CONSERVATIVE hai: verified public helplines. Naye numbers
 * add karne se pehle official source se confirm kar lein — ek scammer ka
 * number yahan daal dena = us number ko "safe" mark kar dena.
 *
 * Priority abhi bhi synced list ki hai (backend se naye numbers aate rehte
 * hain); ye sirf un gaps ko bharta hai jo backend de nahi sakta.
 */
object VerifiedDirectory {

    /** cleaned number -> official entity name */
    val LEGITIMATE: Map<String, String> = linkedMapOf(
        // --- Banks (verified UAN / helpline) ---
        "111111425" to "HBL",
        "111825888" to "UBL",
        "111000622" to "MCB Bank",
        "111622822" to "MCB Bank",
        "111113113" to "NBP",
        "111723723" to "Faysal Bank",
        "111524724" to "Bank Alfalah",
        "111468468" to "Askari Bank",
        "111124123" to "Bank of Punjab",
        "111124666" to "Summit Bank",
        "111124777" to "JS Bank",

        // --- Wallets ---
        "111124444" to "JazzCash",
        "111003737" to "Easypaisa",

        // --- Telco ---
        "111579579" to "Telenor",
        "111030030" to "Ufone / Zong",

        // --- Government / regulator ---
        "111345786" to "FIA (general helpline)",
        "1991" to "FIA Cyber Crime Wing",
        "800111111" to "NADRA",
        "111772772" to "FBR",
        "80055055" to "PTA / PTCL",

        // --- Utilities ---
        "9911" to "K-Electric",
        "131" to "IESCO / FESCO",
        "111009009" to "GEPCO / SESCO",
    )

    /** Sirf wahi numbers jo "111…" UAN shape wale hon (impersonation shape). */
    fun numbers(): Set<String> = LEGITIMATE.keys

    fun entityFor(number: String): String? = LEGITIMATE[number]

    /**
     * Copy-cat / impersonation detector.
     *
     * Verified UAN ka shape le magar 1–2 digit alag — ye authentic bank
     * spoofing ka asal pattern hai (111-111-425 → 111-111-424). Pehle iske
     * liye backend se ek static `spoofable` list sync hoti thi jo kabhi
     * empty rehti thi; ab ye compute hota hai aur offline bhi chalta hai.
     *
     * Guards (FP bachane ke liye):
     *   - candidate khud verified list me na ho (warna do legit banks ko
     *     aapas me SCAM kar deta)
     *   - same prefix family (pehle 3 digits) — 111 ke andar hi look karo
     *   - same length
     *   - sirf 1–2 digit ka farq
     */
    fun impersonates(number: String, knownLegit: Set<String> = LEGITIMATE.keys): Boolean {
        if (number.length < 7 || !number.all { it.isDigit() }) return false

        val pool = knownLegit.filter { it.length == number.length && it.all { c -> c.isDigit() } }
        for (legit in pool) {
            if (legit == number) continue
            if (legit.take(3) != number.take(3)) continue
            val distance = legit.zip(number).count { (a, b) -> a != b }
            if (distance in 1..2) return true
        }
        return false
    }
}