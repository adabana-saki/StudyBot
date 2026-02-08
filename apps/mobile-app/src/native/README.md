# Native Modules Setup Guide

This directory contains stub implementations for platform-specific native modules
that enable app blocking during StudyBot focus sessions. These modules cannot be
fully implemented in JavaScript and require completion in Xcode (iOS) and
Android Studio (Android).

## Overview

StudyBot's Phone Lock feature has three levels:

| Level  | JavaScript | Native Required |
|--------|-----------|-----------------|
| Nudge  | Full-screen overlay + notifications | No |
| Lock   | Full-screen overlay + coin bet | No |
| Shield | Full-screen overlay + **app blocking** | **Yes** |

Levels 1 and 2 work entirely within the React Native app. Level 3 (Shield)
requires native app blocking to prevent users from switching to other apps.

---

## iOS: Screen Time API (Family Controls)

### File
`ios/ScreenTimeManager.swift`

### Requirements
- iOS 15.0+
- Apple Developer Program membership
- Family Controls entitlement (must be requested from Apple)

### Setup Steps

1. **Request the Family Controls entitlement:**
   - Go to [Apple Developer Portal](https://developer.apple.com/account)
   - Navigate to Certificates, Identifiers & Profiles > Identifiers
   - Select your app identifier
   - Enable "Family Controls" capability
   - You may need to submit a request form to Apple explaining your use case

2. **Configure Xcode project:**
   ```
   Open ios/StudyBot.xcworkspace in Xcode
   Select the StudyBot target
   Go to Signing & Capabilities
   Click "+ Capability"
   Add "Family Controls"
   ```

3. **Add frameworks:**
   In Xcode, add the following frameworks to your target:
   - `FamilyControls`
   - `ManagedSettings`
   - `DeviceActivity`

4. **Create Device Activity Monitor extension:**
   The app blocking timer requires a separate app extension:
   ```
   File > New > Target > Device Activity Monitor Extension
   Name: StudyBotDeviceActivityMonitor
   ```
   This extension handles automatic unblocking when the study session ends.

5. **Add the bridge header:**
   Create `ScreenTimeManager.m` for the React Native bridge:
   ```objc
   #import <React/RCTBridgeModule.h>

   @interface RCT_EXTERN_MODULE(ScreenTimeManager, NSObject)

   RCT_EXTERN_METHOD(requestAuthorization:(RCTPromiseResolveBlock)resolve
                     rejecter:(RCTPromiseRejectBlock)reject)

   RCT_EXTERN_METHOD(checkAuthorization:(RCTPromiseResolveBlock)resolve
                     rejecter:(RCTPromiseRejectBlock)reject)

   RCT_EXTERN_METHOD(blockApps:(int)durationMinutes
                     resolver:(RCTPromiseResolveBlock)resolve
                     rejecter:(RCTPromiseRejectBlock)reject)

   RCT_EXTERN_METHOD(unblockApps:(RCTPromiseResolveBlock)resolve
                     rejecter:(RCTPromiseRejectBlock)reject)

   RCT_EXTERN_METHOD(isBlocking:(RCTPromiseResolveBlock)resolve
                     rejecter:(RCTPromiseRejectBlock)reject)

   @end
   ```

6. **Implement the TODO sections in `ScreenTimeManager.swift`**

### Usage from React Native
```typescript
import { NativeModules } from 'react-native';
const { ScreenTimeManager } = NativeModules;

// Request authorization
await ScreenTimeManager.requestAuthorization();

// Block apps for 25 minutes
await ScreenTimeManager.blockApps(25);

// Unblock all apps
await ScreenTimeManager.unblockApps();
```

### Important Notes
- Users must explicitly authorize Screen Time access
- The FamilyActivityPicker UI is provided by Apple and cannot be customized
- App blocking persists even if your app is terminated (handled by the extension)
- Testing requires a physical device (Screen Time API is unavailable in Simulator)

---

## Android: Accessibility Service

### File
`android/AccessibilityManager.kt`

### Requirements
- Android 5.0+ (API level 21+)
- User must manually enable the Accessibility Service in device settings

### Setup Steps

1. **Add the module to your React Native package:**

   Create `AccessibilityManagerPackage.kt`:
   ```kotlin
   package com.studybot.mobile.native

   import com.facebook.react.ReactPackage
   import com.facebook.react.bridge.NativeModule
   import com.facebook.react.bridge.ReactApplicationContext
   import com.facebook.react.uimanager.ViewManager

   class AccessibilityManagerPackage : ReactPackage {
       override fun createNativeModules(
           reactContext: ReactApplicationContext
       ): List<NativeModule> {
           return listOf(AccessibilityManagerModule(reactContext))
       }

       override fun createViewManagers(
           reactContext: ReactApplicationContext
       ): List<ViewManager<*, *>> {
           return emptyList()
       }
   }
   ```

2. **Register the package in `MainApplication.kt`:**
   ```kotlin
   override fun getPackages(): List<ReactPackage> {
       val packages = PackageList(this).packages.toMutableList()
       packages.add(AccessibilityManagerPackage())
       return packages
   }
   ```

3. **Update `AndroidManifest.xml`:**
   ```xml
   <!-- Inside <application> tag -->
   <service
       android:name=".native.StudyBotAccessibilityService"
       android:permission="android.permission.BIND_ACCESSIBILITY_SERVICE"
       android:exported="false">
       <intent-filter>
           <action android:name="android.accessibilityservice.AccessibilityService" />
       </intent-filter>
       <meta-data
           android:name="android.accessibilityservice"
           android:resource="@xml/accessibility_service_config" />
   </service>
   ```

4. **Create `res/xml/accessibility_service_config.xml`:**
   ```xml
   <?xml version="1.0" encoding="utf-8"?>
   <accessibility-service xmlns:android="http://schemas.android.com/apk/res/android"
       android:accessibilityEventTypes="typeWindowStateChanged"
       android:accessibilityFeedbackType="feedbackGeneric"
       android:notificationTimeout="100"
       android:canRetrieveWindowContent="false"
       android:description="@string/accessibility_service_description" />
   ```

5. **Add string resource in `res/values/strings.xml`:**
   ```xml
   <string name="accessibility_service_description">
       StudyBot uses this service to help you stay focused during study sessions
       by preventing access to distracting apps.
   </string>
   ```

6. **Implement the TODO sections in `AccessibilityManager.kt`**

### Usage from React Native
```typescript
import { NativeModules } from 'react-native';
const { AccessibilityManager } = NativeModules;

// Check if service is enabled
const enabled = await AccessibilityManager.isServiceEnabled();

// Open settings for user to enable service
await AccessibilityManager.requestPermission();

// Block specific apps for 25 minutes
await AccessibilityManager.startBlocking(
  ['com.instagram.android', 'com.twitter.android'],
  25
);

// Stop blocking
await AccessibilityManager.stopBlocking();
```

### Important Notes
- Users must manually enable the service in device Accessibility settings
- The service runs in the background even when the app is closed
- Google Play Store may reject apps using Accessibility Services for non-accessibility
  purposes. Consider using the UsageStatsManager API as an alternative for Play Store
  distribution.
- For development/sideloading, the Accessibility Service approach works well.

### Alternative: UsageStatsManager (Less Intrusive)
If you prefer not to use Accessibility Services, you can use the `UsageStatsManager`
API to detect foreground app changes and display an overlay. This requires the
`PACKAGE_USAGE_STATS` permission and is more acceptable for Play Store distribution.

---

## Testing

Both native modules require physical devices for testing:

- **iOS**: Screen Time API is unavailable in the Simulator
- **Android**: Accessibility Service works on emulators but physical device testing
  is recommended

To test the Phone Lock feature without native modules:
1. Set lock level to 1 (Nudge) or 2 (Lock)
2. These levels use only the React Native overlay and do not require native modules
3. The overlay will still block interaction within the app
