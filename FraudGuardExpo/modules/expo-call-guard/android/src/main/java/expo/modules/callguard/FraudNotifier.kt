package expo.modules.callguard

import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.Context
import androidx.core.app.NotificationCompat

object FraudNotifier {
    private const val CHANNEL_ID = "fraud-alerts"

    fun show(context: Context, subject: String, detail: String, status: String) {
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
    }
}
