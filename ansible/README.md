# Ansible: Bauplan der Burg

Reproduzierbare Server-Konfiguration. Ein Befehl, eine Burg.

## Voraussetzungen

```bash
pip install ansible
```

## Playbooks

| Playbook | Was es tut |
|----------|-----------|
| `foundation.yml` | Module 01: Komplettes Burgfundament (UFW, SSH, Fail2Ban, Kernel, Swap, Timezone) |

## Ausfuehrung

**Burg Rheinstein (Strato) haerten:**
```bash
cd develop/ansible
ansible-playbook -i inventory.yml foundation.yml --limit rheinstein
```

**Erster Lauf auf frischem Server (nur root vorhanden):**
```bash
ansible-playbook -i inventory.yml foundation.yml --limit rheinstein \
  -e "ansible_user=root" -e "first_run=true"
```

**Dry-Run (nur pruefen, nichts aendern):**
```bash
ansible-playbook -i inventory.yml foundation.yml --limit rheinstein --check
```

**Nur bestimmte Phase ausfuehren (z.B. nur Kernel):**
```bash
ansible-playbook -i inventory.yml foundation.yml --limit rheinstein --start-at-task="Burgmauern"
```

## Inventory

Beide Koenigreiche sind in `inventory.yml` definiert. Nordwall ist dort vorangelegt, aber auskommentiert bis Deployment ansteht.

## Idempotenz

Jeder Lauf ist sicher wiederholbar. Was bereits konfiguriert ist, wird nicht nochmal angefasst. Swap wird nur angelegt wenn `/swapfile` nicht existiert. Configs werden nur geschrieben wenn sie sich geaendert haben.
