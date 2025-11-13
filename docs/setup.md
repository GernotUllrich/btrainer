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

### Variante B: direnv (empfohlen)
1. `brew install direnv` (oder Paketmanager deiner Wahl).
2. `cp .envrc.example .envrc`
3. Im Repository `direnv allow` ausführen.

Das `.envrc` legt bei Bedarf automatisch eine virtuelle Umgebung unter `.venv/` an, aktiviert sie und exportiert dieselben Variablen wie das Skript. Beim Betreten des Repos brauchst du dich nicht mehr um Python-/DB-Variablen zu kümmern.

> Hinweis: Falls du eine bestehende venv verwenden möchtest, passe den Block in `.envrc` an (`source /pfad/zur/venv/bin/activate`).

## Häufige Befehle
- `python -m pip install -e '.[dev]'` – Projektabhängigkeiten im Editable-Modus installieren (innerhalb der venv).
- `alembic upgrade head` – Datenbankschema anwenden (benötigt `BTRAINER_DATABASE_URL`).
- `pytest` – Test-Suite (nutzt die gesetzte venv + `PYTHONPATH`).
