# Podcast Server — Runbook

**Status:** Foundation komplett (Module 01), `vendor`-Zugang vorbereitet, wartet auf den Public Key des Dienstleisters
**Erstellt:** 2026-09-04
**Zweck:** Server für das Podcast-Verteilsystem. Installation der Anwendung durch externen Dienstleister.

---

## Server

| | |
|---|---|
| Provider | STRATO (IONOS-Infrastruktur), virtueller Server |
| IPv4 | 87.106.162.116 |
| IPv6 | 2a01:239:466:8200::1 |
| OS | Ubuntu 24.04.4 LTS, Neuinstallation 2026-09-04 |
| Hardware | 4 vCPU, 3.7 GB RAM, 116 GB Disk |
| Timezone | Europe/Vienna |
| Hostname | `scriptorium` (gesetzt 2026-09-05, vorher `ubuntu`) |

## Zugang

```bash
ssh strato-podcast          # deploy@87.106.162.116
```

- Key: `~/.ssh/strato_podcast` (ed25519, erzeugt 2026-09-04)
- Root-SSH gesperrt, Passwort-Login deaktiviert
- Root-Passwort nur für die STRATO VNC-Konsole. Ablageort dokumentiert in `~/.secrets/chrisbuilds64/podcast-server.txt` (lokal, nicht im Repo)

## Stand der Härtung (Module 01, 2026-09-04)

| Element | Zustand |
|---|---|
| Deploy User + sudo NOPASSWD | aktiv |
| SSH Hardening (`/etc/ssh/sshd_config.d/99-hardening.conf`) | root aus, Passwort aus, `AllowUsers deploy vendor`, MaxAuthTries 3 |
| UFW | active, offen 22/80/443 + loopback, forward deny |
| Fail2Ban | sshd-Jail aktiv, 3 Versuche / 10 Min = 1h Ban, banaction ufw |
| Kernel-Härtung (`/etc/sysctl.d/99-hardening.conf`) | aktiv |
| Swap | 4 GB, in fstab |
| unattended-upgrades | Timer enabled + active, Security-Origins gesetzt |
| System-Updates | eingespielt, kein Reboot nötig |

Offene Ports nach außen: nur 22. DNS-Resolver lauscht nur auf loopback.

## Abweichungen von Module 01

- **Timezone Europe/Vienna** statt Europe/Berlin.
- **Fail2Ban `backend = systemd`** statt `logpath = /var/log/auth.log`. Ubuntu 24.04 protokolliert SSH über journald; mit dem Dateipfad greift der Jail nicht zuverlässig. Sollte in Module 01 nachgezogen werden.
- **Kein Reverse Proxy.** Module 02 (Docker + Caddy) bewusst nicht gefahren — der Dienstleister bringt seinen eigenen Stack mit, wir legen ihm nichts vor.

## Vendor-Zugang — vorbereitet, wartet auf den Key

Der Dienstleister bekommt einen eigenen User, nicht den `deploy`-Zugang.

**Am 2026-09-05 bereits erledigt** (SEC-036): `vendor` angelegt (UID 1001, Gruppe `sudo`), `/home/vendor/.ssh` mit 700 und eine leere `authorized_keys` mit 600, `AllowUsers deploy vendor` aktiv und per `sshd -t` geprüft. Verifiziert: `deploy` kommt weiterhin rein, `vendor` bekommt `Permission denied (publickey)`, weil die `authorized_keys` leer ist und Passwort-Auth global aus ist. **Der User existiert, das Tor bleibt zu, bis der Key eingetragen wird.**

Es fehlt nur noch der Key selbst.

Sobald der Public Key vorliegt, fehlt nur noch eine Zeile:

```bash
ssh strato-podcast
echo "SSH-PUBLIC-KEY-DES-VENDORS" | sudo tee -a /home/vendor/.ssh/authorized_keys
```

Die ursprüngliche Vollanleitung, falls der Zugang neu aufgebaut werden muss:

```bash
ssh strato-podcast
sudo adduser --disabled-password --gecos "Vendor" vendor
sudo usermod -aG sudo vendor
sudo mkdir -p /home/vendor/.ssh
echo "SSH-PUBLIC-KEY-DES-VENDORS" | sudo tee /home/vendor/.ssh/authorized_keys
sudo chown -R vendor:vendor /home/vendor/.ssh
sudo chmod 700 /home/vendor/.ssh
sudo chmod 600 /home/vendor/.ssh/authorized_keys
```

**Stolperfalle:** `AllowUsers deploy` in `99-hardening.conf` sperrt jeden anderen User aus. Zeile auf `AllowUsers deploy vendor` ändern, dann `sudo sshd -t && sudo systemctl reload ssh`. Ohne diesen Schritt kommt der Vendor trotz gültigem Key nicht rein.

**Ein Key pro Person**, kein geteilter Account — sonst ist im `auth.log` nicht unterscheidbar, wer was getan hat.

**Nach Abnahme:** `sudo deluser --remove-home vendor` und `AllowUsers` zurücksetzen.

## Rückfallwege — es gibt kein Backup und keinen Snapshot

**Das STRATO-Paket VPS Linux M bietet weder Backup noch Snapshot im Panel.** Verifiziert am 2026-09-05 über alle Menüs: der Punkt "Backup & Recovery" / "BackupControl" gehört zum älteren Produkt "STRATO V-Server" und existiert hier nicht, es gibt keine Snapshot-Aktion (ServerCloud ist ein anderes Produkt, dort ohnehin nur drei Tage Aufbewahrung), und unter "Sicherheit" liegen nur SSL-Zertifikate, Troubleshooting und Passwortverwaltung. **Nicht erneut danach suchen.**

Stattdessen stehen im Server-Login drei Wege bereit, in dieser Reihenfolge:

| Weg | Wofür | Kosten |
|---|---|---|
| **Rettungssystem starten** | Bootet ein Recovery-Linux. Platte mounten, kaputte Konfiguration reparieren. Der realistische Fall, wenn eine `sshd`-Änderung den Zugang zerlegt. **Erste Wahl.** | Minuten |
| **VNC Konsole öffnen** | Direkter root-Login ohne Netzwerk. Wenn SSH tot ist, das Dateisystem aber intakt. | Minuten |
| **Neuinstallation** | Ubuntu 24.04 neu, dann Module 01 fahren. Vollständiger Rückfall. | rund 1 Stunde |

**Warum das für die Vendor-Phase reicht:** Der Server ist leer. Alles, was darauf steht, stammt aus Module 01, und das wurde am 2026-09-04 gefahren und verifiziert. Ein Totalverlust kostet eine Stunde, keine Daten. Ein gekauftes Backup-Paket (STRATO Cyber Protect) hätte diesen Befund zugedeckt statt gelöst.

**Wann sich das ändert:** Sobald das Podcast-System installiert ist und Daten trägt. Das Backup-Konzept wird deshalb bei der Abnahme vom Dienstleister eingefordert (Abnahmepunkt 5) — dann erst ist Cyber Protect die Frage.

## Erreichbarkeit von außen — verifiziert 2026-09-05

Geprüft von `rheinstein` aus (82.165.165.199), nicht aus dem Büronetz. **Der Grund:** Das Büronetz beantwortet jedes SYN, auch auf geschlossenen Ports — ein Scan von dort meldete selbst Port 12345 als offen und ist damit wertlos.

| Port | Antwort | Bedeutung |
|---|---|---|
| 22 | verbindet, 16 ms | offen, `sshd` lauscht |
| 80 / 443 | Connection refused, 16 ms | UFW lässt durch, es lauscht noch kein Dienst |
| 12345 und weitere | Timeout, 6 s | UFW blockt (DROP) |

Die 16 Millisekunden gegen 6 Sekunden sind der Beleg: Bei 80/443 antwortet der Kernel mit RST, das Paket kam also durch die Firewall. Bei geschlossenen Ports verschwindet es lautlos. **Die Aussage "22/80/443 sind offen" gegenüber dem Dienstleister stimmt** — die beiden Web-Ports warten nur auf dessen Stack.

## Offen

- [x] ~~Hostname setzen~~ → `scriptorium`, 2026-09-05
- [x] ~~`vendor`-User anlegen~~ → angelegt 2026-09-05, wartet nur noch auf den Key
- [x] ~~Snapshot-Möglichkeit bei STRATO prüfen~~ → existiert nicht, Rückfallwege oben dokumentiert
- [ ] Public Key des Dienstleisters anfordern (Mail-Entwurf liegt bereit)
- [ ] Welches System wird installiert? Bestimmt Ports, DNS-Records, TLS-Verantwortung
- [ ] DNS-Records: welche Namen auf diesen Server
- [ ] Backup-Konzept — bei der Abnahme vom Dienstleister einfordern
