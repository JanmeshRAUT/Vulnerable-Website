#!/bin/bash

###############################################################################
# AWS EC2 Deployment Script for Vulnerable E-Commerce Lab
# 
# This script automates the deployment of the vulnerable e-commerce application
# on an Ubuntu EC2 instance.
#
# Usage: 
#   1. Upload this script to your EC2 instance
#   2. Make it executable: chmod +x deploy_ec2.sh
#   3. Run it: ./deploy_ec2.sh
#
# WARNING: This application contains intentional vulnerabilities.
#          Deploy only in controlled environments!
###############################################################################

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
APP_DIR="/home/ubuntu/vulnerable_ecommerce"
APP_USER="ubuntu"
APP_GROUP="ubuntu"
VENV_DIR="$APP_DIR/venv"
SERVICE_NAME="vulnerable-ecommerce"

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Vulnerable E-Commerce Lab Deployment${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# Check if running as root
if [ "$EUID" -eq 0 ]; then 
    echo -e "${RED}Please do not run this script as root${NC}"
    echo "Run as ubuntu user: ./deploy_ec2.sh"
    exit 1
fi

echo -e "${YELLOW}[1/8] Updating system packages...${NC}"
sudo apt update
sudo apt upgrade -y

echo -e "${YELLOW}[2/8] Installing dependencies...${NC}"
sudo apt install -y python3 python3-pip python3-venv nginx git

echo -e "${YELLOW}[3/8] Setting up application directory...${NC}"
if [ ! -d "$APP_DIR" ]; then
    echo -e "${RED}Error: Application directory not found at $APP_DIR${NC}"
    echo "Please upload your application files first or clone from GitHub"
    exit 1
fi

cd "$APP_DIR"

echo -e "${YELLOW}[4/8] Creating Python virtual environment...${NC}"
if [ -d "$VENV_DIR" ]; then
    echo "Virtual environment already exists, removing..."
    rm -rf "$VENV_DIR"
fi

python3 -m venv "$VENV_DIR"
source "$VENV_DIR/bin/activate"

echo -e "${YELLOW}[5/8] Installing Python dependencies...${NC}"
pip install --upgrade pip
pip install -r requirements.txt
pip install gunicorn

echo -e "${YELLOW}[6/8] Setting up systemd service...${NC}"

# Create systemd service file
sudo tee /etc/systemd/system/$SERVICE_NAME.service > /dev/null <<EOF
[Unit]
Description=Vulnerable E-Commerce Lab Application
After=network.target

[Service]
Type=notify
User=$APP_USER
Group=$APP_GROUP
WorkingDirectory=$APP_DIR
Environment="PATH=$VENV_DIR/bin"
ExecStart=$VENV_DIR/bin/gunicorn --workers 3 --bind 127.0.0.1:5000 --timeout 120 app:app
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Reload systemd and enable service
sudo systemctl daemon-reload
sudo systemctl enable $SERVICE_NAME
sudo systemctl start $SERVICE_NAME

echo -e "${YELLOW}[7/8] Configuring Nginx...${NC}"

# Get the public IP of the EC2 instance
PUBLIC_IP=$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4 || echo "localhost")

# Create Nginx configuration
sudo tee /etc/nginx/sites-available/$SERVICE_NAME > /dev/null <<EOF
server {
    listen 80;
    server_name $PUBLIC_IP _;

    # Security headers
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-Frame-Options "SAMEORIGIN" always;

    # Increase client body size for file uploads (Lab 5)
    client_max_body_size 50M;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        
        # Increase timeout for slow requests
        proxy_connect_timeout 120s;
        proxy_send_timeout 120s;
        proxy_read_timeout 120s;
    }

    # Static files optimization
    location /static {
        alias $APP_DIR/static;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }
}
EOF

# Enable the site
sudo ln -sf /etc/nginx/sites-available/$SERVICE_NAME /etc/nginx/sites-enabled/$SERVICE_NAME

# Remove default site if it exists
if [ -f /etc/nginx/sites-enabled/default ]; then
    sudo rm /etc/nginx/sites-enabled/default
fi

# Test Nginx configuration
sudo nginx -t

# Restart Nginx
sudo systemctl restart nginx

echo -e "${YELLOW}[8/8] Verifying deployment...${NC}"

# Check if service is running
if sudo systemctl is-active --quiet $SERVICE_NAME; then
    echo -e "${GREEN}✓ Application service is running${NC}"
else
    echo -e "${RED}✗ Application service failed to start${NC}"
    echo "Check logs with: sudo journalctl -u $SERVICE_NAME -n 50"
    exit 1
fi

# Check if Nginx is running
if sudo systemctl is-active --quiet nginx; then
    echo -e "${GREEN}✓ Nginx is running${NC}"
else
    echo -e "${RED}✗ Nginx failed to start${NC}"
    exit 1
fi

# Test if application is responding
sleep 2
if curl -s http://127.0.0.1:5000 > /dev/null; then
    echo -e "${GREEN}✓ Application is responding${NC}"
else
    echo -e "${RED}✗ Application is not responding${NC}"
    echo "Check logs with: sudo journalctl -u $SERVICE_NAME -n 50"
    exit 1
fi

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Deployment Completed Successfully!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "Application URL: ${GREEN}http://$PUBLIC_IP${NC}"
echo ""
echo "Useful commands:"
echo "  - View logs:        sudo journalctl -u $SERVICE_NAME -f"
echo "  - Restart app:      sudo systemctl restart $SERVICE_NAME"
echo "  - Stop app:         sudo systemctl stop $SERVICE_NAME"
echo "  - Restart Nginx:    sudo systemctl restart nginx"
echo "  - Check status:     sudo systemctl status $SERVICE_NAME"
echo ""
echo -e "${YELLOW}⚠️  SECURITY REMINDER:${NC}"
echo "This application contains intentional vulnerabilities."
echo "Ensure your security group restricts access to authorized IPs only!"
echo ""
