#!/usr/bin/env bash
set -euo pipefail
test "$(id -u)" -eq 0
config_dir="$(cd -- "$(dirname -- "$0")" && pwd)"
target=/etc/nginx/sites-available/event.hcmutertic.com
enabled=/etc/nginx/sites-enabled/event.hcmutertic.com
curl --noproxy '*' --silent --fail http://192.168.1.17:8512/health >/dev/null
install -d -m 0755 /var/www/letsencrypt/.well-known/acme-challenge
install -d -m 0700 /root/fit-club-event-backups
if [ -e "$target" ]; then cp -a "$target" "/root/fit-club-event-backups/event.$(date -u +%Y%m%dT%H%M%SZ).conf"; fi
install -m 0644 "$config_dir/event.hcmutertic.com.http.conf" "$target"
if [ ! -e "$enabled" ] && [ ! -L "$enabled" ]; then ln -s "$target" "$enabled"; fi
test "$(readlink -f "$enabled")" = "$target"
nginx -t
systemctl reload nginx
certbot certonly --webroot --webroot-path /var/www/letsencrypt --domain event.hcmutertic.com --cert-name event.hcmutertic.com --email hovietanh147@gmail.com --agree-tos --non-interactive
install -m 0644 "$config_dir/event.hcmutertic.com.conf" "$target"
nginx -t
systemctl reload nginx
install -d -m 0755 /etc/letsencrypt/renewal-hooks/deploy
cat > /etc/letsencrypt/renewal-hooks/deploy/fit-club-event-nginx.sh <<'HOOK'
#!/bin/sh
set -e
/usr/sbin/nginx -t
/bin/systemctl reload nginx
HOOK
chmod 0755 /etc/letsencrypt/renewal-hooks/deploy/fit-club-event-nginx.sh
systemctl enable --now certbot.timer
echo 'Event Nginx site and Certbot certificate configured.'
