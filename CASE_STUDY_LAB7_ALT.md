# Case Study: Lab 7 - Incident Narrative Edition

## Incident Header

**Program**: Sentinel Commerce Assurance  
**Engagement Type**: Adversarial Validation Drill  
**Quarter**: Q2 2026  
**Risk Rating**: Critical

---

## Situation Brief

A red-team simulation was launched after unusual query behavior was detected in two business surfaces:

- Public catalog filtering endpoints (possible record overexposure)
- Internal employee login portals (possible authentication bypass)

The drill confirms whether SQL-like payload tampering can:

1. Reveal unreleased items in catalog routes (Lab 7.1)
2. Grant admin context in login routes (Lab 7.2)

---

## Threat Storyline

The application treats user input as trusted query fragments.

```python
category = request.args.get('category')
query = f"SELECT * FROM products WHERE category = '{category}'"
```

```python
username = request.form.get('username')
password = request.form.get('password')
query = f"SELECT id, username, role FROM users WHERE username = '{username}' AND password = '{password}'"
```

### Operational Exposure

- Unreleased SKUs become discoverable
- Privileged session context can be forged
- Data access controls are bypassed at query-construction time
- Monitoring appears healthy while logic is already compromised

---

## Lab Execution Map (Aligned to Current Build)

### Track A: Catalog Injection (Lab 7.1)

| Variant | Route | Baseline Input | Injection Payload | Expected Delta |
|---|---|---|---|---|
| A | `/lab7/1` | `Gifts` | `Gifts' OR '1'='1` | Hidden records appear |
| B | `/lab7/1/b` | `Work` | `Work' OR '1'='1` | Hidden records appear |
| C | `/lab7/1/c` | `Adventure` | `Adventure' OR '1'='1` | Hidden records appear |

Completion signal: Variant-specific flag in success banner.

### Track B: Auth Bypass (Lab 7.2)

| Variant Theme | Route | Username Payload | Password | Expected Delta |
|---|---|---|---|---|
| Northstar Office | `/lab7/2/login` | `administrator'--` | any value | Admin context returned |
| Aegis Workforce | `/lab7/2/b/login` | `administrator' --` | any value | Admin context returned |
| Helix Admin Gateway | `/lab7/2/c/login` | `administrator'--` | any value | Admin context returned |

Completion signal: Variant-specific flag + displayed executed query.

---

## Variant Playbooks

## 7.1.A - GiftShop Exposure Path

1. Browse `/lab7/1?category=Gifts`.
2. Confirm only released catalog entries are visible.
3. Replay with `Gifts' OR '1'='1`.
4. Verify unreleased products are now present and capture flag.

## 7.1.B - OfficeCore Exposure Path

1. Browse `/lab7/1/b?category=Work`.
2. Capture baseline product count.
3. Replay with `Work' OR '1'='1`.
4. Verify expanded set includes hidden entries and capture flag.

## 7.1.C - Summit Supply Exposure Path

1. Browse `/lab7/1/c?category=Adventure`.
2. Confirm only publicly released items.
3. Replay with `Adventure' OR '1'='1`.
4. Verify hidden expedition products and capture flag.

## 7.2.A - Northstar Office Login Bypass

1. Open `/lab7/2/login`.
2. Submit a known-invalid normal login to establish failure baseline.
3. Submit username `administrator'--` with any password.
4. Confirm admin profile fields and flag are returned.

## 7.2.B - Aegis Workforce Login Bypass

1. Open `/lab7/2/b/login`.
2. Submit invalid baseline credentials and observe rejection.
3. Submit username `administrator' --` with any password.
4. Confirm admin context, query output, and flag.

## 7.2.C - Helix Admin Gateway Login Bypass

1. Open `/lab7/2/c/login`.
2. Confirm invalid credentials fail.
3. Submit username `administrator'--` with any password.
4. Confirm privileged session view and flag.

---

## Module Boundaries

Active in this build:

- 7.1 variants A-C
- 7.2 variants A-C

Not active in this build:

- 7.1.D standalone exploit route
- 7.3 time-based blind SQLi route

---

## Reporting Format (Required)

Use one record per variant:

```json
{
  "variant": "7.2.B",
  "route": "/lab7/2/b/login",
  "baseline_behavior": "Invalid credentials",
  "payload": "username=administrator' --&password=x",
  "post_payload_behavior": "Admin profile rendered",
  "evidence": "Executed query block displayed",
  "flag": "FLAG{lab7_variation_B_[hash12]}"
}
```

---

## Lab Hardening Plan

### Immediate Controls

1. Replace string-concatenated query assembly with parameter binding.
2. Introduce strict allow-lists for category filters.
3. Enforce credential verification using hash-compare workflows, not inline query composition.

### Detection Controls

1. Alert on patterns like `' OR`, `'--`, and atypical auth payloads.
2. Track response deltas where hidden records suddenly appear.
3. Correlate repeated failed logins followed by bypass-style success.

### Governance Controls

1. Separate low-privilege app DB identities from admin-capable identities.
2. Require review checks for any dynamic query construction.
3. Add automated tests for bypass payloads across all active variants.

---

## Analyst Conclusions

1. Theme/branding changes across 7.2 variants do not change exploitability.
2. Input concatenation remains the root cause for both tracks.
3. Every active variant should be treated as independently exploitable until fixed.
4. Prepared statements and strict input controls are the primary remediation path.
