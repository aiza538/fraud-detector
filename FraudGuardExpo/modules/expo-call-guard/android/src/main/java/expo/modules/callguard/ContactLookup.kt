package expo.modules.callguard

import android.Manifest
import android.content.Context
import android.content.pm.PackageManager
import android.provider.ContactsContract
import androidx.core.content.ContextCompat

object ContactLookup {

    /**
     * Teeno states kaafi hain. Pehle sirf Boolean tha, jiski wajah se
     * "phonebook me nahi mila" aur "READ_CONTACTS permission nahi mili" dono
     * ek hi ho jate thay — permission deny hote hi har SAVED contact unknown
     * samajh kar alert ho jata tha (bar delivery rider / bar dost par alert).
     */
    enum class Result { SAVED, NOT_SAVED, UNKNOWN }

    private const val CACHE_TTL_MS = 10 * 60 * 1000L

    @Volatile private var cachedNumbers: Set<String>? = null
    @Volatile private var cachedNames: Set<String>? = null
    @Volatile private var cachedAt: Long = 0L
    @Volatile private var permissionDenied = false

    // ContextCompat.checkSelfPermission — `context.checkSelfPermission` sirf
    // API 23+ (minSdk 21 par) compile nahi hota. Pehle yahan direct
    // `context.packageManager.checkSelfPermission` tha jo Kotlin ne unresolved
    // reference diya aur poora native module compile hi nahi hua tha.
    fun hasPermission(context: Context): Boolean =
        ContextCompat.checkSelfPermission(context, Manifest.permission.READ_CONTACTS) ==
            PackageManager.PERMISSION_GRANTED

    /**
     * Permission abhi mili (ya time out ho gaya) to cache foran refresh karo.
     * `startCallMonitor` ye permission ke baad call karta hai — warna pehla
     * lookup permission-denied par cache karke baqi app lifetime tak galat
     * verdict deta.
     */
    fun invalidate() {
        cachedNumbers = null
        cachedNames = null
        cachedAt = 0L
        permissionDenied = false
    }

    private fun ensureLoaded(context: Context): Boolean {
        val now = System.currentTimeMillis()
        if (cachedNumbers != null && cachedNames != null && now - cachedAt < CACHE_TTL_MS) return true
        if (permissionDenied && now - cachedAt < CACHE_TTL_MS) return false
        return load(context)
    }

    /**
     * Poori phonebook ek hi baar (ya 10 min baad) memory me load hoti hai.
     * Pehle har call/message par poori phonebook row-by-row scan hoti thi —
     * wo BroadcastReceiver aur NotificationListenerService ke thread par
     * chalti thi (ANR-prone, aur ek 2000-contact phonebook par har notification
     * par noticeable lag).
     */
    private fun load(context: Context): Boolean {
        if (!hasPermission(context)) {
            permissionDenied = true
            cachedAt = System.currentTimeMillis()
            cachedNumbers = null
            cachedNames = null
            return false
        }
        val numbers = HashSet<String>(512)
        val names = HashSet<String>(256)
        try {
            context.contentResolver.query(
                ContactsContract.CommonDataKinds.Phone.CONTENT_URI,
                arrayOf(ContactsContract.CommonDataKinds.Phone.NUMBER),
                null, null, null,
            )?.use { c ->
                val col = c.getColumnIndex(ContactsContract.CommonDataKinds.Phone.NUMBER)
                if (col >= 0) {
                    while (c.moveToNext()) {
                        val n = normalize(c.getString(col) ?: "")
                        if (n.length >= 7) numbers.add(n)
                    }
                }
            }
            context.contentResolver.query(
                ContactsContract.Contacts.CONTENT_URI,
                arrayOf(ContactsContract.Contacts.DISPLAY_NAME),
                null, null, null,
            )?.use { c ->
                val col = c.getColumnIndex(ContactsContract.Contacts.DISPLAY_NAME)
                if (col >= 0) {
                    while (c.moveToNext()) {
                        // `?.lowercase()` String? deta hai — pehle `n` nullable
                        // rahta tha aur `names.add(n)` compile nahi hua tha.
                        val n = c.getString(col)?.trim()?.lowercase()
                        if (!n.isNullOrEmpty()) names.add(n)
                    }
                }
            }
        } catch (_: Exception) {
            // SecurityException (permission revoke) ya provider error
            permissionDenied = true
            cachedAt = System.currentTimeMillis()
            cachedNumbers = null
            cachedNames = null
            return false
        }
        cachedNumbers = numbers
        cachedNames = names
        cachedAt = System.currentTimeMillis()
        permissionDenied = false
        return true
    }

    /**
     * Number ko 10-digit suffix tak normalize karo taake 0300…/+92 300…/92300…
     * sab match hon, phir exact set membership dekho.
     */
    private fun normalize(raw: String): String {
        var c = raw.replace(" ", "").replace("-", "")
            .replace("(", "").replace(")", "").replace("\u00A0", "")
        if (c.startsWith("+92")) c = c.substring(3)
        else if (c.startsWith("0092")) c = c.substring(4)
        if (c.startsWith("0")) c = c.substring(1)
        if (c.length > 10) c = c.takeLast(10)
        return c
    }

    fun lookupNumber(context: Context, rawNumber: String?): Result {
        val cleaned = normalize(rawNumber.orEmpty())
        if (cleaned.length < 7) return Result.NOT_SAVED
        if (!ensureLoaded(context)) return Result.UNKNOWN
        return if (cleaned in (cachedNumbers ?: emptySet())) Result.SAVED else Result.NOT_SAVED
    }

    fun isSavedContact(context: Context, rawNumber: String?): Boolean =
        lookupNumber(context, rawNumber) == Result.SAVED

    /**
     * WhatsApp group title / SMS alphanumeric header ke liye: kya ye EXACTLY
     * kisi saved contact ka naam hai?
     *
     * Pehle ye `DISPLAY_NAME LIKE ?` SQL query thi. SQLite ka `LIKE`
     * case-insensitive hai AUR `%`/`_` wildcard — yaani ye substring match
     * karti thi. Is se do tarah ke bug hote thay:
     *   - group title "Family" ya header "HBL" kisi bhi "HBL Fan" jaise
     *     contact se match kar jata tha → ASLI bank scam SMS silently skip.
     *   - "unknown number kabhi known ban jata tha" — isi substring match ki
     *     wajah se.
     * Ab exact (case-insensitive, trimmed) set membership hai.
     */
    fun lookupName(context: Context, displayName: String): Result {
        val name = displayName.trim().lowercase()
        if (name.isEmpty()) return Result.NOT_SAVED
        if (!ensureLoaded(context)) return Result.UNKNOWN
        return if (name in (cachedNames ?: emptySet())) Result.SAVED else Result.NOT_SAVED
    }

    fun hasContactNamed(context: Context, displayName: String): Boolean =
        lookupName(context, displayName) == Result.SAVED
}