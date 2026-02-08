/**
 * AccessibilityManager.kt
 *
 * STUB: Android Accessibility Service for app blocking during focus sessions.
 * This file must be completed in Android Studio with proper manifest configuration.
 *
 * The Android Accessibility Service can:
 * - Detect when the user opens a blocked app
 * - Redirect the user back to StudyBot
 * - Display an overlay blocking the screen
 *
 * Alternative approaches:
 * - UsageStatsManager: Monitor app usage (requires PACKAGE_USAGE_STATS permission)
 * - Device Policy Manager (DPM): For enterprise/kiosk mode
 * - AppOpsManager: Monitor app operations
 *
 * Prerequisites:
 * 1. Declare AccessibilityService in AndroidManifest.xml
 * 2. Create accessibility_service_config.xml
 * 3. User must manually enable the service in Settings > Accessibility
 *
 * Usage from React Native:
 * This module is exposed via a native module bridge. Call methods from JS:
 *   NativeModules.AccessibilityManager.requestPermission()
 *   NativeModules.AccessibilityManager.startBlocking(packageNames, durationMinutes)
 *   NativeModules.AccessibilityManager.stopBlocking()
 */

package com.studybot.mobile.native

import android.accessibilityservice.AccessibilityService
import android.accessibilityservice.AccessibilityServiceInfo
import android.content.Context
import android.content.Intent
import android.provider.Settings
import android.view.accessibility.AccessibilityEvent
import com.facebook.react.bridge.Promise
import com.facebook.react.bridge.ReactApplicationContext
import com.facebook.react.bridge.ReactContextBaseJavaModule
import com.facebook.react.bridge.ReactMethod
import com.facebook.react.bridge.ReadableArray

/**
 * React Native bridge module for the Accessibility-based app blocker.
 */
class AccessibilityManagerModule(
    private val reactContext: ReactApplicationContext
) : ReactContextBaseJavaModule(reactContext) {

    override fun getName(): String = "AccessibilityManager"

    /**
     * Check if the accessibility service is enabled.
     */
    @ReactMethod
    fun isServiceEnabled(promise: Promise) {
        // TODO: Check if StudyBotAccessibilityService is enabled
        // val enabledServices = Settings.Secure.getString(
        //     reactContext.contentResolver,
        //     Settings.Secure.ENABLED_ACCESSIBILITY_SERVICES
        // )
        // val isEnabled = enabledServices?.contains(
        //     "${reactContext.packageName}/com.studybot.mobile.native.StudyBotAccessibilityService"
        // ) == true
        // promise.resolve(isEnabled)

        promise.reject("NOT_IMPLEMENTED", "Native module not yet implemented. Complete in Android Studio.")
    }

    /**
     * Open the accessibility settings page for the user to enable the service.
     */
    @ReactMethod
    fun requestPermission(promise: Promise) {
        // TODO: Open accessibility settings
        // try {
        //     val intent = Intent(Settings.ACTION_ACCESSIBILITY_SETTINGS)
        //     intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
        //     reactContext.startActivity(intent)
        //     promise.resolve(null)
        // } catch (e: Exception) {
        //     promise.reject("SETTINGS_ERROR", "Failed to open accessibility settings", e)
        // }

        promise.reject("NOT_IMPLEMENTED", "Native module not yet implemented. Complete in Android Studio.")
    }

    /**
     * Start blocking specified apps for a duration.
     *
     * @param packageNames Array of package names to block (e.g., ["com.instagram.android"])
     * @param durationMinutes Duration in minutes
     */
    @ReactMethod
    fun startBlocking(packageNames: ReadableArray, durationMinutes: Int, promise: Promise) {
        // TODO: Store blocked packages and duration, notify the accessibility service
        //
        // Implementation outline:
        // 1. Save blocked package list to SharedPreferences
        // 2. Save end time (System.currentTimeMillis() + durationMinutes * 60 * 1000)
        // 3. The AccessibilityService reads these preferences
        // 4. When a blocked app is detected in onAccessibilityEvent, redirect to StudyBot
        //
        // val prefs = reactContext.getSharedPreferences("studybot_blocker", Context.MODE_PRIVATE)
        // val packages = mutableListOf<String>()
        // for (i in 0 until packageNames.size()) {
        //     packageNames.getString(i)?.let { packages.add(it) }
        // }
        // prefs.edit()
        //     .putStringSet("blocked_packages", packages.toSet())
        //     .putLong("block_end_time", System.currentTimeMillis() + durationMinutes * 60 * 1000L)
        //     .putBoolean("is_blocking", true)
        //     .apply()
        //
        // promise.resolve(null)

        promise.reject("NOT_IMPLEMENTED", "Native module not yet implemented. Complete in Android Studio.")
    }

    /**
     * Stop blocking all apps immediately.
     */
    @ReactMethod
    fun stopBlocking(promise: Promise) {
        // TODO: Clear blocking state
        // val prefs = reactContext.getSharedPreferences("studybot_blocker", Context.MODE_PRIVATE)
        // prefs.edit()
        //     .putBoolean("is_blocking", false)
        //     .remove("blocked_packages")
        //     .remove("block_end_time")
        //     .apply()
        //
        // promise.resolve(null)

        promise.reject("NOT_IMPLEMENTED", "Native module not yet implemented. Complete in Android Studio.")
    }

    /**
     * Check if blocking is currently active.
     */
    @ReactMethod
    fun isBlocking(promise: Promise) {
        // TODO: Check SharedPreferences
        // val prefs = reactContext.getSharedPreferences("studybot_blocker", Context.MODE_PRIVATE)
        // val isBlocking = prefs.getBoolean("is_blocking", false)
        // val endTime = prefs.getLong("block_end_time", 0)
        // val stillActive = isBlocking && System.currentTimeMillis() < endTime
        // promise.resolve(stillActive)

        promise.reject("NOT_IMPLEMENTED", "Native module not yet implemented. Complete in Android Studio.")
    }
}

/**
 * Accessibility Service that monitors foreground app changes and blocks restricted apps.
 *
 * IMPORTANT: This service must be declared in AndroidManifest.xml:
 *
 * <service
 *     android:name=".native.StudyBotAccessibilityService"
 *     android:permission="android.permission.BIND_ACCESSIBILITY_SERVICE"
 *     android:exported="false">
 *     <intent-filter>
 *         <action android:name="android.accessibilityservice.AccessibilityService" />
 *     </intent-filter>
 *     <meta-data
 *         android:name="android.accessibilityservice"
 *         android:resource="@xml/accessibility_service_config" />
 * </service>
 *
 * And accessibility_service_config.xml in res/xml/:
 *
 * <?xml version="1.0" encoding="utf-8"?>
 * <accessibility-service xmlns:android="http://schemas.android.com/apk/res/android"
 *     android:accessibilityEventTypes="typeWindowStateChanged"
 *     android:accessibilityFeedbackType="feedbackGeneric"
 *     android:notificationTimeout="100"
 *     android:canRetrieveWindowContent="false"
 *     android:description="@string/accessibility_service_description" />
 */
class StudyBotAccessibilityService : AccessibilityService() {

    override fun onAccessibilityEvent(event: AccessibilityEvent?) {
        // TODO: Implement app blocking logic
        //
        // if (event?.eventType == AccessibilityEvent.TYPE_WINDOW_STATE_CHANGED) {
        //     val packageName = event.packageName?.toString() ?: return
        //
        //     val prefs = getSharedPreferences("studybot_blocker", Context.MODE_PRIVATE)
        //     val isBlocking = prefs.getBoolean("is_blocking", false)
        //     val endTime = prefs.getLong("block_end_time", 0)
        //     val blockedPackages = prefs.getStringSet("blocked_packages", emptySet()) ?: emptySet()
        //
        //     if (!isBlocking || System.currentTimeMillis() > endTime) return
        //
        //     if (packageName in blockedPackages) {
        //         // Redirect back to StudyBot
        //         val intent = packageManager.getLaunchIntentForPackage(this.packageName)
        //         intent?.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
        //         startActivity(intent)
        //     }
        // }
    }

    override fun onInterrupt() {
        // Called when the system wants to interrupt the service
    }

    override fun onServiceConnected() {
        super.onServiceConnected()
        // Configure the service
        val info = AccessibilityServiceInfo().apply {
            eventTypes = AccessibilityEvent.TYPE_WINDOW_STATE_CHANGED
            feedbackType = AccessibilityServiceInfo.FEEDBACK_GENERIC
            notificationTimeout = 100
        }
        serviceInfo = info
    }
}
