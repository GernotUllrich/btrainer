# Workflow Versammlungsstöße (Long Gather Shots)

## Ziel
Erfassung von Versammlungsstößen (Gather Shots) aus Xavier Gretillats *L'apprentissage du billard français* für Trainings- und Projektionszwecke.

## Nummerierung
- Kapitelnummer + Diagrammnummer, z. B. `2.1` für "Direct Point – Gather Shot by One Band".
- Interner Schlüssel: `VS-Lang-02-01` (`VS` = Versammlungsstoß, `Lang` = Long Gather, `02` = Kapitel 2, `01` = erstes Diagramm).

## Datenfluss
1. Rohmaterial (`data/raw/gretillat`) enthält PNGs/Texte aus dem Buch.
2. Szenenbeschreibung als YAML (`data/annotations/...`).
3. CLI `btrainer-capture capture` aktualisiert Ballpositionen aus dem Bild und schreibt zurück in YAML sowie in die PostgreSQL-Datenbank (`BTRAINER_DATABASE_URL`).
4. `btrainer-capture ingest` überführt YAML-Dateien in die Datenbank.
5. Alembic-Migrationen halten das DB-Schema versioniert (`alembic/`).

## Koordinatensystem
- Rechteckiger Match-Tisch 40 × 80 Einheiten (≈ 284 × 142 cm) als Standard, Variante "small_tournament" 30 × 60 Einheiten.
- Ursprung (0,0) unten links, X entlang langer Bande, Y entlang kurzer Bande.
- Rasterauflösung 0,5 Einheiten; Detailausschnitte bei Bedarf mit höherer Genauigkeit (0,5 cm).

## CLI-Bedienung
```bash
export BTRAINER_DATABASE_URL=postgresql+psycopg://user:pass@localhost:5432/btrainer
# Interaktive Erfassung
btrainer-capture capture data/annotations/gretillat/VS-Lang-02-01.yaml data/raw/gretillat/long_gather-185.png
# YAML → DB importieren
btrainer-capture ingest data/annotations/gretillat/VS-Lang-02-01.yaml
```

## Datenelemente (YAML)
- `balls`: Positionen der tatsächlichen Bälle `B1`, `B2`, `B3`.
- `ghost_ball`: virtuelle Position des Ghost Balls bei der Berührung mit `B2`.
- `cue`: Stoßparameter (Stoßrichtung, Attackhöhe, Effet-Stufe, Queue-Neigung, Notizen).
- `tempo_force`: Tempo (0–5) und Kraft (0–5) gemäß Buch.
- `trajectory`: Segmentliste pro Ball (Geraden, Banden, stationäre Phasen).
- `remarks`: Hinweise aus dem Buch (z. B. Toleranzen, Varianten).
- `text`: Originalexcerpt + deutsche Kurzfassung zur späteren semantischen Suche.

## Vorgehen
1. **Quelle prüfen**: PNG/TXT unter `data/raw/gretillat/` öffnen.
2. **Kalibrieren & Klicken**: CLI führt durch drei Referenzpunkte + Ball-/Ghost-Positionen in einem Fenster.
3. **Koordinaten prüfen**: CLI zeigt Pixel- und Tischwerte an.
4. **Optional**: Zusätzliche Punkte für Trajektorien erfassen.
5. **Speichern**: YAML wird aktualisiert, Szene landet via SQLAlchemy in der Datenbank.
6. **Alembic**: Neue Tabellenfelder via `alembic revision --autogenerate -m "…"` + `alembic upgrade head` deployen.

## Begriffe
- **Versammlungsstoß (Gather Shot)**: Stoß, bei dem die Bälle in einer Sammelzone zusammengeführt werden.
- **Ghost Ball**: Virtuelle Position des Spielballs im Moment der Treffpunkt-Kollision mit `B2`. Verbindungslinie Ghost Ball ↔ `B2` bestimmt die Abstoßrichtung von `B2`.
- **Effet-Stufen**: Gemäß Effler (Stufen 1–4, 45°-Effet, >4). In den Daten als `effect_stage` gespeichert.

## ToDo
- Trajektorienpunkte aus YAML in CLI integrieren.
- Textbausteine automatisch in Vektorindex überführen.
- FastAPI-Endpunkt für Szenenabfrage bereitstellen.
