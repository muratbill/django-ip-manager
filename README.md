# 🌐 Django IP Management
## 👤 Author
**Murat Bilal** 


A clean and modern **Django-based IP Management (IPAM)** application, built with:
- Django 6.0
- Poetry for dependency management
- PostgreSQL 16 for persistence
- `.env`-based configuration for security

Designed for **local development on Ubuntu** and easy future expansion.

---

## 📋 Prerequisites

This guide assumes **Ubuntu 22.04 / 24.04**.

### System Packages

Update your system and install required packages:

```bash
sudo apt update
sudo apt install -y \
  python3 python3-pip python3-venv \
  postgresql postgresql-contrib \
  libpq-dev build-essential

Install Poetry
sudo apt install pipx -y
pipx ensurepath

Enable Auto-Completion for Pipx Commands:
echo 'eval "$(register-python-argcomplete pipx)"' >> ~/.bashrc
source ~/.bashrc

⚠️ Reopen your terminal (or source your shell rc file) after this step.
pipx install poetry
poetry --version

PostgreSQL Setup (Local Development)
Create Database & User

sudo -u postgres psql
CREATE DATABASE ipdb;
CREATE USER <youruser> WITH PASSWORD 'yourpass';

ALTER ROLE <youruser> SET client_encoding TO 'utf8';
ALTER ROLE <youruser> SET default_transaction_isolation TO 'read committed';
ALTER ROLE <youruser> SET timezone TO 'UTC';

GRANT ALL PRIVILEGES ON DATABASE ipdb TO <youruser>;
\q

Create Schema & Set Search Path
sudo -u postgres psql -d ipdb

CREATE SCHEMA <yourschema> AUTHORIZATION <youruser>;
ALTER ROLE <youruser> SET search_path = <yourschema>, public;
\q

Create Django Project with Poetry
mkdir ip-django
cd ip-django
poetry init -n
poetry env use python3

Add Dependencies:
poetry add "django==6.*" psycopg[binary]
poetry add --group dev python-dotenv

Create Django Project & App
poetry run django-admin startproject config .
poetry run python manage.py startapp ipmanager


Install arping and allow non-root usage

sudo apt update
sudo apt install -y arping
sudo setcap cap_net_raw+ep "$(command -v arping)"

Quick sanity test (should work without sudo):
arping -c 1 -I wlo1 192.168.1.1
echo $?
# 0 means ARP reply OK
```

---

## 🔐 Security Notice: Free IP Detection (ARP Usage)

This project optionally uses **ARP-based probing** to detect free IP addresses on the **local Layer-2 network**.

### Why ARP is used
To reliably determine whether an IP address is already in use, the application may send **ARP requests** using the `arping` utility. This is a common and industry-accepted technique used by:
- DHCP servers
- IPAM systems
- Virtualization platforms
- Container networking plugins

ARP operates strictly at **Layer 2 (local subnet only)** and does **not** perform:
- Port scanning
- Service enumeration
- Authentication attempts
- Remote network discovery

### Privilege model
To avoid running the application as `root`, the binary `arping` may be granted the Linux capability:

```bash
cap_net_raw
```

This capability is narrowly scoped and allows only the creation of raw network packets required for ARP. It does not grant:

File system access

Packet sniffing

Privilege escalation

Network configuration changes

Network impact

ARP requests are small broadcast frames

Requests are limited to the local subnet

No parallel or aggressive scanning is performed by default

On typical networks (e.g. /24 or /23), the traffic impact is negligible and safe for lab and enterprise environments.

Important notice for users

ARP-based probing should only be used on networks you own or are authorized to operate

Some enterprise security environments may flag raw socket usage for review

If required by policy, ARP probing can be disabled or replaced with passive detection methods
