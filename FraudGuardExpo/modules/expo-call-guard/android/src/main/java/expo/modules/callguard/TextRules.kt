package expo.modules.callguard

import android.content.Context
import android.util.Log
import org.json.JSONArray
import org.json.JSONObject

object TextRules {
    private data class Rule(
        val keywords: List<String>,
        /** Rule tab fire hoga jab kam-se-kam itne *distinct* keywords milein. */
        val minMatch: Int,
        /**
         * Wo lafz jinme se kam-se-kam EK ka zaroor hona chahie. Yahi backend ka
         * `anchors` field hai (backend/pattern_matcher.py) aur yahi poori false
         * positive control ka core hai.
         *
         * Pehle ye mirror anchors ke baghair likha gaya tha, jis se sirf
         * `beta` + `emergency` + `hospital` jaise aam lafz bhi "family emergency
         * scam" bana dete thay. Ab generic lafz sirf count hote hain — faisla
         * tab hota hai jab koi ASLI scam signal (OTP maangna, bank ka naam,
         * prize/lottery, voice clone) bhi maujood ho.
         */
        val anchors: List<String>,
        val label: String,
    )

    // --- Rules ka data ----------------------------------------------------------
    //
    // Saare keywords, anchors aur word lists `phone_rules.json` me hain — wahi
    // file jo server `/v1/rules` par deta hai (backend/data/phone_rules.json).
    // App ke andar us ki ek copy (assets/phone_rules.json) hamesha hoti hai;
    // server se nayi version aaye to wo SharedPreferences me save hoti hai aur
    // usi ko istemal kiya jata hai. Is tarah rules naye app release ke baghair
    // update ho jate hain, aur internet na ho to bhi purani copy chalti hai.

    private class RuleSet(
        val rules: List<Rule>,
        val abuseTlds: List<String>,
        val officialSuffixes: List<String>,
        val officialHosts: List<String>,
        val genericTrusted: List<String>,
        val brandTokens: List<String>,
        val otpDeliveryHints: List<String>,
        val otpNegationHints: List<String>,
        val otpWords: List<String>,
        val giveSend: List<String>,
        val giveDemand: List<String>,
        val weakAction: List<String>,
        val urgency: List<String>,
    )

    /** Is version ki app sirf isi schema ki file samajhti hai. */
    private const val SCHEMA = 1
    private const val ASSET = "phone_rules.json"
    private const val PREFS = "call_guard_rules"
    private const val KEY_JSON = "text_rules_json"
    private const val KEY_VERSION = "text_rules_version"

    @Volatile
    private var current: RuleSet? = null

    private val data: RuleSet
        get() = current ?: error("TextRules.ensureLoaded() pehle call karein")

    fun ensureLoaded(context: Context) {
        if (current == null) reload(context)
    }

    @Synchronized
    private fun reload(context: Context) {
        val synced = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
            .getString(KEY_JSON, null)
        current = synced?.let { parse(it) }
            ?: parse(context.assets.open(ASSET).bufferedReader(Charsets.UTF_8).use { it.readText() })
            ?: error("Bundled $ASSET parse nahi hui")
    }

    /**
     * Server se aayi rules file save karo. Ghalat/adhoori file (ya naya schema
     * jo ye app nahi samajhti) kabhi save nahi hoti — purane rules chalte rehte hain.
     * Return: true agar nayi rules lag gayin.
     */
    @Synchronized
    fun saveDownloaded(context: Context, json: String): Boolean {
        val parsed = parse(json) ?: return false
        val version = try { JSONObject(json).optString("version") } catch (e: Exception) { "" }
        context.getSharedPreferences(PREFS, Context.MODE_PRIVATE).edit()
            .putString(KEY_JSON, json)
            .putString(KEY_VERSION, version)
            .apply()
        current = parsed
        return true
    }

    /** Phone par lagi hui downloaded rules ka version (server se "kuch naya?" poochne ke liye). */
    fun downloadedVersion(context: Context): String? =
        context.getSharedPreferences(PREFS, Context.MODE_PRIVATE).getString(KEY_VERSION, null)

    private fun strings(array: JSONArray): List<String> =
        (0 until array.length()).map { array.getString(it) }

    private fun parse(json: String): RuleSet? = try {
        val root = JSONObject(json)
        if (root.optInt("schema") != SCHEMA) {
            null
        } else {
            val otp = root.getJSONObject("otp")
            val links = root.getJSONObject("links")
            val rulesJson = root.getJSONArray("rules")
            val rules = (0 until rulesJson.length()).map { i ->
                val r = rulesJson.getJSONObject(i)
                Rule(
                    strings(r.getJSONArray("keywords")),
                    r.getInt("min_match"),
                    strings(r.getJSONArray("anchors")),
                    r.getString("label"),
                )
            }
            // Khali rules = scanner chup. Aisi file ko rules nahi maana jata.
            if (rules.isEmpty()) null else RuleSet(
                rules = rules,
                abuseTlds = strings(links.getJSONArray("abuse_tlds")),
                officialSuffixes = strings(links.getJSONArray("official_suffixes")),
                officialHosts = strings(links.getJSONArray("official_hosts")),
                genericTrusted = strings(links.getJSONArray("generic_trusted")),
                brandTokens = strings(links.getJSONArray("brand_tokens")),
                otpDeliveryHints = strings(otp.getJSONArray("delivery_hints")),
                otpNegationHints = strings(otp.getJSONArray("negation_hints")),
                otpWords = strings(otp.getJSONArray("words")),
                giveSend = strings(otp.getJSONArray("give_send")),
                giveDemand = strings(otp.getJSONArray("give_demand")),
                weakAction = strings(otp.getJSONArray("weak_action")),
                urgency = strings(otp.getJSONArray("urgency")),
            )
        }
    } catch (e: Exception) {
        Log.w("CallGuard", "phone rules parse failed: ${e.message}")
        null
    }

    private val RULES: List<Rule> get() = data.rules

    // --- Link analysis -------------------------------------------------------
    //
    // Pehle har unknown domain par "malicious link, mobile khatray me hai" chal
    // padata tha: host mein 3 dots (www.jobs.gov.pk!) ya path mein "prize"/"verify"
    // jaisa lafz hone se hi flag ho jata tha. Ab sirf positive spoofing signals:
    // abuse-free TLD, direct IP, ya bank/wallet ka naam copy-cat domain par.

    private val URL_REGEX = Regex("""https?://[^\s<>"']+|www\.[^\s<>"']+""", RegexOption.IGNORE_CASE)

    // Free/bulk-registration TLDs — Pakistani fraud campaigns yahi use karti hain.
    //
    // NOTE: `.work`, `.loan`, `.cam`, `.rest`, `.monster` is list se nikal diye
    // gaye — ye aaj kal bohat se ASLI companies (recruiters, training institutes,
    // fintech) use karti hain, aur in par scam ka koi khaas signal nahi hai.
    // Sirf TLD dekh ke flag lagana = har nayi company ko scam kehna. Ab in
    // host par tabhi alert hai jab brand-token copy-cat ya credentials@host
    // jaisa POSITIVE impersonation signal bhi ho (niche `hasBrandToken`).
    private val ABUSE_TLDS: List<String> get() = data.abuseTlds

    // Sarkari/talebmi domains kabhi "unknown" shak ke qabil nahi
    private val OFFICIAL_SUFFIXES: List<String> get() = data.officialSuffixes

    // Bank/wallet/authority ki ASLI domains
    private val OFFICIAL_HOSTS: List<String> get() = data.officialHosts

    // Aapke/hamare apne saved numbers — inke links legitimate hain (bank statement,
    // Daraz order, govt portal). Link analysis in skip kar deta hai.
    private val USER_TRUSTED_HOSTS = mutableSetOf<String>()

    fun setUserTrustedHosts(hosts: Collection<String>) {
        USER_TRUSTED_HOSTS.clear()
        USER_TRUSTED_HOSTS.addAll(hosts)
    }

    fun addUserTrustedHost(host: String) {
        val h = host.trim().lowercase().removePrefix("www.")
        if (h.isNotEmpty() && "." in h) USER_TRUSTED_HOSTS.add(h)
    }

    // In lafzon ka host mein hona, official domain na hone par = impersonation
    private val BRAND_TOKENS: List<String> get() = data.brandTokens

    private val GENERIC_TRUSTED: List<String> get() = data.genericTrusted

    private val IP_HOST = Regex("""^\d{1,3}(\.\d{1,3}){3}$""")

    private fun authorityOf(url: String): String =
        url.substringAfter("://", url).substringBefore('/')

    private fun hostOf(url: String): String =
        authorityOf(url)
            .substringBefore('@')       // credentials@host — spoofing trick
            .substringBefore(':')
            .trimStart('.')

    private fun endsWithAny(host: String, domains: List<String>): Boolean =
        domains.any { host == it || host.endsWith(".$it") }

    private fun endsWithAny(host: String, domains: Set<String>): Boolean =
        domains.any { host == it || host.endsWith(".$it") }

    // Host ka koi label brand token se match ho (albada lafz ke tor par):
    // "verify-hbl.top" haan, "hbline.com" nahi
    private fun hasBrandToken(host: String): Boolean = BRAND_TOKENS.any { token ->
        Regex("(^|[^a-z])${Regex.escape(token)}([^a-z]|$)").containsMatchIn(host)
    }

    // Return: label jab link par positive fraud signal ho, warna null
    fun matchSuspiciousLink(text: String): String? {
        for (raw in URL_REGEX.findAll(text)) {
            val url = raw.value.lowercase().trimEnd('.', ',', ')', ']', '>')
            val host = hostOf(url)
            if (host.isEmpty()) continue
            if (endsWithAny(host, OFFICIAL_HOSTS) || endsWithAny(host, GENERIC_TRUSTED)) continue
            if (endsWithAny(host, USER_TRUSTED_HOSTS)) continue
            if (OFFICIAL_SUFFIXES.any { host.endsWith(it) }) continue

            val reason = when {
                IP_HOST.matches(host) -> "the link opens a raw IP address"
                authorityOf(url).contains("@") -> "the link hides its real address (credentials@domain)"
                ABUSE_TLDS.any { host.endsWith(it) } -> "the site uses a domain ending that scammers often abuse ($host)"
                hasBrandToken(host) -> "the site uses a bank or government name but is not their official website ($host)"
                else -> continue
            }
            return "Suspicious link — $reason. Confirm with the official helpline before you open it."
        }
        return null
    }

    // --- Bank ki APNI automated SMS vs scammer ka OTP request ----------------
    //
    // Scam OTP *maangta* hai; bank OTP *deta* hai aur "do not share" likhta hai.
    // Ye distinction na hone se har official OTP/alert SMS "credential harvesting"
    // kehla raha tha.
    private val OTP_DELIVERY_HINTS: List<String> get() = data.otpDeliveryHints

    private fun looksLikeOtpDelivery(text: String): Boolean =
        Regex("""\b\d{4,8}\b""").containsMatchIn(text) &&
            OTP_DELIVERY_HINTS.any { text.contains(it) }

    // Roman Urdu spelling variants: "bhij dy" aur "bhej dein" ek hi request hain,
    // magar plain contains() mein ye match nahi hote — isi se OTP scams miss hote thay.
    private val OTP_WORDS: List<String> get() = data.otpWords
    private val GIVE_WORDS_SEND: List<String> get() = data.giveSend

    // Tier A me OTP + "bhej do" / "share karein" / "code bata" / "maangein".
    private val GIVE_WORDS_DEMAND: List<String> get() = data.giveDemand

    // Tier B — kamzor signal. Ye AKELA scam nahi: bank ki apni notification bhi
    // "OTP verify karein" likhti hai. Inhe sirf tab amber dena hai jab link ya
    // urgency bhi ho. Pehle ye sab GIVE_WORDS me thay, jis se har official
    // OTP notification "OTP harvesting" kehlaati thi.
    private val WEAK_ACTION_WORDS: List<String> get() = data.weakAction
    private val URGENCY_WORDS: List<String> get() = data.urgency

    // Chhoti tokens (de/dy/do/di) ko word-boundary se match karo, warna "department"
    // jaisi words mein false positive milega
    private fun hasAnyWord(text: String, words: List<String>): Boolean {
        for (word in words) {
            val hit = if (word.length <= 3) {
                Regex("(^|[^a-z])${Regex.escape(word)}([^a-z]|$)").containsMatchIn(text)
            } else {
                text.contains(word)
            }
            if (hit) return true
        }
        return false
    }

    // Keyword match word-boundary aware. `contains()` se "claim" → "disclaimer",
    // "won" → "wonderful", "mubarak" → har Eid greeting par match hota tha.
    private fun containsKeyword(haystack: String, keyword: String): Boolean {
        val kw = keyword.trim()
        if (kw.isEmpty()) return false
        // Lafz jisme space/slash hai (jaise "account detail", "24 hour") — unpar
        // plain contains theek hai, koi prefix/suffix collision nahi hota.
        if (kw.any { it.isWhitespace() || it == '/' }) return haystack.contains(kw)
        if (kw.first().isDigit()) return haystack.contains(kw)
        return Regex("(^|[^a-z0-9])${Regex.escape(kw)}([^a-z0-9]|$)").containsMatchIn(haystack)
    }

    fun match(text: String): String? {
        val lower = text.lowercase()
        for (rule in RULES) {
            val matched = rule.keywords.filter { containsKeyword(lower, it) }.toSet()
            if (matched.size < rule.minMatch) continue
            // Anchor gate: kam-se-kam ek anchor bhi matched set me hona chahie.
            if (rule.anchors.none { it in matched }) continue
            return rule.label
        }
        return null
    }

    /**
     * Message OTP ke baare me "mat karo" warn kar raha hai — to ye scam nahi.
     * Bina iske "security ke liye OTP ka maangna nahi chahiye" jaisi NORMAL
     * message bhi "OTP harvesting" alert bana deti thi.
     */
    private val OTP_NEGATION_HINTS: List<String> get() = data.otpNegationHints

    private fun mentionsDoNotShare(text: String): Boolean =
        looksLikeOtpDelivery(text) || OTP_NEGATION_HINTS.any { text.contains(it) }

    /**
     * Unknown number se OTP maangna — sabse common attack. Do tier:
     *   Tier A: OTP + "bhej"/"share"/"maangein"          -> SCAM
     *   Tier B: OTP + "enter/verify" + link ya urgency  -> SUSPICIOUS
     */
    fun matchOtpHarvest(text: String): String? {
        val l = text.lowercase()
        if (mentionsDoNotShare(l)) return null
        if (!hasAnyWord(l, OTP_WORDS)) return null

        if (hasAnyWord(l, GIVE_WORDS_SEND) || hasAnyWord(l, GIVE_WORDS_DEMAND)) {
            return "OTP theft attempt — an unknown sender is asking for your OTP or code. Never share an OTP; banks and authorities never ask for it."
        }

        if (hasAnyWord(l, WEAK_ACTION_WORDS)) {
            val hasLink = URL_REGEX.containsMatchIn(l)
            val urgent = hasAnyWord(l, URGENCY_WORDS)
            if (hasLink || urgent) {
                return "This message asks you to use an OTP through a link or urgently. Confirm with your bank's official helpline first."
            }
        }
        return null
    }

    /**
     * Sender ka naam/number aur message ka text le kar verdict deta hai.
     * Return: (label, severity) — severity "scam" sirf tab jab pakka fraud ho,
     * baaki "suspicious" (laal "Scam detected" alert har keyword par galat tha,
     * user ne khud share kiya hua link bhi scam kehla raha tha).
     *
     * `trustedSender` true ho to rule engine poori tarah skip — saved contact ya
     * WhatsApp group ke andar ka member. Bina iske saved logon ki normal baat
     * (family emergency, "paise bhej do") par alert aata tha.
     *
     * `isGroup` true ho to LINK analysis poori tarah skip — sirf text-based scam
     * (OTP mangna, prize/lottery, bank impersonation) par alert. Ye is liye
     * zaroori hai ke WhatsApp group notification ka title GROUP KA NAAM hota
     * hai, member ka number nahi — app ko pata hi nahi chalta ke link kisne
     * bheja. Group mein job/course/training ke asli ads roz aate hain, aur
     * `.top`/`.xyz`/`.link`/`.work` jaise naye TLD in par lagte hain — jis se
     * har asli course ad "suspicious link" alert bana deta tha (test:
     * careercourse.top, jobsapply.xyz, smmcourse.link, ccna-course.work — 4/4).
     * Sender ki identity group me available hi nahi hoti, to link par faisla
     * lagana galat verdict hai, chahe signal kitna bhi strong ho.
     */
    fun classifyMessageWithSeverity(
        title: String,
        body: String,
        context: Context,
        trustedSender: Boolean = false,
        isGroup: Boolean = false,
    ): Pair<String, String>? {
        ensureLoaded(context)
        val full = "$title $body".lowercase()

        // Saved contact / trusted group se aayi message — koi alert nahi.
        if (trustedSender) return null

        // Bank ki apni OTP/alert SMS — keyword rules skip, link check phir bhi
        // `Severity` NumberRules ke andar nested enum hai — `import ...NumberRules.Severity`
        // ke baghair ye unresolved reference deta tha aur module compile nahi hua tha.
        if (!looksLikeOtpDelivery(full)) {
            match(full)?.let { return it to NumberRules.Severity.SCAM.name.lowercase() }
            // Tier B (kamzor OTP signal) sirf amber — laal scam nahi.
            if (isWeakOtpSignal(full)) {
                matchOtpHarvest(full)?.let { return it to NumberRules.Severity.SUSPICIOUS.name.lowercase() }
            } else {
                matchOtpHarvest(full)?.let { return it to NumberRules.Severity.SCAM.name.lowercase() }
            }
        }
        // Group mein sirf text-based scam alert karta hai — link nahi.
        // 1:1 chat mein link analysis chalti hai (wahan sender ki identity hai).
        if (!isGroup) {
            matchSuspiciousLink(full)?.let {
                return it to NumberRules.Severity.SUSPICIOUS.name.lowercase()
            }
        }

        // Sender number community-reported scam list mein ho — pakki baat.
        // Sirf tab jab title poori tarah ek number ho; warna group title jaise
        // "Class 2024 batch" me ka "2024" number samajh ke check hota tha.
        val senderNumber = extractSenderNumber(title) ?: return null
        if (NumberRules.classify(senderNumber, context) == NumberRules.Severity.SCAM)
            return "The sender's number is a community-reported scam number" to NumberRules.Severity.SCAM.name.lowercase()
        return null
    }

    // Tier B detector: weak action + (link ya urgency), aur koi send/demand
    // word nahi. Ye sirf severity decide karta hai, verdict nahi.
    private fun isWeakOtpSignal(text: String): Boolean {
        if (!hasAnyWord(text, OTP_WORDS)) return false
        if (hasAnyWord(text, GIVE_WORDS_SEND) || hasAnyWord(text, GIVE_WORDS_DEMAND)) return false
        if (!hasAnyWord(text, WEAK_ACTION_WORDS)) return false
        return URL_REGEX.containsMatchIn(text) || hasAnyWord(text, URGENCY_WORDS)
    }

    // Title ka number wahi hai jo poori tarah number hai ya "sender" ki jagah
    // aata hai — group title ke andar ka koi number nahi.
    fun extractSenderNumber(title: String): String? {
        val t = title.trim()
        val m = Regex("""^\+?\d[\d\s\-()]{6,}$""").find(t) ?: return null
        val cleaned = NumberRules.clean(m.value)
        return if (cleaned.length >= 7) cleaned else null
    }
}