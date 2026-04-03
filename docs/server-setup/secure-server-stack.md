# Secure Server Stack

**Status:** Living Document
**Applies to:** Strato (chrisbuilds64) + Hetzner (Freund-Projekt)
**Philosophy:** Backend Excellence, KISS, Security First, Defense in Depth
**Origin:** DAY-035 "The 15-Euro Stack"

---

## Architektur: Schichten-Modell (von außen nach innen)

```
Internet
   |
   v
+----------------------------------+
|  Layer 1: NETZWERK + FIREWALL    |  UFW + Fail2Ban + SSH Hardening
+----------------------------------+
|  Layer 2: REVERSE PROXY + TLS    |  Caddy (auto HTTPS, zero-config TLS)
+----------------------------------+
|  Layer 3: DOCKER ISOLATION       |  Docker Compose, isolierte Netzwerke
|  +--------+ +--------+ +------+ |
|  | PROD   | | DEMO   | | DEV  | |  Getrennte Compose-Stacks
|  |        | |        | |      | |
|  | App    | | App    | | App  | |  Python + KI
|  | DB     | | DB     | | DB   | |  PostgreSQL
|  +--------+ +--------+ +------+ |
+----------------------------------+
|  Layer 4: MONITORING             |  Uptime Kuma + Logrotate + Unattended Upgrades
+----------------------------------+
|  Layer 5: BACKUP                 |  Borgmatic (lokal) + Storage Box (off-site)
+----------------------------------+
|  Layer 6: REPRODUCIBILITY        |  Ansible Playbooks
+----------------------------------+
```

---

## Die Burg-Analogie: Defense in Depth

```
                         Angreifer (Internet)
                                |
                    ========================
                    ~~ BURGGRABEN (UFW) ~~        Firewall: Nur 3 Zugbruecken offen
                    ~~ Wasser + Krokodile ~~      (SSH, HTTP, HTTPS). Alles andere
                    ========================      versinkt im Graben.
                                |
                    +-----------------------+
                    |   WACHTURM (Fail2Ban) |     Waechter beobachten den Graben.
                    |   Augen ueberall      |     Wer 3x falsches Passwort ruft,
                    |                       |     wird mit heissem Oel begruesst
                    +-----------------------+     (IP-Ban).
                                |
                    +-----------------------+
                    |  BURGTOR (Caddy)      |     Reverse Proxy + TLS.
                    |  Versiegelter         |     Prueft Siegel (Zertifikate),
                    |  Briefverkehr         |     leitet Besucher zum richtigen
                    |                       |     Gebaude weiter.
                    +-----------------------+
                                |
                  +-----------------------------+
                  |     INNERE BURGMAUER        |
                  |     (Docker Networks)       |
                  |                             |
                  |  +--------+ +------+ +---+  |  Jedes Gebaeude hat eigene
                  |  |Thron-  | |Gaeste| |Werk|  |  Mauern. Wer im Gaestehaus
                  |  |saal    | |haus  | |statt  |  ist, kommt nicht in den
                  |  |(PROD)  | |(DEMO)| |(DEV)  |  Thronsaal.
                  |  +--------+ +------+ +---+  |
                  +-----------------------------+
                                |
                    +-----------------------+
                    |  NACHTWACHE           |     Uptime Kuma patrouilliert.
                    |  (Monitoring)         |     Alle 60 Sekunden: "Alles klar?"
                    |  Alarm bei Gefahr     |     Bei Stille: Alarm (Telegram).
                    +-----------------------+
                                |
                    +-----------------------+
                    |  SCHATZKAMMER          |     Borgmatic Backup.
                    |  (Backup)             |     Kopie aller Schaetze in einem
                    |  Ausserhalb der Burg  |     geheimen Lager ausserhalb
                    |  (Storage Box)        |     der Burg (off-site).
                    +-----------------------+
                                |
                    +-----------------------+
                    |  BAUPLAN (Ansible)     |     Wenn die Burg brennt:
                    |  Exakte Anleitung      |     Bauplan nehmen, identische
                    |  zum Wiederaufbau      |     Burg in 30 Minuten neu bauen.
                    +-----------------------+
```

### Mapping: Burg vs. Server

| Burg | Server | Funktion |
|---|---|---|
| **Burggraben** | UFW Firewall | Erste Barriere. Nur definierte Eingaenge passierbar. |
| **Wachturm** | Fail2Ban | Beobachtet Zugangsversuche. Wer zu oft scheitert, wird verbannt. |
| **Burgtor mit Siegel** | Caddy (Reverse Proxy + TLS) | Einziger kontrollierter Eingang. Prueft Zertifikate, verschluesselt Verkehr. |
| **SSH-Geheimgang** | SSH mit Key-Auth | Nur der Burgherr kennt den Tunnel. Kein Passwort, nur der richtige Schluessel. |
| **Innere Burgmauer** | Docker Networks | Trennt Gebaeude voneinander. Einbruch im Gaestehaus gefaehrdet nicht den Thronsaal. |
| **Thronsaal** | Production Stack | Herzstueck. Hoechster Schutz, eingeschraenkter Zugang. |
| **Gaestehaus** | Demo Stack | Fuer Besucher/Kunden. Zeigt die Burg, ohne Zugang zu echten Schaetzen. |
| **Werkstatt** | Dev Stack | Hier wird experimentiert. Darf kaputt gehen, ohne dass der Rest leidet. |
| **Nachtwache** | Uptime Kuma + Logs | Patrouilliert rund um die Uhr. Schlaegt Alarm, wenn etwas nicht stimmt. |
| **Schatzkammer (extern)** | Borgmatic + Storage Box | Kopie aller Werte an sicherem Ort ausserhalb. Wenn die Burg faellt, sind die Schaetze sicher. |
| **Bauplan** | Ansible Playbooks | Exakte Anleitung zum Wiederaufbau. Neue Burg in Minuten. |
| **Burginspektor** | Lynis + Docker Bench | Prueft regelmaessig: Sind alle Mauern intakt? Gibt es geheime Loecher? |
| **Spion (eigener)** | nmap + testssl.sh | Testet die eigene Burg von aussen: Was sieht ein Angreifer? |

**Kerngedanke:** Keine einzelne Mauer schuetzt die Burg. Es ist die Kombination aus Graben, Wachtturm, Tor, inneren Mauern und Nachtwache. Faellt eine Schicht, fangen die anderen auf. Das ist **Defense in Depth**, und es funktioniert seit dem Mittelalter.

---

## Komponenten-Entscheidungen

### JETZT (Phase 1: Secure Foundation)

| Komponente | Tool | Warum dieses? |
|---|---|---|
| **OS** | Ubuntu 24.04 LTS | Standard, LTS, riesige Community, Hetzner/Strato Default |
| **Firewall** | UFW | Einfachstes iptables-Frontend. 3 Befehle fuer Grundschutz |
| **Brute-Force Schutz** | Fail2Ban | Automatisches IP-Banning nach X Fehlversuchen |
| **SSH Hardening** | sshd_config | Key-only, kein Root, kein Passwort, Port aendern |
| **Reverse Proxy** | Caddy | Auto-HTTPS (Let's Encrypt), kein Cert-Management noetig. Simpler als Nginx |
| **Container** | Docker + Compose | Isolation, Reproduzierbarkeit, Standard |
| **Datenbank** | PostgreSQL (in Docker) | Robust, bewaehrt, gut fuer Python/AI |
| **Auto-Updates** | unattended-upgrades | Security Patches automatisch |

**Warum Caddy statt Nginx?**
- Automatisches HTTPS ohne Certbot/Cron
- Config ist 10 Zeilen statt 50
- Reverse Proxy zu Docker-Containern trivial
- Performance fuer diesen Use-Case identisch
- KISS-Prinzip: weniger Config = weniger Fehlerquellen

### GLEICH DANACH (Phase 2: Monitoring + Backup)

| Komponente | Tool | Warum? |
|---|---|---|
| **Uptime Monitoring** | Uptime Kuma | Self-hosted, schoenes UI, Alerts (Email/Telegram) |
| **Log Management** | Logrotate + journald | Schon da, reicht erstmal. Kein ELK/Loki noetig |
| **Backup** | Borgmatic + Storage Box | Dedupliziert, verschluesselt, guenstig |
| **Resource Monitoring** | ctop oder lazydocker | Terminal-basiert, null Setup |

### SPAETER (Phase 3: Automation + Hardening)

| Komponente | Tool | Warum erst spaeter? |
|---|---|---|
| **Reproducibility** | Ansible | Erst wenn Setup stabil. Dann als Code festhalten |
| **Security Scanning** | Lynis + Docker Bench | Hardening-Audit, nachdem alles laeuft |
| **IDS** | CrowdSec | Community-basierte Threat Intelligence, Fail2Ban++ |
| **CI/CD** | GitHub Actions | Erst wenn Deployment-Workflow klar ist |
| **Secrets Management** | Docker Secrets oder SOPS | Wenn mehrere Entwickler dazukommen |

### BEWUSST NICHT (Overengineering fuer diesen Scale)

| Was | Warum nicht |
|---|---|
| Kubernetes | Ein Server, 2-3 Stacks. Docker Compose reicht. |
| ELK/Grafana/Prometheus | Overkill fuer Start. Uptime Kuma + journald reichen |
| Terraform | Ein Server, kein Multi-Cloud. Ansible reicht |
| Vault (HashiCorp) | Docker Secrets + .env mit restriktiven Permissions reichen |
| WAF (ModSecurity) | Caddy + Fail2Ban + UFW reichen fuer den Start |

---

## SSH Key-Pair: Der Geheimgang zur Burg

### Warum SSH Keys statt Passwort?

Ein Passwort kann erraten werden. Brute-Force-Angriffe probieren tausende Kombinationen pro Minute. Ein SSH Key ist ein kryptographisches Schluesselpaar: mathematisch unknackbar, solange der private Schluessel geheim bleibt.

Das Prinzip: Du erzeugst zwei Dateien auf deinem lokalen Rechner.
- **Private Key** (`strato_vps`): Bleibt auf deinem Rechner. Zeigst du niemandem. Ist dein Burgherren-Siegel.
- **Public Key** (`strato_vps.pub`): Kommt auf den Server. Ist das Schloss an der Tuer, das nur dein Siegel oeffnet.

Der Server kennt nur das Schloss. Nur dein Rechner hat den Schluessel. Kein Passwort reist uebers Netzwerk. Nichts zu erraten.

### Key erzeugen (einmalig, auf deinem lokalen Rechner)

```bash
ssh-keygen -t ed25519 -C "dein-label-fuer-den-key"
```

- `-t ed25519`: Modernster Algorithmus. Schneller und sicherer als RSA. Kuerzere Keys.
- `-C "..."`: Ein Label, damit du spaeter weisst welcher Key das ist (z.B. "chrisbuilds64-strato-vps")

Der Befehl fragt:
1. **Speicherort**: Default ist `~/.ssh/id_ed25519`. Besser: spezifischer Name wie `~/.ssh/strato_vps`
2. **Passphrase**: Optional, aber empfohlen. Schuetzt den Key falls dein Laptop gestohlen wird. Ohne Passphrase ist der Key so sicher wie ein unverschlossener Tresor.

Ergebnis: zwei Dateien.
```
~/.ssh/strato_vps       # Private Key (chmod 600, NIE teilen)
~/.ssh/strato_vps.pub   # Public Key (kommt auf den Server)
```

### Public Key auf den Server bringen

**Bei Neuinstallation (Strato/Hetzner):** Public Key ins Webformular kopieren.

```bash
cat ~/.ssh/strato_vps.pub
# Ausgabe kopieren, z.B.:
# ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAI... chrisbuilds64-strato-vps
```

**Bei laufendem Server:**
```bash
ssh-copy-id -i ~/.ssh/strato_vps.pub root@SERVER_IP
```

### Verbinden mit spezifischem Key

```bash
ssh -i ~/.ssh/strato_vps root@SERVER_IP
```

Oder in `~/.ssh/config` hinterlegen (einmalig):
```
Host strato
    HostName SERVER_IP
    User root
    IdentityFile ~/.ssh/strato_vps
```

Danach reicht: `ssh strato`

### Warum ed25519 statt RSA?

| | RSA | ed25519 |
|---|---|---|
| Key-Laenge | 3072+ Bit | 256 Bit |
| Sicherheit | Equivalent | Equivalent (bei viel kuerzerem Key) |
| Performance | Langsamer | Schneller |
| Standard seit | 1990er | 2014 |

ed25519 ist der aktuelle Standard. RSA funktioniert, ist aber der Burggraben von gestern.

---

## Security Hardening Checklist (Phase 1)

### SSH
- [ ] Root Login deaktivieren (`PermitRootLogin no`)
- [ ] Passwort-Auth deaktivieren (`PasswordAuthentication no`)
- [ ] SSH Key-Pair erzeugen + deployen (siehe oben)
- [ ] SSH Port aendern (z.B. 2222, reduziert Noise)
- [ ] `AllowUsers` auf spezifische User beschraenken

### Firewall (UFW)
- [ ] Default: deny incoming, allow outgoing
- [ ] Allow: SSH (custom port), HTTP (80), HTTPS (443)
- [ ] Alles andere: zu

### Fail2Ban
- [ ] SSH Jail aktivieren (maxretry=3, bantime=1h)
- [ ] Optional: Caddy Jail (HTTP Auth Brute-Force)

### Docker Security
- [ ] Docker Rootless Mode evaluieren (oder: User Namespaces)
- [ ] Container als non-root User laufen lassen
- [ ] Docker Networks: jeder Stack eigenes Netzwerk (kein cross-talk)
- [ ] Keine `--privileged` Container
- [ ] Read-only Filesystems wo moeglich (`read_only: true`)
- [ ] Resource Limits (CPU/Memory) pro Container

### System
- [ ] unattended-upgrades aktivieren (security only)
- [ ] Swap-File einrichten (AI braucht RAM)
- [ ] Timezone + NTP korrekt
- [ ] Unnoetige Services deaktivieren

---

## Environment-Trennung (Docker Compose)

```
/opt/
+-- prod/
|   +-- docker-compose.yml
|   +-- .env              # Production secrets (chmod 400)
|   +-- data/             # Persistent volumes
+-- demo/
|   +-- docker-compose.yml
|   +-- .env
|   +-- data/
+-- dev/                  # Optional, nur bei Bedarf
    +-- docker-compose.yml
    +-- .env
    +-- data/
```

**Netzwerk-Isolation:**
```yaml
# Jeder Stack hat sein eigenes Netzwerk
networks:
  prod-net:
    name: prod-network
  # demo-net, dev-net analog
```

**Caddy routet nach Subdomain:**
```
app.example.com      -> prod:8000
demo.example.com     -> demo:8000
dev.example.com      -> dev:8000   # Optional, ggf. IP-restricted
```

---

## Security Testing

### Automated (regelmaessig)
| Tool | Was es testet | Wann |
|---|---|---|
| **Lynis** | OS Hardening Score (0-100) | Nach Setup + monatlich |
| **Docker Bench Security** | CIS Docker Benchmark | Nach Setup + bei Aenderungen |
| **trivy** | Container Image Vulnerabilities | Bei jedem Build |

### Manual (einmalig + bei Aenderungen)
| Tool | Was es testet |
|---|---|
| **nmap** (von extern) | Offene Ports, Service Detection |
| **testssl.sh** | TLS Config, Cipher Suites, Cert Chain |
| **nikto** | Web Server Misconfiguration |
| **OWASP ZAP** | Web App Vulnerabilities (Proxy-basiert) |

### Monitoring (kontinuierlich)
| Was | Wie |
|---|---|
| Uptime | Uptime Kuma (HTTP Checks alle 60s) |
| Disk | df-Alert bei 80% |
| Docker | Restart-Policies + healthchecks in Compose |
| Logs | journald + logrotate, fail2ban Alerts |

---

## Vorgehensplan (Reihenfolge)

**Phase 1: Foundation**
1. Server initial aufsetzen (OS, User, SSH Keys)
2. SSH Hardening
3. UFW Firewall
4. Fail2Ban
5. Docker + Docker Compose installieren
6. Erster Container-Stack (Prod) mit Caddy
7. Test: nmap von aussen, testssl.sh

**Phase 2: Stacks + Monitoring**
1. Demo-Stack aufsetzen (Kopie von Prod, andere Subdomain)
2. Uptime Kuma deployen
3. Borgmatic Backup einrichten
4. Lynis + Docker Bench laufen lassen, Findings fixen
5. unattended-upgrades konfigurieren

**Phase 3: Automation**
1. Alles in Ansible Playbooks ueberfuehren
2. CI/CD Pipeline fuer Container-Builds
3. CrowdSec evaluieren (Fail2Ban-Ersatz mit Community Intel)
4. Security Testing automatisieren (trivy in Pipeline)

---

## Architektur-Entscheidungen

- **Caddy > Nginx** fuer diesen Use-Case (Auto-TLS, weniger Config, KISS)
- **Borgmatic > rsync** (Deduplication, Encryption, Storage Box Support)
- **Uptime Kuma > Grafana/Prometheus** (ein Server, self-hosted, simpel)
- **UFW + Fail2Ban > iptables direkt** (Abstraktion, weniger Fehler)
- **Docker Compose > Kubernetes** (ein Server, maximal 3 Stacks)
- **Ansible erst Phase 3** (erst manuell aufsetzen, verstehen, dann automatisieren)
