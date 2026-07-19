# infra/ansible/

Ansible playbooks for server provisioning.

## Planned Playbooks

- `foundation.yml` — Base OS hardening, SSH configuration, firewall (UFW), fail2ban
- `docker.yml` — Docker Engine + Docker Compose installation
- `stack.yml` — Deploy all services (Oracle, ORDS, Python API, Traefik)

## Requirements

- Ansible 2.15+
- Target: Debian/Ubuntu LTS
- Secrets: Ansible Vault (`.env` files per environment, never committed)

## Phase

Phase 2. See [ADR-003](../../docs/adr/003-environment-strategy.md) for environment strategy.
