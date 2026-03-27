[app]

# (str) Title of your application
title = Vulnerable E-Commerce Lab

# (str) Package name
package.name = vuln_ecommerce

# (str) Package domain (needed for android/ios packaging)
package.domain = org.aslab

# (source.dir) Source code directory
source.dir = .

# (list) Source files to include (let empty to include all the files)
source.include_exts = py,png,jpg,kv,atlas,txt,md

# (list) List of inclusions using pattern matching
source.include_patterns = data/*, static/*, templates/*, etc/*, files/*, home/*

# (list) Source files to exclude (let empty to don't exclude anything)
source.exclude_exts = spec

# (list) List of directory to exclude (let empty to not exclude anything)
source.exclude_dirs = tests, bin, venv, build, dist, .git

# (list) List of exclusions using pattern matching
source.exclude_patterns = license,images/*/*.py

# (int) Port number to specify user port
# This port is used for the webview
webview_port = 8000

[app:android]

# (bool) Indicate if the application should be fullscreen or not
fullscreen = 0

# (string) Supported orientation (landscape, portrait or all)
orientation = portrait

# (list) Permissions
android.permissions = INTERNET,ACCESS_NETWORK_STATE,WRITE_EXTERNAL_STORAGE,READ_EXTERNAL_STORAGE

# (int) Target Android API, should be as high as possible.
android.api = 31

# (int) Minimum API your APK will support.
android.minapi = 21

# (int) Android SDK version to use
android.sdk = 31

# (str) Android NDK version to use
android.ndk = 23b

# (bool) Use --private data storage (True) or --dir public storage (False)
android.private_storage = True

# (str) Android app theme, default is ok for Kivy-based app
android.theme = "@android:style/Theme.NoTitleBar"

# (bool) Copy library instead of making a libpymodules.so
android.copy_libs = 1

# (str) The Android arch to build for, choices: armeabi-v7a, arm64-v8a, x86, x86_64
android.archs = arm64-v8a,armeabi-v7a

# (bool) Enable AndroidX support
android.enable_androidx = True

# (list) Pattern to whitelist for the whole project
android.whitelist = lib-dynload/termios.so

[buildozer]

# (int) Log level (0 = error, 1 = info, 2 = debug (with command output))
log_level = 2

# (int) Display warnings (1) or not (0)
warn_on_root = 1
