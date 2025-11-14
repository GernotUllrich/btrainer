#!/usr/bin/env python3
"""Extrahiert Viertelbillard-Szenen (Width Gather Shots) aus dem PDF.

- Extrahiert Seiten 252-271 als PNG-Images (width_gather-nnn.png)
- Erstellt YAML-Dateien VS-width-02-01 bis VS-width-02-33
- Ab Seite 255: 2 Szenen pro Seite
"""

from pathlib import Path
import sys

try:
    import fitz  # PyMuPDF
except ImportError:
    print("Fehler: PyMuPDF nicht installiert. Bitte installieren: pip install PyMuPDF")
    sys.exit(1)

import yaml

# Pfade
PDF_PATH = Path("49210831040 Gernot Ullrich.pdf")
OUTPUT_IMAGE_DIR = Path("data/raw/gretillat")
OUTPUT_YAML_DIR = Path("data/annotations/gretillat")

# Erstelle Verzeichnisse
OUTPUT_IMAGE_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_YAML_DIR.mkdir(parents=True, exist_ok=True)


def extract_images(pdf_path: Path, start_page: int, end_page: int) -> None:
    """Extrahiert Seiten aus PDF als PNG-Images."""
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF nicht gefunden: {pdf_path}")
    
    doc = fitz.open(pdf_path)
    print(f"Extrahiere Seiten {start_page}-{end_page} aus PDF...")
    
    for page_num in range(start_page - 1, end_page):  # 0-indexed
        if page_num >= len(doc):
            print(f"  ⚠ Seite {page_num + 1} existiert nicht im PDF")
            continue
        
        page = doc[page_num]
        # Render mit hoher Auflösung
        pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))  # 2x Zoom für bessere Qualität
        
        # Speichere als width_gather-nnn.png
        output_path = OUTPUT_IMAGE_DIR / f"width_gather-{page_num + 1}.png"
        pix.save(output_path)
        print(f"  ✓ Seite {page_num + 1} → {output_path.name}")
    
    doc.close()
    print(f"✓ {end_page - start_page + 1} Seiten extrahiert\n")


def create_yaml_template(scene_id: str, page: int | str, scene_index: int) -> dict:
    """Erstellt eine YAML-Vorlage für eine Viertelbillard-Szene.
    
    Args:
        scene_id: ID der Szene (z.B. "VS-width-02-01")
        page: Seitenzahl als Integer oder String mit Position (z.B. 270 oder "270 oben")
        scene_index: Index der Szene (1-basiert)
    """
    return {
        "scene": {
            "id": scene_id,
            "title": f"Width Gather Shot – Szene {scene_index:02d}",
            "source": {
                "work": "Gretillat - L'apprentissage du billard français",
                "section": "Width Gather Shots",
                "page": page,
            },
            "difficulty": "easy",
            "description": "TODO: Szene beschreiben.",
            "table": {
                "type": "carom_standard",
                "size_units": [40.0, 80.0],
                "unit": "diamonds",
                "origin": "bottom_left",
                "grid_resolution": 0.5,
                "physical_size_cm": [284.0, 142.0],
                "variant": "match",
            },
            "balls": {
                "B1": {"color": "white", "position": [0.0, 0.0]},
                "B2": {"color": "yellow", "position": [0.0, 0.0]},
                "B3": {"color": "red", "position": [0.0, 0.0]},
            },
            "ghost_ball": {
                "position": [0.0, 0.0],
                "notes": "Virtuelle Position des Spielballs bei Kontakt mit B2",
            },
            "ball_contact": {
                "fraction": 0.0,
                "label": "pending",
            },
            "cue": {
                "cue_direction": [0.0, 0.0],
                "attack_height": "pending",
                "effect_stage": "stage_0",
                "effect_side": "none",
                "cue_inclination_deg": 0.0,
                "notes": ["TODO – ergänzen"],
            },
            "tempo_force": {
                "tempo": 0,
                "force": 0,
                "comments": "pending",
            },
            "trajectory": {
                "B1": [],
                "B2": [],
                "B3": [],
            },
            "text": {
                "original_language": "fr",
                "original_excerpt": "TODO – ergänzen",
                "de_summary": "TODO – übersetzen",
            },
            "remarks": ["TODO – ergänzen"],
        }
    }


def create_yaml_files() -> None:
    """Erstellt YAML-Dateien für alle Viertelbillard-Szenen."""
    print("Erstelle YAML-Dateien...")
    
    # Ab Seite 255: 2 Szenen pro Seite bis Seite 271
    # VS-width-02-01 bis VS-width-02-33 (33 Szenen)
    scene_num = 1
    
    # Seite 255-270: je 2 Szenen (oben/unten)
    for page in range(255, 271):
        for scene_in_page, position in enumerate(["oben", "unten"], 1):
            scene_id = f"VS-width-02-{scene_num:02d}"
            page_with_position = f"{page} {position}"
            yaml_data = create_yaml_template(scene_id, page_with_position, scene_num)
            
            output_path = OUTPUT_YAML_DIR / f"{scene_id}.yaml"
            with output_path.open("w", encoding="utf-8") as fh:
                yaml.safe_dump(yaml_data, fh, allow_unicode=True, sort_keys=False, default_flow_style=False)
            
            print(f"  ✓ {scene_id}.yaml (Seite {page_with_position})")
            scene_num += 1
    
    # Seite 271: letzte Szene (VS-width-02-33)
    if scene_num <= 33:
        scene_id = f"VS-width-02-{scene_num:02d}"
        yaml_data = create_yaml_template(scene_id, "271 oben", scene_num)
        
        output_path = OUTPUT_YAML_DIR / f"{scene_id}.yaml"
        with output_path.open("w", encoding="utf-8") as fh:
            yaml.safe_dump(yaml_data, fh, allow_unicode=True, sort_keys=False, default_flow_style=False)
        
        print(f"  ✓ {scene_id}.yaml (Seite 271 oben, letzte Szene)")
    
    print(f"\n✓ {scene_num} YAML-Dateien erstellt")


def main():
    """Hauptfunktion."""
    print("=" * 60)
    print("Extraktion der Viertelbillard-Szenen (Width Gather Shots)")
    print("=" * 60)
    print()
    
    # 1. Extrahiere Images (Seiten 252-271)
    extract_images(PDF_PATH, 252, 271)
    
    # 2. Erstelle YAML-Dateien
    create_yaml_files()
    
    print()
    print("=" * 60)
    print("✓ Extraktion abgeschlossen!")
    print("=" * 60)
    print(f"Images: {OUTPUT_IMAGE_DIR}")
    print(f"YAMLs:  {OUTPUT_YAML_DIR}")


if __name__ == "__main__":
    main()

