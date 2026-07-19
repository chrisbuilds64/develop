# Oracle 26ai — Connecting with SQL Developer

Oracle runs inside Docker on the server, bound to `127.0.0.1:1521` only.
It is **not accessible from the internet**. Access requires an SSH tunnel.

## Step 1: Open SSH Tunnel

```bash
ssh -L 1521:localhost:1521 deploy@YOUR_SERVER_IP -N
```

Keep this terminal open while working. The `-N` flag keeps it running without a shell.

You can also add it to `~/.ssh/config` for convenience:

```
Host strato-oracle
  HostName YOUR_SERVER_IP
  User deploy
  IdentityFile ~/.ssh/your_key
  LocalForward 1521 localhost:1521
```

Then just: `ssh strato-oracle -N`

## Step 2: Connect in SQL Developer

Create three connections — one per PDB:

| Field         | DEV                        | TEST                        | PROD                        |
|---------------|----------------------------|-----------------------------|-----------------------------|
| Name          | SDLC_DEV                   | SDLC_TEST                   | SDLC_PROD                   |
| Username      | system                     | system                      | system                      |
| Password      | (your ORACLE_PASSWORD)     | (your ORACLE_PASSWORD)      | (your ORACLE_PASSWORD)      |
| Hostname      | localhost                  | localhost                   | localhost                   |
| Port          | 1521                       | 1521                        | 1521                        |
| Service name  | SDLC_DEV                   | SDLC_TEST                   | SDLC_PROD                   |

Use **Service name** (not SID). Connection type: **Basic**.

## App User Connection

For application-level access (Python API, read/write data only):

| Field        | Value               |
|--------------|---------------------|
| Username     | sdlc_app            |
| Password     | (your ORACLE_APP_PASSWORD) |
| Service name | SDLC_DEV / SDLC_TEST / SDLC_PROD |

## SYS Connection (admin tasks)

| Field        | Value                         |
|--------------|-------------------------------|
| Username     | sys                           |
| Role         | SYSDBA                        |
| Service name | FREE (CDB) or SDLC_DEV (PDB) |

## Verify Connection (SQL)

After connecting, run to confirm which PDB you are in:

```sql
SELECT SYS_CONTEXT('USERENV', 'CON_NAME') AS current_pdb FROM dual;
```

Expected output: `SDLC_DEV`, `SDLC_TEST`, or `SDLC_PROD`.
