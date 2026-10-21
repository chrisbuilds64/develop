# Deploying the public demo

The demo is the real core and surface on fictional data: every visitor gets a sandbox copied from a world
template, bound to a cookie (ADR-016). No sign-in, no tracking, uploads stay in the sandbox, old sandboxes are
swept after 24 hours, a cap keeps the disk bounded, a per-IP limit keeps the host up.

## On the host (Debian/Ubuntu, as root)

```bash
curl -fsSL https://raw.githubusercontent.com/chrisbuilds64/develop/main/apps/casefile/deploy/install.sh -o /tmp/install.sh
bash /tmp/install.sh                 # user, venv, worlds, systemd unit on 127.0.0.1:8410
```

Re-running the script updates the checkout and restarts the service. The surface is built on the host when
`npm` exists; otherwise build `web/dist` elsewhere (`npm ci && npm run build`) and copy it to `/opt/casefile/app/web/dist`.

## Under a path (e.g. `https://pressroom.chrisbuilds64.com/demo/`)

Build the surface with the base path and drop it on the host before running the installer:

```bash
cd apps/casefile/web && VITE_BASE=/demo/ npm run build && rsync -a dist/ root@host:/opt/casefile/web-dist/
```

The proxy strips the prefix: `location /demo/ { proxy_pass http://127.0.0.1:8410/; … }` (note the trailing slash).

## Reverse proxy

A site for the demo's host name that proxies to `127.0.0.1:8410` with TLS. On CloudPanel: *Sites → Add site →
Reverse proxy*, target `http://127.0.0.1:8410`, then a Let's Encrypt certificate from the site's SSL tab. The
service trusts `X-Forwarded-For` from the proxy, so the rate limit counts visitors, not the proxy.

nginx, if written by hand:

```nginx
location / {
  proxy_pass http://127.0.0.1:8410;
  proxy_set_header Host $host;
  proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
  proxy_set_header X-Forwarded-Proto $scheme;
  client_max_body_size 12m;
}
```

## Checks before the audience arrives

```bash
systemctl status casefile-demo
curl -s https://<host>/api/me                   # a fresh sandbox, person "du", world "claims"
journalctl -u casefile-demo -n 50
du -sh /opt/casefile/demo/sessions              # bounded by the cap (500) and the sweep (24 h)
```

A load check from any machine with Node: `node apps/casefile/deploy/load.mjs https://<host> 20` opens twenty
sandboxes in parallel and walks the claims path in each.

## What the demo never has

Real pipeline data, real names besides the operator's, a sign-in, a live agent run. Those stay with the operator's
own installation (`CASEFILE_ROOT` mode), on a machine the customer controls.
