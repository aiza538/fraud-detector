package com.fraudguardmobile; // Make sure this matches your MainApplication.java package

import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.Service;
import android.content.Intent;
import android.os.Build;
import android.os.Bundle;
import android.os.IBinder;
import android.service.notification.NotificationListenerService;
import android.service.notification.StatusBarNotification;

import androidx.core.app.NotificationCompat;

public class NotificationService extends NotificationListenerService {

    @Override
    public void onNotificationPosted(StatusBarNotification sbn) {
        String pkg = sbn.getPackageName();
        
        // Target: WhatsApp, SMS, Telegram
        if (!pkg.equals("com.whatsapp") && 
            !pkg.equals("com.android.mms") &&
            !pkg.equals("org.telegram.messenger")) return;
            
        Bundle extras = sbn.getNotification().extras;
        String text = extras.getCharSequence(Notification.EXTRA_TEXT, "").toString();
        String title = extras.getCharSequence(Notification.EXTRA_TITLE, "").toString();
        
        if (text.isEmpty()) return;
        
        // Here you would send a broadcast to React Native
        // For simplicity, you can use a library or NativeModules to pass this to JS
        // In a real app, you'd trigger an HTTP request to your backend directly from here,
        // OR send it to React Native via a HeadlessJS task.
    }
}