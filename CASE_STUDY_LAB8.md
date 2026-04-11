# Case Study: Lab 8 - Cross-Site Scripting (XSS)

## Business Context

**Company**: SocialFlow Media Platform  
**Role**: Frontend Security Tester  
**Date**: Q2 2026  
**Severity**: HIGH ⚠️

---

## Executive Summary

Module 8 currently runs two active XSS tracks:

- **Lab 8.1: Reflected XSS (A-E variants)**
- **Lab 8.2: Stored XSS (profile workflow)**

In Lab 8.1, each variant reflects a different input field back into rendered output and uses server-side payload pattern checks to confirm likely execution contexts.  
In Lab 8.2, profile values are stored without sanitization and then rendered with unsafe template output, enabling stored script execution.

Your task is to trigger variant-specific payload behavior and capture the generated flag responses.

---

## Business Problem

The application accepts user input and renders it in browser-visible views without complete contextual sanitization.

### Current Implementation Issues
1. User-controlled values are reflected in live UI previews across multiple flows.
2. XSS detection logic relies on pattern matching instead of safe output encoding.
3. Variant completion flags are generated when dangerous payload patterns are detected.
4. Stored profile fields in Lab 8.2 are rendered with unsafe template output.

---

## Challenge: Lab 8.1 - Reflected XSS (A-E)

### Problem Statement

Lab 8.1 uses five themed variants with distinct input fields and reflected render surfaces. Each variant checks for active XSS payload markers and issues a variation-specific Lab 8 flag when matched.

### Shared Trigger Patterns in Current Code

`check_xss_payload()` accepts payloads containing one or more of:

- `<script`
- `onerror=`
- `onload=`
- `onclick=`
- `javascript:`
- `"; fetch`
- `'; fetch`

Variant **C** also accepts:

- `"; alert`
- `'; alert`
- `";prompt`
- `';prompt`
- `";confirm`
- `';confirm`

### Flag Endpoint

Successful payloads may call:

```http
GET /xss-success?variant=A|B|C|D|E
```

Response:

```json
{
  "success": true,
  "flag": "FLAG{lab8_variation_X_[hash12]}",
  "message": "XSS Payload Executed Successfully on Variant X!"
}
```

---

## Variant 8.1 A: TechCorp Employee Portal

### Route
- `/lab8/1/a/search`

### Input Field
- `search_query`

### Problem Statement
Search queries are reflected in the search preview and response panel.

### Exploitation Steps
1. Open `/lab8/1/a/login` and sign in with any non-empty username and password.
2. Go to `/lab8/1/a/search`.
3. Submit a payload in `search_query`, for example:
   ```html
   <script>alert('xss')</script>
   ```
4. Confirm the "Script Execution Successful" state.
5. Capture the flag shown in the variant result panel.

### Expected Result
- Payload detection enabled.
- Variation A flag generated via `get_random_flag('lab8', variation='variation_A')`.

---

## Variant 8.1 B: PixelArt Marketplace

### Route
- `/lab8/1/b/upload`

### Input Field
- `image_alt`

### Problem Statement
Image metadata (alt-style input) is reflected in preview output and can trigger attribute/event payload patterns.

### Exploitation Steps
1. Open `/lab8/1/b/login` and sign in with any non-empty seller name and password.
2. Go to `/lab8/1/b/upload`.
3. Submit payload in `image_alt`, for example:
   ```text
   " onerror="alert('xss')" x="
   ```
4. Submit upload form (`upload_btn`).
5. Confirm "Metadata Injection Success" and capture the displayed flag.

### Expected Result
- Variation B flag generated via `get_random_flag('lab8', variation='variation_B')`.

---

## Variant 8.1 C: GraphicStudio

### Route
- `/lab8/1/c/create`

### Input Field
- `project_desc`

### Problem Statement
Project metadata is reflected in a JS-like render preview. Variant C explicitly supports string-breakout style markers (`"; alert`, etc.).

### Exploitation Steps
1. Open `/lab8/1/c/login` and sign in with any non-empty designer name and password.
2. Go to `/lab8/1/c/create`.
3. Submit payload in `project_desc`, for example:
   ```text
   "; alert('xss');//
   ```
4. Submit create form (`create_btn`).
5. Confirm "SVG Sync Executed" and capture the displayed flag.

### Expected Result
- Variation C flag generated via `get_random_flag('lab8', variation='variation_C')`.

---

## Variant 8.1 D: SocialHub

### Route
- `/lab8/1/d/myfeed`

### Input Field
- `post_content`

### Problem Statement
Post content is reflected in feed preview and can trigger HTML/event-handler payload detection.

### Exploitation Steps
1. Open `/lab8/1/d/login` and sign in with any non-empty handle and password.
2. Go to `/lab8/1/d/myfeed`.
3. Submit payload in `post_content`, for example:
   ```html
   <img src=x onerror="alert('xss')">
   ```
4. Submit post form (`post_btn`).
5. Confirm "Event Handler Triggered" and capture the displayed flag.

### Expected Result
- Variation D flag generated via `get_random_flag('lab8', variation='variation_D')`.

---

## Variant 8.1 E: DocVault

### Route
- `/lab8/1/e/upload`

### Input Field
- `doc_source`

### Problem Statement
Repository/source input is reflected in link preview and accepts protocol-handler patterns such as `javascript:`.

### Exploitation Steps
1. Open `/lab8/1/e/login` and sign in with any non-empty user value and password.
2. Go to `/lab8/1/e/upload`.
3. Submit payload in `doc_source`, for example:
   ```text
   javascript:alert('xss');void(0)
   ```
4. Submit upload form (`upload_btn`).
5. Confirm "IFrame Containment Breach" and capture the displayed flag.

### Expected Result
- Variation E flag generated via `get_random_flag('lab8', variation='variation_E')`.

---

## Challenge: Lab 8.2 - Stored XSS (Profile Workflow)

### Active Routes
- `/lab8/2`
- `/lab8/2/dashboard`
- `/lab8/2/update`

### Login Credentials
- `test / test`

### Problem Statement
Profile values are stored unsanitized and rendered with unsafe template output (`|safe`) in dashboard views.

### Trigger Logic
A Lab 8.2 flag is generated when any updated field contains:

- `<script>`
- `%3cscript%3e`

Checked fields:

- `full_name`
- `address`
- `email`
- `bio`

### Exploitation Steps
1. Open `/lab8/2`.
2. Login with `test / test`.
3. In profile update form, inject payload into `bio` or `full_name`, for example:
   ```html
   <script>alert('stored-xss')</script>
   ```
4. Submit update to `/lab8/2/update`.
5. Return to `/lab8/2/dashboard` and confirm flag banner appears.

### Expected Result
- Flag generated via `get_random_flag('lab8_2')`.
- Stored payload is reflected in unsafe-rendered profile areas.

---

## Lab 8 Complete Variant Map

```text
Lab 8.1 (Reflected XSS)
├─ Variant A: TechCorp Search Reflection
├─ Variant B: PixelArt Attribute Reflection
├─ Variant C: GraphicStudio JS-String Reflection
├─ Variant D: SocialHub Feed Reflection
└─ Variant E: DocVault URL/Protocol Reflection

Lab 8.2 (Stored XSS)
└─ Profile update + unsafe dashboard rendering
```

---

## Complete Exploitation Workflow

### Phase 1: Access
```text
1. Open /lab8
2. Choose /lab8/1 (A-E) or /lab8/2
3. Authenticate where required
```

### Phase 2: Payload Delivery
```text
Lab 8.1:
- Submit context-specific payload in the variant input field
- Trigger preview/render branch
- Capture variant flag

Lab 8.2:
- Login test/test
- Store script payload in profile fields
- Reload dashboard
- Capture stored XSS flag
```

### Phase 3: Evidence Capture
```text
- Route used
- Parameter/field used
- Payload used
- Execution indicator shown
- Captured flag
```

---

## Expected Discoveries

### Lab 8.1 A-E
```json
{
  "entry_points": [
    "/lab8/1/a/search",
    "/lab8/1/b/upload",
    "/lab8/1/c/create",
    "/lab8/1/d/myfeed",
    "/lab8/1/e/upload"
  ],
  "success_condition": "Payload matches XSS detection patterns",
  "flag_source": "/xss-success or variant response panel",
  "flag_family": "lab8"
}
```

### Lab 8.2
```json
{
  "entry_point": "/lab8/2/update",
  "success_condition": "Stored profile field contains <script> marker",
  "flag_source": "/lab8/2/dashboard",
  "flag_family": "lab8_2"
}
```

---

## Technical Concepts Tested

### Reflected XSS (Lab 8.1)
```text
User input
→ reflected in response/preview context
→ browser interprets dangerous payload
→ XSS condition confirmed
```

### Stored XSS (Lab 8.2)
```text
User input stored without sanitization
→ later rendered with unsafe output
→ script executes on page load/render
```

### Core Lessons
- Context-specific encoding is mandatory.
- Pattern-based blocking is not a complete defense.
- Stored data must be sanitized before unsafe rendering paths.

---

## Recommended Testing Tools

- Browser DevTools (Network + DOM inspection)
- Burp Suite Repeater
- OWASP ZAP
- Manual form replay with crafted payloads

---

## Flag Submission Checklist

- [ ] Chosen active Lab 8 route
- [ ] Identified vulnerable input field
- [ ] Submitted context-valid payload
- [ ] Observed execution/success indicator
- [ ] Captured flag
- [ ] Documented route, payload, and evidence

---

## Real-World Impact

If unresolved in production systems, these issues can lead to:

- Session theft and account takeover
- Unauthorized actions in user context
- Credential and token exfiltration
- Wormable client-side payload spread

---

## Key Takeaways

1. Module 8 currently includes reflected and stored XSS workflows.
2. Lab 8.1 uses variant-specific reflected input surfaces (A-E).
3. Lab 8.2 demonstrates unsanitized persistence and unsafe rendering.
4. Context-aware output encoding and safe DOM APIs are required defenses.
5. Always report route, parameter, payload chain, and captured flag.

---

## Related Security Concepts

- **CWE-79**: Cross-site Scripting (XSS)
- **OWASP A03:2021**: Injection
- **Stored XSS vs Reflected XSS**: Execution timing and persistence differences

---

Document findings per variant with route, field name, payload chain, execution evidence, and captured flag.
