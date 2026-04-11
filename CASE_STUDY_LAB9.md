# Case Study: Lab 9 - Mobile Binary Analysis & Secret Extraction (VARIANT-WISE)

## Business Context

**Company**: SecureApp Development Corp  
**Role**: Mobile Security Researcher  
**Date**: Q2 2024  
**Severity**: CRITICAL ⚠️

---

## Executive Summary

SecureApp now exposes a single mobile-binary analysis workflow. The current build does not use the variant-wise Lab 9.1/9.2/9.3/9.4 route structure shown later in this document. Instead, the active flow is:

1. Open the analyzer at `/lab9`
2. Optionally download the bundled sample APK from `/lab9/sample`
3. Upload an APK to `/lab9/analyze`
4. Review `package_name`, `binary_hash`, `findings`, `archive_contents`, and `flags_found`
5. Export the report with `/lab9/export`

The scanner performs signature-based static analysis on the uploaded binary. It looks for flags, AWS keys, Google API keys, Sentinel Research URLs, Firebase hostnames, IPv4 addresses, and archive markers such as DEX and native libraries.

The sample APK includes a dynamic flag embedded in `res/values/strings.xml`, plus additional mock secrets in `assets/secrets.conf`.

---

## Current Build Alignment

### Active Entry Point
- `/lab9`

### Active Analyzer Endpoint
- `/lab9/analyze`

### Active Export Endpoint
- `/lab9/export`

### Optional Sample Download
- `/lab9/sample`

### Correct Current Workflow
1. Open `/lab9`
2. Download `/lab9/sample` if you need a test APK
3. Upload the APK to `/lab9/analyze`
4. Confirm the scan returns `flags_found` and `findings`
5. Click export or POST the same JSON to `/lab9/export`
6. Save the generated forensic report

### What the Current Build Actually Detects
- `FLAG{...}` values in the binary stream
- `AKIA...` AWS keys
- `AIza...` Google or Maps keys
- `https://*.sentinel-research.io...` URLs
- `*.firebaseio.com` hostnames
- IPv4 literals
- Presence of `.dex` and `.so` files in the APK archive

### What the Current Build Does Not Require
- JADX decompilation is not required by the app
- Manifest parsing is not required by the app
- Variant-specific routes are not present in the current build

---

# Lab 9.1 - Hardcoded Credentials in Source Code

## Legacy Reference Only

The sections below are historical variant narratives and do not reflect the current code paths. Use the Current Build Alignment section above for the active workflow.

## Variant 9.1 A: Plaintext Database Credentials in Code

### Problem Statement
The Android developer hardcoded database credentials directly into the Java source:
```java
public class DatabaseConfig {
    static final String DB_HOST = "admin.internal.database.company.com";
    static final String DB_USER = "admin";
    static final String DB_PASS = "SuperSecret123!Admin";
}
```
After compilation to DEX format and APK packaging, these strings remain in the binary, just obfuscated by the DEX format (not encrypted). When decompiled with JADX or apktool, all strings are immediately visible.

### Vulnerability Description
String literals in Java source are compiled into the DEX bytecode as plaintext string constants. Decompilation exposes them exactly as written.

### Extraction Steps
1. Download the APK file
2. Use JADX to decompile: `jadx application.apk -d output/`
3. Search for database-related strings in source files
4. Find: `DatabaseConfig.java` with credentials
5. Extract: admin / SuperSecret123!Admin

### Flag
```
FLAG!lab9_1a_[hash]
```

---

## Variant 9.1 B: API Keys in BuildConfig

### Problem Statement
Android developers often put build-time constants in the `BuildConfig` class:
```java
public class BuildConfig {
    public static final String API_KEY = "sk_live_abcd1234efgh5678ijkl";
    public static final String API_SECRET = "secret_9876543210abcdefghijkl";
}
```
These are compiled into the APK and exposed during decompilation. While "BuildConfig" suggests this is for builds, the final compiled values are embedded in the release binary.

### Vulnerability Description
Build configuration constants are hardcoded into bytecode. Even "dynamic" values (set at compile time) become static strings in the APK.

### Extraction Steps
1. Decompile APK with JADX
2. Search for `BuildConfig.java`
3. Find API key and secret constants
4. Use them to make authenticated API requests

### Flag
```
FLAG!lab9_1b_[hash]
```

---

## Variant 9.1 C: Encryption Keys Embedded for "Security"

### Problem Statement
Developer thought: "Let's encrypt sensitive data!" But then embedded the encryption key in the same APK:
```java
public class CryptoUtils {
    private static final String ENCRYPTION_KEY = "MySecretKey12345";
    
    public static String decrypt(String encrypted) {
        // Uses ENCRYPTION_KEY from above
    }
}
```
The "security" is completely negated because the key is in the same binary. Anyone decompiling gets both the encrypted data AND the key needed to decrypt it.

### Vulnerability Description
Encryption key is hardcoded in the APK alongside encrypted data. The security is illusory because both components are in the same package.

### Extraction Steps
1. Decompile APK
2. Find encryption key in source
3. Find encrypted strings or data
4. Decrypt using the embedded key
5. Obtain plaintext secrets

### Flag
```
FLAG!lab9_1c_[hash]
```

---

# Lab 9.2 - Secrets in Android Manifest

## Variant 9.2 A: Firebase Config & Third-Party Keys

### Problem Statement
The `AndroidManifest.xml` contains Firebase configuration and third-party service keys:
```xml
<meta-data
    android:name="com.google.android.gms.version"
    android:value="@integer/google_play_services_version" />
    
<meta-data
    android:name="com.google.firebase.provider.DATABASE_URL"
    android:value="https://myapp-abc123.firebaseio.com" />
    
<meta-data
    android:name="com.stripe.api_key"
    android:value="sk_live_xxxxxxxxxxxxxx" />
```
The manifest is plaintext XML in the APK. These API keys and URLs are immediately accessible without decompilation.

### Vulnerability Description
AndroidManifest.xml is human-readable XML embedded in the APK. Any metadata, keys, or configuration values are plaintext.

### Extraction Steps
1. Extract APK: `unzip application.apk`
2. Read `AndroidManifest.xml` directly (it's XML)
3. Find all `<meta-data>` tags
4. Extract Firebase URL, API keys, service credentials
5. Use them to access services (Firebase database, Stripe payments, etc.)

### Flag
```
FLAG!lab9_2a_[hash]
```

---

## Variant 9.2 B: Deep Links with Internal Endpoints

### Problem Statement
The manifest defines deep links (for app linking):
```xml
<activity android:name=".AdminPanelActivity">
    <intent-filter android:label="@string/app_name">
        <action android:name="android.intent.action.VIEW" />
        <category android:name="android.intent.category.DEFAULT" />
        <category android:name="android.intent.category.BROWSABLE" />
        <data android:scheme="app" 
              android:host="admin" 
              android:path="/panel" />
    </intent-filter>
</activity>
```
Additionally, the manifest might reveal internal service endpoints:
```xml
<service android:name=".backend.AdminService"
    android:exported="true">
```
These expose internal API endpoints and admin functionality locations.

### Vulnerability Description
Intent filters and service declarations in manifest reveal application architecture, admin endpoints, and deep link paths without needing decompilation.

### Extraction Steps
1. Extract APK
2. Parse `AndroidManifest.xml`
3. Find all `<intent-filter>`, `<service>`, and `<activity>` declarations
4. Extract deep link schemes and hosts
5. Discover internal API paths and admin panel locations
6. Access using discovered paths

### Flag
```
FLAG!lab9_2b_[hash]
```

---

# Lab 9.3 - Metadata & Resource Extraction

## Variant 9.3 A: Developer Information in Binary

### Problem Statement
Debug symbols and metadata left in the APK reveal developer information:
- Source file names: `DatabaseConfig.java`, `UserModel.java`
- Package structure shows the app's architecture
- Developer names in build metadata
- Git commit hashes in build tags
- File paths on developer's machine: `/Users/alice/Projects/SecureApp/src/...`

This metadata is retained when building with debug flags not fully stripped.

### Vulnerability Description
Symbols, file paths, and source metadata remain in compiled binary (DEX) if not stripped. Decompilation reveals exact source structure, developer names, and build environment.

### Extraction Steps
1. Decompile APK with JADX
2. Look at class names and package structure
3. Find source file name references (shows architecture)
4. Search for strings like "/Users/", "/home/", "src/"
5. Extract developer paths and information
6. Search for debug logging with exposed endpoints

### Flag
```
FLAG!lab9_3a_[hash]
```

---

## Variant 9.3 B: Embedded Configuration Files

### Problem Statement
The APK's `assets/` folder contains plaintext configuration files:
```
application.apk:
  assets/
    config.json   → Contains API endpoints, database URLs
    keys.xml      → API keys and secrets
    urls.txt      → Internal service URLs
    build_info    → Build date, developer, version details
```
These files are not compiled or protected, just included as-is in the APK.

### Vulnerability Description
Any files in the `assets/` or `res/raw/` folders are included plaintext in the APK. Extraction reveals configuration, URLs, and often embedded secrets.

### Extraction Steps
1. Extract APK: `unzip application.apk`
2. Navigate to `assets/` folder
3. Read plaintext config files
4. Extract API endpoints, database URLs, service secrets
5. Use configuration to target internal services

### Flag
```
FLAG!lab9_3b_[hash]
```

---

# Lab 9.4 - Decompilation & Code Analysis

## Variant 9.4 A: Full Source Reconstruction via JADX

### Problem Statement
Using JADX decompiler on the APK produces near-complete source code reconstruction:
```java
// Source partially obfuscated by ProGuard, but still readable
public class a {
    public static String b = "admin_db_password_12345";
    public static void c(String s) {
        HttpRequest req = new HttpRequest("https://internal-api.company.com/admin");
        req.setAuth(b); // Uses password literal
    }
}
```
Even with some obfuscation (names shortened to a, b, c), the functionality and secrets are visible. Reverse engineers can trace code flow to find credential usage.

### Vulnerability Description
DEX decompilation produces readable Java-like code. Even obfuscated code retains logic, string constants, and data flow, allowing reverse engineers to understand secrets and how they're used.

### Extraction Steps
1. Decompile APK: `jadx application.apk -d output/`
2. Open the project in IDE-like viewer
3. Search for strings like "password", "key", "secret", "token"
4. Trace usage of found credentials
5. Understand how they're used in code
6. Extract and use them

### Flag
```
FLAG!lab9_4a_[hash]
```

---

## Expected Discoveries

- **Variant 9.1A**: Database admin credentials in source
- **Variant 9.1B**: API keys in BuildConfig constants
- **Variant 9.1C**: Encryption key and encrypted data (both accessible)
- **Variant 9.2A**: Firebase and Stripe keys in manifest metadata
- **Variant 9.2B**: Deep links and internal APIs in manifest
- **Variant 9.3A**: Developer paths and debug symbols in binary
- **Variant 9.3B**: Config files with URLs and secrets in assets folder
- **Variant 9.4A**: Full source reconstruction with readable logic and secrets

---

## Tools & Techniques Reference

| Variant | Tool | Technique |
|---------|------|-----------|
| 9.1A, 9.1B, 9.1C | JADX | Decompile DEX → Java source |
| 9.2A, 9.2B | strings, apktool | Parse AndroidManifest.xml |
| 9.3A, 9.3B | unzip, strings | Extract assets, search metadata |
| 9.4A | JADX, bytecode analysis | Full code reconstruction |

---

**Document all extracted secrets and demonstrate their usage.**
├── lib/                 (Native libraries)
└── META-INF/            (Certificates, signatures)
```

**Static Analysis Approach:**
```
1. Extract APK contents
2. Decompile DEX to Java/Smali code
3. Search for hardcoded strings
4. Analyze configurations
5. Extract sensitive data
6. Identify API endpoints
7. Find credentials
```

---

## Challenge 1: APK Extraction & Structure Analysis

### Vulnerability Description

APKs are ZIP archives and can be extracted with standard tools.

### Your Objectives:

**Objective 1: Extract APK Contents**
```bash
# APK is a ZIP file
unzip application.apk -d extracted_apk/

# Or using 7-Zip GUI
7z x application.apk
```

**Objective 2: Examine AndroidManifest.xml**
```xml
<?xml version="1.0" encoding="utf-8"?>
<manifest xmlns:android="http://schemas.android.com/apk/res/android"
    package="com.example.app">
    
    <!-- Permissions reveal app capabilities -->
    <uses-permission android:name="android.permission.INTERNET" />
    <uses-permission android:name="android.permission.READ_CONTACTS" />
    
    <!-- Activities, Services, Receivers -->
    <application>
        <activity android:name=".MainActivity" />
        <service android:name=".ApiService" />
        <!-- Look for exported components that can be accessed externally -->
    </application>
</manifest>
```

**What to look for:**
- Hardcoded URLs/endpoints in manifest
- Exported components (security risk)
- Permissions requested (reveals functionality)
- Meta-data tags (API keys, configuration)

**Objective 3: Inspect Resources**
```
- Strings.xml: Often contains hardcoded strings
- Config files: URLs, API endpoints
- Assets: Encrypted databases, configuration
- Raw resources: Key material, certificates
```

---

## Challenge 2: Decompiling Java Bytecode

### Vulnerability Description

DEX (Dalvik Executable) files contain compiled Java code that can be decompiled back to readable source.

### Decompilation Tools

**CFR / Fernflower / JADX**
```bash
# Using JADX (recommended - best output)
jadx application.apk -o output_source/

# Result: Full Java source code
application/
├── MainActivity.java
├── ApiService.java
├── DatabaseHelper.java
└── Constants.java
```

**Output Example:**
```java
public class Constants {
    public static final String API_KEY = "AIzaSyC1k_Mz-P4...";  // Firebase API key
    public static final String DB_URL = "jdbc:mysql://192.168.1.100/app";
    public static final String DB_USER = "admin";
    public static final String DB_PASSWORD = "SecurePassword123!";
    public static final String ENCRYPTION_KEY = "abc123...";
}
```

### Your Objectives:

**Objective 1: Extract Source Code**
```
Use JADX to decompile entire APK to Java source
```

**Objective 2: Search for Sensitive Strings**
```bash
# In Linux
grep -r "password\|key\|secret\|api\|token" extracted_source/

# Patterns to find:
grep -r "API_KEY\|API_SECRET\|DATABASE_PASSWORD\|ENCRYPTION_KEY"
grep -r "http://\|https://" | grep -v "common URLs"
```

**Objective 3: Identify Hardcoded Credentials**
```java
// Commonly found patterns:
String apiKey = "AIzaSyD...";  // Firebase
String awsKey = "AKIAIOSFODNN...";  // AWS
String dbPassword = "admin123";
String encryptionKey = "0x...";
```

---

## Challenge 3: String Extraction & Analysis

### Vulnerability Description

Even without full decompilation, strings can be extracted from binaries.

### String Extraction Tools

**Using `strings` command:**
```bash
strings application.apk | grep -i "api\|key\|secret\|password"
```

**Using `apktool`:**
```bash
apktool d application.apk
# Extracts resources.arsc, AndroidManifest.xml as readable XML
```

**Output Example:**
```
apiKey: AIzaSyC1k_Mz_P4xvdnm8yQ...
Firebase API key
baseUrl: https://192.168.1.50:8443/api/v2
admin_password: Tr0pic#1
database_name: secureapp_prod
encryption_key: badf00d...
encryption_iv: cafebabe...
```

### Your Objectives:

**Objective 1: Extract All Strings**
```bash
apktool d -r application.apk
# Resumes only, no dex decoding
```

**Objective 2: Search for Patterns**
```bash
# API keys
strings application.apk | grep -E "AIza|AKIA|sk_"

# URLs/Endpoints
strings application.apk | grep -E "http://|https://|jdbc:"

# Common secrets
strings application.apk | grep -iE "password|secret|key|token|credential"
```

**Objective 3: Analyze Firebase Config**
```
Look for google-services.json entries:
- project_id
- API_key
- Database URL
- Storage bucket
```

---

## Challenge 4: Manifest & Configuration Analysis

### Vulnerability Description

AndroidManifest.xml and configuration files contain security-critical information.

### Analysis Steps

**Step 1: Parse AndroidManifest.xml**
```xml
<application
    android:debuggable="true"  <!-- SECURITY ISSUE -->
    android:icon="@drawable/icon">
    
    <!-- Exported components = accessible externally -->
    <activity android:name=".LoginActivity"
        android:exported="true">  <!-- DANGER: Can be launched by other apps -->
    </activity>
    
    <!-- Meta-data with secrets -->
    <meta-data
        android:name="com.google.firebase.ml.vision.DEPENDENCIES"
        android:value="com.google.firebase.ml.vision.internal.vkp" />
</application>
```

**Step 2: Check for Debuggable Flag**
```xml
<!-- If android:debuggable="true" in non-debug build = critical issue -->
<!-- Allows full app debugging, execution as app user -->
```

**Step 3: Analyze Data Storage**
```
Look for:
- SharedPreferences (often unencrypted)
- SQLite databases (credentials stored?)
- Files in app directory
- Environment variables
```

### Your Objectives:

**Objective 1: Examine Manifest**
- [ ] Check debuggable flag
- [ ] List all activities/services
- [ ] Identify exported components
- [ ] Find meta-data entries
- [ ] Extract permissions

**Objective 2: Analyze Configuration Files**
- [ ] Read resources.arsc
- [ ] Extract strings.xml
- [ ] Find config XML files in assets/
- [ ] Look for hardcoded URLs

**Objective 3: Identify Security Issues**
- [ ] Debuggable build
- [ ] Exported components
- [ ] Hardcoded credentials
- [ ] Internal URLs exposed
- [ ] Debug symbols present

---

## Challenge 5: Native Code & Assets

### Vulnerability Description

Native libraries (C/C++) and asset files may contain additional secrets.

### Analysis Approach

**Native Libraries (lib/ folder):**
```bash
# Extract native libraries
find extracted_apk/lib -name "*.so"

# Analyze with objdump (if available)
objdump -d libnative.so | grep -A20 "function_name"

# String extraction
strings extracted_apk/lib/armeabi-v7a/libnative.so | grep -i "key\|password"
```

**Asset Files:**
```bash
# Check assets/ directory
ls -la extracted_apk/assets/

# Common findings:
- config.json (API endpoints, credentials)
- test_data.db (database with sample data)
- keys.xml (encryption keys)
- server.crt (SSL certificates)
```

---

## Lab 9 Workflow

### Phase 1: Acquisition
```
1. Download APK (provided as test file)
   OR
2. Download from app store (if real app testing)
```

### Phase 2: Extraction
```
1. Extract APK using unzip or apktool
2. Examine directory structure
3. Identify interesting files
```

### Phase 3: Decompilation
```
1. Decompile DEX using JADX
2. Generate source code
3. Open in IDE for analysis
```

### Phase 4: Analysis
```
1. Search for hardcoded strings
2. Look for:
   - API_KEY, API_SECRET
   - DATABASE credentials
   - ENCRYPTION keys
   - Internal URLs
   - Endpoints
3. Extract all findings
```

### Phase 5: Exploitation
```
1. Use extracted credentials to access:
   - Backend APIs
   - Databases
   - Admin panels
2. Confirm validity of secrets
3. Document security impact
```

### Phase 6: Reporting
```
1. List all extracted secrets
2. Categorize by severity
3. Suggest remediation
4. Submit findings
```

---

## Tools & Utilities

### Primary Tools

| Tool | Purpose | Command |
|------|---------|---------|
| **apktool** | Decompile APK | `apktool d app.apk` |
| **JADX** | Decompile DEX→Java | `jadx app.apk -o src/` |
| **strings** | Extract text strings | `strings app.apk \| grep key` |
| **unzip** | Extract APK | `unzip app.apk` |
| **adb** | Android Debug Bridge | `adb install app.apk` |

### Online Tools

- **APKtool GUI** - Decompile without CLI
- **Frida** - Dynamic analysis & hook functions
- **Burp Suite Mobile** - Network interception
- **MobSF** - Mobile Security Framework (automated analysis)

### Search Patterns

```bash
# API Keys
grep -r "AIza\|AKIA\|sk_live\|sk_test"

# Database URLs
grep -r "jdbc:\|postgresql://\|mysql://\|mongodb://"

# Passwords & Secrets
grep -r "password\|passwd\|pwd\|secret"

# Encryption Keys
grep -r "0x[0-9a-f]\|[A-F0-9]\{32\}"

# URLs/Endpoints
grep -r "http://\|https://" | grep -v "common domains"

# Firebase
grep -r "firebaseapp\|firestore\|realtime\|database.rules"
```

---

## Expected Findings

### Lab 9 Extract Types

**Type 1: API Keys**
```
Firebase API Key: AIzaSyC1k_Mz-P4xvdnm8yQc...
AWS Access Key: AKIAIOSFODNN7EXAMPLE
Google Maps API: AIzaSyC...
```

**Type 2: Database Credentials**
```
Database Host: 192.168.1.100
Database Name: secureapp_prod
Database User: admin
Database Password: SuperSecret123!
```

**Type 3: Internal URLs**
```
Backend API: https://api.internal.company.com
Admin Panel: https://admin.192.168.1.50:8443
Database Server: jdbc:mysql://192.168.1.100:3306/app
```

**Type 4: Encryption Keys**
```
Encryption Key: badf00dcafebabe...
Encryption IV: 0123456789abcdef...
```

**Type 5: Debug Information**
```
Debuggable: true
Build Path: /home/developer/projects/SecureApp
Build Timestamp: 2024-01-15 14:23:45
Developer Email: dev@company.com
```

---

## Security Impact

### Risks of Exposed Secrets

```
API Keys + Backend URL
    ↓ Attacker
    ↓ Can make unlimited API requests
    ↓ Can enumerate users, modify data
    ↓ Potential DDoS amplification
    ↓ Cost overruns for API usage
```

```
Database Credentials
    ↓ Attacker
    ↓ Direct database access
    ↓ Extract entire user database (PII)
    ↓ Malicious data modification
    ↓ Complete system compromise
```

```
Encryption Keys
    ↓ Attacker
    ↓ Decrypt "secure" data
    ↓ Impersonate users
    ↓ Forge transactions
    ↓ Authentication bypass
```

---

## Prevention & Hardening

### ✅ Never Hardcode Secrets
```java
// WRONG
String apiKey = "sk_live_123...";

// RIGHT
String apiKey = loadFromSecureStorage();  // System KeyStore
```

### ✅ Use Android Keystore
```java
// Secure storage for keys
KeyStore keyStore = KeyStore.getInstance("AndroidKeyStore");
keyStore.load(null);
SecretKey key = (SecretKey) keyStore.getKey("key_alias", null);
```

### ✅ Remove Debug Information
```bash
# Disable debuggable in release build
<!-- AndroidManifest.xml -->
android:debuggable="false"

# Strip symbols from native libraries
arm-linux-gnueabi-strip libexample.so
```

### ✅ Configure Proguard/R8 Obfuscation
```
# proguard-rules.pro
-keepclassmembernames class * {
    java.lang.String *;
}
```

### ✅ Implement API Key Rotation
```
- Store keys server-side, not client
- Issue short-lived tokens
- Rotate regularly
- Revoke compromised keys quickly
```

### ✅ Code Obfuscation
```
- Makes decompiled code harder to read
- Doesn't prevent extraction but increases effort
- Use ProGuard, R8, DexGuard
```

---

## Mitigation Checklist

- [ ] Remove all hardcoded credentials
- [ ] Use secure storage (Keystore)
- [ ] Disable debuggable flag in release
- [ ] Implement API token system (not keys)
- [ ] Obfuscate sensitive code
- [ ] Strip debug symbols
- [ ] Use encryption for sensitive strings
- [ ] Implement certificate pinning
- [ ] Log access to sensitive data
- [ ] Regular security audits

---

## Real-World Examples

**Uber (2015)**: Hardcoded API keys in APK allowed attacker access to backend
**Snapchat**: Various hardcoded credentials found in APKs
**Major Banks**: Encryption keys exposed in mobile apps
**Many AWS**: Exposed API keys from APKs = infrastructure compromise

---

## Key Takeaways

1. **Mobile apps are decompilable** - Never assume binary safety
2. **Secrets must be external** - Fetch at runtime from secure backend
3. **Defense in depth** - Obfuscation + Encryption + Secure storage
4. **Monitor for key exposure** - Scan GitHub, APK stores regularly
5. **Rotate secrets** - Keys can't protect if they're public
6. **Principle of least privilege** - App shouldn't have admin credentials
7. **Code review is critical** - Don't hardcode even in development

---

## Related Concepts

- **CWE-798**: Use of Hard-Coded Credentials
- **CWE-259**: Use of Hard-Coded Password
- **OWASP Mobile**: M02 Insecure Data Storage
- **OWASP Mobile**: M10 Extraneous Functionality
- **Android Security**: Secure Coding Guidelines

---

## Flag Submission Checklist

- [ ] Downloaded/accessed APK file
- [ ] Extracted APK contents
- [ ] Decompiled source code
- [ ] Searched for hardcoded secrets
- [ ] Found API keys/credentials
- [ ] Identified internal URLs/endpoints
- [ ] Found database credentials
- [ ] Located encryption keys
- [ ] Documented all findings
- [ ] Submitted extracted secrets/flag

---

**Document all extracted secrets, their locations in code, and security impact. Security review requires complete inventory of exposed data.**
