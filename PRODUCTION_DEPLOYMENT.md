# Production Deployment Guide

This guide will help you deploy the Hotel Management Backend to production.

## Prerequisites

- Python 3.9+
- PostgreSQL 12+
- Tesseract OCR
- Docker & Docker Compose (optional)
- Nginx (recommended for reverse proxy)
- SSL Certificate (for HTTPS)

## 1. Environment Setup

### Copy Environment Template
```bash
cp env.example .env
```

### Configure Production Settings
Edit `.env` file with your production values:

```bash
# Critical Security Settings
ENVIRONMENT=production
DEBUG=false
SECRET_KEY=your-super-secret-key-here-change-in-production
JWT_SECRET_KEY=your-jwt-secret-key-here

# Database (PostgreSQL recommended)
DATABASE_URL=postgresql://username:password@localhost:5432/hotel_management

# CORS (restrict to your domain)
CORS_ALLOW_ORIGINS=https://yourdomain.com,https://www.yourdomain.com

# Email Settings
SMTP_SERVER=smtp.gmail.com
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password
```

## 2. Database Setup

### Install PostgreSQL
```bash
# Ubuntu/Debian
sudo apt update
sudo apt install postgresql postgresql-contrib

# CentOS/RHEL
sudo yum install postgresql postgresql-server postgresql-contrib

# macOS
brew install postgresql
```

### Create Database and User
```sql
CREATE DATABASE hotel_management;
CREATE USER hotel_user WITH PASSWORD 'secure_password';
GRANT ALL PRIVILEGES ON DATABASE hotel_management TO hotel_user;
```

### Run Database Migrations
```bash
# Install Alembic
pip install alembic

# Initialize migrations
alembic init migrations

# Create initial migration
alembic revision --autogenerate -m "Initial migration"

# Apply migrations
alembic upgrade head
```

## 3. Application Deployment

### Option A: Direct Deployment

1. **Install Dependencies**
```bash
pip install -r requirements.prod.txt
```

2. **Start Production Server**
```bash
# Windows
start_production.bat

# Linux/Mac
chmod +x start_production.sh
./start_production.sh
```

### Option B: Docker Deployment

1. **Build and Run**
```bash
docker-compose up -d
```

2. **Check Status**
```bash
docker-compose ps
docker-compose logs -f app
```

## 4. Reverse Proxy Setup (Nginx)

### Install Nginx
```bash
# Ubuntu/Debian
sudo apt install nginx

# CentOS/RHEL
sudo yum install nginx
```

### Configure Nginx
Create `/etc/nginx/sites-available/hotel-management`:

```nginx
server {
    listen 80;
    server_name yourdomain.com www.yourdomain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name yourdomain.com www.yourdomain.com;

    ssl_certificate /path/to/your/certificate.crt;
    ssl_certificate_key /path/to/your/private.key;

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header Referrer-Policy "no-referrer-when-downgrade" always;
    add_header Content-Security-Policy "default-src 'self' http: https: data: blob: 'unsafe-inline'" always;

    # Proxy settings
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_redirect off;
    }

    # Static files
    location /uploads/ {
        alias /path/to/your/app/uploads/;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
}
```

### Enable Site
```bash
sudo ln -s /etc/nginx/sites-available/hotel-management /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

## 5. SSL Certificate Setup

### Let's Encrypt (Free)
```bash
# Install Certbot
sudo apt install certbot python3-certbot-nginx

# Get certificate
sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com

# Auto-renewal
sudo crontab -e
# Add: 0 12 * * * /usr/bin/certbot renew --quiet
```

## 6. System Service Setup

### Create Systemd Service
Create `/etc/systemd/system/hotel-management.service`:

```ini
[Unit]
Description=Hotel Management Backend
After=network.target postgresql.service

[Service]
Type=exec
User=hotel
Group=hotel
WorkingDirectory=/path/to/your/app
Environment=PATH=/path/to/your/venv/bin
ExecStart=/path/to/your/venv/bin/gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 127.0.0.1:8000 --timeout 120 --keep-alive 5
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### Enable Service
```bash
sudo systemctl daemon-reload
sudo systemctl enable hotel-management
sudo systemctl start hotel-management
sudo systemctl status hotel-management
```

## 7. Monitoring and Logging

### Health Checks
- Endpoint: `/health` and `/api/health`
- Monitor response time and status
- Set up alerts for unhealthy status

### Log Management
```bash
# View logs
tail -f logs/app.log

# Log rotation (add to /etc/logrotate.d/hotel-management)
/path/to/your/app/logs/*.log {
    daily
    missingok
    rotate 52
    compress
    delaycompress
    notifempty
    create 644 hotel hotel
    postrotate
        systemctl reload hotel-management
    endscript
}
```

### Performance Monitoring
```bash
# Install monitoring tools
pip install prometheus-fastapi-instrumentator

# Access metrics at /metrics endpoint
```

## 8. Backup Strategy

### Database Backups
```bash
# Create backup script
#!/bin/bash
BACKUP_DIR="/path/to/backups"
DATE=$(date +%Y%m%d_%H%M%S)
pg_dump hotel_management > "$BACKUP_DIR/db_backup_$DATE.sql"

# Add to crontab
# 0 2 * * * /path/to/backup_script.sh
```

### File Backups
```bash
# Backup uploads and models
tar -czf "backups/files_$(date +%Y%m%d_%H%M%S).tar.gz" uploads/ ml_models/
```

## 9. Security Checklist

- [ ] Environment variables properly set
- [ ] Database credentials secured
- [ ] JWT secrets changed from defaults
- [ ] CORS origins restricted
- [ ] HTTPS enabled
- [ ] Firewall configured
- [ ] Regular security updates
- [ ] Database access restricted
- [ ] File permissions set correctly
- [ ] Monitoring and alerting configured

## 10. Troubleshooting

### Common Issues

1. **Database Connection Failed**
   - Check PostgreSQL service status
   - Verify connection string
   - Check firewall settings

2. **Permission Denied**
   - Verify file ownership
   - Check directory permissions
   - Ensure user has proper access

3. **Port Already in Use**
   - Check if another service is using port 8000
   - Use `netstat -tulpn | grep :8000`

4. **SSL Certificate Issues**
   - Verify certificate validity
   - Check Nginx configuration
   - Ensure proper file permissions

### Log Analysis
```bash
# Application logs
tail -f logs/app.log

# System logs
sudo journalctl -u hotel-management -f

# Nginx logs
sudo tail -f /var/log/nginx/error.log
```

## Support

For additional support, check:
- Application logs in `logs/app.log`
- System service logs: `sudo journalctl -u hotel-management`
- Nginx logs: `/var/log/nginx/`
- Database logs: PostgreSQL logs in system journal
