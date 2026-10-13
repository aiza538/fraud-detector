package expo.modules.callguard

import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.Context
import androidx.core.app.NotificationCompat

object FraudNotifier {
    private const val CHANNEL_ID = "fraud-alerts"
    private const val PREFS = "fraud_notifier_dedupe"

    /**
     * Same subject par dobara alert kitni der baad? 12 ghante.
     *
     * Bina iske ek hi scammer 10 baar call kare to 10 notifications — user
     * ignore karna seekh leta hai aur ASLI alert bhi nazar se chhoot jata
     * hai. 12h cooldown ke baad bhi alert history me entry banti hai, sirf
     * notification dobara fire nahi hoti.
     */
    private const val COOLDOWN_MS = 12 * 60 * 60 * 1000L

    /**
     * Notification dikhayi ya cooldown ki wajah se skip hui.
     *
     * `false` return karne par caller ko `alerted = false` emit karna chahie
     * taake JS alert history me duplicate entry na banaaye.
     */
    fun show(context: Context, subject: String, detail: String, status: String): Boolean {
        val key = "last:${subject.trim().lowercase()}"
        val prefs = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
        val now = System.currentTimeMillis()
        val last = prefs.getLong(key, 0L)
        if (last > 0 && now - last < COOLDOWN_MS) {
            return false
        }
        prefs.edit().putLong(key, now).apply()

        val manager = context.getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
        manager.createNotificationChannel(
            NotificationChannel(CHANNEL_ID, "Fraud Alerts", NotificationManager.IMPORTANCE_MAX)
        )

        val title = when (status) {
            "scam" -> "🚨 Scam detected"
            else -> "⚠️ Suspicious activity"
        }
        val launch = context.packageManager.getLaunchIntentForPackage(context.packageName)
        val pending = launch?.let {
            PendingIntent.getActivity(context, 0, it, PendingIntent.FLAG_IMMUTABLE)
        }

        val notification = NotificationCompat.Builder(context, CHANNEL_ID)
            .setSmallIcon(android.R.drawable.ic_dialog_alert)
            .setContentTitle("$title — $subject")
            .setContentText(detail)
            .setStyle(NotificationCompat.BigTextStyle().bigText("$subject\n$detail\nTap to open FraudGuard for details."))
            .setPriority(NotificationCompat.PRIORITY_MAX)
            .setAutoCancel(true)
            .setContentIntent(pending)
            .build()

        manager.notify(System.currentTimeMillis().toInt(), notification)
        return true
    }
}
