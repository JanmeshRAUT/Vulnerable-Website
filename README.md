# Vulnerable E-Commerce App

A deliberately vulnerable web application for educational purposes.
Based on PortSwigger Web Security Academy concepts.

## ⚠️ WARNING

**DO NOT RUN THIS APPLICATION ON A PUBLIC SERVER.**
It contains severe security vulnerabilities including Remote Code Execution (RCE), SQL Injection, and Path Traversal.
Run strictly on `localhost` or an isolated VM.

## Prerequisites

- Python 3.x

## Installation

1. Navigate to the project directory:
   ```
   cd safe/path/to/vulnerable_ecommerce
   ```
2. Install dependencies:
   ```
   pip install flask requests
   ```

## Usage

1. Run the application:
   ```
   python app.py
   ```
2. Open your browser and go to:
   [http://localhost:5000](http://localhost:5000)

## Labs Included

1. **Path Traversal**: Access sensitive files.
2. **Access Control**: Broken access control and IDOR.
3. **Authentication**: Weak login and enumeration.
4. **SSRF**: Server-Side Request Forgery.
5. **File Upload**: Unrestricted upload of dangerous files.
6. **Command Injection**: OS command execution.
7. **SQL Injection**: Extract database data.

## Note

The database (`database.db`) is automatically created and populated on the first run.
passwords for users:

- admin: admin123
- user: password
- alice: alice123
