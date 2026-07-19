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
| Burgmauern | Kernel Hardening (sysctl) | ICMP-Angriffe, Spoofing, Injection blockiert |
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

Auf dem Server (als root oder deploy mit sudo).

**Warum Drop-in statt Hauptdatei editieren?** Die `sshd_config` wird bei SSH-Updates überschrieben. Dateien in `sshd_config.d/` überleben Updates, sind sauber getrennt und reversibel (Datei löschen = alles zurück auf Default).

```bash
# Backup der Original-Config (Sicherheitsnetz)
sudo cp /etc/ssh/sshd_config /etc/ssh/sshd_config.backup

# Drop-in-Datei mit allen Hardening-Parametern
sudo tee /etc/ssh/sshd_config.d/99-hardening.conf << 'EOF'
# === Access Control ===
PermitRootLogin no
AllowUsers deploy
PasswordAuthentication no
PermitEmptyPasswords no
HostbasedAuthentication no
KbdInteractiveAuthentication no
IgnoreRhosts yes

# === Brute-Force Limits ===
MaxAuthTries 3
LoginGraceTime 30
MaxStartups 10:30:60

# === Session ===
ClientAliveInterval 300
ClientAliveCountMax 2
X11Forwarding no
EOF

# Config prüfen (WICHTIG: bei Fehler NICHT neustarten!)
sudo sshd -t && echo "Config OK" || echo "FEHLER! Nicht neustarten!"

# Neustart (nur wenn Config OK)
sudo systemctl reload ssh
```

**Parameter erklärt:**
- `MaxStartups 10:30:60`: Ab 10 unauthentifizierten Verbindungen werden 30% abgelehnt, ab 60 alle. Schützt gegen Connection-Flooding.
- `ClientAliveInterval 300`: Server pingt Client alle 5 Minuten. Nach 2 ausbleibenden Antworten (10 Min) wird die Verbindung getrennt. Verhindert Zombie-Sessions.
- `X11Forwarding no`: Kein Grafik-Forwarding. Auf einem Server ohne GUI eine unnötige Angriffsfläche.

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
# Default: alles zu (incoming UND forward!)
sudo ufw default deny incoming
sudo ufw default deny forward
sudo ufw default allow outgoing

# Loopback erlauben (lokale Dienste brauchen das)
sudo ufw allow in on lo

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

**Warum `deny forward`?** Docker manipuliert iptables direkt und umgeht UFW-Regeln. Mit `deny forward` als Default werden Docker-Container nicht versehentlich ans Internet durchgereicht. Wer Docker-Ports nach außen braucht, muss das explizit über Caddy routen.

**Warum Loopback?** Dienste auf dem Server kommunizieren oft über `localhost` (z.B. App -> Datenbank). Ohne Loopback-Regel blockiert UFW diesen internen Verkehr.

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
banaction = ufw

[sshd]
enabled = true
port = ssh
filter = sshd
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
- `banaction = ufw`: Fail2Ban sperrt IPs über UFW-Regeln statt iptables direkt. Ohne das können sich UFW und iptables gegenseitig überschreiben.

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

## Schritt 10: Kernel-Härtung (Burgmauern)

Der Kernel ist das Betriebssystem unter dem Betriebssystem. Diese Parameter schließen Angriffsvektoren die über Netzwerk-Tricks funktionieren: gefälschte Absenderadressen, umgeleiteter Verkehr, Prozess-Injection.

```bash
sudo tee /etc/sysctl.d/99-hardening.conf << 'EOF'
# === Netzwerk (IPv4) ===
# ICMP-Redirects: Angreifer kann Verkehr umleiten (Man-in-the-Middle)
net.ipv4.conf.all.accept_redirects = 0
net.ipv4.conf.default.accept_redirects = 0
net.ipv4.conf.all.send_redirects = 0
net.ipv4.conf.default.send_redirects = 0

# Source-Routing: Absender bestimmt Route (Firewall-Umgehung)
net.ipv4.conf.all.accept_source_route = 0
net.ipv4.conf.default.accept_source_route = 0

# Martian-Logging: Pakete mit unmöglichen Absenderadressen loggen
net.ipv4.conf.all.log_martians = 1
net.ipv4.conf.default.log_martians = 1

# Strict Reverse Path: Pakete nur akzeptieren wenn Absenderadresse plausibel
net.ipv4.conf.all.rp_filter = 1
net.ipv4.conf.default.rp_filter = 1

# SYN-Flood-Schutz (oft schon aktiv, explizit setzen)
net.ipv4.tcp_syncookies = 1

# Broadcast-ICMP ignorieren (Smurf-Angriff)
net.ipv4.icmp_echo_ignore_broadcasts = 1

# Bogus ICMP-Fehlermeldungen ignorieren
net.ipv4.icmp_ignore_bogus_error_responses = 1

# === Netzwerk (IPv6) ===
net.ipv6.conf.all.accept_redirects = 0
net.ipv6.conf.default.accept_redirects = 0
net.ipv6.conf.all.accept_source_route = 0
net.ipv6.conf.default.accept_source_route = 0

# === Kernel ===
# ASLR voll aktiv (Speicher-Layout zufällig)
kernel.randomize_va_space = 2

# Magic SysRq aus (Tastenkombination für Kernel-Kommandos)
kernel.sysrq = 0

# Kernel-Log nur für root
kernel.dmesg_restrict = 1

# Kernel-Pointer komplett verstecken
kernel.kptr_restrict = 2

# ptrace einschränken (verhindert Process-Injection)
kernel.yama.ptrace_scope = 2

# Unprivilegiertes BPF deaktivieren
kernel.unprivileged_bpf_disabled = 1

# perf nur für root
kernel.perf_event_paranoid = 3

# === Dateisystem ===
# Core-Dumps von SUID-Programmen verhindern
fs.suid_dumpable = 0

# Hardlink- und Symlink-Schutz
fs.protected_hardlinks = 1
fs.protected_symlinks = 1
EOF

# Aktivieren
sudo sysctl -p /etc/sysctl.d/99-hardening.conf

# Verifizieren (Stichprobe)
sysctl net.ipv4.conf.all.accept_redirects    # Muss 0 sein
sysctl kernel.yama.ptrace_scope              # Muss 2 sein
```

**Burg-Analogie:** Die Firewall (UFW) ist der Burggraben. Der Kernel-Hardening ist die Dicke der Burgmauern selbst. Ohne diese Parameter könnte ein Angreifer den Verkehr umleiten (ICMP-Redirect = gefälschte Wegweiser aufstellen), Absenderadressen fälschen (Spoofing = sich als Bote des Königs verkleiden), oder laufende Prozesse kapern (ptrace = einem Wachmann ins Ohr flüstern).

---

## Schritt 11: unattended-upgrades (Wartungstruppe)

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

### Setup

- [ ] SSH Key-Pair erzeugt (ed25519)
- [ ] Deploy User erstellt mit SSH Key + sudo
- [ ] SSH gehärtet (Drop-in: Root aus, Passwort aus, AllowUsers, Limits)
- [ ] UFW aktiv (deny incoming + forward, allow 22/80/443 + loopback)
- [ ] Fail2Ban aktiv (SSH Jail, 3 Versuche, 1h Ban, banaction=ufw)
- [ ] Kernel gehärtet (sysctl: ICMP, Spoofing, ptrace, BPF)
- [ ] System-Updates installiert
- [ ] Timezone gesetzt (Europe/Berlin)
- [ ] Swap eingerichtet (4 GB)
- [ ] unattended-upgrades aktiv

### Verifikation (von einem anderen Rechner aus!)

| Test | Erwartung |
|------|-----------|
| `ssh deploy@SERVER_IP` (mit Key) | Erfolgreich |
| `ssh root@SERVER_IP` | Permission denied |
| `ssh -o PasswordAuthentication=yes deploy@SERVER_IP` | Permission denied |
| `sudo ufw status` | 22, 80, 443 offen, Rest zu |
| `sudo fail2ban-client status sshd` | Jail aktiv |
| `sysctl net.ipv4.conf.all.accept_redirects` | 0 |
| Port-Scan von außen: `nmap -sS SERVER_IP` | Nur 22, 80, 443 offen |

**Wenn alle Punkte erledigt:** Weiter mit Module 02 (Docker + Caddy).
