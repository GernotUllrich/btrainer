#!/usr/bin/env python3
"""Visualisiert eine Szenen-YAML mit Trajektorien auf dem zugehörigen Bild."""

from pathlib import Path
from typing import Dict, List, Tuple

import matplotlib.pyplot as plt
import numpy as np
import typer

from src.services.ingest import load_scene_yaml

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


if __name__ == "__main__":
    app()

