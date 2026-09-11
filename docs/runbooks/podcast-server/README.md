# Podcast Server — Runbook

**Status:** Foundation komplett (Module 01), `vendor`-Zugang offen seit 2026-09-06, volles sudo seit 2026-09-09 — Installation durch den Dienstleister läuft
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
| DNS | `podcast.chrisbuilds64.com` · `test-podcast.chrisbuilds64.com` — beide A auf die IPv4, verifiziert 2026-09-09 |

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

## Vendor-Zugang — offen, mit vollem sudo

Der Dienstleister bekommt einen eigenen User, nicht den `deploy`-Zugang.

**Zugang offen seit 2026-09-06.** Der Public Key des Dienstleisters ist eingetragen, Datei 600 und `vendor:vendor`, `sshd -T -C user=vendor` gegengeprüft. Key-Fingerprint und Zuordnung stehen in `control/planning/2026-09-04_podcast-server-vendor.md` (PRIVATE, Personenbezug).

**sudo seit 2026-09-09** über `/etc/sudoers.d/vendor` mit `vendor ALL=(ALL) NOPASSWD:ALL`, Datei 440, `visudo -c` grün. Anlass: Der Dienstleister installiert ein Control Panel und übernimmt anschließend die Wartung.

**Gruppe `sudo` allein genügt nicht — das ist die eigentliche Falle.** `vendor` war am 05.09. mit `adduser --disabled-password` angelegt und per `usermod -aG sudo vendor` in die Gruppe gesteckt. Die Gruppe erlaubt sudo, aber sudo verlangt das Passwort des aufrufenden Users, und ein Passwort existiert bei `--disabled-password` nicht. Ergebnis: Gruppenmitgliedschaft vorhanden, sudo unbenutzbar, drei Tage lang unbemerkt. **Bei key-only-Usern immer eine NOPASSWD-Regel setzen oder ein Passwort vergeben — sonst ist das Recht nur behauptet.**

Die Vollanleitung, falls der Zugang neu aufgebaut werden muss:

```bash
ssh strato-podcast
sudo adduser --disabled-password --gecos "Vendor" vendor
sudo mkdir -p /home/vendor/.ssh
echo "SSH-PUBLIC-KEY-DES-VENDORS" | sudo tee /home/vendor/.ssh/authorized_keys
sudo chown -R vendor:vendor /home/vendor/.ssh
sudo chmod 700 /home/vendor/.ssh
sudo chmod 600 /home/vendor/.ssh/authorized_keys
echo "vendor ALL=(ALL) NOPASSWD:ALL" | sudo tee /etc/sudoers.d/vendor
sudo chmod 440 /etc/sudoers.d/vendor
sudo visudo -c
```

`visudo -c` ist nicht optional. Eine fehlerhafte Datei in `sudoers.d/` sperrt sudo für **alle** User; der Rückweg führt dann nur über die VNC-Konsole.

**Stolperfalle SSH:** `AllowUsers deploy` in `99-hardening.conf` sperrt jeden anderen User aus. Zeile auf `AllowUsers deploy vendor` ändern, dann `sudo sshd -t && sudo systemctl reload ssh`. Ohne diesen Schritt kommt der Vendor trotz gültigem Key nicht rein.

**Ein Key pro Person**, kein geteilter Account — sonst ist im `auth.log` nicht unterscheidbar, wer was getan hat.

**Entscheid 2026-09-06: genau ein Zugang.** Der Server-Zugang liegt ausschließlich beim technischen Ansprechpartner des Dienstleisters. Weitere Personen bekommen keinen Shell-Zugang; die Abstimmung läuft über Mail. Bei der Abnahme wird die User-Liste gegen diese Vorgabe geprüft.

**Nach Abnahme: `sudo deluser --remove-home vendor` und `AllowUsers` zurücksetzen — unter Vorbehalt.** Eine Wartungsübernahme durch den Dienstleister ist angesprochen, aber nicht vereinbart; geklärt wird sie nach Abschluss der Installation. Kommt sie, bleibt der User samt sudo bestehen und dieser Punkt entfällt. In beiden Fällen wird bei der Abnahme die User-Liste gegen die Ein-Zugang-Vorgabe geprüft: ob neben `deploy` und `vendor` weitere Accounts oder Keys entstanden sind.

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
- [x] ~~Public Key des Dienstleisters anfordern~~ → eingetragen 2026-09-06
- [x] ~~sudo für `vendor`~~ → `/etc/sudoers.d/vendor`, NOPASSWD, 2026-09-09
- [ ] **Welches Control Panel wird installiert?** Der Dienstleister nannte "CP Panel". Falls cPanel/WHM gemeint ist: **das läuft auf Ubuntu 24.04 nicht** — offiziell unterstützt sind AlmaLinux, CloudLinux und RHEL, Ubuntu kam über 20.04 LTS nie hinaus. Dann steht eine Neuinstallation mit anderem OS an, und Module 01 ist erneut zu fahren. Plesk, CloudPanel und CyberPanel laufen auf 24.04. **Diese Frage entscheidet, ob der Server so bestehen bleibt.**
- [ ] Ports für das Panel öffnen (cPanel 2082–2087, Plesk 8443). Aktuell nur 22/80/443. Wer UFW anfasst, ist abzustimmen — bringt das Panel eine eigene Firewall mit (cPanel: csf), kollidiert sie mit UFW
- [x] ~~DNS-Records: welche Namen auf diesen Server~~ → `podcast.chrisbuilds64.com` und `test-podcast.chrisbuilds64.com`, beide A auf `87.106.162.116`, per `dig` verifiziert 2026-09-09
- [ ] TLS: Let's Encrypt aus dem Vendor-Stack oder Zertifikate von uns — offen
- [ ] Backup-Konzept — bei der Abnahme vom Dienstleister einfordern
- [ ] Reboot ausstehend (Kernel-Update, `*** System restart required ***` seit 2026-09-09) + 2 offene Updates. **Nicht ohne Abstimmung** — der Dienstleister arbeitet auf der Maschine
