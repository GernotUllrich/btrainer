# Workflow Versammlungsstöße (Long Gather Shots)

## Ziel
Erfassung von Versammlungsstößen (Gather Shots) aus Xavier Gretillats *L'apprentissage du billard français* für Trainings- und Projektionszwecke.

## Nummerierung
- Kapitelnummer + Diagrammnummer, z. B. `2.1` für "Direct Point – Gather Shot by One Band".
- Interner Schlüssel: `VS-Lang-02-01` (`VS` = Versammlungsstoß, `Lang` = Long Gather, `02` = Kapitel 2, `01` = erstes Diagramm).

## Koordinatensystem
- Rechteckiger Match-Tisch 40 × 80 Einheiten (≈ 284 × 142 cm) als Standard.
- Optional kleines Turnierbillard 30 × 60 Einheiten (≈ 210 × 105 cm); Variante wird in der Szene vermerkt.
- Ursprung (0,0) unten links, X entlang langer Bande, Y entlang kurzer Bande.
- Rasterauflösung 0,5 Einheiten; Detailausschnitte bei Bedarf mit höherer Genauigkeit (0,5 cm).

## Datenelemente
- `balls`: Positionen der drei Bälle (`B1` = Spielball, `B2`, `B3`).
- `ghost_ball`: Position des Ghost Balls bei der Berührung mit `B2` (ermöglicht Rückschluss auf Treffpunkt und Laufweg `B2`).
- `cue`: Stoßparameter (Stoßrichtung, Attackhöhe, Effet-Stufe, Queue-Neigung falls relevant).
- `tempo_force`: Tempo (0–5) und Kraft (0–5) gemäß Buch.
- `ball_contact`: Überdeckungsgrad zwischen `B1` und `B2` (z. B. `2/3` oder 0.66).
- `trajectory`: Segmentliste für `B1`, `B2`, `B3` (Geraden, Bandenkontakte).
- `text`: Quellenzitate (Originalsprache) und deutschsprachige Zusammenfassung.
- `remarks`: Weitere Hinweise (z. B. Toleranzen, Varianten, eigene Beobachtungen).

## Vorgehen
1. **Quelle prüfen**: PNG/TXT unter `data/raw/gretillat/` öffnen.
2. **Kalibrieren**: Zwei Referenzpunkte (Diamanten) wählen, um Pixel → Koordinate zu bestimmen.
3. **Koordinaten messen**: Ballmittelpunkte, Ghost Ball und relevante Bandenpunkte erfassen.
4. **Parameter übertragen**: Angaben zu Ballmenge, Effet, Stoßhöhe, Tempo/Kraft, Schwierigkeitsgrad.
5. **Text erfassen**: Originalpassage (Kurztext) übernehmen und eine deutsche Zusammenfassung formulieren.
6. **Struktur ausfüllen**: YAML-Datei unter `data/annotations/gretillat/` ergänzen.
7. **Validieren**: Szene mit Notebook visualisieren; Plausibilität prüfen.

## Begriffe
- **Versammlungsstoß (Gather Shot)**: Stoß, bei dem die Bälle in einer Sammelzone zusammengeführt werden.
- **Ghost Ball**: Virtuelle Position des Spielballs im Moment der Treffpunkt-Kollision mit `B2`. Verbindungslinie Ghost Ball ↔ `B2` bestimmt die Abstoßrichtung von `B2`.
- **Effet-Stufen**: Gemäß Effler (Stufen 1–4, 45°-Effet, >4). In den Daten als `effect_stage` gespeichert.

## ToDo
- Kalibrierungs-Notebook erstellen.
- Lookup-Tabellen (`effect_stages.yaml`, `ball_contact_levels.yaml`) befüllen.
- Erste Szenen vollständig mit Koordinaten versehen.
