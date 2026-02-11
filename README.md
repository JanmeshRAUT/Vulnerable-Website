# Vulnerable E-Commerce Lab Platform

A deliberately vulnerable web application for educational purposes, designed for security training and penetration testing practice. Based on PortSwigger Web Security Academy concepts.

## ⚠️ SECURITY WARNING

**THIS APPLICATION CONTAINS INTENTIONAL SECURITY VULNERABILITIES FOR EDUCATIONAL PURPOSES ONLY.**

- **DO NOT** deploy on public servers without proper security controls
- **DO NOT** use real user data or credentials
- **ONLY** use in controlled, isolated environments
- This is designed for security training and ethical hacking practice

---

## 🎯 Features

- **8 Comprehensive Labs** covering major web vulnerabilities
- **Realistic E-Commerce Interface** for practical learning
- **Multiple Deployment Options** (Local, Docker, AWS EC2, Standalone .exe)
- **Burp Suite Compatible** for hands-on penetration testing
- **No Internet Required** for local deployment
- **Easy to Reset** for repeated practice

---

## 📚 Labs Included

1. **Lab 1: Path Traversal** - Access sensitive files outside intended directories
2. **Lab 2: Access Control** - Exploit broken access controls and IDOR vulnerabilities
3. **Lab 3: Authentication** - Practice brute force attacks and user enumeration
4. **Lab 4: SSRF** - Server-Side Request Forgery exploitation
5. **Lab 5: File Upload** - Unrestricted upload of dangerous files
6. **Lab 6: Command Injection** - OS command execution vulnerabilities
7. **Lab 7: SQL Injection** - Extract and manipulate database data
8. **Lab 8: XSS** - Cross-Site Scripting (Reflected and Stored)

Each lab includes multiple variations with different themes and difficulty levels.

---

## 🚀 Deployment Options

### Option 1: Standalone Executable (Easiest for Students) ⭐

**Perfect for:** Distributing to students, no installation needed

```powershell
# Build the .exe (one-time setup)
.\build.bat

# Distribute the file
dist\VulnerableEcommerceLab.exe
```

**Students just double-click the .exe file!**

📖 **Guides:**

- Quick: `QUICKSTART_BUILD_EXE.md`
- Detailed: `BUILD_EXE_GUIDE.md`
- User Instructions: `USER_INSTRUCTIONS.txt`

---

### Option 2: Local Development (Quick Start)

**Perfect for:** Individual practice, development

```bash
# 1. Clone or download the repository
cd vulnerable_ecommerce

# 2. Create virtual environment
python -m venv venv

# 3. Activate virtual environment
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# 4. Install dependencies
pip install -r requirements.txt

# 5. Run the application
python app.py

# 6. Access at http://localhost:5000
```

---

### Option 3: Docker (Isolated Environment)

**Perfect for:** Easy reset, portability, isolation

```bash
# Build the image
docker build -t vuln-ecommerce .

# Run the container
docker run -p 5000:5000 vuln-ecommerce

# Access at http://localhost:5000
```

---

### Option 4: AWS EC2 (Production Labs)

**Perfect for:** Remote access, multiple students, professional setup

```bash
# Quick deployment with automated script
./deploy_ec2.sh

# Access at http://YOUR_EC2_PUBLIC_IP
```

📖 **Guides:**

- Quick: `QUICKSTART_EC2.md`
- Detailed: `AWS_EC2_DEPLOYMENT.md`
- Overview: `AWS_DEPLOYMENT_README.md`

---

### Option 5: Local Network (Classroom)

**Perfect for:** Lab environments, same building

```bash
# Already configured for 0.0.0.0:5000
python app.py

# Students access at http://YOUR_LOCAL_IP:5000
```

---

## 📖 Complete Documentation

### Deployment Guides

- **DEPLOYMENT_OPTIONS.md** - Compare all deployment methods
- **DEPLOYMENT.md** - General deployment guide (Local, Docker, Network, Cloud)
- **AWS_EC2_DEPLOYMENT.md** - Comprehensive AWS EC2 guide
- **QUICKSTART_EC2.md** - Quick AWS EC2 deployment
- **BUILD_EXE_GUIDE.md** - Build standalone Windows executable
- **QUICKSTART_BUILD_EXE.md** - Quick executable build guide

### User Guides

- **USER_INSTRUCTIONS.txt** - Instructions for students using the .exe
- **LAB7_GUIDE.md** - SQL Injection lab guide
- **SOLUTIONS.md** - Lab solutions (for instructors)

### Technical Documentation

- **IMPLEMENTATION_STATUS.md** - Implementation details
- **WEBSITE_IMPROVEMENTS.md** - Design improvements

---

## 🛠️ System Requirements

### For Running (Local/Docker)

- Python 3.8 or higher
- 200 MB free disk space
- Modern web browser
- (Optional) Burp Suite for penetration testing

### For Building Executable

- Windows OS
- Python 3.8+
- PyInstaller (auto-installed by build script)

### For AWS EC2

- AWS Account
- SSH key pair
- Basic Linux knowledge

---

## 🎓 For Instructors

### Quick Setup for Classroom

**Option A: Standalone Executable (Recommended)**

1. Run `build.bat` to create the .exe
2. Distribute `VulnerableEcommerceLab.exe` + `USER_INSTRUCTIONS.txt`
3. Students double-click to run

**Option B: AWS EC2 (Remote Learning)**

1. Launch EC2 instance (Ubuntu 22.04, t2.small)
2. Run `deploy_ec2.sh`
3. Share the URL with students

**Option C: Local Network (Same Building)**

1. Run `python app.py` on instructor machine
2. Share your local IP with students
3. Students access via browser

### Default Credentials

For testing authentication labs:

- **admin** : admin123
- **user** : password
- **alice** : alice123

### Lab Management

```bash
# Reset database
rm database.db
python app.py  # Creates fresh database

# Clear uploaded files (Lab 5)
rm -rf static/lab5/uploads/*

# View logs (if using systemd on Linux)
sudo journalctl -u vulnerable-ecommerce -f
```

---

## 🔒 Security Best Practices

Even though this is intentionally vulnerable:

1. **Network Isolation**: Deploy on isolated networks or VPNs
2. **Access Control**: Use IP whitelisting or VPN access
3. **Dummy Data Only**: Never use real credentials or sensitive data
4. **Monitoring**: Enable logging and monitor for abuse
5. **Time-Limited**: Consider time-limited access for students
6. **Ethical Guidelines**: Educate students on responsible disclosure

---

## 🧪 Using with Burp Suite

1. Configure Burp Suite proxy (127.0.0.1:8080)
2. Configure browser to use Burp proxy
3. Enable intercept in Burp Suite
4. Navigate to the application
5. Intercept and modify HTTP requests
6. Practice exploiting vulnerabilities

---

## 📊 Comparison of Deployment Options

| Method              | Difficulty  | Cost      | Multi-User | Remote Access | Best For                         |
| ------------------- | ----------- | --------- | ---------- | ------------- | -------------------------------- |
| **Standalone .exe** | ⭐ Easy     | Free      | ❌ No      | ❌ No         | Individual students              |
| **Local**           | ⭐ Easy     | Free      | ❌ No      | ❌ No         | Personal practice                |
| **Docker**          | ⭐⭐ Medium | Free      | ❌ No      | ❌ No         | Isolated testing                 |
| **Network**         | ⭐⭐ Medium | Free      | ✅ Yes     | ⚠️ LAN only   | Classroom (same building)        |
| **AWS EC2**         | ⭐⭐⭐ Hard | $20-30/mo | ✅ Yes     | ✅ Yes        | Remote learning, production labs |

---

## 🆘 Troubleshooting

### Application won't start

- Check if port 5000 is already in use
- Verify Python version (3.8+)
- Check if all dependencies are installed

### Database errors

- Delete `database.db` and restart
- Application will recreate it automatically

### Labs not working

- Clear browser cache
- Reset database
- Check console/logs for errors

### Executable issues

- Windows Defender: Click "More info" → "Run anyway"
- Port in use: Close other applications using port 5000

---

## 📞 Support & Resources

- **GitHub**: https://github.com/JanmeshRAUT/Vulnerable-Website
- **Burp Suite**: https://portswigger.net/burp
- **OWASP Top 10**: https://owasp.org/www-project-top-ten/
- **Web Security Academy**: https://portswigger.net/web-security

---

## 🎯 Quick Decision Guide

**Choose your deployment method:**

1. **Distributing to students?** → Build standalone .exe
2. **Just me practicing?** → Local development
3. **Want easy reset?** → Docker
4. **Classroom (same building)?** → Local network
5. **Remote students?** → AWS EC2

---

## ✅ Getting Started Checklist

- [ ] Choose deployment method (see comparison above)
- [ ] Read the relevant deployment guide
- [ ] Set up the application
- [ ] Test Lab 1 to verify setup
- [ ] Configure Burp Suite (optional)
- [ ] Review ethical hacking guidelines
- [ ] Start practicing!

---

## 📝 License & Disclaimer

This application is for **EDUCATIONAL PURPOSES ONLY**.

- Use only in authorized, controlled environments
- Never attack real systems without explicit permission
- Understand that unauthorized hacking is illegal
- Use responsibly and ethically

---

## 🙏 Credits

- Developed for security education and training
- Based on PortSwigger Web Security Academy concepts
- Built with Flask, Python, and modern web technologies

---

**Happy Learning! 🎓🔒**

Remember: With great power comes great responsibility. Use these skills to make the internet safer!
