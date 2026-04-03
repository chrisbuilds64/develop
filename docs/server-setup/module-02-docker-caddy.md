# Module 02: Docker + Caddy (Die Einrichtung der Burg)

**Status:** Entwurf (2026-04-03)
**Dauer:** ~45 Minuten
**Voraussetzung:** Module 01 abgeschlossen (Foundation steht)
**Ergebnis:** Docker laeuft, Prod-Stack deployed, Caddy routet HTTPS-Traffic

---

## Was dieses Modul macht

Die Mauern stehen (Module 01). Jetzt ziehen die Bewohner ein:

| Burg-Element | Komponente | Was es tut |
|---|---|---|
| Stallungen | Docker Engine + Compose | Container-Infrastruktur, jeder Dienst in seinem Stall |
| Thronsaal | Prod-Stack | FastAPI + PostgreSQL (das Herzstueck) |
| Burgtor | Caddy | Empfaengt Besucher, prueft Siegel (TLS), leitet weiter |
| Innere Mauern | Docker Networks | Thronsaal und Gaestehaus getrennt |
| Verzeichnisse | /opt/prod, /opt/caddy | Feste Plaetze fuer jeden Bewohner |

---

## Architektur nach Modul 02

```
Internet
   |
   | HTTPS (443)
   v
+--Caddy (Burgtor)-------------------+
|  api.chrisbuilds64.com -> :8000    |
|  (spaeter: demo.chrisbuilds64.com) |
+--------|----------------------------+
         |
         | Docker Network: caddy-net
         |
+--------|----------------------------+
|  PROD-STACK (Thronsaal)            |
|  +----------+    +-----------+     |
|  | FastAPI  |----| PostgreSQL|     |
|  | :8000    |    | :5432     |     |
|  +----------+    +-----------+     |
|        Docker Network: prod-net    |
+------------------------------------+
```

**Caddy** lebt in seinem eigenen Container und ist der einzige der von aussen erreichbar ist (Port 80/443). Die App-Container sind NICHT direkt erreichbar. Caddy spricht mit ihnen ueber ein gemeinsames Docker Network (`caddy-net`).

**Warum nicht einfach `ports: "8000:8000"`?** Weil dann jeder im Internet direkt auf die API zugreifen kann, ohne HTTPS, ohne Caddy. Das Burgtor waere nutzlos. Stattdessen: App hoert nur auf das interne Netzwerk, Caddy leitet den verschluesselten Verkehr weiter.

---

## Schritt 1: Docker installieren

Docker's offizielles Repository (nicht das Ubuntu-Paket, das ist veraltet):

```bash
# Alte Docker-Pakete entfernen (falls vorhanden)
sudo apt remove -y docker docker-engine docker.io containerd runc 2>/dev/null

# Docker GPG Key + Repository
sudo apt update
sudo apt install -y ca-certificates curl
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc

echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] \
  https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Docker installieren
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# Deploy User zur Docker-Gruppe hinzufuegen
sudo usermod -aG docker deploy
```

**WICHTIG:** Nach `usermod` muss die SSH-Session neu gestartet werden, damit die Gruppenzugehoerigkeit greift:

```bash
# Ausloggen + neu einloggen
exit
ssh strato
```

**Verifizieren:**
```bash
docker --version
docker compose version
docker run --rm hello-world
```

---

## Schritt 2: Verzeichnisstruktur anlegen

Feste Plaetze fuer jeden Burgbewohner:

```bash
# Hauptverzeichnisse
sudo mkdir -p /opt/prod
sudo mkdir -p /opt/caddy

# Spaeter (wenn benoetigt):
# sudo mkdir -p /opt/demo
# sudo mkdir -p /opt/dev

# Deploy User als Eigentuemer
sudo chown -R deploy:deploy /opt/prod /opt/caddy

# Permissions (nur Eigentuemer darf rein)
chmod 750 /opt/prod /opt/caddy
```

**Ergebnis:**
```
/opt/
├── prod/                   # Thronsaal (Production)
│   ├── docker-compose.yml  # Stack-Definition
│   ├── .env                # Secrets (chmod 400!)
│   └── backend/            # App-Code
├── caddy/                  # Burgtor
│   ├── docker-compose.yml  # Caddy-Definition
│   └── Caddyfile           # Routing-Regeln
├── demo/                   # Gaestehaus (spaeter)
└── dev/                    # Werkstatt (spaeter)
```

---

## Schritt 3: Docker Networks anlegen

Die inneren Burgmauern. Jeder Stack hat sein eigenes Netzwerk, plus ein gemeinsames fuer Caddy:

```bash
# Caddy-Netzwerk (Caddy <-> alle Stacks)
docker network create caddy-net

# Prod-Netzwerk (nur innerhalb des Prod-Stacks)
docker network create prod-net
```

**Warum zwei Netzwerke fuer Prod?**
- `prod-net`: FastAPI redet mit PostgreSQL. Intern, niemand sonst.
- `caddy-net`: Caddy redet mit FastAPI. Das ist der Weg vom Burgtor zum Thronsaal.

PostgreSQL ist NUR in `prod-net`. Caddy kann die Datenbank nicht sehen. Das ist die innere Burgmauer.

---

## Schritt 4: Caddy einrichten (Burgtor)

### Caddyfile erstellen

```bash
cat > /opt/caddy/Caddyfile << 'EOF'
# Burgtor: Routing-Regeln
# Caddy holt sich automatisch TLS-Zertifikate von Let's Encrypt.

api.chrisbuilds64.com {
    reverse_proxy prod-backend:8000
}

# Spaeter:
# demo.chrisbuilds64.com {
#     reverse_proxy demo-backend:8000
# }
EOF
```

### Caddy docker-compose.yml

```bash
cat > /opt/caddy/docker-compose.yml << 'EOF'
services:
  caddy:
    image: caddy:2-alpine
    container_name: caddy
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
      - "443:443/udp"   # HTTP/3
    volumes:
      - ./Caddyfile:/etc/caddy/Caddyfile:ro
      - caddy_data:/data       # Zertifikate
      - caddy_config:/config   # Runtime-Config
    networks:
      - caddy-net

volumes:
  caddy_data:
    name: caddy-data
  caddy_config:
    name: caddy-config

networks:
  caddy-net:
    external: true
EOF
```

**Erklaerung:**
- `caddy_data`: Hier speichert Caddy die TLS-Zertifikate. Ueberlebt Container-Neustarts.
- `caddy_config`: Runtime-Konfiguration.
- `443:443/udp`: HTTP/3 Support (schnelleres HTTPS, optional).
- `caddy-net: external: true`: Nutzt das vorher erstellte Netzwerk.

---

## Schritt 5: Prod-Stack einrichten (Thronsaal)

### Backend-Code auf den Server bringen

```bash
# Vom lokalen Rechner aus:
# Option A: Git Clone (bevorzugt)
ssh strato "cd /opt/prod && git clone https://github.com/chrisbuilds64/develop.git backend"

# Option B: Rsync (wenn lokale Aenderungen noch nicht gepusht)
# rsync -avz --exclude '.git' --exclude '__pycache__' --exclude '.env*' \
#   ./develop/backend/ strato:/opt/prod/backend/
```

### .env erstellen (Secrets)

```bash
cat > /opt/prod/.env << 'EOF'
# Production Environment
ENV=production
DEBUG=false
LOG_LEVEL=INFO

# Database
POSTGRES_DB=chrisbuilds64
POSTGRES_USER=chrisbuilds
POSTGRES_PASSWORD=HIER_SICHERES_PASSWORT_SETZEN

# Constructed (nicht manuell aendern)
DATABASE_URL=postgresql://chrisbuilds:HIER_SICHERES_PASSWORT_SETZEN@postgres:5432/chrisbuilds64
EOF

# Secrets schuetzen
chmod 400 /opt/prod/.env
```

**Passwort generieren:**
```bash
openssl rand -base64 32
```

### Production docker-compose.yml

```bash
cat > /opt/prod/docker-compose.yml << 'EOF'
services:
  # ============================================
  # PostgreSQL (Schatzkammer)
  # ============================================
  postgres:
    image: postgres:16-alpine
    container_name: prod-postgres
    restart: unless-stopped
    environment:
      POSTGRES_DB: ${POSTGRES_DB}
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER}"]
      interval: 10s
      timeout: 5s
      retries: 5
    networks:
      - prod-net
    # KEIN ports: ! Datenbank ist nur intern erreichbar.

  # ============================================
  # FastAPI Backend (Thronsaal)
  # ============================================
  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    container_name: prod-backend
    restart: unless-stopped
    environment:
      ENV: ${ENV}
      DEBUG: ${DEBUG}
      LOG_LEVEL: ${LOG_LEVEL}
      DATABASE_URL: ${DATABASE_URL}
    depends_on:
      postgres:
        condition: service_healthy
    networks:
      - prod-net     # Spricht mit PostgreSQL
      - caddy-net    # Caddy leitet Traffic hierher
    # KEIN ports: ! Nur ueber Caddy erreichbar.

volumes:
  postgres_data:
    name: prod-postgres-data

networks:
  prod-net:
    external: true
  caddy-net:
    external: true
EOF
```

**Entscheidende Unterschiede zum lokalen docker-compose.yml:**
- **Keine `ports:`** bei Backend und PostgreSQL. Nichts ist direkt von aussen erreichbar.
- **Zwei Netzwerke** beim Backend: `prod-net` (intern, DB-Zugriff) + `caddy-net` (Caddy-Zugriff).
- **Ein Netzwerk** bei PostgreSQL: nur `prod-net`. Caddy sieht die DB nicht.
- **`restart: unless-stopped`**: Container starten nach Reboot automatisch neu.
- **Kein `--reload`**: Production braucht keinen Hot-Reload.
- **Kein Volume-Mount** fuer Source-Code: Code ist im Image gebacken.

---

## Schritt 6: DNS konfigurieren

Bevor Caddy Zertifikate holen kann, muss die Domain auf den Server zeigen:

```
api.chrisbuilds64.com  ->  A-Record  ->  82.165.165.199
```

Das wird beim Domain-Provider (Strato) eingestellt. Caddy wartet geduldig und holt sich das Zertifikat sobald der DNS-Eintrag propagiert ist.

**Pruefen ob DNS funktioniert:**
```bash
# Vom lokalen Rechner:
dig api.chrisbuilds64.com +short
# Muss die Server-IP zurueckgeben
```

---

## Schritt 7: Starten

Reihenfolge ist wichtig: Erst die App (damit der Container-Name existiert auf den Caddy zeigt), dann Caddy.

```bash
# 1. Prod-Stack starten
cd /opt/prod
docker compose up -d --build

# Warten bis healthy
docker compose ps
docker compose logs -f backend    # Ctrl+C zum Beenden

# 2. Caddy starten
cd /opt/caddy
docker compose up -d

# Caddy Logs (Zertifikat-Abruf sichtbar)
docker compose logs -f caddy
```

**Verifizieren:**
```bash
# Container laufen?
docker ps

# Backend antwortet intern?
docker exec caddy wget -qO- http://prod-backend:8000/health

# HTTPS funktioniert? (vom lokalen Rechner)
curl https://api.chrisbuilds64.com/health
```

---

## Schritt 8: Deployment-Workflow

Wenn neuer Code deployed werden soll:

```bash
ssh strato

# Code aktualisieren
cd /opt/prod/backend
git pull

# Container neu bauen + starten (zero-downtime bei einem Server unrealistisch)
cd /opt/prod
docker compose up -d --build backend

# Logs pruefen
docker compose logs -f backend
```

Fuer spaeter (CI/CD): GitHub Action die bei Push auf `main` automatisch auf dem Server deployed. Kommt in Modul 05 (Ansible Phase 3).

---

## Monitoring-Cheatsheet

```bash
# Alle Container
docker ps

# Container-Logs (letzte 50 Zeilen, live)
docker compose -f /opt/prod/docker-compose.yml logs -f --tail 50

# Caddy-Logs (Zertifikate, Requests)
docker compose -f /opt/caddy/docker-compose.yml logs -f

# Resource-Verbrauch
docker stats --no-stream

# Netzwerke inspizieren (wer kann wen sehen?)
docker network inspect caddy-net --format '{{range .Containers}}{{.Name}} {{end}}'
docker network inspect prod-net --format '{{range .Containers}}{{.Name}} {{end}}'

# Caddy Zertifikate pruefen
docker exec caddy caddy list-certs 2>/dev/null || \
  docker exec caddy ls /data/caddy/certificates/

# PostgreSQL: Verbindung testen
docker exec prod-postgres pg_isready -U chrisbuilds

# Disk-Verbrauch Docker
docker system df
```

---

## Sicherheits-Checkliste Module 02

- [ ] Docker installiert (offizielle Quelle, nicht Ubuntu-Paket)
- [ ] Deploy User in Docker-Gruppe
- [ ] `/opt/prod/.env` mit chmod 400
- [ ] PostgreSQL KEIN `ports:` (nur intern)
- [ ] Backend KEIN `ports:` (nur ueber Caddy)
- [ ] Caddy HTTPS funktioniert (Zertifikat von Let's Encrypt)
- [ ] Docker Networks getrennt (prod-net, caddy-net)
- [ ] `restart: unless-stopped` bei allen Containern
- [ ] DNS A-Record zeigt auf Server-IP
- [ ] `docker ps` zeigt alle Container als healthy/running

---

## Fehlerbehebung

**Caddy bekommt kein Zertifikat:**
- DNS A-Record pruefen: `dig api.chrisbuilds64.com +short`
- Port 80 offen? `sudo ufw status` (muss HTTP erlauben)
- Caddy Logs: `docker compose -f /opt/caddy/docker-compose.yml logs caddy`
- Let's Encrypt Rate Limits: max 5 Zertifikate pro Domain pro Woche

**Backend startet nicht:**
- Logs: `docker compose -f /opt/prod/docker-compose.yml logs backend`
- DB erreichbar? `docker exec prod-backend python -c "import urllib.request; print('ok')"`
- Migrations gelaufen? Ggf. manuell: `docker exec prod-backend alembic upgrade head`

**Container restartet staendig:**
- `docker inspect prod-backend --format '{{.State.ExitCode}}'`
- OOM? `docker stats --no-stream` (Memory-Limit pruefen)
- Healthcheck: `docker inspect prod-backend --format '{{.State.Health.Status}}'`

---

## Was kommt danach

| Modul | Inhalt | Wann |
|---|---|---|
| 03 | Monitoring (Uptime Kuma) | Wenn Prod laeuft |
| 04 | Backup (Borgmatic + Storage Box) | Wenn Daten da sind |
| 05 | Ansible Playbooks fuer 02-04 | Wenn alles stabil |
| 06 | Demo-Stack (Gaestehaus) | Bei Bedarf |

---

*Erstellt: 3. April 2026 (Hacking Day, Koeln)*
*Basiert auf: secure-server-stack.md, develop/docker-compose.yml, develop/backend/Dockerfile*
