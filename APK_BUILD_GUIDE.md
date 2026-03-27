# Building APK for Vulnerable E-Commerce Lab

This guide explains how to build an Android APK from the Flask web application.

## Prerequisites

### 1. Install Required Tools

#### On Windows:

```powershell
# Install Python 3.9+ (if not already installed)
# Download from https://www.python.org/downloads/

# Install Buildozer and dependencies
pip install buildozer
pip install Cython
pip install Kivy
pip install python-for-android
pip install lxml
pip install .
```

#### Java Development Kit (JDK)
```
Download and install JDK 11+
Add JAVA_HOME to environment variables
```

#### Android SDK
```
Download Android SDK from https://developer.android.com/studio
Install API 31 and build tools
Set ANDROID_SDK_ROOT environment variable
```

#### Android NDK
```
Download NDK r23b from https://developer.android.com/ndk/downloads
Extract and set ANDROID_NDK_ROOT environment variable
```

## Build Steps

### 1. Install Dependencies

```cmd
pip install -r requirements.txt
pip install kivy
pip install buildozer python-for-android Cython
```

### 2. Prepare Build Files

The following files are already created:
- `buildozer.spec` - Configuration for buildozer
- `main.py` - Kivy wrapper for Flask app

### 3. Build APK

#### Option A: Using Buildozer (Recommended)

```cmd
# Debug APK (for testing)
buildozer android debug

# Release APK (for distribution)
buildozer android release
```

The APK will be generated in:
```
bin/vuln_ecommerce-0.1-debug.apk
```

#### Option B: Using WSL

If you're on Windows, you can use Windows Subsystem for Linux (WSL) for better compatibility:

```bash
# In WSL terminal
wsl
cd /mnt/e/AS\ LAb/vulnerable_ecommerce
buildozer android debug
```

### 4. Install on Android Device

```cmd
# Connect Android device via USB or use an emulator

# Install APK
adb install bin/vuln_ecommerce-0.1-debug.apk

# Or for release build:
adb install bin/vuln_ecommerce-0.1-release-unsigned.apk
```

### 5. Run App

- Open the installed app on your Android device
- The embedded Flask server will start
- The web interface will load in the WebView

## Troubleshooting

### Issue: Buildozer not found
```
Solution: pip install buildozer --upgrade
```

### Issue: Android SDK not found
```
Solution: Set ANDROID_SDK_ROOT environment variable
Example: set ANDROID_SDK_ROOT=C:\Android\Sdk
```

### Issue: Java not found
```
Solution: Install JDK and set JAVA_HOME
Example: set JAVA_HOME=C:\Program Files\Java\jdk-11
```

### Issue: NDK errors
```
Solution: Download NDK r23b and set ANDROID_NDK_ROOT
Example: set ANDROID_NDK_ROOT=C:\android-ndk-r23b
```

### Issue: "Could not find permission android.permission.INTERNET"
```
Solution: Update buildozer.spec with correct Android API version
```

## Alternative: Online APK Builder

If local build fails, use online APK builders:
- **Kivy Cloud** - https://toolchain.kivy.org/
- **App1Build** - https://app1build.com/

Upload your project and let the cloud service build it.

## Environment Variables (Windows)

Add these to your system environment variables:

```
JAVA_HOME = C:\Program Files\Java\jdk-11
ANDROID_SDK_ROOT = C:\Android\Sdk
ANDROID_NDK_ROOT = C:\android-ndk-r23b
```

## Project Structure for APK

The APK will include:
- `main.py` - Kivy app entry point
- `app.py` - Flask application  
- `requirements.txt` - Python dependencies
- `static/` - CSS, images
- `templates/` - HTML templates
- `data/` - Application data

## Notes

- The APK runs entirely on the device
- Flask server starts automatically when the app opens
- WebView displays the local Flask web interface
- All labs are accessible from mobile device
- No internet connection required after app is installed

## APK Size

Expected size: ~80-150 MB (varies based on included libraries)

## Security Note

This APK contains intentional vulnerabilities for educational purposes. 
Do not distribute or use for production purposes.
