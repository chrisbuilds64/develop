# Module 01: Foundation (Burgfundament)

**Status:** Getestet auf Strato VPS (Ubuntu 24.04, 2026-04-03)
**Dauer:** ~30 Minuten
**Voraussetzung:** Frischer Ubuntu 24.04 Server mit Root-Zugang
**Ergebnis:** Gehärteter Server mit SSH Key-Auth, Firewall, Fail2Ban, Auto-Updates

---

## Was dieses Modul macht

Alle Schritte die VOR Docker/Caddy/Applikation kommen. Das Fundament der Burg:

| Burg-Element | Komponente | Was es tut |
|---|---|---|
| Geheimgang | SSH Key-Auth + Deploy User | Nur ein Schlüssel öffnet die Tür |
| Burggraben | UFW Firewall | Nur 3 Ports offen (22, 80, 443) |
| Wachturm | Fail2Ban | 3 Fehlversuche = 1h gesperrt |
| Vorratskeller | Swap | Notfall-RAM wenn Speicher knapp |
| Uhr | Timezone | Logs in lokaler Zeit |
| Wartungstruppe | unattended-upgrades | Security-Patches automatisch |

---

## Schritt 0: SSH Key erzeugen (lokal, einmalig)

Auf deinem lokalen Rechner, NICHT auf dem Server:

```bash
ssh-keygen -t ed25519 -C "dein-label"
```

- Speicherort: z.B. `~/.ssh/mein_server`
- Passphrase: empfohlen (schützt Key bei Laptop-Diebstahl)

Ergebnis: zwei Dateien.
```
~/.ssh/mein_server       # Private Key (NIE teilen, chmod 600)
~/.ssh/mein_server.pub   # Public Key (kommt auf den Server)
```

**Warum ed25519?** Moderner als RSA, kürzere Keys, gleiche Sicherheit, schneller.

**Public Key bei Neuinstallation:** Im Webpanel (Strato/Hetzner) ins SSH-Key Feld kopieren:
```bash
cat ~/.ssh/mein_server.pub
```

---

## Schritt 1: SSH Config lokal einrichten

Damit du nicht jedes Mal IP, Port, User und Key tippen musst:

```bash
# ~/.ssh/config
Host mein-server
    HostName SERVER_IP
    User root
    IdentityFile ~/.ssh/mein_server
```

Danach reicht: `ssh mein-server`

**Permissions:**
```bash
chmod 600 ~/.ssh/config
chmod 600 ~/.ssh/mein_server
```

---

## Schritt 2: Erster Login + known_hosts

```bash
ssh mein-server
```

Beim ersten Mal kommt:
```
The authenticity of host 'SERVER_IP' can't be established.
ED25519 key fingerprint is SHA256:...
Are you sure you want to continue connecting (yes/no)?
```

Das ist normal. `yes` eingeben. Der Fingerprint wird in `~/.ssh/known_hosts` gespeichert. Bei Neuinstallation des Servers ändert sich der Fingerprint. Dann:

```bash
ssh-keygen -R SERVER_IP
```

Das löscht den alten Eintrag und beim nächsten Login wird der neue akzeptiert.

---

## Schritt 3: Deploy User erstellen

Auf dem Server (als root):

```bash
# User erstellen (kein Passwort-Login)
adduser --disabled-password --gecos "Deploy User" deploy

# Sudo-Rechte geben
usermod -aG sudo deploy

# SSH Key vom root kopieren
mkdir -p /home/deploy/.ssh
cp /root/.ssh/authorized_keys /home/deploy/.ssh/authorized_keys
chown -R deploy:deploy /home/deploy/.ssh
chmod 700 /home/deploy/.ssh
chmod 600 /home/deploy/.ssh/authorized_keys

# Passwortloses sudo
echo "deploy ALL=(ALL) NOPASSWD:ALL" > /etc/sudoers.d/deploy
chmod 440 /etc/sudoers.d/deploy
```

**Testen** (vom lokalen Rechner, neues Terminal):
```bash
ssh -i ~/.ssh/mein_server deploy@SERVER_IP
sudo whoami    # Muss "root" ausgeben
```

**Erst weitermachen wenn der deploy-Login funktioniert!**

---

## Schritt 4: SSH Hardening

Auf dem Server (als root oder deploy mit sudo):

```bash
# Backup der Original-Config
sudo cp /etc/ssh/sshd_config /etc/ssh/sshd_config.backup

# Root Login aus
sudo sed -i 's/^#*PermitRootLogin.*/PermitRootLogin no/' /etc/ssh/sshd_config

# Passwort-Auth aus
sudo sed -i 's/^#*PasswordAuthentication.*/PasswordAuthentication no/' /etc/ssh/sshd_config

# Nur deploy User erlauben + Limits
echo "" | sudo tee -a /etc/ssh/sshd_config
echo "# Security Hardening" | sudo tee -a /etc/ssh/sshd_config
echo "AllowUsers deploy" | sudo tee -a /etc/ssh/sshd_config
echo "MaxAuthTries 3" | sudo tee -a /etc/ssh/sshd_config
echo "LoginGraceTime 30" | sudo tee -a /etc/ssh/sshd_config

# Config prüfen (WICHTIG: bei Fehler NICHT neustarten!)
sudo sshd -t && echo "Config OK" || echo "FEHLER! Nicht neustarten!"

# Neustart (nur wenn Config OK)
sudo systemctl restart ssh
```

**Lokale SSH Config anpassen** (User ist jetzt deploy, nicht mehr root):
```bash
# ~/.ssh/config
Host mein-server
    HostName SERVER_IP
    User deploy
    IdentityFile ~/.ssh/mein_server
```

**Verifizieren:**
```bash
# Das muss funktionieren:
ssh mein-server "whoami"    # deploy

# Das darf NICHT funktionieren:
ssh -i ~/.ssh/mein_server root@SERVER_IP    # Permission denied
```

---

## Schritt 5: UFW Firewall (Burggraben)

```bash
# Default: alles zu
sudo ufw default deny incoming
sudo ufw default allow outgoing

# Drei Zugbrücken öffnen
sudo ufw allow 22/tcp comment 'SSH'
sudo ufw allow 80/tcp comment 'HTTP'
sudo ufw allow 443/tcp comment 'HTTPS'

# Aktivieren
sudo ufw --force enable

# Status prüfen
sudo ufw status verbose
```

**WICHTIG:** SSH (Port 22) ZUERST erlauben, DANN aktivieren. Sonst sperrst du dich aus.

**Weitere Ports** (später, bei Bedarf):
```bash
sudo ufw allow 8000/tcp comment 'FastAPI Dev'    # Nur temporär!
sudo ufw delete allow 8000/tcp                    # Wieder schliessen
```

---

## Schritt 6: Fail2Ban (Wachturm)

```bash
# Installieren
sudo apt install -y fail2ban

# Config erstellen (nie jail.conf editieren!)
sudo tee /etc/fail2ban/jail.local << 'EOF'
[DEFAULT]
bantime = 3600
findtime = 600
maxretry = 3

[sshd]
enabled = true
port = ssh
logpath = /var/log/auth.log
maxretry = 3
bantime = 3600
EOF

# Starten
sudo systemctl restart fail2ban
sudo systemctl enable fail2ban

# Status prüfen
sudo fail2ban-client status sshd
```

**Regeln:**
- 3 Fehlversuche innerhalb von 10 Minuten = IP gesperrt für 1 Stunde
- `jail.local` überlebt Updates, `jail.conf` nicht

**Monitoring-Befehle:**
```bash
# Wer ist gebannt?
sudo fail2ban-client status sshd

# Alle gebannten IPs
sudo fail2ban-client banned

# IP manuell entbannen
sudo fail2ban-client set sshd unbanip 1.2.3.4

# Fail2Ban Log
sudo tail -50 /var/log/fail2ban.log
```

---

## Schritt 7: System-Updates

```bash
# Alle Updates installieren (frischer Server, unkritisch)
sudo apt update && sudo apt upgrade -y
```

**Auf Produktionssystemen:** NICHT blind `apt upgrade` ausführen!

**Update-Strategie für Production:**
1. **unattended-upgrades** (Minimum): Nur Security-Patches, automatisch, brechen fast nie etwas
2. **Staged Updates**: Erst auf Dev/Demo testen, 24-48h laufen lassen, dann Production
3. **Pinned Versions**: Paketversionen einfrieren, Updates nur im Wartungsfenster nach Backup/Snapshot

**Reboot nötig?**
```bash
cat /var/run/reboot-required 2>/dev/null || echo "Kein Reboot nötig"
```

---

## Schritt 8: Timezone

```bash
# Aktuelle Timezone prüfen
timedatectl

# Auf Europe/Berlin setzen
sudo timedatectl set-timezone Europe/Berlin

# Verifizieren
timedatectl
```

**Warum?** Logs, Cronjobs und Monitoring zeigen lokale Zeit. Datenbanken speichern intern UTC (das ist korrekt und bleibt so).

---

## Schritt 9: Swap (Vorratskeller)

```bash
# 4 GB Swap-Datei erstellen
sudo fallocate -l 4G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile

# Permanent machen (überlebt Reboot)
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab

# Prüfen
free -h | grep Swap
```

**Faustregeln für Swap-Größe:**
- Server mit 2-4 GB RAM: Swap = RAM (also 2-4 GB)
- Server mit 8-32 GB RAM: Swap = 4 GB (Notfallpuffer reicht)
- Server mit 64+ GB RAM: Swap = 2 GB oder gar kein Swap

---

## Schritt 10: unattended-upgrades (Wartungstruppe)

```bash
# Installieren (oft schon vorinstalliert)
sudo apt install -y unattended-upgrades

# Prüfen ob aktiv
sudo systemctl status apt-daily-upgrade.timer
```

Läuft als Systemd Timer, täglich ab 6:00 Uhr (+ zufälliger Versatz bis 7:00). Installiert nur Security-Patches, keine Feature-Updates.

**Prüfen was erlaubt ist:**
```bash
sudo grep -v '//' /etc/apt/apt.conf.d/50unattended-upgrades | grep -A5 'Allowed-Origins'
```

Muss enthalten: `${distro_id}:${distro_codename}-security`

---

## Monitoring-Cheatsheet

Nach der Installation regelmäßig prüfen:

```bash
# SSH: Wer hämmert an die Tür?
sudo grep -c 'Failed\|Invalid user' /var/log/auth.log

# SSH: Top Angreifer-IPs
sudo grep 'Invalid user\|Failed' /var/log/auth.log \
  | grep -oE '[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+' \
  | sort | uniq -c | sort -rn | head -10

# Fail2Ban: Wer ist gebannt?
sudo fail2ban-client status sshd

# Firewall: Was ist offen?
sudo ufw status

# System: RAM + Swap
free -h

# System: Disk
df -h

# System: Reboot nötig?
cat /var/run/reboot-required 2>/dev/null || echo "Nein"

# Updates: Was steht an?
apt list --upgradable 2>/dev/null
```

---

## Checkliste: Foundation komplett?

- [ ] SSH Key-Pair erzeugt (ed25519)
- [ ] Deploy User erstellt mit SSH Key + sudo
- [ ] Root-Login deaktiviert
- [ ] Passwort-Auth deaktiviert
- [ ] AllowUsers auf deploy beschränkt
- [ ] UFW aktiv (nur 22, 80, 443)
- [ ] Fail2Ban aktiv (SSH Jail, 3 Versuche, 1h Ban)
- [ ] System-Updates installiert
- [ ] Timezone gesetzt (Europe/Berlin)
- [ ] Swap eingerichtet (4 GB)
- [ ] unattended-upgrades aktiv

**Wenn alle Punkte erledigt:** Weiter mit Module 02 (Docker + Caddy).
