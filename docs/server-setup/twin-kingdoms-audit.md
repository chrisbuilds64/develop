# The Twin Kingdoms: Burg Rheinstein vs. Burg Nordwall

**Datum:** 3. April 2026
**Status:** Vergleichs-Audit beider Burgen mit Handlungsanweisungen
**Zweck:** Zwei Burgherren bauen gleichzeitig ihre Festungen. Was kann der eine vom anderen lernen?

---

## Die Königreiche

```
                KÖNIGREICH RHEINLAND                    KÖNIGREICH NORDWALL
                ~~~~~~~~~~~~~~~~~~~                     ~~~~~~~~~~~~~~~~~~

        Burgherr: Christian                     Burgherr: Lars
        Burg:     RHEINSTEIN                    Burg:     NORDWALL
        Lage:     Strato (Deutschland)          Lage:     Hetzner (Helsinki)
        Terrain:  Ubuntu 24.04                  Terrain:  Ubuntu 24.04
        Zweck:    AI Backend + Content          Zweck:    (in Aufbau)

        +------------------+                    +------------------+
        |   RHEINSTEIN     |                    |    NORDWALL      |
        |   ============   |                    |    =========     |
        |  /            \  |                    |  /            \  |
        | | Thronsaal   | |                    | | (leer)      | |
        | | (Prod API)  | |                    | |             | |
        |  \            /  |                    |  \            /  |
        |   ‾‾‾‾‾‾‾‾‾‾‾   |                    |   ‾‾‾‾‾‾‾‾‾‾‾   |
        |  Burggraben: JA  |                    |  Burggraben: NEU |
        |  Wachturm: JA    |                    |  Wachturm: NEU   |
        |  Mauern: NEU     |                    |  Mauern: NEIN    |
        +------------------+                    +------------------+
```

---

## Befund-Vergleich

### Was BEIDE Burgen haben (Grundmauern stehen)

| Element | Rheinstein | Nordwall | Status |
|---------|-----------|----------|--------|
| SSH Key (ed25519) | Ja | Ja | Beide sicher |
| unattended-upgrades | Ja | Ja | Patches automatisch |
| ASLR (Speicher-Schutz) | Ja (Default) | Ja (Default) | Kernel-Standard |
| tcp_syncookies | Ja | Ja | SYN-Flood-Schutz |
| AppArmor | Ja (Default) | Ja (24 Profile) | Nordwall explizit geprueft |

---

### Was RHEINSTEIN hat, was NORDWALL fehlt

Diese Elemente sollte Lars in Nordwall nachrüsten:

#### 1. Vorratskeller (Swap)

**Problem:** Nordwall hat keinen Notfall-Vorrat. Wenn der Thronsaal (Applikation) zu viel RAM frisst, stuerzt alles ab. Kein Puffer, kein Fallback.

**Handlung Lars:**
```bash
sudo fallocate -l 4G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
free -h | grep Swap
```

**Faustregeln:** 8 GB RAM = 4 GB Swap. Nicht mehr, nicht weniger.

---

#### 2. Burguhr (Timezone)

**Problem:** Nordwall steht in Helsinki, die Uhr zeigt vermutlich UTC oder finnische Zeit. Wenn Lars nachts in den Logs nach einem Vorfall sucht, muss er im Kopf Zeitzonen umrechnen.

**Handlung Lars:**
```bash
sudo timedatectl set-timezone Europe/Berlin
timedatectl
```

---

#### 3. Wachturm-Handbuch (Monitoring-Cheatsheet)

**Problem:** Nordwall hat ein exzellentes Audit. Aber wer patrouilliert nach dem Audit? Es fehlen die täglichen Kontroll-Befehle.

**Handlung Lars:** Diese Befehle irgendwo griffbereit ablegen:

```bash
# Wer hämmert an die Tür?
sudo grep -c 'Failed\|Invalid user' /var/log/auth.log

# Top Angreifer-IPs
sudo grep 'Invalid user\|Failed' /var/log/auth.log \
  | grep -oE '[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+' \
  | sort | uniq -c | sort -rn | head -10

# Wer ist gebannt?
sudo fail2ban-client status sshd

# Was ist offen?
sudo ufw status

# RAM + Swap + Disk
free -h && df -h

# Reboot nötig?
cat /var/run/reboot-required 2>/dev/null || echo "Nein"
```

---

#### 4. Lokale Burgtor-Konfiguration (SSH Config + known_hosts)

**Problem:** Lars muss jedes Mal IP, User und Key eintippen. Und wenn der Server neu installiert wird, scheitert SSH wegen geändertem Fingerprint.

**Handlung Lars:** Auf seinem lokalen Rechner:

```bash
# ~/.ssh/config
Host nordwall
    HostName 204.168.203.39
    User admin
    IdentityFile ~/.ssh/hetzner_key
```

Danach reicht: `ssh nordwall`

Bei Server-Neuinstallation: `ssh-keygen -R 204.168.203.39`

---

### Was NORDWALL hat, was RHEINSTEIN fehlte (jetzt nachgerüstet)

Diese Punkte aus Lars' Audit haben wir in Rheinsteins Modul 01 übernommen:

| Element | Vorher (Rheinstein) | Nachher (aus Nordwall gelernt) |
|---------|-------------------|-------------------------------|
| UFW forward | Nur `deny incoming` | Jetzt auch `deny forward` (Docker-Schutz) |
| UFW loopback | Fehlte | `allow in on lo` |
| SSH Config | `sed` auf Hauptdatei | Drop-in `/etc/ssh/sshd_config.d/99-hardening.conf` |
| SSH Parameter | Nur 3 (Root, Password, AllowUsers) | Jetzt 11 (+ MaxStartups, ClientAlive, X11, etc.) |
| fail2ban banaction | Default (iptables) | `banaction = ufw` |
| Kernel Hardening | Fehlte komplett | Neuer Schritt 10 (sysctl: ICMP, Spoofing, ptrace, BPF) |
| Verifikation | Nur Checkliste | Jetzt mit konkreten Tests (nmap, SSH-Probes) |

**Fazit:** Lars' Audit war der Burginspektor, den Rheinstein gebraucht hat.

---

### Was NORDWALL plant, was RHEINSTEIN bewusst nicht macht

#### VPN-Tunnel (WireGuard)

Lars baut einen geheimen Tunnel zur Burg: SSH wird komplett von der öffentlichen Straße genommen, nur noch über WireGuard erreichbar. Wer die Burg betreten will, muss erst durch den Tunnel.

**Nordwall-Ansatz:** Internet -> WireGuard (51820) -> SSH (nur über VPN)
**Rheinstein-Ansatz:** Internet -> SSH (22) + Fail2Ban + Key-Only

| | Nordwall (VPN) | Rheinstein (kein VPN) |
|---|---|---|
| SSH von außen sichtbar? | Nein | Ja |
| Brute-Force möglich? | Nein (Port zu) | Ja (aber Key-Only + Ban) |
| Komplexität | Höher (VPN-Client nötig) | Niedriger |
| Mobiler Zugriff | VPN-App nötig | Direkt per SSH |
| Wenn VPN ausfällt | Kein Zugang (nur Konsole) | SSH funktioniert weiter |

**Bewertung:** Beide Ansätze sind valide. Nordwall ist sicherer (SSH unsichtbar). Rheinstein ist einfacher (KISS). Für einen Ein-Admin-Server mit Key-Auth + Fail2Ban ist Rheinsteins Ansatz vertretbar. Sobald mehrere Admins Zugang brauchen oder sensiblere Daten verarbeitet werden, wird VPN zur Pflicht.

---

#### auditd (Burgchronist)

Nordwall plant einen Chronisten, der jede Änderung an kritischen Dokumenten protokolliert: Wer hat die Zugangsliste geändert? Wer hat die Wachturm-Config angefasst?

**Rheinstein:** Erstmal nicht. Journald + Fail2Ban-Logs reichen für den Start. Wenn Rheinstein wächst (mehr Dienste, mehr User), wird ein Chronist nötig.

**Handlung (beide, optional):**
```bash
sudo apt install -y auditd audispd-plugins
# Audit-Regeln: siehe Lars' Dokument Phase 5
```

---

## Handlungsplan: Wer macht was?

### Lars (Burg Nordwall)

Sein Audit ist hervorragend. Die Massnahmen sind klar priorisiert. Zusätzlich empfohlen:

| Nr | Was | Prio | Aufwand |
|----|-----|------|---------|
| L1 | Swap einrichten (4 GB) | HOCH | 2 Min |
| L2 | Timezone setzen (Europe/Berlin) | MITTEL | 30 Sek |
| L3 | Monitoring-Cheatsheet ablegen | MITTEL | 5 Min |
| L4 | Lokale SSH Config einrichten | NIEDRIG | 2 Min |
| L5 | Phase 1-3 seines Plans abarbeiten | KRITISCH | 30 Min |

**Reihenfolge:** L5 zuerst (sein Plan ist gut priorisiert), dann L1-L4 einstreuen.

### Christian (Burg Rheinstein)

Modul 01 ist aktualisiert. Auf dem Strato-Server nachfahren:

| Nr | Was | Prio | Aufwand |
|----|-----|------|---------|
| C1 | UFW: `deny forward` + loopback nachrüsten | HOCH | 2 Min |
| C2 | SSH: Drop-in-Datei statt sed-Edits | HOCH | 5 Min |
| C3 | fail2ban: `banaction = ufw` setzen | HOCH | 2 Min |
| C4 | Kernel-Härtung (sysctl) anwenden | MITTEL | 5 Min |
| C5 | Verifikation: nmap von außen | MITTEL | 5 Min |

**Reihenfolge:** C1 -> C3 -> C2 -> C4 -> C5 (Firewall zuerst, dann Rest).

---

## Die Burg-Bilanz

```
                    RHEINSTEIN              NORDWALL
                    ==========              ========

Burggraben          [################]      [################]
(UFW)               Aktiv + Forward-Deny    Aktiv (nach Phase 1)

Wachturm            [################]      [################]
(Fail2Ban)          banaction=ufw           banaction=ufw

Geheimgang          [############----]      [################]
(SSH)               Drop-in, 11 Params      Drop-in + VPN-Lock

Burgmauern          [################]      [################]
(Kernel)            sysctl komplett         sysctl komplett

Vorratskeller       [################]      [----------------]
(Swap)              4 GB                    FEHLT!

Burguhr             [################]      [--------????????]
(Timezone)          Europe/Berlin           Unklar

Geheimtunnel        [----------------]      [################]
(VPN)               Bewusst nicht           WireGuard geplant

Chronist            [----------------]      [############----]
(auditd)            Später                  Geplant (Phase 5)

Nachtwache          [####------------]      [----------------]
(Monitoring)        Cheatsheet              Fehlt
```

**Kerngedanke:** Zwei Burgen, verschiedene Stärken. Rheinstein ist pragmatisch (KISS), Nordwall ist gründlich (Defense in Depth mit VPN). Beide lernen voneinander. Das ist der Wert einer Allianz.

---

*Dokument-Version: 1.0*
*Erstellt: 3. April 2026 (Hacking Day, Köln)*
*Nächste Prüfung: Nach Umsetzung aller Massnahmen auf beiden Servern*
