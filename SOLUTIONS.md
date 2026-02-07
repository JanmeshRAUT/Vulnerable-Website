# 🕵️ Vulnerable E-Commerce - Solutions Guide

This guide details how to exploit each lab using **Burp Suite**.

## 🛠️ Setup

1.  **Configure Proxy**: Set your browser (or Burp's built-in browser) to route traffic through Burp Proxy (usually `127.0.0.1:8080`).
2.  **Turn off Intercept**: Initially keep "Intercept" off in the Proxy tab to browse the site.
3.  **Target**: Access `http://localhost:5000`.

---

## 🟢 Lab 1: Path Traversal

**Goal**: Access sensitive files on the server (e.g., source code).

**Steps with Burp Suite:**

1.  Go to **Lab 1**.
2.  Click any "Download" button.
3.  Go to **Proxy > HTTP History** in Burp.
4.  Find the request: `GET /lab1/download?file=invoice1.txt`.
5.  Right-click -> **Send to Repeater**.
6.  In Repeater, change the `file` parameter value to:
    ```text
    ../../../etc/passwd
    ```
7.  Click **Send**.
8.  **Result**: The response will contain a list of user accounts and "passwords" (simulated /etc/passwd).

---

## 🟢 Lab 2: Access Control (IDOR & Broken Access)

**Goal**: View another user's profile and access the hidden admin panel.

### Part A: IDOR (Insecure Direct Object Reference)

1.  Go to **Lab 2** and click "View Profile (ID: 2)".
2.  **Intercept is ON**: Refresh the page.
3.  Modify the request in the Proxy tab (or send to **Repeater**).
4.  Change the `id` parameter from `2` to `1` (Admin's ID) or `3` (Alice).
    ```http
    GET /lab2/user?id=1 HTTP/1.1
    ```
5.  Forward/Send.
6.  **Result**: You see the Admin's profile details.

### Part B: Broken Access Control

1.  The "Admin Panel" button is disabled/hidden in the UI.
2.  Observe the URL pattern `/lab2/user`.
3.  **Guess** the admin URL (a common technique) or look at source code comments if available.
4.  Try requesting: `GET /lab2/admin` in **Repeater**.
5.  **Result**: You get a 200 OK and the list of all users with passwords, bypassing the "security through obscurity".

---

## 🟠 Lab 3: Authentication

**Goal**: Enumerate a valid username and brute-force the password.

### Step 1: Username Enumeration

1.  Go to **Lab 3**.
2.  Enter a random username (e.g., `test`) and random password.
3.  Send the `POST /lab3` request to **Repeater**.
4.  Observe the error behavior:
    - Invalid User: "User does not exist"
    - Valid User (try `admin`): "Incorrect password"
5.  _Using Intruder (Optional)_:
    - Send request to **Intruder**.
    - Highlight the username value.
    - Load a list of usernames (admin, user, administrator, root).
    - Start Attack. Sort results by "Length" or look for the different error message.

### Step 2: Password Brute Force

1.  Once you know `admin` exists, put `admin` in the username field.
2.  Send the request to **Intruder**.
3.  Highlight the password value.
4.  Load a password list (common passwords like `123456`, `password`, `admin123`).
5.  Start Attack.
6.  **Result**: The payload `admin123` will return a status or length different from the others (Success message).

---

## 🟠 Lab 4: SSRF (Server-Side Request Forgery)

**Goal**: Make the server request an internal resource it shouldn't access.

1.  Go to **Lab 4**.
2.  Enter a URL (e.g., `http://example.com`) and click "Check Stock".
3.  Send the request to **Repeater**:
    ```http
    POST /lab4/check_stock HTTP/1.1
    ...
    stock_api=http://example.com
    ```
4.  Change `stock_api` to an internal URL:
    ```text
    http://localhost:5000/lab2/admin
    ```
5.  **Result**: The application fetches and displays the "Admin Dashboard" content inside the stock check result, confirming SSRF.

---

## 🔴 Lab 5: File Upload

**Goal**: Upload a malicious file.

1.  Go to **Lab 5**.
2.  Create a file named `hack.html` with content: `<h1>HACKED</h1><script>alert(1)</script>`.
3.  Upload the file.
4.  **Intercept** the request to see plain file content being sent.
5.  For a real exploit in a Python/Flask environment without execution of PHP, we aim for **Stored XSS**.
6.  After upload, click the "View File" link.
7.  **Result**: The browser renders your HTML/JS. If this were a PHP server, uploading `shell.php` would give Remote Code Execution (RCE).

---

## 🔴 Lab 6: Command Injection

**Goal**: Execute system commands on the host server.

1.  Go to **Lab 6**.
2.  Enter `8.8.8.8` and click Track.
3.  Send to **Repeater**.
4.  Modify `address` to append a command:
    - **Windows**: `8.8.8.8 && dir` or `8.8.8.8 | whoami`
    - **Linux**: `8.8.8.8 ; ls -la` or `8.8.8.8 && id`
5.  Payload Example:
    ```text
    address=8.8.8.8 && dir
    ```
6.  **Result**: The response contains the directory listing of the server.

---

## 🔴 Lab 7: SQL Injection

**Goal**: Extract data from the database using UNION attacks.

1.  Go to **Lab 7**.
2.  Search for `Mug`.
3.  Send to **Repeater**.
4.  **Determine column count**:
    - `' ORDER BY 1 --` (Works)
    - `' ORDER BY 10 --` (Error)
    - Find exact number (let's say 4).
5.  **Inject UNION payload**:
    - Target query structure: `SELECT * FROM products WHERE name LIKE '%...%'`
    - Payload: `' UNION SELECT 1, username, password, 4, 5, 6 FROM users --`
    - _Note_: Ensure the number of columns in the SELECT matches the visible product table columns (id, name, description, price, image, stock -> 6 columns).
6.  Final Payload to put in Repeater:
    ```text
    search=' UNION SELECT 1, username, password, 4, 'img', 6 FROM users --
    ```
7.  **Result**: The product list will now display usernames and passwords from the `users` table mingled with products.
