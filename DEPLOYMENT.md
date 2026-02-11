# Deployment Guide - Vulnerable E-Commerce Lab Platform

## ⚠️ IMPORTANT SECURITY WARNING

**THIS APPLICATION CONTAINS INTENTIONAL SECURITY VULNERABILITIES FOR EDUCATIONAL PURPOSES ONLY.**

- **DO NOT** deploy this to a public-facing production environment
- **DO NOT** use real user data or credentials
- **ONLY** deploy in isolated, controlled environments (local networks, VMs, containers)
- This is designed for security training and penetration testing practice

---

## Deployment Options

### Option 1: Local Development (Recommended for Testing)

#### Prerequisites

- Python 3.8 or higher
- pip (Python package manager)

#### Steps

1. **Clone/Navigate to the project directory**

   ```bash
   cd "E:\AS LAb\vulnerable_ecommerce"
   ```

2. **Create a virtual environment (recommended)**

   ```bash
   python -m venv venv

   # On Windows
   venv\Scripts\activate

   # On Linux/Mac
   source venv/bin/activate
   ```

3. **Install dependencies**

   ```bash
   pip install flask
   ```

4. **Run the application**

   ```bash
   python app.py
   ```

5. **Access the application**
   - Open browser: `http://127.0.0.1:5000`
   - Or: `http://localhost:5000`

---

### Option 2: Docker Deployment (Isolated Environment)

#### Prerequisites

- Docker installed
- Docker Compose (optional)

#### Create Dockerfile

Create a file named `Dockerfile` in the project root:

```dockerfile
FROM python:3.10-slim

WORKDIR /app

# Copy application files
COPY . /app

# Install dependencies
RUN pip install --no-cache-dir flask

# Expose port
EXPOSE 5000

# Set environment variables
ENV FLASK_APP=app.py
ENV FLASK_ENV=development

# Run the application
CMD ["python", "app.py"]
```

#### Build and Run

```bash
# Build the Docker image
docker build -t vulnerable-ecommerce .

# Run the container
docker run -p 5000:5000 vulnerable-ecommerce

# Access at http://localhost:5000
```

#### Using Docker Compose (Optional)

Create `docker-compose.yml`:

```yaml
version: "3.8"

services:
  web:
    build: .
    ports:
      - "5000:5000"
    volumes:
      - .:/app
    environment:
      - FLASK_ENV=development
    restart: unless-stopped
```

Run with:

```bash
docker-compose up
```

---

### Option 3: Network Deployment (Lab Environment)

For deploying to a local network for multiple students:

#### Using Gunicorn (Production-like server)

1. **Install Gunicorn**

   ```bash
   pip install gunicorn
   ```

2. **Update app.py** - Change the last line from:

   ```python
   app.run(debug=True)
   ```

   to:

   ```python
   app.run(host='0.0.0.0', port=5000, debug=True)
   ```

3. **Run with Gunicorn**

   ```bash
   gunicorn -w 4 -b 0.0.0.0:5000 app:app
   ```

4. **Access from other machines**
   - Find your IP: `ipconfig` (Windows) or `ifconfig` (Linux/Mac)
   - Access from other devices: `http://YOUR_IP:5000`

#### Firewall Configuration (Windows)

```powershell
# Allow inbound connections on port 5000
New-NetFirewallRule -DisplayName "Flask Lab App" -Direction Inbound -LocalPort 5000 -Protocol TCP -Action Allow
```

---

### Option 4: Cloud Deployment (For Controlled Access)

⚠️ **Only deploy with proper access controls and monitoring**

#### Heroku Deployment

1. **Create `requirements.txt`**

   ```
   Flask==2.3.0
   gunicorn==21.2.0
   ```

2. **Create `Procfile`**

   ```
   web: gunicorn app:app
   ```

3. **Update app.py** - Remove the `if __name__ == '__main__':` block or change to:

   ```python
   if __name__ == '__main__':
       app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
   ```

4. **Deploy to Heroku**
   ```bash
   heroku login
   heroku create your-lab-name
   git init
   git add .
   git commit -m "Initial deployment"
   git push heroku main
   ```

#### AWS EC2 / DigitalOcean / VPS

1. **Set up a Linux server** (Ubuntu recommended)

2. **Install dependencies**

   ```bash
   sudo apt update
   sudo apt install python3 python3-pip
   pip3 install flask gunicorn
   ```

3. **Upload your application**

   ```bash
   scp -r vulnerable_ecommerce user@server-ip:/home/user/
   ```

4. **Run with systemd service**

   Create `/etc/systemd/system/vulnerable-ecommerce.service`:

   ```ini
   [Unit]
   Description=Vulnerable E-Commerce Lab
   After=network.target

   [Service]
   User=www-data
   WorkingDirectory=/home/user/vulnerable_ecommerce
   ExecStart=/usr/local/bin/gunicorn -w 4 -b 0.0.0.0:5000 app:app
   Restart=always

   [Install]
   WantedBy=multi-user.target
   ```

   Enable and start:

   ```bash
   sudo systemctl enable vulnerable-ecommerce
   sudo systemctl start vulnerable-ecommerce
   ```

5. **Set up Nginx reverse proxy** (optional)

   ```nginx
   server {
       listen 80;
       server_name your-domain.com;

       location / {
           proxy_pass http://127.0.0.1:5000;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
       }
   }
   ```

---

## Security Recommendations for Deployment

### 1. Network Isolation

- Deploy on an isolated network/VLAN
- Use VPN access for remote students
- Implement firewall rules to restrict access

### 2. Access Control

- Add basic authentication if needed
- Use IP whitelisting
- Monitor access logs

### 3. Data Protection

- Use dummy/fake data only
- Regularly reset the database
- Don't store sensitive information

### 4. Monitoring

- Enable logging
- Monitor for unusual activity
- Set up alerts for excessive requests

### 5. Documentation

- Clearly label as "INTENTIONALLY VULNERABLE"
- Provide usage guidelines to students
- Include ethical hacking policies

---

## Recommended Deployment for Educational Use

**Best Practice: Docker + Local Network**

```bash
# 1. Build Docker image
docker build -t vuln-ecommerce-lab .

# 2. Run on specific network
docker run -d \
  --name ecommerce-lab \
  -p 5000:5000 \
  --restart unless-stopped \
  vuln-ecommerce-lab

# 3. Access at http://YOUR_IP:5000
```

---

## Troubleshooting

### Port Already in Use

```bash
# Windows - Find process using port 5000
netstat -ano | findstr :5000
taskkill /PID <PID> /F

# Linux/Mac
lsof -i :5000
kill -9 <PID>
```

### Database Issues

```bash
# Reset database
rm ecommerce.db
python app.py  # Will recreate on startup
```

### Permission Errors

```bash
# Linux/Mac - Fix permissions
chmod +x app.py
chown -R $USER:$USER .
```

---

## Post-Deployment Checklist

- [ ] Application accessible from intended devices
- [ ] All labs (1-8) loading correctly
- [ ] Burp Suite can intercept requests
- [ ] Database initializes properly
- [ ] File uploads working (Lab 5)
- [ ] Command injection endpoints responding (Lab 6)
- [ ] SQL injection vulnerable (Lab 7)
- [ ] XSS payloads executing (Lab 8)
- [ ] Access restricted to authorized users only
- [ ] Monitoring/logging enabled

---

## Support & Maintenance

### Regular Tasks

- Clear uploaded files: Delete `uploads/` directory contents
- Reset database: Delete `ecommerce.db`
- Check logs for errors
- Update dependencies periodically

### Backup

```bash
# Backup database
cp ecommerce.db ecommerce_backup_$(date +%Y%m%d).db

# Backup uploads
tar -czf uploads_backup_$(date +%Y%m%d).tar.gz uploads/
```

---

## Contact & Resources

- **Burp Suite**: https://portswigger.net/burp
- **OWASP Top 10**: https://owasp.org/www-project-top-ten/
- **Web Security Academy**: https://portswigger.net/web-security

---

**Remember: This is for EDUCATIONAL PURPOSES ONLY. Use responsibly and ethically.**
