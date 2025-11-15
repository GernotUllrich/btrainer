# Billard-Visualisierung: Koordinatensystem und Skalierung

## Zusammenfassung

Dieses Dokument beschreibt die Implementierung der Billard-Tisch-Visualisierung mit korrekter Koordinatentransformation und proportionaler Skalierung für verschiedene Tischgrößen.

## Koordinatensystem

### YAML-Koordinaten (Diamond Units)

Die YAML-Dateien speichern Positionen in **Diamond Units**:
- **x-Achse**: Entlang der kurzen Seite (0..40 diamond units)
- **y-Achse**: Entlang der langen Seite (0..80 diamond units)
- **Ursprung**: Links unten (0, 0)

**Beispiel**: Position `(27.46, 14.17)` bedeutet:
- x = 27.46: Entlang der kurzen Seite (etwa 68.7% von links nach rechts)
- y = 14.17: Entlang der langen Seite (etwa 17.7% von unten nach oben)

### Display-Modi

#### Portrait-Mode (`--portrait`)

- **x-Achse**: Horizontal, kurze Bande (0..40 diamond units = 142 cm bei Match)
- **y-Achse**: Vertikal, lange Bande (0..80 diamond units = 284 cm bei Match)
- **Ursprung**: Links unten (0, 0)
- **Transformation**: Keine Rotation nötig - direkte Skalierung

**Visualisierung**: Höher als breit (10×14 inch figure size)

#### Landscape-Mode (`--landscape`, Default)

- **x-Achse**: Horizontal, lange Bande (0..80 diamond units = 284 cm bei Match)
- **y-Achse**: Vertikal, kurze Bande (0..40 diamond units = 142 cm bei Match)
- **Ursprung**: Links unten (0, 0)
- **Transformation**: Rotation um 90° nach rechts

**Transformation im Landscape-Mode**:
```
(x_new, y_new) = (y_old, width - x_old)
```

**Visualisierung**: Breiter als hoch (14×10 inch figure size)

## Tischvarianten

### Match-Billard (Standard)
- **Größe**: 284×142 cm
- **Diamond Units**: 80×40
- **Verwendung**: Standard aus YAML, oder wenn `--tb` nicht gesetzt

### Turnier-Billard (`--tb` Flag)
- **Größe**: 210×105 cm
- **Diamond Units**: 60×30
- **Skalierungsfaktor**: ~0.739 (105/142 ≈ 210/284)

## Proportionale Skalierung

### Wichtigste Erkenntnis

**Alle Positionen und Linien müssen proportional skaliert werden, aber die Transformation muss auf den Original-Dimensionen erfolgen, bevor die proportionale Skalierung angewendet wird.**

### Skalierungsprozess

#### Portrait-Mode

1. **Schritt 1**: Skaliere von diamond units auf Original-Dimensionen (Match)
   ```python
   x_cm_orig = (x_diamond / orig_width_units) * orig_width_cm
   y_cm_orig = (y_diamond / orig_length_units) * orig_length_cm
   ```

2. **Schritt 2**: Skaliere proportional auf Ziel-Dimensionen (z.B. Turnier)
   ```python
   scale_factor_width = dims['width_cm'] / orig_dims['width_cm']
   scale_factor_length = dims['length_cm'] / orig_dims['length_cm']
   x_cm_final = x_cm_orig * scale_factor_width
   y_cm_final = y_cm_orig * scale_factor_length
   ```

#### Landscape-Mode

1. **Schritt 1**: Skaliere von diamond units auf Original-Dimensionen (Match)
   ```python
   x_cm_orig = (x_diamond / orig_width_units) * orig_width_cm
   y_cm_orig = (y_diamond / orig_length_units) * orig_length_cm
   ```

2. **Schritt 2**: Transformiere (Rotation um 90° nach rechts)
   ```python
   x_transformed = y_cm_orig  # y wird zu x (lange Seite)
   y_transformed = orig_width_cm - x_cm_orig  # width - x wird zu y (kurze Seite)
   ```

3. **Schritt 3**: Skaliere proportional auf Ziel-Dimensionen
   ```python
   scale_factor_length = dims['length_cm'] / orig_dims['length_cm']
   scale_factor_width = dims['width_cm'] / orig_dims['width_cm']
   x_cm_final = x_transformed * scale_factor_length
   y_cm_final = y_transformed * scale_factor_width
   ```

### Wichtig: Reihenfolge der Transformationen

**❌ FALSCH**: Skalieren auf Ziel-Dimensionen → Transformieren
- Dies führt zu nicht-proportionalen Positionen
- Beispiel: Turnier-Tisch zeigt Bälle zu weit unten

**✅ RICHTIG**: Skalieren auf Original-Dimensionen → Transformieren (falls Landscape) → Proportional skalieren auf Ziel-Dimensionen
- Positionen bleiben relativ zur Tischgröße gleich
- Beispiel: 68.7% der Breite bleibt 68.7% der Breite, unabhängig von Tischgröße

## Ballgröße

### Wichtigste Regel

**Bälle haben immer einen absoluten Durchmesser von 61.5 mm, unabhängig von der Tischgröße.**

- **Match-Tisch**: 61.5 mm = 4.3% der Breite (142 cm)
- **Turnier-Tisch**: 61.5 mm = 5.9% der Breite (105 cm) - **relativ größer**

### Implementierung

```python
BALL_DIAMETER_MM = 61.5
radius_cm = (BALL_DIAMETER_MM / 2) / 10.0
# Keine Skalierung basierend auf Tischgröße!
```

### Konsequenzen

- Auf dem kleineren Turnier-Tisch erscheinen die Bälle relativ größer
- Überlappungen zwischen B2 und Ghostball können auftreten - **das ist gewollt**
- Dies hilft bei der Beurteilung, ob die erfassten Daten auf dem kleineren Tisch nutzbar sind

## Grid-Elemente

### Tabellenrand

- **Linienstärke**: 1 Pixel (dünn)
- **Position**: Innenkante liegt genau bei (0, 0)
- **Farbe**: Schwarz

### Cadrelinien (Klein-Cadre)

- **Anzahl**: 4 Linien (2 lange, 2 kurze)
- **Stil**: Durchgezogen, dunkelgrau (`darkgray`)
- **Linienstärke**: 0.8 Pixel

#### CADREABSTAND

**Wichtigste Regel**: CADREABSTAND = **1/3 der Tischbreite (kurze Seite)**, nicht der Länge!

#### Portrait-Mode

- **Horizontale Cadrelinien** (lange Linien): Dritteln den Tisch in Längsrichtung
  - 2 Linien bei y = (1/3) × length und (2/3) × length
- **Vertikale Cadrelinien** (kurze Linien): Im CADREABSTAND von den kurzen Banden
  - Linke Linie: x = CADREABSTAND (von linker Bande)
  - Rechte Linie: x = width - CADREABSTAND (von rechter Bande)

#### Landscape-Mode

- **Vertikale Cadrelinien** (lange Linien): Dritteln den Tisch in Längsrichtung
  - 2 Linien bei x = (1/3) × length und (2/3) × length
- **Horizontale Cadrelinien** (kurze Linien): Im CADREABSTAND von den kurzen Banden
  - Untere Linie: y = CADREABSTAND (von unterer Bande)
  - Obere Linie: y = width - CADREABSTAND (von oberer Bande)

**Beispiel Match-Tisch**:
- CADREABSTAND = 142 cm / 3 = 47.33 cm

**Beispiel Turnier-Tisch**:
- CADREABSTAND = 105 cm / 3 = 35.00 cm
- Skalierungsfaktor: 35.00 / 47.33 ≈ 0.739 ✓

### Diamantenlinien

- **Anzahl**: Immer 4×8 Quadrate, unabhängig von Tischgröße
- **Stil**: Gestrichelt (`--`), grau (`gray`)
- **Linienstärke**: 0.5 Pixel

#### Portrait-Mode

- **Vertikale Diamantlinien**: 3 Linien (für 4 Quadrate)
  - Bei x = (1/4), (2/4), (3/4) × width
- **Horizontale Diamantlinien**: 7 Linien (für 8 Quadrate)
  - Bei y = (1/8), (2/8), ..., (7/8) × length

#### Landscape-Mode

- **Vertikale Diamantlinien**: 7 Linien (für 8 Quadrate)
  - Bei x = (1/8), (2/8), ..., (7/8) × length
- **Horizontale Diamantlinien**: 3 Linien (für 4 Quadrate)
  - Bei y = (1/4), (2/4), (3/4) × width

**Wichtig**: Diamantenlinien werden proportional skaliert, behalten aber immer das 4×8-Gitter-Muster bei.

## Implementierung

### Befehlszeilen-Schnittstelle

```bash
# Standard: Match-Billard, Landscape-Mode
btrainer-visualize draw data/annotations/gretillat/VS-width-02-01.yaml

# Turnier-Billard
btrainer-visualize draw data/annotations/gretillat/VS-width-02-01.yaml --tb

# Portrait-Mode
btrainer-visualize draw data/annotations/gretillat/VS-width-02-01.yaml --portrait

# Turnier-Billard in Portrait-Mode
btrainer-visualize draw data/annotations/gretillat/VS-width-02-01.yaml --tb --portrait

# Ausgabe in Datei
btrainer-visualize draw data/annotations/gretillat/VS-width-02-01.yaml --tb -o output.png
```

### Parameter

- `--tb`: Turnier-Billard verwenden (210×105 cm statt 284×142 cm)
- `--portrait`: Portrait-Mode (x=kurze Seite, y=lange Seite)
- `--landscape` / `--no-landscape`: Landscape-Mode (Default, x=lange Seite, y=kurze Seite, 90° rotiert)
- `-o, --output`: Ausgabepfad für das Bild (optional)
- `--dpi`: Auflösung für gespeichertes Bild (Default: 150)

## Code-Struktur

### Hauptfunktion: `draw()`

- Lädt YAML-Datei
- Bestimmt Tischvariante (aus YAML oder `--tb` Flag)
- Berechnet Display-Dimensionen basierend auf Modus (Portrait/Landscape)
- Transformiert Positionen (Bälle, Ghost Ball, Trajectory) mit korrekter Skalierung
- Zeichnet Grid-Elemente
- Zeichnet Bälle mit absoluter Größe (61.5 mm)

### Hilfsfunktion: `_draw_table_grid()`

- Zeichnet Tabellenrand
- Zeichnet Cadrelinien (proportional skaliert)
- Zeichnet Diamantenlinien (proportional skaliert, 4×8-Gitter)

### Hilfsfunktion: `_draw_ball()`

- Zeichnet Bälle mit fester Größe (61.5 mm Durchmesser)
- B1/B2: Weiß mit schwarzem Rand
- B3: Schwarz gefüllt mit weißer Schrift
- GHOST: Gestrichelter Rand

## Wichtige Erkenntnisse und Fallstricke

### ❌ Häufige Fehler

1. **Skalierung vor Transformation**: Falsch → Positionen werden nicht proportional
2. **CADREABSTAND falsch berechnet**: Sollte 1/3 der **Breite** (kurze Seite) sein, nicht der Länge
3. **Diamantenlinien falsch skaliert**: Sollten immer 4×8 Quadrate bilden, proportional skaliert
4. **Ballgröße skaliert**: Bälle sollten immer 61.5 mm haben, unabhängig von Tischgröße

### ✅ Korrekte Implementierung

1. **Skalierungsreihenfolge**: Original → Transformiere (falls Landscape) → Proportional
2. **CADREABSTAND**: Immer 1/3 der kurzen Seite (width)
3. **Diamantenlinien**: 4×8-Gitter, proportional skaliert
4. **Ballgröße**: Konstante 61.5 mm

## Test-Beispiele

### Verifikation der proportionalen Skalierung

**Position (27.46, 14.17) im Portrait-Mode**:
- Match: x = 97.48 cm (68.7% der Breite), y = 50.30 cm (17.7% der Länge)
- Turnier: x = 72.08 cm (68.7% der Breite), y = 37.20 cm (17.7% der Länge)
- ✓ Proportional (68.7% bleibt 68.7%)

**Position (27.46, 14.17) im Landscape-Mode**:
- Match: x = 50.30 cm, y = 44.52 cm (31.3% der Breite)
- Turnier: x = 37.20 cm, y = 32.92 cm (31.3% der Breite)
- ✓ Proportional (31.3% bleibt 31.3%)

## Zukünftige Verbesserungen

- [ ] Projizierung auf den physischen Tisch (Kalibrierung erforderlich)
- [ ] Fadenkreuze für große Bälle (für bessere Sichtbarkeit)
- [ ] Weitere Tischvarianten unterstützen
- [ ] Interaktive Visualisierung mit Zoom/Pan

