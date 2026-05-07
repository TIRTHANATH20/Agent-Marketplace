# Deployment Guide

## EC2 Instance Setup (Ubuntu 22.04)

### 1. Initial Server Configuration

```bash
# SSH into instance
ssh -i your-key.pem ubuntu@your-ec2-ip

# Update system
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3.10 python3-pip nodejs npm nginx git sqlite3

# Clone repository
git clone https://github.com/TIRTHANATH20/Agent-Marketplace.git
cd Agent-Marketplace
```

### 2. Backend Deployment

```bash
cd backend

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Create production .env
cat > .env << 'ENVEOF'
DATABASE_URL=sqlite:///./marketplace.db
JWT_SECRET_KEY=your-secure-secret-key
ENVIRONMENT=production
FRONTEND_URL=https://your-domain.com
GROQ_API_KEY=optional-api-key
ENVEOF

# Run with gunicorn
pip install gunicorn
gunicorn main:app --workers 4 --bind 0.0.0.0:8000
```

### 3. Frontend Build & Deployment

```bash
cd frontend

# Build production bundle
REACT_APP_API_BASE_URL=https://api.your-domain.com npm run build

# Copy to Nginx
sudo cp -r build/* /var/www/html/
```

### 4. Nginx Configuration

```bash
# Create Nginx config
sudo tee /etc/nginx/sites-available/marketplace << 'NGINXEOF'
upstream backend {
    server localhost:8000;
}

server {
    listen 80;
    server_name your-domain.com;

    # Frontend
    location / {
        root /var/www/html;
        try_files $uri /index.html;
    }

    # API Proxy
    location /api/ {
        proxy_pass http://backend/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
NGINXEOF

# Enable site and reload
sudo ln -s /etc/nginx/sites-available/marketplace /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### 5. SSL/HTTPS (Let's Encrypt)

```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com
```

### 6. Process Management (Systemd)

```bash
# Create service file
sudo tee /etc/systemd/system/marketplace-backend.service << 'SERVICEEOF'
[Unit]
Description=Agent Marketplace Backend
After=network.target

[Service]
Type=notify
User=ubuntu
WorkingDirectory=/home/ubuntu/Agent-Marketplace/backend
Environment="PATH=/home/ubuntu/Agent-Marketplace/backend/venv/bin"
ExecStart=/home/ubuntu/Agent-Marketplace/backend/venv/bin/gunicorn main:app --workers 4 --bind 0.0.0.0:8000

[Install]
WantedBy=multi-user.target
SERVICEEOF

# Start service
sudo systemctl daemon-reload
sudo systemctl start marketplace-backend
sudo systemctl enable marketplace-backend
```

## Monitoring

- **Logs**: `sudo journalctl -u marketplace-backend -f`
- **Status**: `systemctl status marketplace-backend`
- **Nginx**: `sudo tail -f /var/log/nginx/access.log`

## Health Checks

```bash
# Test backend
curl http://localhost:8000/health

# Test frontend
curl http://localhost/
```

## Troubleshooting

**Backend won't start?** → Check `.env` variables
**Frontend shows 404?** → Check Nginx config, ensure build files in `/var/www/html`
**API calls failing?** → Check CORS settings in backend, verify proxy headers
