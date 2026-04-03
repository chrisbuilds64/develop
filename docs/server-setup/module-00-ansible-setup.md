# Module 00: Ansible Setup (Der Bauplan-Tisch)

**Status:** Getestet auf macOS (2026-04-03)
**Dauer:** ~5 Minuten
**Voraussetzung:** Python 3, SSH-Zugang zum Server
**Ergebnis:** Ansible lauffaehig, Inventar konfiguriert, Playbooks bereit

---

## Was dieses Modul macht

Bevor die Burg gebaut wird, braucht der Architekt einen Tisch, Werkzeug und den Bauplan. Dieses Modul richtet die lokale Ansible-Umgebung ein.

| Burg-Element | Komponente | Was es tut |
|---|---|---|
| Bauplan-Tisch | Ansible (lokal) | Werkzeug zum Ausfuehren der Bauplaene |
| Grundriss | inventory.yml | Welche Burgen existieren, wer ist Burgherr |
| Bauplan | foundation.yml | Schritt-fuer-Schritt Anleitung fuer das Fundament |
| Burginspektor | verify.yml | Prueft ob alles korrekt gebaut wurde |

---

## Schritt 1: Ansible installieren

```bash
pip3 install ansible
```

Verifizieren:
```bash
ansible --version
```

---

## Schritt 2: Verzeichnisstruktur

```
develop/ansible/
├── inventory.yml        # Alle Burgen (Hosts + Variablen)
├── foundation.yml       # Modul 01: Burgfundament
├── verify.yml           # Burginspektor: Testprotokoll
└── README.md            # Kurzanleitung
```

---

## Schritt 3: Inventory verstehen

`inventory.yml` definiert jede Burg mit ihren Eigenheiten:

```yaml
rheinstein:
  ansible_host: 82.165.165.199    # IP der Burg
  ansible_user: deploy             # Burgherr (SSH User)
  ansible_ssh_private_key_file: ~/.ssh/strato_vps   # Schluessel
  deploy_user: deploy              # User der im Playbook angelegt wird
  swap_size: "4G"                  # Vorratskeller-Groesse
  timezone: "Europe/Berlin"        # Burguhr
```

Neue Burg hinzufuegen = neuen Block ins Inventory. Selber Bauplan, andere Parameter.

---

## Ausfuehrung

### Normale Ausfuehrung (Burg haerten)

```bash
cd develop/ansible
ansible-playbook -i inventory.yml foundation.yml --limit rheinstein
```

### Erster Lauf auf frischem Server (nur root)

```bash
ansible-playbook -i inventory.yml foundation.yml --limit rheinstein \
  -e "ansible_user=root" -e "first_run=true"
```

### Dry-Run (nur pruefen, nichts aendern)

```bash
ansible-playbook -i inventory.yml foundation.yml --limit rheinstein --check
```

### Burginspektion (Testprotokoll)

```bash
ansible-playbook -i inventory.yml verify.yml --limit rheinstein
```

### Nur eine Phase ausfuehren

```bash
# Nur Kernel-Haertung
ansible-playbook -i inventory.yml foundation.yml --limit rheinstein \
  --tags kernel

# Nur SSH
ansible-playbook -i inventory.yml foundation.yml --limit rheinstein \
  --tags ssh
```

---

## Neue Parameter zu Modul 01 hinzufuegen

Wenn wir eine neue Verteidigungsschicht einbauen wollen (z.B. neuer sysctl-Parameter, neuer SSH-Parameter, neuer UFW-Port), gibt es einen festen Ablauf:

### 1. Manuell testen

Erst auf dem Server manuell ausfuehren und verifizieren. Nie ungetestete Aenderungen in den Bauplan schreiben.

```bash
ssh strato "sudo sysctl -w neuer.parameter=wert"
# Funktioniert? Keine Seiteneffekte?
```

### 2. Playbook aktualisieren (foundation.yml)

Parameter in die passende Phase einfuegen. Beispiele:

**Neuer sysctl-Parameter:** In den `content`-Block von "Burgmauern: Sysctl Hardening" einfuegen.

**Neuer SSH-Parameter:** In den `content`-Block von "Geheimgang: SSH Drop-in Config" einfuegen.

**Neuer UFW-Port:** Neuen Eintrag in die `loop`-Liste von "Burggraben: Zugbruecken oeffnen".

**Neue Variable:** In `vars:` definieren und im Inventory pro Host setzen.

### 3. Testfall ergaenzen (verify.yml)

Fuer jeden neuen Parameter einen Check in `verify.yml` hinzufuegen. Ohne Test existiert der Parameter nicht.

### 4. Dokumentation aktualisieren (module-01-foundation.md)

Neuen Schritt oder Parameter in die manuelle Anleitung aufnehmen. Der Bauplan (Ansible) und die Anleitung (Markdown) muessen immer synchron sein.

### 5. Dry-Run + Verify

```bash
# Aenderung pruefen (aendert nichts)
ansible-playbook -i inventory.yml foundation.yml --limit rheinstein --check

# Ausfuehren
ansible-playbook -i inventory.yml foundation.yml --limit rheinstein

# Testen
ansible-playbook -i inventory.yml verify.yml --limit rheinstein
```

### Checkliste: Neuer Parameter

- [ ] Manuell auf Server getestet
- [ ] In `foundation.yml` eingefuegt (richtige Phase)
- [ ] Variable in `vars:` definiert (falls konfigurierbar)
- [ ] Variable in `inventory.yml` pro Host gesetzt (falls abweichend)
- [ ] Testfall in `verify.yml` ergaenzt
- [ ] `module-01-foundation.md` aktualisiert
- [ ] Dry-Run erfolgreich
- [ ] Verify erfolgreich

---

## Idempotenz

Jeder Lauf ist sicher wiederholbar. Ansible prueft den Ist-Zustand und aendert nur was abweicht:

- Swap existiert schon? Wird uebersprungen.
- SSH-Config identisch? Kein Reload.
- UFW-Regel schon da? Kein Duplikat.

Das bedeutet: Nach einem manuellen Eingriff auf dem Server bringt ein Playbook-Lauf alles zurueck in den Soll-Zustand. Der Bauplan ist die Wahrheit.

---

## Fehlerbehandlung

**SSH-Verbindung schlaegt fehl:**
```bash
# Manuell testen
ssh strato "whoami"

# Verbose-Modus
ansible rheinstein -i inventory.yml -m ping -vvv
```

**Playbook bricht ab:**
- Ansible stoppt beim ersten Fehler
- Alles VOR dem Fehler ist bereits angewendet
- Fehler fixen, Playbook nochmal starten (Idempotenz!)

**Server ausgesperrt:**
- Hetzner/Strato Cloud-Konsole als Fallback
- SSH-Config reparieren
- Playbook mit `--start-at-task="Burggraben"` ab bestimmtem Punkt starten

---

*Erstellt: 3. April 2026*
*Getestet mit: Ansible 12.3.0, ansible-core 2.19.8*
