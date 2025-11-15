#!/usr/bin/env python3
"""Visualisiert eine Szenen-YAML mit Trajektorien auf dem zugehörigen Bild."""

from pathlib import Path
from typing import Dict, List, Tuple, Literal, Optional

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
import typer

from src.services.ingest import load_scene_yaml
from src.db.models import TableVariant

app = typer.Typer(help="Visualisiert Szenen-YAMLs mit Trajektorien")


def _table_to_pixel_simple(table_point: Tuple[float, float], image_shape: Tuple[int, int], 
                           table_size: Tuple[float, float] = (40.0, 80.0)) -> Tuple[float, float]:
    """Vereinfachte Transformation: Tisch-Koordinaten zu Pixel (ohne Kalibrierung).
    
    Nimmt an, dass das Bild den gesamten Tisch zeigt und die Koordinaten relativ sind.
    Dies ist nur eine Näherung für die Visualisierung.
    """
    tx, ty = table_point
    img_h, img_w = image_shape[:2]
    table_w, table_h = table_size
    
    # Einfache lineare Skalierung (Annahme: Bild zeigt gesamten Tisch)
    # Ursprung ist bottom_left, also y wird invertiert
    px = (tx / table_w) * img_w
    py = img_h - (ty / table_h) * img_h  # y invertiert wegen bottom_left origin
    
    return float(px), float(py)


@app.command()
def visualize(
    yaml_path: Path = typer.Argument(..., help="Pfad zur Szenen-YAML-Datei"),
    output_path: Path = typer.Option(None, "--output", "-o", help="Ausgabepfad für das Bild (optional)"),
) -> None:
    """Visualisiert eine Szenen-YAML mit Trajektorien auf dem zugehörigen Bild."""
    
    scene_model = load_scene_yaml(yaml_path)
    
    # Lade Bild basierend auf Seitenzahl
    if scene_model.source.page is None:
        raise typer.BadParameter("Keine Seitenzahl in YAML vorhanden")
    
    # Extrahiere Seitennummer (kann String wie "270 oben" sein)
    from src.tools.capture_scene import _extract_page_number
    page_num = _extract_page_number(scene_model.source.page)
    if page_num is None:
        raise typer.BadParameter(f"Konnte Seitennummer nicht aus '{scene_model.source.page}' extrahieren")
    
    # Bestimme Bildtyp basierend auf Scene-ID
    scene_id = scene_model.id
    if scene_id.startswith("VS-width"):
        image_name = f"width_gather-{page_num}.png"
    else:
        image_name = f"long_gather-{page_num}.png"
    
    image_path = Path("data/raw/gretillat") / image_name
    if not image_path.exists():
        raise typer.BadParameter(f"Bilddatei nicht gefunden: {image_path}")
    
    image = np.array(plt.imread(image_path))
    
    # Erstelle Plot
    fig, ax = plt.subplots(figsize=(12, 16))
    ax.imshow(image)
    ax.set_title(f"{scene_model.id}: {scene_model.title}", fontsize=14, fontweight='bold')
    
    # Für die Transformation brauchen wir eine Kalibrierungsmatrix
    # Da wir die nicht haben, plotten wir direkt in Pixel-Koordinaten
    # Wir müssen die Tisch-Koordinaten zu Pixel transformieren
    # Dafür brauchen wir die Kalibrierung - aber die haben wir nicht gespeichert
    # Alternative: Wir zeigen die Koordinaten als Text an und plotten relativ
    
    # Farben für die Bälle
    ball_colors = {
        'B1': 'white',
        'B2': 'yellow',
        'B3': 'red',
    }
    
    table_size = (scene_model.table.size_units[0], scene_model.table.size_units[1])
    
    # Zeichne Ball-Positionen
    ball_info = []
    for ball_name, ball_data in scene_model.balls.items():
        x, y = ball_data.position
        color_name = ball_colors.get(ball_name, 'gray')
        px, py = _table_to_pixel_simple((x, y), image.shape, table_size)
        
        # Zeichne Ball
        circle_color = 'white' if color_name == 'white' else color_name
        edge_color = 'black' if color_name == 'white' else 'white'
        circle = plt.Circle((px, py), 15, color=circle_color, ec=edge_color, lw=2, zorder=10)
        ax.add_patch(circle)
        ax.text(px, py, ball_name, ha='center', va='center', fontsize=8, fontweight='bold', zorder=11)
        
        ball_info.append(f"{ball_name}: ({x:.2f}, {y:.2f})")
    
    # Zeichne Ghost Ball
    if scene_model.ghost_ball:
        gx, gy = scene_model.ghost_ball.position
        gpx, gpy = _table_to_pixel_simple((gx, gy), image.shape, table_size)
        circle = plt.Circle((gpx, gpy), 15, color='none', ec='gray', lw=2, linestyle='--', zorder=9)
        ax.add_patch(circle)
        ax.text(gpx, gpy, 'G', ha='center', va='center', fontsize=8, color='gray', zorder=10)
        ball_info.append(f"GHOST: ({gx:.2f}, {gy:.2f})")
    
    # Zeichne Trajektorien
    trajectory_info = []
    trajectory_colors = {
        'B1': 'red',
        'B2': 'blue', 
        'B3': 'green',
    }
    
    for ball_name, segments in scene_model.trajectory.items():
        if not segments:
            continue
        
        color = trajectory_colors.get(ball_name, 'orange')
        points_px = []
        
        # Startpunkt ist die Ball-Position
        if ball_name in scene_model.balls:
            start_x, start_y = scene_model.balls[ball_name].position
            start_px, start_py = _table_to_pixel_simple((start_x, start_y), image.shape, table_size)
            points_px.append((start_px, start_py))
        
        for idx, segment in enumerate(segments):
            tx, ty = segment.point
            px, py = _table_to_pixel_simple((tx, ty), image.shape, table_size)
            points_px.append((px, py))
            trajectory_info.append(f"{ball_name}[{idx+1}]: ({tx:.2f}, {ty:.2f}) - {segment.path_type}")
        
        # Zeichne Trajektorie als Linie
        if len(points_px) > 1:
            xs, ys = zip(*points_px)
            ax.plot(xs, ys, color=color, linewidth=2, alpha=0.7, zorder=5, label=f"{ball_name} Trajektorie")
            
            # Zeichne Punkte
            for i, (px, py) in enumerate(points_px[1:], 1):  # Skip first (ball position)
                ax.plot(px, py, 'o', color=color, markersize=8, zorder=6)
                ax.text(px + 10, py, str(i), color=color, fontsize=8, fontweight='bold', 
                       bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.7), zorder=7)
    
    # Zeige Informationen als Text
    info_text = f"Bälle:\n" + "\n".join(ball_info)
    if trajectory_info:
        info_text += f"\n\nTrajektorien ({len(trajectory_info)} Punkte):\n" + "\n".join(trajectory_info[:15])  # Erste 15
        if len(trajectory_info) > 15:
            info_text += f"\n... ({len(trajectory_info) - 15} weitere)"
    
    ax.text(10, image.shape[0] - 10, info_text, 
            bbox=dict(boxstyle='round', facecolor='white', alpha=0.9),
            fontsize=8, verticalalignment='top', family='monospace', zorder=20)
    
    # Legende
    if scene_model.trajectory and any(scene_model.trajectory.values()):
        ax.legend(loc='upper right', fontsize=8)
    
    # Warnung über Näherung
    ax.text(0.5, 0.02, "HINWEIS: Positionen sind Näherungen (ohne Kalibrierungsmatrix)",
            transform=ax.transAxes, ha='center', fontsize=9,
            bbox=dict(boxstyle='round', facecolor='yellow', alpha=0.8), zorder=21)
    
    plt.tight_layout()
    
    if output_path:
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        typer.echo(f"Bild gespeichert: {output_path}")
    else:
        plt.show()


# Table dimensions in cm
TABLE_DIMENSIONS = {
    TableVariant.MATCH: {
        'length_cm': 284.0,
        'width_cm': 142.0,
        'length_units': 80.0,
        'width_units': 40.0,
    },
    TableVariant.SMALL_TOURNAMENT: {
        'length_cm': 210.0,
        'width_cm': 105.0,
        'length_units': 80.0,  # Diamond units sind unabhängig von Tischgröße - immer 80×40
        'width_units': 40.0,
    },
}

# Ball diameter in mm (61.5 mm for carom billiards)
BALL_DIAMETER_MM = 61.5


def _get_table_dimensions(table_variant: TableVariant) -> Dict[str, float]:
    """Gibt die Tabellendimensionen für eine Variante zurück."""
    return TABLE_DIMENSIONS[table_variant]


def _table_to_cm(table_point: Tuple[float, float], table_variant: TableVariant) -> Tuple[float, float]:
    """Transformiert Tisch-Koordinaten (in diamond units) zu cm."""
    x, y = table_point
    dims = _get_table_dimensions(table_variant)
    
    # Skaliere von diamond units zu cm
    x_cm = (x / dims['length_units']) * dims['length_cm']
    y_cm = (y / dims['width_units']) * dims['width_cm']
    
    return x_cm, y_cm


def _draw_table_grid(ax, length_cm: float, width_cm: float, 
                     length_units: float, width_units: float,
                     margin_cm: float = 5.0, rotate: bool = False,
                     display_length_cm: float = None, display_width_cm: float = None,
                     display_length_units: float = None, display_width_units: float = None,
                     orig_length_cm: float = None, orig_width_cm: float = None):
    """Zeichnet das Tischgitter (Banden, Diamantlinien, Cadrelinien)."""
    
    # Verwende Display-Dimensionen für Rechteck (falls angegeben, sonst Original)
    if display_length_cm is None:
        display_length_cm = length_cm
    if display_width_cm is None:
        display_width_cm = width_cm
    if display_length_units is None:
        display_length_units = length_units
    if display_width_units is None:
        display_width_units = width_units
    
    # Zeichne Tischränder (Bandeninnenseiten) als dünne durchgehende Linie
    # Portrait-Mode: width×length (142×284), x: 0..142, y: 0..284
    # Ursprung links unten, x horizontal (kurze Seite), y vertikal (lange Seite)
    # Dünne Linie, damit Innenkante genau bei (0,0) liegt
    rect = mpatches.Rectangle(
        (0, 0), display_length_cm, display_width_cm,
        linewidth=1, edgecolor='black', facecolor='none', zorder=1
    )
    ax.add_patch(rect)
    
    # Zeichne Klein-Cadre-Linien - durchgehend, fein
    # 4 Linien: 2 lange (dritteln in Längsrichtung) und 2 kurze (im Cadreabstand von den kurzen Banden)
    # CADREABSTAND = 1/3 der Tischbreite (kurze Seite)
    # Lange Cadrelinien: Dritteln den Tisch in Längsrichtung (3 gleichbreite Streifen)
    # Kurze Cadrelinien: Im CADREABSTAND von den kurzen Banden
    if rotate:
        # Portrait-Mode: x ist kurze Seite (width), y ist lange Seite (length)
        # CADREABSTAND = 1/3 der Tischbreite = 1/3 von x (kurze Seite)
        cadre_distance_units = display_length_units / 3.0  # x ist kurze Seite
        cadre_distance_cm = display_length_cm / 3.0
        
        # Horizontale Cadrelinien (parallel zu x): Dritteln den Tisch (entlang y - lange Seite)
        # Diese bilden 3 gleichbreite horizontale Streifen
        for i in [1, 2]:
            y_pos = (i / 3.0) * display_width_cm  # y ist lange Seite
            ax.axhline(y_pos, color='darkgray', linewidth=0.8, linestyle='-', zorder=2)
        
        # Vertikale Cadrelinien (parallel zu y): Im CADREABSTAND von den kurzen Banden (links/rechts entlang x)
        # NICHT dritteln! Nur 2 Linien im CADREABSTAND von links und rechts
        x_left = cadre_distance_cm  # CADREABSTAND von linker Bande (x = 0)
        x_right = display_length_cm - cadre_distance_cm  # CADREABSTAND von rechter Bande (x = width)
        ax.axvline(x_left, color='darkgray', linewidth=0.8, linestyle='-', zorder=2)
        ax.axvline(x_right, color='darkgray', linewidth=0.8, linestyle='-', zorder=2)
    else:
        # Landscape-Mode: x ist lange Seite (length), y ist kurze Seite (width)
        # CADREABSTAND = 1/3 der Tischbreite = 1/3 von y (kurze Seite)
        cadre_distance_units = display_width_units / 3.0  # y ist kurze Seite
        cadre_distance_cm = display_width_cm / 3.0
        
        # Vertikale Cadrelinien (parallel zu y): Im CADREABSTAND von den kurzen Banden (links/rechts entlang x)
        # NICHT dritteln! Nur 2 Linien im CADREABSTAND von links und rechts
        x_left = cadre_distance_cm  # CADREABSTAND von linker Bande (x = 0)
        x_right = display_length_cm - cadre_distance_cm  # CADREABSTAND von rechter Bande (x = length)
        ax.axvline(x_left, color='darkgray', linewidth=0.8, linestyle='-', zorder=2)
        ax.axvline(x_right, color='darkgray', linewidth=0.8, linestyle='-', zorder=2)
        
        # Horizontale Cadrelinien (parallel zu x): Dritteln den Tisch (entlang y - kurze Seite)
        # Diese bilden 3 gleichbreite horizontale Streifen
        for i in [1, 2]:
            y_pos = (i / 3.0) * display_width_cm  # y ist kurze Seite
            ax.axhline(y_pos, color='darkgray', linewidth=0.8, linestyle='-', zorder=2)
    
    # Zeichne Diamantlinien - gestrichelt, fein
    # Diamantenlinien teilen IMMER in 4×8 Quadrate, unabhängig von der Tischgröße
    # Lange Seite: 8 Quadrate → 7 Linien
    # Kurze Seite: 4 Quadrate → 3 Linien
    if rotate:
        # Portrait-Mode: x ist kurze Seite, y ist lange Seite
        # Vertikale Diamantlinien (parallel zu y, entlang x - kurze Seite): 4 Quadrate → 3 Linien
        for i in range(1, 4):  # 3 Linien für 4 Quadrate
            x_pos = (i / 4.0) * display_length_cm
            ax.axvline(x_pos, color='gray', linewidth=0.5, linestyle='--', zorder=2)
        
        # Horizontale Diamantlinien (parallel zu x, entlang y - lange Seite): 8 Quadrate → 7 Linien
        for i in range(1, 8):  # 7 Linien für 8 Quadrate
            y_pos = (i / 8.0) * display_width_cm
            ax.axhline(y_pos, color='gray', linewidth=0.5, linestyle='--', zorder=2)
    else:
        # Landscape-Mode: x ist lange Seite, y ist kurze Seite
        # Vertikale Diamantlinien (parallel zu y, entlang x - lange Seite): 8 Quadrate → 7 Linien
        for i in range(1, 8):  # 7 Linien für 8 Quadrate
            x_pos = (i / 8.0) * display_length_cm
            ax.axvline(x_pos, color='gray', linewidth=0.5, linestyle='--', zorder=2)
        
        # Horizontale Diamantlinien (parallel zu x, entlang y - kurze Seite): 4 Quadrate → 3 Linien
        for i in range(1, 4):  # 3 Linien für 4 Quadrate
            y_pos = (i / 4.0) * display_width_cm
            ax.axhline(y_pos, color='gray', linewidth=0.5, linestyle='--', zorder=2)
    
    # Setze Achsenbegrenzungen mit Margin
    # Portrait-Mode: x: 0..width (142 cm), y: 0..length (284 cm)
    # Ursprung links unten (0,0)
    ax.set_xlim(-margin_cm, display_length_cm + margin_cm)  # x: 0..142
    ax.set_ylim(-margin_cm, display_width_cm + margin_cm)   # y: 0..284
    ax.set_aspect('equal')
    ax.grid(False)
    # WICHTIG: y-Achse sollte nicht invertiert werden (Ursprung unten)


def _draw_ball(ax, position_cm: Tuple[float, float], ball_name: str):
    """Zeichnet einen Ball mit korrektem Stil."""
    x_cm, y_cm = position_cm
    
    # Ball-Radius in cm
    radius_cm = (BALL_DIAMETER_MM / 2) / 10.0
    
    # B1 und B2: weiß mit schwarzem Rand
    # B3: schwarz gefüllt
    if ball_name == 'B3':
        facecolor = 'black'
        edgecolor = 'black'
        textcolor = 'white'
    elif ball_name in ['B1', 'B2']:
        facecolor = 'white'
        edgecolor = 'black'
        textcolor = 'black'
    else:  # Ghost Ball
        facecolor = 'none'
        edgecolor = 'gray'
        textcolor = 'gray'
    
    # Zeichne Ball-Kreis
    # Linienstärke: 1.0 Pixel für bessere Beurteilung der Daten
    if ball_name == 'GHOST':
        circle = mpatches.Circle(
            (x_cm, y_cm), radius_cm,
            facecolor=facecolor, edgecolor=edgecolor, linewidth=1.0,
            linestyle='--', zorder=10
        )
    else:
        circle = mpatches.Circle(
            (x_cm, y_cm), radius_cm,
            facecolor=facecolor, edgecolor=edgecolor, linewidth=1.0,
            zorder=10
        )
    ax.add_patch(circle)
    
    # Zeichne Label - zentriert auf dem Ball, Text bleibt immer aufrecht
    ax.text(x_cm, y_cm, ball_name, ha='center', va='center',
            fontsize=10, fontweight='bold', color=textcolor, zorder=11, rotation=0)


def _draw_trajectory(ax, trajectory_points_cm: List[Tuple[float, float]], 
                     ball_name: str, start_position_cm: Tuple[float, float]):
    """Zeichnet eine Trajektorie."""
    trajectory_colors = {
        'B1': 'red',
        'B2': 'blue',
        'B3': 'green',
    }
    color = trajectory_colors.get(ball_name, 'orange')
    
    # Verbinde alle Punkte
    all_points = [start_position_cm] + trajectory_points_cm
    if len(all_points) < 2:
        return
    
    xs, ys = zip(*all_points)
    ax.plot(xs, ys, color=color, linewidth=2, alpha=0.7, zorder=5)
    
    # Zeichne Punkte
    for i, (x, y) in enumerate(trajectory_points_cm, 1):
        ax.plot(x, y, 'o', color=color, markersize=6, zorder=6)


@app.command()
def draw(
    yaml_path: Path = typer.Argument(..., help="Pfad zur Szenen-YAML-Datei"),
    tb: bool = typer.Option(False, "--tb", help="Turnier-Billard verwenden (210×105 cm statt 284×142 cm)"),
    portrait: bool = typer.Option(False, "--portrait", help="Portrait-Mode: x=kurze Seite (0..40), y=lange Seite (0..80)"),
    landscape: bool = typer.Option(True, "--landscape/--no-landscape", help="Landscape-Mode (Default): x=lange Seite (0..80), y=kurze Seite (0..40), 90° nach rechts gedreht"),
    output_path: Optional[Path] = typer.Option(None, "--output", "-o", help="Ausgabepfad für das Bild (optional)"),
    dpi: int = typer.Option(150, "--dpi", help="Auflösung für gespeichertes Bild"),
) -> None:
    """Zeichnet eine Szenen-YAML auf einem sauberen Canvas mit Gitter.
    
    Landscape-Mode (Default):
    - Ursprung links unten (0,0)
    - x-Achse: horizontal, lange Bande (0..80 diamond units = 284 cm)
    - y-Achse: vertikal, kurze Bande (0..40 diamond units = 142 cm)
    - Alle Positionen um 90° nach rechts gedreht
    
    Portrait-Mode (--portrait):
    - Ursprung links unten (0,0)
    - x-Achse: horizontal, kurze Bande (0..40 diamond units = 142 cm)
    - y-Achse: vertikal, lange Bande (0..80 diamond units = 284 cm)
    """
    
    # Bestimme Modus: Wenn --portrait gesetzt, verwende Portrait, sonst Landscape
    use_portrait = portrait
    
    scene_model = load_scene_yaml(yaml_path)
    
    # Bestimme Tischvariante
    if tb:
        # --tb gesetzt: Turnier-Billard verwenden
        table_var = TableVariant.SMALL_TOURNAMENT
    else:
        # Verwende Variante aus YAML
        table_var = scene_model.table.variant
    
    dims = _get_table_dimensions(table_var)
    orig_dims = _get_table_dimensions(scene_model.table.variant)
    
    # YAML-Koordinaten: x = entlang kurzer Seite (0..40), y = entlang langer Seite (0..80)
    if use_portrait:
        # Portrait-Mode: x entlang width (kurze Seite), y entlang length (lange Seite)
        display_length_cm = dims['width_cm']   # x: 0..142 (kurze Seite horizontal)
        display_width_cm = dims['length_cm']   # y: 0..284 (lange Seite vertikal)
        display_length_units = dims['width_units']  # 40 (x-Achse)
        display_width_units = dims['length_units']  # 80 (y-Achse)
        fig, ax = plt.subplots(figsize=(10, 14))  # Portrait: höher als breit
    else:
        # Landscape-Mode: x entlang length (lange Seite), y entlang width (kurze Seite)
        display_length_cm = dims['length_cm']  # x: 0..284 (lange Seite horizontal)
        display_width_cm = dims['width_cm']    # y: 0..142 (kurze Seite vertikal)
        display_length_units = dims['length_units']  # 80 (x-Achse)
        display_width_units = dims['width_units']    # 40 (y-Achse)
        fig, ax = plt.subplots(figsize=(14, 10))  # Landscape: breiter als hoch
    
    # Transformiere Positionen von diamond units zu cm
    # YAML-Koordinaten: (x, y) wobei x entlang kurzer Seite (0..40), y entlang langer Seite (0..80)
    balls_cm = {}
    for ball_name, ball_data in scene_model.balls.items():
        x_diamond, y_diamond = ball_data.position
        
        if use_portrait:
            # Portrait-Mode: x entlang kurzer Seite (width), y entlang langer Seite (length)
            # Keine Transformation nötig, aber proportionale Skalierung erforderlich
            # Schritt 1: Skaliere auf Original-Dimensionen (bezogen auf orig_dims)
            x_cm_orig = (x_diamond / orig_dims['width_units']) * orig_dims['width_cm']  # x entlang kurzer Seite
            y_cm_orig = (y_diamond / orig_dims['length_units']) * orig_dims['length_cm']  # y entlang langer Seite
            
            # Schritt 2: Skaliere proportional auf Ziel-Dimensionen
            scale_factor_width = dims['width_cm'] / orig_dims['width_cm']  # Skalierungsfaktor für kurze Seite
            scale_factor_length = dims['length_cm'] / orig_dims['length_cm']  # Skalierungsfaktor für lange Seite
            x_cm_final = x_cm_orig * scale_factor_width  # x entlang kurzer Seite
            y_cm_final = y_cm_orig * scale_factor_length  # y entlang langer Seite
        else:
            # Landscape-Mode: Um 90° nach rechts gedreht
            # WICHTIG: Für proportionale Positionen müssen wir zuerst auf Original-Dimensionen skalieren,
            # dann transformieren, dann proportional auf Ziel-Dimensionen skalieren
            # Oder einfacher: Verwende orig_dims für Skalierung, dann transformiere, dann skaliere proportional
            
            # Schritt 1: Skaliere auf Original-Dimensionen (bezogen auf orig_dims)
            x_cm_orig = (x_diamond / orig_dims['width_units']) * orig_dims['width_cm']  # x entlang kurzer Seite
            y_cm_orig = (y_diamond / orig_dims['length_units']) * orig_dims['length_cm']  # y entlang langer Seite
            
            # Schritt 2: Transformiere (Rotation um 90° nach rechts)
            # (x_new, y_new) = (y_old, width - x_old)
            x_transformed = y_cm_orig  # y wird zu x (lange Seite)
            y_transformed = orig_dims['width_cm'] - x_cm_orig  # width - x wird zu y (kurze Seite)
            
            # Schritt 3: Skaliere proportional auf Ziel-Dimensionen
            scale_factor_length = dims['length_cm'] / orig_dims['length_cm']  # Skalierungsfaktor für lange Seite
            scale_factor_width = dims['width_cm'] / orig_dims['width_cm']  # Skalierungsfaktor für kurze Seite
            x_cm_final = x_transformed * scale_factor_length  # x entlang langer Seite
            y_cm_final = y_transformed * scale_factor_width  # y entlang kurzer Seite
        
        balls_cm[ball_name] = (x_cm_final, y_cm_final)
    
    # Transformiere Ghost Ball
    ghost_ball_cm = None
    if scene_model.ghost_ball:
        gx_diamond, gy_diamond = scene_model.ghost_ball.position
        
        if use_portrait:
            # Portrait-Mode: proportionale Skalierung
            gx_cm_orig = (gx_diamond / orig_dims['width_units']) * orig_dims['width_cm']
            gy_cm_orig = (gy_diamond / orig_dims['length_units']) * orig_dims['length_cm']
            scale_factor_width = dims['width_cm'] / orig_dims['width_cm']
            scale_factor_length = dims['length_cm'] / orig_dims['length_cm']
            gx_cm_final = gx_cm_orig * scale_factor_width
            gy_cm_final = gy_cm_orig * scale_factor_length
        else:
            # Landscape-Mode: Um 90° nach rechts gedreht
            # Wie bei normalen Bällen: Skaliere auf Original, transformiere, skaliere proportional
            gx_cm_orig = (gx_diamond / orig_dims['width_units']) * orig_dims['width_cm']
            gy_cm_orig = (gy_diamond / orig_dims['length_units']) * orig_dims['length_cm']
            gx_transformed = gy_cm_orig
            gy_transformed = orig_dims['width_cm'] - gx_cm_orig
            scale_factor_length = dims['length_cm'] / orig_dims['length_cm']
            scale_factor_width = dims['width_cm'] / orig_dims['width_cm']
            gx_cm_final = gx_transformed * scale_factor_length
            gy_cm_final = gy_transformed * scale_factor_width
        
        ghost_ball_cm = (gx_cm_final, gy_cm_final)
    
    # Zeichne Gitter
    _draw_table_grid(ax, display_length_cm, display_width_cm, 
                     display_length_units, display_width_units, rotate=use_portrait,
                     display_length_cm=display_length_cm, display_width_cm=display_width_cm,
                     display_length_units=display_length_units, display_width_units=display_width_units,
                     orig_length_cm=dims['length_cm'], orig_width_cm=dims['width_cm'])
    
    # Zeichne Trajektorien (vor den Bällen, damit sie darunter liegen)
    for ball_name, segments in scene_model.trajectory.items():
        if not segments or ball_name not in balls_cm:
            continue
        
        start_pos = balls_cm[ball_name]
        trajectory_points_cm = []
        
        for segment in segments:
            tx_diamond, ty_diamond = segment.point
            
            if use_portrait:
                # Portrait-Mode: proportionale Skalierung
                tx_cm_orig = (tx_diamond / orig_dims['width_units']) * orig_dims['width_cm']
                ty_cm_orig = (ty_diamond / orig_dims['length_units']) * orig_dims['length_cm']
                scale_factor_width = dims['width_cm'] / orig_dims['width_cm']
                scale_factor_length = dims['length_cm'] / orig_dims['length_cm']
                tx_cm_final = tx_cm_orig * scale_factor_width
                ty_cm_final = ty_cm_orig * scale_factor_length
            else:
                # Landscape-Mode: Um 90° nach rechts gedreht
                # Wie bei normalen Bällen: Skaliere auf Original, transformiere, skaliere proportional
                tx_cm_orig = (tx_diamond / orig_dims['width_units']) * orig_dims['width_cm']
                ty_cm_orig = (ty_diamond / orig_dims['length_units']) * orig_dims['length_cm']
                tx_transformed = ty_cm_orig
                ty_transformed = orig_dims['width_cm'] - tx_cm_orig
                scale_factor_length = dims['length_cm'] / orig_dims['length_cm']
                scale_factor_width = dims['width_cm'] / orig_dims['width_cm']
                tx_cm_final = tx_transformed * scale_factor_length
                ty_cm_final = ty_transformed * scale_factor_width
            
            trajectory_points_cm.append((tx_cm_final, ty_cm_final))
        
        _draw_trajectory(ax, trajectory_points_cm, ball_name, start_pos)
    
    # Zeichne Bälle
    for ball_name, position_cm in balls_cm.items():
        _draw_ball(ax, position_cm, ball_name)
    
    # Zeichne Ghost Ball
    if ghost_ball_cm:
        _draw_ball(ax, ghost_ball_cm, 'GHOST')
    
    # Titel und Labels
    table_name = "Match-Tisch" if table_var == TableVariant.MATCH else "Turnier-Tisch"
    if use_portrait:
        # Portrait-Mode: x entlang kurzer Seite (width), y entlang langer Seite (length)
        title = f"PORTRAIT MODE\n{scene_model.id}: {scene_model.title}\n{table_name}: {display_length_cm:.0f}×{display_width_cm:.0f} cm"
        title += f"\nKoordinatensystem: Ursprung links unten, x: 0..{int(display_length_units)} (kurze Seite), y: 0..{int(display_width_units)} (lange Seite)"
        ax.set_xlabel(f"x (diamond units: 0..{int(display_length_units)}, kurze Seite)", fontsize=10)
        ax.set_ylabel(f"y (diamond units: 0..{int(display_width_units)}, lange Seite)", fontsize=10)
    else:
        # Landscape-Mode: x entlang langer Seite (length), y entlang kurzer Seite (width), 90° nach rechts gedreht
        title = f"LANDSCAPE MODE (NORMAL)\n{scene_model.id}: {scene_model.title}\n{table_name}: {display_length_cm:.0f}×{display_width_cm:.0f} cm"
        title += f"\nKoordinatensystem: Ursprung links unten, x: 0..{int(display_length_units)} (lange Seite), y: 0..{int(display_width_units)} (kurze Seite), 90° nach rechts gedreht"
        ax.set_xlabel(f"x (diamond units: 0..{int(display_length_units)}, lange Seite)", fontsize=10)
        ax.set_ylabel(f"y (diamond units: 0..{int(display_width_units)}, kurze Seite)", fontsize=10)
    ax.set_title(title, fontsize=12, fontweight='bold', pad=20)
    
    plt.tight_layout()
    
    if output_path:
        plt.savefig(output_path, dpi=dpi, bbox_inches='tight')
        typer.echo(f"Bild gespeichert: {output_path}")
    else:
        plt.show()


if __name__ == "__main__":
    app()

