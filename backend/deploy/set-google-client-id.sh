#!/usr/bin/env bash
set -euo pipefail
test "$(id -u)" -eq 0
client_id="${1:?Provide the public Google Web Client ID}"
/usr/bin/python3 - "$client_id" <<'PY'
from pathlib import Path
import os
import re
import sys
import tempfile
value = sys.argv[1]
if not re.fullmatch(r'[A-Za-z0-9_-]+\.apps\.googleusercontent\.com', value):
    raise SystemExit('Invalid Google Web Client ID')
path = Path('/etc/fit-club-event/.env')
info = path.stat()
lines = path.read_text().splitlines()
lines = [line for line in lines if not line.startswith('GOOGLE_CLIENT_ID=')]
lines.append('GOOGLE_CLIENT_ID=' + value)
with tempfile.NamedTemporaryFile(mode='w', dir=path.parent, delete=False) as stream:
    temporary = Path(stream.name)
    os.fchmod(stream.fileno(), 0o600)
    os.fchown(stream.fileno(), info.st_uid, info.st_gid)
    stream.write('\n'.join(lines) + '\n')
os.replace(temporary, path)
PY
systemctl restart fit-club-event.service
echo 'Google Web Client ID updated; service restarted.'
