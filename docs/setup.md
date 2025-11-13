# Entwicklungseinrichtung

## Lokales Environment schnell aktivieren

### Variante A: Shell-Skript
```
source scripts/env.sh
```
- setzt `PYTHONPATH` automatisch auf das Repository.
- setzt `BTRAINER_DATABASE_URL` auf `postgresql+psycopg://localhost/btrainer` (falls nicht bereits gesetzt).
- gibt die aktuell gesetzten Werte zur Kontrolle aus.

Optional kannst du die Zeile in deine `~/.zshrc` aufnehmen:
```
source /Volumes/EXT2TB/gullrich/DEV/btrainer/scripts/env.sh
```

### Variante B: direnv (automatisch beim `cd`)
1. `brew install direnv` (oder Paketmanager deiner Wahl).
2. `cp .envrc.example .envrc`
3. Im Repository `direnv allow` ausführen.

Das `.envrc` nutzt `layout python python3` (legt eine lokale venv an) und exportiert dieselben Variablen wie das Skript. Beim Betreten des Repos werden sie automatisch gesetzt.

> Hinweis: Wenn du bereits eine eigene virtuelle Umgebung verwendest, kannst du `layout python` entfernen und stattdessen `source .venv/bin/activate` o. Ä. eintragen.

## Häufige Befehle
- `pip install -e '.[dev]'` – Projektabhängigkeiten im Editable-Modus installieren.
- `alembic upgrade head` – Datenbankschema anwenden (benötigt `BTRAINER_DATABASE_URL`).
- `pytest` – Test-Suite (nutzt gesetzten `PYTHONPATH`).
