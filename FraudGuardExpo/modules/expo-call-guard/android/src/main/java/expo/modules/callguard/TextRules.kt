package expo.modules.callguard

import android.content.Context

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

    // backend/data/scam_patterns.json ke WhatsApp rules ka offline mirror.
    // Har rule ka `anchors` wahi hai jo backend pattern me hai.
    private val RULES = listOf(
        Rule(
            listOf("whatsapp", "ban", "verification", "code", "24 hour", "band", "recover", "forward"),
            3,
            listOf("verification code", "24 hour", "recover", "band"),
            "WhatsApp account ban hoax — verification code mangna hijacking attempt hai",
        ),
        Rule(
            listOf("invest", "profit", "trading", "group", "dollar", "daily", "return", "fee", "telegram"),
            3,
            listOf("invest", "profit", "trading", "telegram"),
            "Investment group scam — guaranteed daily profit Ponzi fraud hai",
        ),
        Rule(
            // "beta" / "hospital" / "emergency" aam family baat ke lafz hain —
            // anchor sirf tab: "meri awaz" (voice clone), ya paise/udhaar maanga gaya.
            listOf("meri awaz", "voice", "audio message", "beta", "bachi", "loan", "udhaar", "paise bhej", "emergency", "hospital"),
            3,
            listOf("meri awaz", "loan", "udhaar", "paise bhej"),
            "Cloned voice / family emergency scam — voice message identity proof nahi",
        ),
        Rule(
            listOf(
                "otp", "bhij", "bhej", "paise", "jaldi", "foran", "easypaisa", "jazzcash",
                "account detail", "atm card",
            ),
            3,
            listOf("otp", "easypaisa", "jazzcash", "account detail", "atm card"),
            "Money/OTP harvesting message — koi bhi OTP ya payment request verify karke hi bhejein",
        ),
        Rule(
            // "Otp number bhij dy, account secure bnna hy" — 2 credential signals ka
            // combo hi kaafi hai; 3 keywords wala shart Roman Urdu ke chhote messages
            // par poori nahi hoti thi.
            //
            // Anchor zaroori hai: "account block" / "account secure" aam bank-support
            // baat ke lafz hain. Pehle minMatch=2 bina anchor ke "mera account block
            // ho gaya, account secure rakhein" jaisi NORMAL message scam kehlaati thi.
            listOf(
                "otp", "verification code", "atm card", "card number", "cnic",
                "account detail", "bank account", "account secure", "account block",
                "account band", "account freeze",
            ),
            2,
            listOf("otp", "verification code", "atm card", "card number", "cnic", "account detail", "bank account"),
            "Credential harvesting attempt — bank/authority OTP, ATM details ya CNIC KABHI nahi mangta",
        ),
        Rule(
            // Pakistan-specific: unknown SMS/WhatsApp reward scams (call back bait).
            // Anchor sirf actual reward/lottery claim — "claim"/"win" aam lafz hain
            // ("I claim that...", "winning habits", "Eid Mubarak") inhe anchor nahi banaya.
            listOf("lucky draw", "luckydraw", "prize bond", "prizebond", "coupon", "win", "won", "jeet", "bike", "motorbike", "scooty", "mobile phone", "lottery", "cash price", "cash prize", "inam", "mubarak", "rabta", "claim", "winner"),
            3,
            listOf("lucky draw", "luckydraw", "prize bond", "prizebond", "lottery", "cash prize", "cash price", "winner", "inam", "rabta"),
            "Lucky draw / prize scam — unknown SMS ka 'bike/cash jeet gaye' nara fake lottery bait hai, call-back se fraud hota hai",
        ),
    )

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
    private val ABUSE_TLDS = listOf(
        ".tk", ".ml", ".ga", ".cf", ".gq", ".xyz", ".top", ".click", ".link", ".buzz",
        ".icu", ".vip", ".quest", ".cyou",
    )

    // Sarkari/talebmi domains kabhi "unknown" shak ke qabil nahi
    private val OFFICIAL_SUFFIXES = listOf(".gov.pk", ".gob.pk", ".edu.pk", ".gov", ".gob")

    // Bank/wallet/authority ki ASLI domains
    private val OFFICIAL_HOSTS = listOf(
        "hbl.com", "ubl.com.pk", "nbp.com.pk", "mcb.com.pk", "alliedbank.com", "abl.com",
        "bankalfalah.com", "meezanbank.com", "bop.com.pk", "sc.com", "bankislami.com.pk",
        "faysalbank.com", "askari.com", "soneribank.com", "hmb.com.pk", "summitbank.com.pk",
        "karobank.com.pk", "sindhbank.gov.pk", "easypaisa.com.pk", "esappk.com",
        "jazzcash.com.pk", "jazz.com.pk", "zong.com.pk", "ufone.com", "telia.com.pk",
        "nadra.gov.pk", "fia.gov.pk", "fbr.gov.pk", "pta.gov.pk", "bisp.gov.pk",
        "sbp.org.pk", "complaint.sbp.org.pk", "sadapay.pk", "nayapay.com.pk",
    )

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
    private val BRAND_TOKENS = listOf(
        "hbl", "nbp", "mcb", "ubl", "alfalah", "meezan", "islami", "askari", "faysal",
        "soneri", "jamhoor", "samba", "silkbank", "kmb", "summit", "karo", "citi",
        "standardchartered", "easypaisa", "jazzcash", "jazz", "zong", "ufone", "telia",
        "nadra", "fbr", "fia", "pta", "bisp", "ehsaas", "statebank", "sbp", "sadapay",
        "nepcard", "omnipay", "finja", "police", "court", "tax",
    )

    private val GENERIC_TRUSTED = listOf(
        "facebook.com", "instagram.com", "whatsapp.com", "google.com", "youtube.com",
        "twitter.com", "x.com", "linkedin.com", "microsoft.com", "apple.com", "apple.co",
    )

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
                IP_HOST.matches(host) -> "link direct IP address par khula raha hai"
                authorityOf(url).contains("@") -> "link mein chhupa hua address (credentials@domain) hai"
                ABUSE_TLDS.any { host.endsWith(it) } -> "host free/abuse-host TLD par hai ($host)"
                hasBrandToken(host) -> "host mein bank/sarkari idare ka naam hai lekin ye unki official domain nahi ($host)"
                else -> continue
            }
            return "Suspicious link — $reason. Is par click karne se pehle bank ki official helpline se confirm karein."
        }
        return null
    }

    // --- Bank ki APNI automated SMS vs scammer ka OTP request ----------------
    //
    // Scam OTP *maangta* hai; bank OTP *deta* hai aur "do not share" likhta hai.
    // Ye distinction na hone se har official OTP/alert SMS "credential harvesting"
    // kehla raha tha.
    private val OTP_DELIVERY_HINTS = listOf(
        "do not share", "don't share", "donot share", "never share", "not share",
        "share na kare", "share mat kare", "share na kr", "kisi ke sath share",
        "kisi ko na", "for your security", "for the security", "not authorized",
    )

    private fun looksLikeOtpDelivery(text: String): Boolean =
        Regex("""\b\d{4,8}\b""").containsMatchIn(text) &&
            OTP_DELIVERY_HINTS.any { text.contains(it) }

    // Roman Urdu spelling variants: "bhij dy" aur "bhej dein" ek hi request hain,
    // magar plain contains() mein ye match nahi hote — isi se OTP scams miss hote thay.
    private val OTP_WORDS = listOf(
        "otp", "one time password", "one-time password", "verification code", "otp number", "code bata",
    )
    private val GIVE_WORDS_SEND = listOf(
        "bhej", "bhij", "bej", "bheeg", "bhejna", "bhejo", "send", "forward", "share",
        "dena", "deina", "dein", "dijiye", "day", "de", "dy", "di", "do",
    )

    // Tier A me OTP + "bhej do" / "share karein" / "code bata" / "maangein".
    private val GIVE_WORDS_DEMAND = listOf(
        "maang", "mang", "chahiye", "chahe", "milwa", "mila", "bataye", "bataiye",
    )

    // Tier B — kamzor signal. Ye AKELA scam nahi: bank ki apni notification bhi
    // "OTP verify karein" likhti hai. Inhe sirf tab amber dena hai jab link ya
    // urgency bhi ho. Pehle ye sab GIVE_WORDS me thay, jis se har official
    // OTP notification "OTP harvesting" kehlaati thi.
    private val WEAK_ACTION_WORDS = listOf(
        "enter", "fill", "verify", "activate", "update", "click", "submit", "karein", "karen", "karo",
    )
    private val URGENCY_WORDS = listOf(
        "foran", "jaldi", "abhi", "turant", "immediately", "right now", "expires", "expire",
    )

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
    private val OTP_NEGATION_HINTS = listOf(
        "do not share", "don't share", "donot share", "never share", "not share",
        "share na kare", "share na kro", "share na karo", "share mat kare",
        "mat batao", "mat batana", "mat bhejo", "mat bhejein", "mat dein", "mat do",
        "kisi ko mat", "kisi ko nahi", "kisi ko na bata",
        "maangna nahi", "mangna nahi", "nahi mangna", "koi maang", "kabhi",
        "hum nahi", "hum kabhi",
        "do not give", "don't give", "no one will ask",
    )

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
            return "OTP harvesting attempt — unknown number OTP/code maang raha hai. Koi OTP kabhi kisi ke sath share NAHI karna, bank/authority kabhi OTP nahi maangta."
        }

        if (hasAnyWord(l, WEAK_ACTION_WORDS)) {
            val hasLink = URL_REGEX.containsMatchIn(l)
            val urgent = hasAnyWord(l, URGENCY_WORDS)
            if (hasLink || urgent) {
                return "OTP ke saath link ya foran-action maanga gaya hai — bank ki official helpline se confirm karein."
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
            return "Sender number community-reported scam hai" to NumberRules.Severity.SCAM.name.lowercase()
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