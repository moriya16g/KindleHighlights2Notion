# AWS Lightsail Deployment Guide

[日本語版](deploy_guide.ja.md)

## 1. Create a Lightsail Instance

1. Log in to the [AWS Lightsail console](https://lightsail.aws.amazon.com/)
2. Click "Create instance"
3. Settings:
   - **Region**: Choose your nearest region (e.g., Tokyo ap-northeast-1)
   - **Platform**: Linux/Unix
   - **Blueprint**: OS Only → **Ubuntu 22.04 LTS**
   - **Plan**: $3.50 USD/month (512MB RAM, 1 vCPU) is sufficient
   - **Instance name**: `kindle-highlights`
4. Click "Create instance"

## 2. Network Configuration

Lightsail Console → Instance → Networking:
- **HTTP (80)** — should be open by default
- **HTTPS (443)** — add this rule
- **Custom TCP 8000** — not needed (nginx proxies requests)

## 3. (Optional) Domain Setup

If you have a custom domain:
- Point a DNS A record to the Lightsail Static IP
- Assign a Static IP in the Lightsail console

You can also use the IP address directly (but HTTPS won't work without a domain).

## 4. SSH Login & Setup

```bash
# Use Lightsail's "Connect using SSH" or your downloaded key
ssh ubuntu@<instance-ip-address>

# Clone the repository
git clone https://github.com/<your-username>/kindle-highlights-notion.git
cd kindle-highlights-notion

# Run the setup script
sudo bash deploy_setup.sh
```

## 5. Configure .env

```bash
sudo nano /opt/kindle-highlights/.env
```

Set the following:
```
HOST=0.0.0.0
PORT=8000
BASE_URL=https://your-domain.com   # Without domain: http://<IP>
BASIC_AUTH_USER=myuser
BASIC_AUTH_PASS=mysecretpassword
```

## 6. Start the Service

```bash
sudo systemctl start kindle-highlights
sudo systemctl status kindle-highlights
```

## 7. Enable HTTPS (if you have a domain)

```bash
sudo certbot --nginx -d your-domain.com
```

Certbot will automatically configure nginx and set up auto-renewal.

## 8. Verify

```bash
# Test locally
curl http://localhost:8000

# Access from browser
# http://<IP> or https://your-domain.com
```

---

## Operations

```bash
# View logs
sudo journalctl -u kindle-highlights -f

# Restart
sudo systemctl restart kindle-highlights

# Stop
sudo systemctl stop kindle-highlights

# Update code
cd ~/kindle-highlights-notion
git pull
sudo cp server.py /opt/kindle-highlights/
sudo systemctl restart kindle-highlights

# Backup data
sudo cp -r /opt/kindle-highlights/data ~/backup-data
```

## Troubleshooting

### Service won't start
```bash
sudo journalctl -u kindle-highlights --no-pager -n 50
```

### 502 Bad Gateway
- Check if Python server is running: `sudo systemctl status kindle-highlights`
- Check port: `ss -tlnp | grep 8000`

### HTTPS certificate renewal
Certbot handles auto-renewal, but to renew manually:
```bash
sudo certbot renew
```
