# Runbook: Troubleshooting (Der Burgwächter-Leitfaden)

**Zweck:** Schnelle Diagnose wenn ein User nicht zugreifen kann.
**Zielgruppe:** Admin (du), bei Anruf/Alert.
**Reihenfolge:** Von oben nach unten durchgehen. Erster Treffer = wahrscheinliche Ursache.

---

## Schnell-Checkliste

| # | Check | Befehl (lokal) | Befehl (Server) | Typischer Fix |
|---|---|---|---|---|
| 1 | Server erreichbar? | `ping 82.165.165.199` | - | Strato Cloud-Konsole |
| 2 | SSH geht? | `ssh strato uptime` | - | Cloud-Konsole, Key pruefen |
| 3 | IP gebannt? | - | `sudo fail2ban-client get sshd banned` | `sudo fail2ban-client set sshd unbanip IP` |
| 4 | Container laufen? | - | `docker ps` | `docker compose up -d` im jeweiligen Verzeichnis |
| 5 | Disk voll? | - | `df -h` | Logs/Images aufraeumen |
| 6 | Port offen? | `nc -zv 82.165.165.199 443` | `sudo ss -tlnp` | `sudo ufw allow PORT` |
| 7 | Zertifikat ok? | `echo \| openssl s_client -connect api.chrisbuilds64.com:443 2>/dev/null \| openssl x509 -dates -noout` | - | Caddy neustarten |
| 8 | DNS stimmt? | `dig api.chrisbuilds64.com +short` | - | A-Record bei Strato pruefen |

---

## 1. Server erreichbar?

```bash
# Vom lokalen Rechner
ping 82.165.165.199
ssh strato "uptime"
```

**Kein Ping:** Server down, Netzwerk-Problem bei Strato, oder ICMP geblockt (bei uns nicht).
**Kein SSH:** Server laeuft evtl., aber SSH-Dienst oder Firewall blockiert.
**Fix:** Strato Kundenportal → Cloud-Konsole (KVM/VNC Zugang).

---

## 2. Laufen die Dienste?

```bash
# Auf dem Server
systemctl status ssh
systemctl status docker
systemctl status fail2ban
sudo ufw status
```

### Container pruefen

```bash
# Alle laufenden Container
docker ps

# Auch gestoppte/gecrashte
docker ps -a

# Einzelne Container-Logs (letzte 50 Zeilen, live)
docker compose -f /opt/prod/docker-compose.yml logs --tail 50 -f backend
docker compose -f /opt/prod/docker-compose.yml logs --tail 50 -f postgres
docker compose -f /opt/caddy/docker-compose.yml logs --tail 50 -f caddy
```

### Container neu starten

```bash
# Einzelner Container
docker compose -f /opt/prod/docker-compose.yml restart backend

# Ganzer Stack
cd /opt/prod && docker compose down && docker compose up -d
cd /opt/caddy && docker compose down && docker compose up -d
```

---

## 3. User-IP gebannt? (Fail2Ban)

Haeufigster Grund fuer "ploetzlich geht nichts mehr". Fail2Ban sperrt IPs nach zu vielen fehlgeschlagenen SSH-Versuchen.

```bash
# Wer ist gebannt?
sudo fail2ban-client status sshd

# Gebannte IPs auflisten
sudo fail2ban-client get sshd banned

# IP entbannen
sudo fail2ban-client set sshd unbanip 203.0.113.42

# Fail2Ban Bans auch in UFW sichtbar
sudo ufw status numbered
```

**Achtung:** Wenn die eigene IP gebannt ist, kommst du per SSH nicht drauf. Dann: Strato Cloud-Konsole nutzen.

---

## 4. Netzwerk-Diagnose

### Von aussen (lokaler Rechner)

```bash
# DNS aufloesen
dig api.chrisbuilds64.com +short

# TCP-Port erreichbar?
nc -zv 82.165.165.199 22    # SSH
nc -zv 82.165.165.199 80    # HTTP
nc -zv 82.165.165.199 443   # HTTPS

# HTTPS-Verbindung testen (ausfuehrlich)
curl -v https://api.chrisbuilds64.com/health

# Nur HTTP-Status
curl -s -o /dev/null -w "%{http_code}" https://api.chrisbuilds64.com/health
```

### Auf dem Server

```bash
# Welche Ports hoeren?
sudo ss -tlnp

# Health intern pruefen (ohne Caddy)
docker exec caddy wget -qO- http://prod-backend:8000/health

# Health direkt im Backend-Container
docker exec prod-backend curl -s http://localhost:8000/health
```

---

## 5. Ressourcen

```bash
# CPU + RAM Ueberblick
top -bn1 | head -20

# RAM + Swap
free -h

# Disk (voll = alles steht!)
df -h

# Was frisst den Platz?
du -sh /var/log/*
du -sh /opt/*

# Docker-spezifisch
docker stats --no-stream     # Container-Ressourcen
docker system df             # Docker Disk-Verbrauch
```

### Disk aufraeumen

```bash
# Alte Docker Images/Container/Volumes (vorsichtig!)
docker system prune          # Gestoppte Container + unbenutzte Images
docker system prune -a       # ALLES unbenutzte (auch Images die nicht laufen)
docker volume prune          # Unbenutzte Volumes (ACHTUNG: Daten!)

# Alte Logs
sudo journalctl --vacuum-time=7d    # Logs aelter als 7 Tage loeschen
```

---

## 6. Logs lesen

### System-Logs

```bash
# Letzte Stunde (alles)
journalctl -xe --since "1 hour ago"

# SSH spezifisch
journalctl -u ssh --since today
sudo tail -100 /var/log/auth.log

# Fail2Ban
journalctl -u fail2ban --since today

# System allgemein
sudo tail -100 /var/log/syslog
```

### Docker/App-Logs

```bash
# Caddy (Requests, TLS, Fehler)
docker logs caddy --since 1h

# Backend (App-Fehler, Requests)
docker logs prod-backend --since 1h

# PostgreSQL (Queries, Connections)
docker logs prod-postgres --since 1h

# Live mitlesen (Ctrl+C zum Beenden)
docker logs -f caddy
docker logs -f prod-backend
```

---

## 7. TLS/Zertifikat-Probleme

```bash
# Zertifikat Ablaufdatum pruefen (lokal)
echo | openssl s_client -connect api.chrisbuilds64.com:443 2>/dev/null | openssl x509 -dates -noout

# Caddy Zertifikate anzeigen
docker exec caddy ls /data/caddy/certificates/

# Caddy Logs nach TLS-Fehlern durchsuchen
docker logs caddy 2>&1 | grep -i "certificate\|tls\|error"
```

### Zertifikat erneuern

Caddy erneuert automatisch. Falls trotzdem Probleme:

```bash
# Caddy neustarten (holt neues Zertifikat)
cd /opt/caddy && docker compose restart caddy

# Caddy komplett neu (Zertifikate werden neu geholt)
cd /opt/caddy && docker compose down
docker volume rm caddy-data caddy-config
docker compose up -d
```

---

## 8. Live-Traffic beobachten

### Caddy Access Logs

Caddy loggt jeden Request wenn Access Logging aktiviert ist:

```bash
# Live mitlesen
docker logs -f caddy

# Nach Status-Codes filtern
docker logs caddy 2>&1 | grep '"status":5'    # 5xx Fehler
docker logs caddy 2>&1 | grep '"status":4'    # 4xx Fehler
```

### Netzwerk-Ebene

```bash
# Live Bandbreite pro Interface
sudo apt install -y nload
nload eth0

# Einzelne Pakete sehen (TCP Port 443)
sudo tcpdump -i eth0 port 443 -n -c 20

# Aktive Verbindungen
ss -tn | grep ESTAB
```

---

## Eskalation

Wenn nichts hilft:

1. **Strato Cloud-Konsole:** KVM/VNC Zugang, auch wenn SSH geblockt ist
2. **Server neustarten:** `sudo reboot` (letztes Mittel, Container starten automatisch via `restart: unless-stopped`)
3. **Komplett-Rebuild:** Ansible-Playbooks neu ausfuehren (foundation.yml + docker-caddy.yml). Der Bauplan ist die Wahrheit.

---

*Erstellt: 3. April 2026 (Hackathon Session 3, Koeln)*
