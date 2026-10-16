#!/usr/bin/env bash
set -euo pipefail
test "$(id -u)" -eq 0
revision="${1:?Provide a Git commit SHA}"
archive="${2:?Provide a release tar.gz}"
[[ "$revision" =~ ^[0-9a-f]{7,40}$ ]] || { echo 'Invalid revision' >&2; exit 1; }
release="/srv/fit-club-event/releases/$revision"
test ! -e "$release" || { echo 'Release directory already exists' >&2; exit 1; }
test -f "$archive"
previous=''
if [ -L /srv/fit-club-event/current ]; then previous="$(readlink -f /srv/fit-club-event/current)"; fi
install -d -m 0755 "$release"
tar -xzf "$archive" -C "$release"
bash "$release/backend/deploy/prepare-event-host.sh"
/usr/bin/python3 -m venv "$release/.venv"
"$release/.venv/bin/python" -m pip install --disable-pip-version-check --quiet -r "$release/backend/requirements.txt"
ln -s /etc/fit-club-event/.env "$release/backend/.env"
(
    cd "$release/backend"
    PYTHONPATH=. "$release/.venv/bin/python" -m pytest -q --ignore=tests/test_browser.py
)
if [ -f /var/lib/fit-club-event/fitclub.db ]; then
    /usr/bin/python3 - <<'PY'
from datetime import datetime, timezone
import sqlite3
name = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
with sqlite3.connect('file:/var/lib/fit-club-event/fitclub.db?mode=ro', uri=True) as source:
    with sqlite3.connect('/var/backups/fit-club-event/' + name + '.db') as destination:
        source.backup(destination)
PY
fi
install -m 0644 "$release/backend/deploy/fit-club-event.service" /etc/systemd/system/fit-club-event.service
systemctl daemon-reload
ln -sfn "$release" /srv/fit-club-event/current
systemctl enable fit-club-event.service
systemctl restart fit-club-event.service
for attempt in $(seq 1 20); do
    if curl --noproxy '*' --silent --fail http://192.168.1.17:8512/health >/dev/null; then
        printf 'Healthy release: %s\nPrevious release: %s\n' "$release" "${previous:-none}"
        exit 0
    fi
    sleep 1
done
echo 'Health check failed; restoring the previous release.' >&2
if [ -n "$previous" ]; then
    ln -sfn "$previous" /srv/fit-club-event/current
    systemctl restart fit-club-event.service
else
    systemctl stop fit-club-event.service
fi
exit 1
