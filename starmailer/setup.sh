#!/bin/bash

# Starmailer Setup Script
# This script sets up a complete mail server environment with Postfix, OpenDKIM, SPF, and DMARC
# Designed for Ubuntu 24.04 LTS

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
}

warn() {
    echo -e "${YELLOW}[WARNING] $1${NC}"
}

error() {
    echo -e "${RED}[ERROR] $1${NC}"
    exit 1
}

# Check if running as root
if [[ $EUID -eq 0 ]]; then
   error "This script should not be run as root. Please run as a regular user with sudo privileges."
fi

# Check if sudo is available
if ! command -v sudo &> /dev/null; then
    error "sudo is required but not installed. Please install sudo first."
fi

log "Starting Starmailer setup..."

# Get domain and server IP
read -p "Enter your domain name (e.g., yourdomain.com): " DOMAIN
read -p "Enter your server IP address: " SERVER_IP

if [[ -z "$DOMAIN" || -z "$SERVER_IP" ]]; then
    error "Domain and server IP are required"
fi

log "Setting up for domain: $DOMAIN with IP: $SERVER_IP"

# Update system
log "Updating system packages..."
sudo apt update && sudo apt upgrade -y

# Install required packages
log "Installing required packages..."
sudo apt install -y \
    postfix \
    opendkim \
    opendkim-tools \
    opendmarc \
    python3 \
    python3-pip \
    python3-venv \
    swaks \
    mailutils \
    dnsutils \
    curl \
    wget \
    git \
    systemd

# Create starmailer user
log "Creating starmailer user..."
if ! id "starmailer" &>/dev/null; then
    sudo useradd -m -s /bin/bash starmailer
    sudo usermod -aG mail starmailer
fi

# Create starmailer directory structure
log "Setting up starmailer directory structure..."
sudo mkdir -p /home/starmailer/starmailer
sudo cp -r . /home/starmailer/starmailer/
sudo chown -R starmailer:starmailer /home/starmailer/

# Set up Python virtual environment
log "Setting up Python virtual environment..."
sudo -u starmailer python3 -m venv /home/starmailer/starmailer/venv
sudo -u starmailer /home/starmailer/starmailer/venv/bin/pip install --upgrade pip

# Install Python dependencies
log "Installing Python dependencies..."
sudo -u starmailer /home/starmailer/starmailer/venv/bin/pip install \
    python-telegram-bot \
    python-dotenv

# Configure Postfix
log "Configuring Postfix..."
sudo debconf-set-selections <<< "postfix postfix/mailname string mail.$DOMAIN"
sudo debconf-set-selections <<< "postfix postfix/main_mailer_type string 'Internet Site'"

# Backup original Postfix configuration
sudo cp /etc/postfix/main.cf /etc/postfix/main.cf.backup

# Create new Postfix configuration
sudo tee /etc/postfix/main.cf > /dev/null <<EOF
# Basic configuration
myhostname = mail.$DOMAIN
mydomain = $DOMAIN
myorigin = \$mydomain
mydestination = \$myhostname, localhost.\$mydomain, localhost, \$mydomain
mynetworks = 127.0.0.0/8 [::ffff:127.0.0.0]/104 [::1]/128

# Network settings
inet_interfaces = all
inet_protocols = all

# SMTP settings
smtp_tls_security_level = may
smtpd_tls_security_level = may
smtpd_tls_cert_file = /etc/ssl/certs/ssl-cert-snakeoil.pem
smtpd_tls_key_file = /etc/ssl/private/ssl-cert-snakeoil.key

# DKIM and DMARC
milter_protocol = 2
milter_default_action = accept
smtpd_milters = inet:localhost:8891,inet:localhost:8893
non_smtpd_milters = inet:localhost:8891

# Message size limits
message_size_limit = 10240000
mailbox_size_limit = 1024000000

# Queue settings
maximal_queue_lifetime = 1d
bounce_queue_lifetime = 1d

# SMTP restrictions
smtpd_helo_restrictions = permit_mynetworks,permit_sasl_authenticated,reject_invalid_helo_hostname,permit
smtpd_sender_restrictions = permit_mynetworks,permit_sasl_authenticated,reject_unknown_sender_domain,permit
smtpd_recipient_restrictions = permit_mynetworks,permit_sasl_authenticated,reject_unauth_destination,permit
EOF

# Set up OpenDKIM
log "Setting up OpenDKIM..."
sudo mkdir -p /etc/opendkim/keys/$DOMAIN

# Generate DKIM keys
log "Generating DKIM keys..."
sudo opendkim-genkey -t -s mail -d $DOMAIN -D /etc/opendkim/keys/$DOMAIN/
sudo chown -R opendkim:opendkim /etc/opendkim/keys

# Create OpenDKIM configuration
sudo tee /etc/opendkim.conf > /dev/null <<EOF
AutoRestart             Yes
AutoRestartRate         10/1h
Canonicalization        relaxed/simple
ExternalIgnoreList      refile:/etc/opendkim/TrustedHosts
InternalHosts           refile:/etc/opendkim/TrustedHosts
KeyTable                refile:/etc/opendkim/KeyTable
LogWhy                  Yes
MinimumKeyBits          1024
Mode                    sv
PidFile                 /var/run/opendkim/opendkim.pid
SigningTable            refile:/etc/opendkim/SigningTable
Socket                  inet:8891@localhost
Syslog                  Yes
SyslogSuccess           Yes
TemporaryDirectory      /var/tmp
UMask                   022
UserID                  opendkim:opendkim
EOF

# Create TrustedHosts
sudo tee /etc/opendkim/TrustedHosts > /dev/null <<EOF
127.0.0.1
localhost
$DOMAIN
mail.$DOMAIN
*.$DOMAIN
EOF

# Create KeyTable
sudo tee /etc/opendkim/KeyTable > /dev/null <<EOF
mail._domainkey.$DOMAIN $DOMAIN:mail:/etc/opendkim/keys/$DOMAIN/mail.private
EOF

# Create SigningTable
sudo tee /etc/opendkim/SigningTable > /dev/null <<EOF
*@$DOMAIN mail._domainkey.$DOMAIN
EOF

# Set up OpenDMARC
log "Setting up OpenDMARC..."
sudo tee /etc/opendmarc.conf > /dev/null <<EOF
AuthservID $DOMAIN
PidFile /var/run/opendmarc/opendmarc.pid
RejectFailures false
Syslog true
TrustedAuthservIDs $DOMAIN
Socket inet:8893@localhost
UMask 0002
UserID opendmarc:opendmarc
IgnoreHosts /etc/opendmarc/ignore.hosts
HistoryFile /var/run/opendmarc/opendmarc.dat
EOF

# Create ignore hosts file for OpenDMARC
sudo tee /etc/opendmarc/ignore.hosts > /dev/null <<EOF
127.0.0.1
localhost
$DOMAIN
mail.$DOMAIN
EOF

# Create starmailer configuration
log "Creating starmailer configuration..."
sudo tee /home/starmailer/starmailer/config.env > /dev/null <<EOF
# Starmailer Configuration
DOMAIN=$DOMAIN
SERVER_IP=$SERVER_IP
TELEGRAM_BOT_TOKEN=YOUR_BOT_TOKEN_HERE
ADMIN_ID=YOUR_ADMIN_ID_HERE

# Postfix Configuration
POSTFIX_SERVER=localhost
POSTFIX_PORT=25
POSTFIX_DOMAIN=$DOMAIN
EOF

sudo chown starmailer:starmailer /home/starmailer/starmailer/config.env

# Create systemd service
log "Creating systemd service..."
sudo tee /etc/systemd/system/starmailer.service > /dev/null <<EOF
[Unit]
Description=Starmailer Telegram Bot
After=network.target postfix.service opendkim.service opendmarc.service
Requires=postfix.service opendkim.service

[Service]
Type=simple
User=starmailer
Group=starmailer
WorkingDirectory=/home/starmailer/starmailer
Environment=PATH=/home/starmailer/starmailer/venv/bin
ExecStart=/home/starmailer/starmailer/venv/bin/python main.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
SyslogIdentifier=starmailer

[Install]
WantedBy=multi-user.target
EOF

# Set correct permissions
sudo chmod 644 /etc/systemd/system/starmailer.service
sudo systemctl daemon-reload

# Start and enable services
log "Starting and enabling services..."
sudo systemctl enable postfix
sudo systemctl enable opendkim
sudo systemctl enable opendmarc
sudo systemctl enable starmailer

sudo systemctl restart postfix
sudo systemctl restart opendkim
sudo systemctl restart opendmarc

# Display DKIM public key
log "Extracting DKIM public key..."
DKIM_KEY=$(sudo cat /etc/opendkim/keys/$DOMAIN/mail.txt | grep -v '^;' | tr -d '\n\t ' | sed 's/.*p=\([^"]*\).*/\1/')

# Create DNS instructions
log "Creating DNS configuration file..."
sudo tee /home/starmailer/starmailer/dns_records.txt > /dev/null <<EOF
=== DNS Records to Configure ===

1. DKIM Record:
   Name: mail._domainkey.$DOMAIN
   Type: TXT
   Value: "v=DKIM1; k=rsa; p=$DKIM_KEY"

2. SPF Record:
   Name: $DOMAIN
   Type: TXT
   Value: "v=spf1 mx a ip4:$SERVER_IP -all"

3. DMARC Record:
   Name: _dmarc.$DOMAIN
   Type: TXT
   Value: "v=DMARC1; p=quarantine; rua=mailto:dmarc@$DOMAIN; ruf=mailto:dmarc@$DOMAIN; fo=1"

4. MX Record:
   Name: $DOMAIN
   Type: MX
   Priority: 10
   Value: mail.$DOMAIN

5. A Record:
   Name: mail.$DOMAIN
   Type: A
   Value: $SERVER_IP

=== Configuration Files ===
- Starmailer config: /home/starmailer/starmailer/config.env
- Postfix config: /etc/postfix/main.cf
- OpenDKIM config: /etc/opendkim.conf
- OpenDMARC config: /etc/opendmarc.conf

=== Next Steps ===
1. Configure the DNS records above in your domain registrar
2. Edit /home/starmailer/starmailer/config.env with your Telegram bot token
3. Start the starmailer service: sudo systemctl start starmailer
4. Check logs: journalctl -u starmailer -f

=== Testing Commands ===
# Test DKIM
sudo opendkim-testkey -d $DOMAIN -s mail -k /etc/opendkim/keys/$DOMAIN/mail.private -vvv

# Test email delivery
echo "Test email body" | mail -s "Test Subject" test@mail-tester.com

# Check service status
sudo systemctl status postfix opendkim opendmarc starmailer
EOF

sudo chown starmailer:starmailer /home/starmailer/starmailer/dns_records.txt

# Final setup
log "Performing final setup..."
sudo postfix reload
sudo systemctl restart opendkim
sudo systemctl restart opendmarc

# Display completion message
echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}    Starmailer Setup Complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "${BLUE}Next steps:${NC}"
echo "1. Configure DNS records (see /home/starmailer/starmailer/dns_records.txt)"
echo "2. Edit /home/starmailer/starmailer/config.env with your Telegram bot token"
echo "3. Start starmailer: sudo systemctl start starmailer"
echo ""
echo -e "${BLUE}Useful commands:${NC}"
echo "- Check status: sudo systemctl status starmailer"
echo "- View logs: journalctl -u starmailer -f"
echo "- Test DKIM: sudo opendkim-testkey -d $DOMAIN -s mail"
echo ""
echo -e "${YELLOW}DNS records have been saved to:${NC}"
echo "/home/starmailer/starmailer/dns_records.txt"
echo ""
echo -e "${GREEN}Setup completed successfully!${NC}"
