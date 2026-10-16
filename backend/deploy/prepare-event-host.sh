#!/usr/bin/env bash
set -euo pipefail
test "$(id -u)" -eq 0
getent passwd fit-event >/dev/null || useradd --system --user-group --home-dir /var/lib/fit-club-event --shell /usr/sbin/nologin fit-event
install -d -m 0755 /srv/fit-club-event/releases
install -d -m 0750 -o root -g fit-event /etc/fit-club-event
install -d -m 0750 -o fit-event -g fit-event /var/lib/fit-club-event
install -d -m 0700 /var/backups/fit-club-event
if [ ! -f /etc/fit-club-event/.env ]; then
    /usr/bin/python3 - <<'PY'
from pathlib import Path
import os
import secrets
path = Path('/etc/fit-club-event/.env')
content = '\n'.join([
    'JWT_SECRET=' + secrets.token_urlsafe(48),
    'GOOGLE_CLIENT_ID=',
    'SUPERADMIN_EMAILS=hovietanh147@gmail.com',
    'DATABASE_URL=sqlite:////var/lib/fit-club-event/fitclub.db',
    'CORS_ORIGINS=https://event.hcmutertic.com',
    'STUDENT_EMAIL_ONLY=true',
    'ACCESS_MINUTES=60',
    'QR_SECONDS=120',
]) + '\n'
fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
with os.fdopen(fd, 'w') as stream:
    stream.write(content)
PY
    chown fit-event:fit-event /etc/fit-club-event/.env
fi
echo 'Event host prepared; production .env kept on server only.'
