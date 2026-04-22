```text
 ██╗   ██╗██╗   ██╗██╗     ███╗   ██╗███████╗ ██████╗ ██████╗ ███╗   ███╗██╗      █████╗ ██████╗ ███████╗
 ██║   ██║██║   ██║██║     ████╗  ██║██╔════╝██╔════╝██╔═══██╗████╗ ████║██║     ██╔══██╗██╔══██╗██╔════╝
 ██║   ██║██║   ██║██║     ██╔██╗ ██║█████╗  ██║     ██║   ██║██╔████╔██║██║     ███████║██████╔╝███████╗
 ╚██╗ ██╔╝██║   ██║██║     ██║╚██╗██║██╔══╝  ██║     ██║   ██║██║╚██╔╝██║██║     ██╔══██║██╔══██╗╚════██║
  ╚████╔╝ ╚██████╔╝███████╗██║ ╚████║███████╗╚██████╗╚██████╔╝██║ ╚═╝ ██║███████╗██║  ██║██████╔╝███████║
   ╚═══╝   ╚═════╝ ╚══════╝╚═╝  ╚═══╝╚══════╝ ╚═════╝ ╚═════╝ ╚═╝     ╚═╝╚══════╝╚═╝  ╚═╝╚═════╝ ╚══════╝
```

# VulneCom Platform: Advanced Cybersecurity Laboratory

Welcome to the **VulneCom Platform** (formerly AS Lab), a sophisticated, multi-layered vulnerable e-commerce environment designed for hands-on cybersecurity training, penetration testing, and secure coding practice.

## 🚀 Overview

VulneCom is a purpose-built Flask application that simulates a real-world e-commerce ecosystem. It contains intentional security vulnerabilities ranging from classic OWASP Top 10 issues to complex architectural flaws. The platform is organized into multiple "Lab Modules," each focusing on specific attack vectors and defensive strategies.

## 🛠️ Technology Stack

- **Backend**: Python 3.9+ / Flask
- **Database**: MongoDB (Primary), SQLite (Legacy/Local)
- **Authentication**: Google OAuth 2.0 Integration
- **Infrastructure**: Vercel ready (Serverless compatible)
- **Security**: Custom middleware for lab-specific authorization and progress tracking

## 🧪 Laboratory Modules

| Lab ID | Focus Area | Description |
| :--- | :--- | :--- |
| **Lab 1** | Injection Attacks | SQLi, NoSQLi, and Command Injection scenarios. |
| **Lab 2** | Broken Authentication | Session hijacking, cookie manipulation, and bypass techniques. |
| **Lab 3** | Data Exposure | IDOR (Insecure Direct Object Reference) and sensitive data leakage. |
| **Lab 4** | XML External Entities | XXE attacks through various file upload and processing vectors. |
| **Lab 5** | Security Misconfig | Insecure defaults, directory listing, and verbose error messages. |
| **Lab 6** | Cross-Site Scripting | Stored, Reflected, and DOM-based XSS vulnerabilities. |
| **Lab 7** | Insecure Deserialization | Exploiting unsafe object reconstruction in Python. |
| **Lab 8** | Vulnerable Components | Exploiting outdated libraries and third-party dependencies. |
| **Lab 9** | Logic Flaws | Business logic bypasses, price manipulation, and checkout exploits. |

## ⚙️ Installation & Setup

### Prerequisites
- Python 3.9 or higher
- MongoDB Atlas account (or local MongoDB instance)
- Google Cloud Console Project (for OAuth)

### Step 1: Clone the Repository
```bash
git clone https://github.com/your-repo/vulnerable_ecommerce.git
cd vulnerable_ecommerce
```

### Step 2: Environment Configuration
Create a `.env` file in the root directory based on `.env.example`:
```env
SECRET_KEY=your_super_secret_key
MONGO_URI=mongodb+srv://user:pass@cluster.mongodb.net/vuln_ecommerce
GOOGLE_CLIENT_ID=your-google-id
GOOGLE_CLIENT_SECRET=your-google-secret
ADMIN_ALERT_EMAILS=admin@example.com
```

### Step 3: Install Dependencies
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### Step 4: Run the Application
```bash
python main.py
```

## 🔐 Security Disclaimer

> [!CAUTION]
> **This application is intentionally vulnerable.**
> Do NOT deploy this application on a production server or expose it to the public internet without proper sandboxing. It is intended for educational purposes only. The authors take no responsibility for any misuse or damage caused by this software.

## 📈 Progress Tracking
The platform includes a built-in progress tracking system. Users can submit "Flags" discovered during their research. Admins can monitor student progress via the administrative dashboard.

## 🤝 Contributing
Contributions are welcome! If you'd like to add a new lab module or improve existing ones, please submit a Pull Request.

---
**Maintained by**: Janmesh Raut
**Project Path**: `e:\AS LAb\vulnerable_ecommerce`
