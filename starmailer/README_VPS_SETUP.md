# Starmailer VPS Setup Guide

This guide provides step-by-step instructions for setting up the starmailer bot on a fresh Ubuntu 24.04 VPS with Postfix, DKIM, SPF, and DMARC configuration.

## Quick Start

1. **Download and run the setup script:**
   ```bash
   wget https://raw.githubusercontent.com/sorryiminsane/d/main/starmailer/setup.sh
   chmod +x setup.sh
   sudo ./setup.sh
   ```

2. **Configure DNS records** (see DNS Configuration section)

3. **Edit bot configuration:**
   ```bash
   sudo nano /home/starmailer/starmailer/config.env
   ```

4. **Start the bot:**
   ```bash
   sudo systemctl start starmailer
   sudo systemctl enable starmailer
   ```

## DNS Configuration

After running the setup script, configure these DNS records for your domain:

### 1. DKIM Record
```
mail._domainkey.yourdomain.com IN TXT "v=DKIM1; k=rsa; p=YOUR_PUBLIC_KEY_HERE"
```

### 2. SPF Record
```
yourdomain.com IN TXT "v=spf1 mx a ip4:YOUR_SERVER_IP -all"
```

### 3. DMARC Record
```
_dmarc.yourdomain.com IN TXT "v=DMARC1; p=quarantine; rua=mailto:dmarc@yourdomain.com; ruf=mailto:dmarc@yourdomain.com; fo=1"
```

### 4. MX Record
```
yourdomain.com IN MX 10 mail.yourdomain.com
```

### 5. A Record
```
mail.yourdomain.com IN A YOUR_SERVER_IP
```

## Manual Setup Instructions

If you prefer to set up manually, follow these steps:

### 1. System Preparation
```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y postfix opendkim opendkim-tools opendmarc python3 python3-pip
```

### 2. Postfix Configuration
Edit `/etc/postfix/main.cf`:
```
myhostname = mail.yourdomain.com
mydomain = yourdomain.com
myorigin = $mydomain
mydestination = $myhostname, localhost.$mydomain, localhost, $mydomain
mynetworks = 127.0.0.0/8 [::ffff:127.0.0.0]/104 [::1]/128

# DKIM
milter_protocol = 2
milter_default_action = accept
smtpd_milters = inet:localhost:8891
non_smtpd_milters = inet:localhost:8891
```

### 3. DKIM Setup
```bash
sudo mkdir -p /etc/opendkim/keys/yourdomain.com
sudo opendkim-genkey -t -s mail -d yourdomain.com
sudo mv mail.private /etc/opendkim/keys/yourdomain.com/
sudo mv mail.txt /etc/opendkim/keys/yourdomain.com/
sudo chown -R opendkim:opendkim /etc/opendkim/keys
```

### 4. Configure OpenDKIM
Create `/etc/opendkim.conf`:
```
AutoRestart             Yes
Canonicalization        relaxed/simple
ExternalIgnoreList      refile:/etc/opendkim/TrustedHosts
InternalHosts           refile:/etc/opendkim/TrustedHosts
KeyTable                refile:/etc/opendkim/KeyTable
SigningTable            refile:/etc/opendkim/SigningTable
Socket                  inet:8891@localhost
```

### 5. Create DKIM configuration files
```bash
# /etc/opendkim/TrustedHosts
127.0.0.1
localhost
yourdomain.com

# /etc/opendkim/KeyTable
mail._domainkey.yourdomain.com yourdomain.com:mail:/etc/opendkim/keys/yourdomain.com/mail.private

# /etc/opendkim/SigningTable
*@yourdomain.com mail._domainkey.yourdomain.com
```

## Testing Your Configuration

### 1. Test DKIM
```bash
sudo opendkim-testkey -d yourdomain.com -s mail -k /etc/opendkim/keys/yourdomain.com/mail.private -vvv
```

### 2. Test SPF
```bash
dig TXT yourdomain.com
```

### 3. Test DMARC
```bash
dig TXT _dmarc.yourdomain.com
```

### 4. Test Email Delivery
```bash
echo "Test email body" | mail -s "Test Subject" your-email@gmail.com
```

### 5. Check Email Headers
Send a test email to mail-tester.com:
```bash
echo "Test email for header analysis" | mail -s "Test Email" test@mail-tester.com
```

## Troubleshooting

### Common Issues

1. **Permission Denied Errors**
   ```bash
   sudo chown -R opendkim:opendkim /etc/opendkim/keys
   sudo chmod 640 /etc/opendkim/keys/yourdomain.com/mail.private
   ```

2. **DKIM Signature Missing**
   - Check OpenDKIM service: `sudo systemctl status opendkim`
   - Verify key permissions: `ls -la /etc/opendkim/keys/`
   - Test DKIM key: `sudo opendkim-testkey`

3. **SPF Failures**
   - Verify SPF record: `dig TXT yourdomain.com`
   - Check server IP matches SPF record

4. **Port 25 Blocked**
   - Check with ISP if port 25 is blocked
   - Consider using port 587 for submission

### Log Files

- **Postfix**: `/var/log/mail.log`
- **OpenDKIM**: `/var/log/mail.log`
- **OpenDMARC**: `/var/log/mail.log`
- **Starmailer**: `journalctl -u starmailer -f`

### Useful Commands

```bash
# Check service status
sudo systemctl status postfix opendkim opendmarc starmailer

# Check mail queue
sudo postqueue -p

# Flush mail queue
sudo postqueue -f

# Check DNS records
dig TXT yourdomain.com
dig TXT mail._domainkey.yourdomain.com
dig TXT _dmarc.yourdomain.com

# Test email authentication
sudo -u starmailer echo "test" | sendmail test@mail-tester.com
```

## Security Considerations

1. **Firewall Configuration**
   - Only allow necessary ports (25, 587, 993, 80, 443)
   - Use fail2ban for brute force protection

2. **SSL/TLS**
   - Use Let's Encrypt certificates
   - Configure TLS for all connections

3. **Rate Limiting**
   - Configure Postfix rate limiting
   - Monitor for abuse

4. **Authentication**
   - Use strong passwords
   - Enable 2FA where possible

## Performance Optimization

1. **DNS Caching**
   ```bash
   sudo apt install pdns-recursor
   ```

2. **Postfix Tuning**
   - Adjust queue sizes
   - Configure connection limits
   - Enable connection caching

3. **Monitoring**
   - Set up log rotation
   - Configure alerts
   - Monitor queue sizes

## Support

For issues or questions:
1. Check the log files first
2. Verify DNS configuration
3. Test with mail-tester.com
4. Check GitHub issues for known problems

## Next Steps

1. Configure monitoring and alerts
2. Set up automated backups
3. Implement rate limiting
4. Add monitoring dashboard
5. Configure log analysis
