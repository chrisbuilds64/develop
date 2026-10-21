#!/usr/bin/env bash
# Install or update the public demo on a Debian/Ubuntu host: a system user, a venv, the built surface, the fictional
# worlds, a systemd unit. Run as root. Idempotent. The reverse proxy (CloudPanel/nginx or Caddy) is set up by hand, see README.
set -euo pipefail

APP=/opt/casefile/app
VENV=/opt/casefile/venv
DEMO=/opt/casefile/demo
REPO=${CASEFILE_REPO:-https://github.com/chrisbuilds64/develop.git}
REF=${CASEFILE_REF:-main}

id -u casefile >/dev/null 2>&1 || useradd --system --home /opt/casefile --shell /usr/sbin/nologin casefile
mkdir -p /opt/casefile "$DEMO"

git config --global --add safe.directory /opt/casefile/src >/dev/null 2>&1 || true
if [ ! -d /opt/casefile/src/.git ]; then
  git clone --depth 1 --branch "$REF" "$REPO" /opt/casefile/src
else
  git -C /opt/casefile/src fetch --depth 1 origin "$REF"
  git -C /opt/casefile/src reset -q --hard FETCH_HEAD
fi
echo "source at $(git -C /opt/casefile/src log --oneline -1)"
rm -rf "$APP" && cp -r /opt/casefile/src/apps/casefile "$APP"

[ -x "$VENV/bin/python" ] || python3 -m venv "$VENV"
"$VENV/bin/pip" install -q --upgrade pip
"$VENV/bin/pip" install -q -e "$APP"     # editable: config/ and demo/ are found next to the package

# the surface: a prebuilt copy in /opt/casefile/web-dist wins; else build on the server when node is there
if [ -d /opt/casefile/web-dist ]; then
  rm -rf "$APP/web/dist" && cp -r /opt/casefile/web-dist "$APP/web/dist"
elif [ ! -d "$APP/web/dist" ]; then
  if command -v npm >/dev/null; then (cd "$APP/web" && npm ci --no-audit --no-fund && VITE_BASE="${CASEFILE_BASE:-/}" npm run build); else echo "web/dist missing and no npm: build it elsewhere (VITE_BASE=/demo/ npm run build) and copy it to /opt/casefile/web-dist"; exit 1; fi
fi

"$VENV/bin/python" -m casefile.demo.worlds "$DEMO/worlds"
mkdir -p "$DEMO/sessions"
[ -f /opt/casefile/demo.env ] || { sed "s/change-me/$(openssl rand -hex 32)/" "$APP/deploy/demo.env.example" > /opt/casefile/demo.env; chmod 600 /opt/casefile/demo.env; }
chown -R casefile:casefile "$APP" "$VENV" "$DEMO" /opt/casefile/demo.env      # src stays root's, web-dist stays the deployer's
install -m 644 "$APP/deploy/casefile-demo.service" /etc/systemd/system/casefile-demo.service
systemctl daemon-reload
systemctl enable --now casefile-demo
systemctl restart casefile-demo
sleep 2
curl -fsS http://127.0.0.1:8410/api/config | head -c 120; echo
echo "casefile demo running on 127.0.0.1:8410 — put the reverse proxy in front (deploy/README.md)"
