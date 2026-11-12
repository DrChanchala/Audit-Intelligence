# Audit Intelligence — Ultra Low Cost AWS Deployment Guide (< $5/Month)

This guide shows you how to host **Audit Intelligence** on AWS for **less than $5/month** (or completely free on the AWS 12-month Free Tier).

---

## 1. Cost Breakdown

| Resource | Service / Tier | Monthly Cost |
| :--- | :--- | :--- |
| **Compute** | EC2 `t4g.nano` (2 vCPU, 0.5 GB RAM) or `t4g.micro` (2 vCPU, 1 GB RAM) | **$2.50 - $3.20** (or $0.00 if Free Tier eligible) |
| **Disk** | 8 GB gp3 EBS Volume | **$0.64** |
| **Database** | Embedded SQLite + Litestream (WAL replication) | **$0.00** |
| **Backups & Media** | S3 Standard / Infrequent Access (DB backups & photos) | **~$0.10** |
| **SSL & CDN** | AWS CloudFront / Let's Encrypt (Caddy) | **$0.00** |
| **Total** | | **~$3.24 - $3.94 / month** |

---

## 2. Launching Your AWS EC2 Instance (5 Minutes)

1. Log into your [AWS Management Console](https://console.aws.amazon.com/).
2. Navigate to **EC2** -> **Launch Instance**.
3. Configure the following:
   * **Name:** `Audit-Intelligence-Server`
   * **AMI:** **Ubuntu Server 24.04 LTS** (choose **64-bit (Arm)** for `t4g` instance savings).
   * **Instance Type:** `t4g.nano` (0.5 GB RAM) or `t4g.micro` (1 GB RAM).
   * **Key Pair:** Create or select your `.pem` key pair.
   * **Network / Security Group:**
     * Allow **SSH (Port 22)** from your IP.
     * Allow **HTTP (Port 80)** from anywhere (`0.0.0.0/0`).
     * Allow **HTTPS (Port 443)** from anywhere (`0.0.0.0/0`).
   * **Storage:** 8 GB General Purpose SSD (gp3).
4. Click **Launch Instance**.

---

## 3. One-Click Setup Script on the Server

Once connected to your EC2 instance via SSH:

```bash
ssh -i your-key.pem ubuntu@<your-ec2-public-ip>
```

Run this automated setup script:

```bash
# 1. Update and install Docker
sudo apt update && sudo apt upgrade -y
sudo apt install -y docker.io docker-compose git curl

# 2. Add ubuntu user to docker group
sudo usermod -aG docker ubuntu
newgrp docker

# 3. Clone or copy your Audit Intelligence repository
mkdir -p /home/ubuntu/audit-intelligence
cd /home/ubuntu/audit-intelligence

# Copy files or clone your repo here
```

Run the application:
```bash
docker-compose up -d --build
```

Check the health status:
```bash
curl http://localhost:8000/api/health
```

---

## 4. Automatic Free SSL with Caddy (Optional & Recommended)

To attach a domain name (e.g. `audit.yourdomain.com`) with automatic Let's Encrypt SSL:

1. Install Caddy:
```bash
sudo apt install -y debian-keyring debian-archive-keyring apt-transport-https curl
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | sudo gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | sudo tee /etc/apt/sources.list.d/caddy-stable.list
sudo apt update
sudo apt install caddy
```

2. Edit `/etc/caddy/Caddyfile`:
```caddy
audit.yourdomain.com {
    reverse_proxy localhost:8000
}
```

3. Reload Caddy:
```bash
sudo systemctl reload caddy
```

Your **Audit Intelligence** dashboard is now live, securely served over HTTPS, backed by persistent SQLite, and running under **$5/month**.
