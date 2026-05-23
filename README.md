# Coregrid

App meant for automation of core operations inside businesses.

## Features

 - to be updated

## Tech stack

### Backend

- PostgeSQL

---

## Setup

### Clone repo

```bash
git clone git@github.com:DMen6L/Coregrid.git
cd Coregrid
```

### Download PostgeSQL

Arch:

```bash
sudo pacman -S postgresql
```

### Start PostgeSQL

```bash
sudo systemctl enable postgresql
sudo systemctl start postgresql
# Optional checks
systemctl status postgresql
```

### Create databases

```bash
sudo -iu postgres psql
```

```sql
CREATE DATABASE coregrid;
```

## Project structure

```text
database/
.gitignore
README.md
```
