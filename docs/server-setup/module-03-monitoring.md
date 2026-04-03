# Module 03: Monitoring (Der Wachturm)

**Status:** Deployed (2026-04-03)
**Dauer:** ~10 Minuten
**Voraussetzung:** Module 01 + 02 abgeschlossen
**Ergebnis:** Uptime Kuma laeuft, Dashboard ueber Caddy erreichbar, Alerting konfigurierbar

---

## Was dieses Modul macht

Die Burg steht, die Bewohner sind eingezogen (Module 02). Aber niemand schaut ob alles laeuft. Der Wachturm ueberwacht die Burg und schlaegt Alarm wenn etwas ausfaellt.

| Burg-Element | Komponente | Was es tut |
|---|---|---|
| Wachturm | Uptime Kuma | Ueberwacht Endpoints, zeigt Uptime-Historie |
| Glocke | Alerting | Benachrichtigt bei Ausfall (Telegram, E-Mail) |
| Burgtor-Erweiterung | Caddy | Routet Dashboard-Traffic ueber HTTPS |

---

## Architektur nach Modul 03

```
Internet
   |
   | HTTPS (443)
   v
+--Caddy (Burgtor)----------------------------+
|  api.chrisbuilds64.dev    -> :8000          |
|  status.chrisbuilds64.dev -> :3001          |
+--------|---------------------|---------------+
         |                     |
         | caddy-net           | caddy-net
         |                     |
+--------|----------+    +-----|-------------+
|  PROD-STACK       |    |  MONITORING       |
|  FastAPI + PgSQL  |    |  Uptime Kuma      |
|  (prod-net)       |    |  (:3001)          |
+-------------------+    +-------------------+
```

Uptime Kuma lebt in seinem eigenen Stack (`/opt/monitoring/`), teilt sich aber `caddy-net` mit den anderen. Es hat KEINEN Zugriff auf `prod-net` (kann die Datenbank nicht sehen).

---

## Automatische Installation (Ansible)

```bash
cd develop/ansible
ansible-playbook -i inventory.yml monitoring.yml --limit rheinstein
```

Das Playbook:
1. Erstellt `/opt/monitoring/`
2. Schreibt `docker-compose.yml` (Uptime Kuma)
3. Aktualisiert Caddyfile (neue Route fuer Monitoring-Domain)
4. Startet Uptime Kuma
5. Laesst Caddy neu laden (TLS-Zertifikat fuer neue Domain)
6. Verifiziert: Container laeuft, antwortet intern

---

## Manuelle Installation

Falls ohne Ansible:

### Schritt 1: Verzeichnis

```bash
sudo mkdir -p /opt/monitoring
sudo chown deploy:deploy /opt/monitoring
chmod 750 /opt/monitoring
```

### Schritt 2: docker-compose.yml

```bash
cat > /opt/monitoring/docker-compose.yml << 'EOF'
services:
  uptime-kuma:
    image: louislam/uptime-kuma:1
    container_name: uptime-kuma
    restart: unless-stopped
    volumes:
      - uptime_data:/app/data
    networks:
      - caddy-net

volumes:
  uptime_data:
    name: uptime-kuma-data

networks:
  caddy-net:
    external: true
EOF
```

### Schritt 3: Caddyfile erweitern

Route fuer die Monitoring-Domain hinzufuegen:

```
status.chrisbuilds64.dev {
    log {
        output stdout
        format json
    }
    reverse_proxy uptime-kuma:3001
}
```

### Schritt 4: Starten

```bash
cd /opt/monitoring && docker compose up -d
cd /opt/caddy && docker compose restart caddy
```

---

## Ersteinrichtung (im Browser)

Beim ersten Aufruf von `https://status.chrisbuilds64.dev`:

1. **Admin-Account anlegen** (Username + Passwort waehlen)
2. **Sprache** auf Englisch oder Deutsch setzen

### Monitors konfigurieren

Empfohlene Monitors fuer unseren Stack:

| Name | Typ | URL/Host | Intervall |
|---|---|---|---|
| API Health | HTTP(s) | `https://api.chrisbuilds64.dev/health` | 60s |
| Caddy | HTTP(s) | `https://api.chrisbuilds64.dev` | 60s |
| SSH | TCP Port | `82.165.165.199:22` | 120s |

**Monitor anlegen:**
1. "Add New Monitor" klicken
2. Typ waehlen (HTTP(s) fuer Web-Endpoints, TCP Port fuer SSH)
3. URL eingeben
4. Intervall setzen (60s = jede Minute)
5. Speichern

### Alerting einrichten

Uptime Kuma unterstuetzt 90+ Notification-Provider. Empfohlen:

**Telegram:**
1. BotFather in Telegram: `/newbot` → Token erhalten
2. Chat-ID herausfinden (z.B. @userinfobot)
3. In Uptime Kuma: Settings → Notifications → Telegram
4. Bot Token + Chat ID eintragen
5. Testen

**E-Mail (ueber Brevo/SMTP):**
1. Settings → Notifications → SMTP
2. Brevo SMTP-Daten eintragen
3. Empfaenger-Adresse setzen

---

## Status Page (oeffentlich)

Uptime Kuma kann eine oeffentliche Status-Seite generieren:

1. Dashboard → "Status Pages" (links)
2. "New Status Page" → Name + Slug waehlen
3. Monitors zuweisen
4. Erreichbar unter `https://status.chrisbuilds64.dev/status/SLUG`

---

## Monitoring-Cheatsheet

```bash
# Container-Status
docker ps --filter name=uptime-kuma

# Logs
docker logs uptime-kuma --tail 50

# Neustart
cd /opt/monitoring && docker compose restart

# Update (neues Image)
cd /opt/monitoring
docker compose pull
docker compose up -d
```

---

## Burginspektion (Module 03)

```bash
# Nur Module 03 pruefen
ansible-playbook -i inventory.yml verify.yml --limit rheinstein --tags module03

# Oder via inspect.sh
./inspect.sh module03
```

Prueft:
- `/opt/monitoring/` existiert
- Uptime Kuma Container laeuft
- Uptime Kuma in caddy-net (korrekt vernetzt)
- Keine direkten Host-Ports (nur ueber Caddy)
- Restart-Policy gesetzt
- Uptime Kuma antwortet intern
- Caddy-Routing konfiguriert

---

## Was kommt danach

| Modul | Inhalt | Wann |
|---|---|---|
| 04 | Backup (Borgmatic + Storage Box) | Wenn Daten da sind |
| 05 | CI/CD (GitHub Actions → Auto-Deploy) | Wenn alles stabil |

---

*Erstellt: 3. April 2026 (Hackathon Session 3, Koeln)*
