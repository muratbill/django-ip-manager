# 🌐 Django IP Management
## 👤 Author
**Murat Bilal** 


A clean and modern **Django-based IP Management (IPAM)** application, built with:
- 🐍 Django
- 📦 Poetry for dependency management
- 🐘 PostgreSQL for persistence
- 🔐 `.env`-based configuration for security

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

📦 Install Poetry
python3 -m pip install --user pipx
python3 -m pipx ensurepath

⚠️ Reopen your terminal (or source your shell rc file) after this step.
pipx install poetry
poetry --version

🐘 PostgreSQL Setup (Local Development)
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

🐍 Create Django Project with Poetry
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
