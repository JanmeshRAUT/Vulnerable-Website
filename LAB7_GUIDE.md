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

1. Navigate to the PetShop portal. The SQL query retrieves four columns: `name, breed, price, image_url`.
2. First, confirm the number of columns using an `ORDER BY` clause, or simply use the fact we know we need 4 columns.
3. The hidden table is `lab7_admin_creds` which stores `username` and `password`.
4. Submit the following payload into the search bar:
   `Dogs' UNION SELECT username, password, 1, 'https://via.placeholder.com/600x400' FROM lab7_admin_creds--`
5. Note: Make sure there's a space after the double dash `-- `.
6. Hit search. The results will append a new row containing the `username` (administrator) and `password` (which contains the flag `FLAG{union_based_sql_injection_master}`)!

### Variation D: HR Portal (Integer-Based SQLi)

**Objective**: Access the secret CEO information that is restricted from public view.

1. Navigate to the HR Portal, which searches for employees by their integer ID.
2. The URL looks like `/lab7/1/d?id=1`.
3. Because this is an integer-based query, it does NOT use quotes around the parameter in the SQL code. The query looks like: `SELECT * FROM lab7_employees WHERE id = {emp_id} AND is_public = 1`.
4. In the search box or URL, change the ID parameter to: `1 OR 1=1--`
5. Notice that you do not need single quotes!
6. The query becomes: `SELECT * FROM lab7_employees WHERE id = 1 OR 1=1-- AND is_public = 1`.
7. This bypasses the `is_public = 1` check and retrieves all rows, revealing the CEO's restricted data and the flag: `FLAG{integer_sqli_expert}`.
