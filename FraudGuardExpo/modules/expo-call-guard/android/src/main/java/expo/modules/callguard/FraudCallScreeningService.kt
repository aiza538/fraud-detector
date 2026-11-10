package expo.modules.callguard

import android.os.Build
import android.telecom.Call
import android.telecom.CallScreeningService
import androidx.annotation.RequiresApi

/**
 * Android 10+ ka official caller-ID raasta. System har aane wali call par ise
 * bulata hai — bas user ne FraudGuard ko "caller ID & spam" app chuna ho
 * (CallGuardModule.requestCallScreeningRole). READ_CALL_LOG ki zarurat nahi.
 *
 * FraudGuard call KABHI nahi rokta, na awaz band karta hai — sirf alert. Ghalat
 * alert par bhi asli bank ki call user tak pohanchni chahiye.
 */
@RequiresApi(Build.VERSION_CODES.Q)
class FraudCallScreeningService : CallScreeningService() {
    override fun onScreenCall(callDetails: Call.Details) {
        // Jawab pehle: jab tak jawab na jaye phone ring nahi karta (max ~5 sec).
        // Default response = call jaise aayi waise chalne do.
        respondToCall(callDetails, CallResponse.Builder().build())

        if (callDetails.callDirection != Call.Details.DIRECTION_INCOMING) return
        // Hidden caller-ID par handle null/khali hota hai — CallAlert usay
        // "suspicious" alert deta hai.
        CallAlert.handleIncoming(this, callDetails.handle?.schemeSpecificPart)
    }
}
