# Podcast Server — Runbook

**Status:** Foundation komplett (Module 01), wartet auf Vendor-Installation
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
| Hostname | `ubuntu` (nicht gesetzt — offen) |

## Zugang

```bash
ssh strato-podcast          # deploy@87.106.162.116
```

- Key: `~/.ssh/strato_podcast` (ed25519, erzeugt 2026-09-04)
- Root-SSH gesperrt, Passwort-Login deaktiviert
- Root-Passwort nur für die STRATO VNC-Konsole, Ablage `~/.secrets/chrisbuilds64/`

## Stand der Härtung (Module 01, 2026-09-04)

| Element | Zustand |
|---|---|
| Deploy User + sudo NOPASSWD | aktiv |
| SSH Hardening (`/etc/ssh/sshd_config.d/99-hardening.conf`) | root aus, Passwort aus, `AllowUsers deploy`, MaxAuthTries 3 |
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

## Vendor-Zugang — noch nicht angelegt

Der Dienstleister bekommt einen eigenen User, nicht den `deploy`-Zugang. Ablauf, sobald der Public Key vorliegt:

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

## Offen

- [ ] Hostname setzen (aktuell `ubuntu`)
- [ ] Public Key des Dienstleisters anfordern → `vendor`-User anlegen
- [ ] Welches System wird installiert? Bestimmt Ports, DNS-Records, TLS-Verantwortung
- [ ] DNS-Records: welche Namen auf diesen Server
- [ ] Backup-Konzept — existiert noch nicht, weder lokal noch off-site
- [ ] Snapshot-Möglichkeit bei STRATO prüfen: Rückfallpunkt vor Vendor-Zugriff wäre sinnvoll
