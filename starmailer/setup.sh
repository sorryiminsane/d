#!/bin/bash

# Starmailer Setup Script
# Installs and configures all required dependencies for starmailer

set -e

echo "Starting starmailer setup..."

# Update system
apt update && apt upgrade -y

# Install required packages
echo "Installing system packages..."
apt install -y \
    postfix \
    opendkim \
    opendkim-tools \
    opendmarc \
    python3 \
    python3-pip \
    python3-venv \
    swaks \
    dnsutils \
    curl \
    wget \
    git

# Install Python dependencies
echo "Installing Python dependencies..."
pip3 install --upgrade pip
pip3 install python-telegram-bot

# Create starmailer user
echo "Creating starmailer user..."
useradd -m -s /bin/bash starmailer || true

# Copy starmailer files
echo "Setting up starmailer directory..."
STARMAILER_DIR="/home/starmailer/starmailer"
mkdir -p "$STARMAILER_DIR"
cp -r . "$STARMAILER_DIR/"
chown -R starmailer:starmailer /home/starmailer/

# Configure Postfix
echo "Configuring Postfix..."
cat > /etc/postfix/main.cf << 'EOF'
smtpd_banner = $myhostname ESMTP $mail_name (Ubuntu)
biff = no
append_dot_mydomain = no
readme_directory = no
compatibility_level = 2

# TLS parameters
smtpd_tls_cert_file=/etc/ssl/certs/ssl-cert-snakeoil.pem
smtpd_tls_key_file=/etc/ssl/private/ssl-cert-snakeoil.key
smtpd_use_tls=yes
smtpd_tls_session_cache_database = btree:${data_directory}/smtpd_scache
smtp_tls_session_cache_database = btree:${data_directory}/smtp_scache

# Basic configuration
myhostname = mail.usp5-sec.me
mydomain = usp5-sec.me
myorigin = $mydomain
mydestination = $myhostname, localhost.$mydomain, localhost, $mydomain
relayhost = 
mynetworks = 127.0.0.0/8 [::ffff:127.0.0.0]/104 [::1]/128
mailbox_size_limit = 0
recipient_delimiter = +
inet_interfaces = all
inet_protocols = all

# DKIM
milter_protocol = 2
milter_default_action = accept
smtpd_milters = inet:localhost:8891
non_smtpd_milters = inet:localhost:8891
EOF

# Configure OpenDKIM
echo "Configuring OpenDKIM..."
mkdir -p /etc/opendkim/keys/usp5-sec.me

cat > /etc/opendkim.conf << 'EOF'
AutoRestart             Yes
AutoRestartRate         10/1h
UMask                   002
Syslog                  yes
SyslogSuccess           Yes
LogWhy                  Yes

Canonicalization        relaxed/simple

ExternalIgnoreList      refile:/etc/opendkim/TrustedHosts
InternalHosts           refile:/etc/opendkim/TrustedHosts
KeyTable                refile:/etc/opendkim/KeyTable
SigningTable            refile:/etc/opendkim/SigningTable

Mode                    sv
PidFile                 /var/run/opendkim/opendkim.pid
SignatureAlgorithm      rsa-sha256

UserID                  opendkim:opendkim

Socket                  inet:8891@localhost
EOF

# Create DKIM keys
echo "Generating DKIM keys..."
cd /etc/opendkim/keys/usp5-sec.me
opendkim-genkey -t -s mail -d usp5-sec.me
chown opendkim:opendkim mail.private
chmod 600 mail.private

# Configure DKIM files
cat > /etc/opendkim/TrustedHosts << 'EOF'
127.0.0.1
localhost
192.168.0.1/24
*.usp5-sec.me
usp5-sec.me
EOF

cat > /etc/opendkim/KeyTable << 'EOF'
mail._domainkey.usp5-sec.me usp5-sec.me:mail:/etc/opendkim/keys/usp5-sec.me/mail.private
EOF

cat > /etc/opendkim/SigningTable << 'EOF'
*@usp5-sec.me mail._domainkey.usp5-sec.me
EOF

# Set permissions
chown -R opendkim:opendkim /etc/opendkim
chmod -R 640 /etc/opendkim/keys

# Create systemd service for starmailer
cat > /etc/systemd/system/starmailer.service << 'EOF'
[Unit]
Description=Starmailer Telegram Bot
After=network.target

[Service]
Type=simple
User=starmailer
WorkingDirectory=/home/starmailer/starmailer
ExecStart=/usr/bin/python3 main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Enable and start services
echo "Starting services..."
systemctl daemon-reload
systemctl enable postfix
systemctl enable opendkim
systemctl enable starmailer
systemctl restart postfix
systemctl restart opendkim

# Display DKIM public key
echo "========================================="
echo "SETUP COMPLETE!"
echo "========================================="
echo ""
echo "Add this DKIM record to your DNS:"
echo "mail._domainkey.usp5-sec.me IN TXT"
cat /etc/opendkim/keys/usp5-sec.me/mail.txt
echo ""
echo "Add these DNS records:"
echo "SPF: usp5-sec.me IN TXT \"v=spf1 mx a ip4:$(curl -s ifconfig.me) -all\""
echo "DMARC: _dmarc.usp5-sec.me IN TXT \"v=DMARC1; p=quarantine; rua=mailto:dmarc@usp5-sec.me\""
echo "MX: usp5-sec.me IN MX 10 mail.usp5-sec.me"
echo "A: mail.usp5-sec.me IN A $(curl -s ifconfig.me)"
echo ""
echo "Configure your Telegram bot token in:"
echo "/home/starmailer/starmailer/token.txt"
echo ""
echo "Then start starmailer:"
echo "systemctl start starmailer"
