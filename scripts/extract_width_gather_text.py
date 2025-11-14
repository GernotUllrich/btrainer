#!/usr/bin/env python3
"""Extrahiert Text aus PDF für Width Gather Shots und aktualisiert YAML-Dateien.

Extrahiert:
- Titel
- cue.notes (Quantité de bille, Hauteur d'attaque, Effet, Energie)
- text.original_excerpt
"""

from pathlib import Path
import re
import yaml

try:
    import pdfplumber
except ImportError:
    print("Fehler: pdfplumber nicht installiert. Bitte installieren: pip install pdfplumber")
    exit(1)

PDF_PATH = Path("49210831040 Gernot Ullrich.pdf")
YAML_DIR = Path("data/annotations/gretillat")


def extract_scene_info(text: str, position: str) -> dict:
    """Extrahiert Informationen für eine Szene aus dem Text.
    
    Args:
        text: Volltext der Seite
        position: "oben" oder "unten"
    
    Returns:
        Dict mit title, cue_notes, original_excerpt
    """
    # Teile Text in obere und untere Hälfte
    lines = text.split('\n')
    mid_point = len(lines) // 2
    
    if position == "oben":
        scene_text = '\n'.join(lines[:mid_point])
    else:
        scene_text = '\n'.join(lines[mid_point:])
    
    # Extrahiere Titel (z.B. "2.1. DIRECT POINT - GATHER SHOT BY ONE BAND")
    # Titel endet vor "Quantité de bille" oder vor dem nächsten Absatz
    title_match = re.search(r'(\d+\.\d+\.?\s+[A-Z][^Q]+?)(?=\s*Quantité|\n\n|$)', scene_text, re.DOTALL)
    if title_match:
        title = title_match.group(1).strip()
        # Bereinige Titel (entferne Zeilenumbrüche, extra Leerzeichen)
        title = re.sub(r'\s+', ' ', title)
        title = re.sub(r'\s*-\s*', ' – ', title)  # Normalisiere Bindestriche
        # Entferne OCR-Artefakte (isolierte Zahlen, einzelne Buchstaben)
        title = re.sub(r'\s+\d+\s+', ' ', title)  # Entferne isolierte Zahlen
        title = re.sub(r'\s+[a-z]\s+', ' ', title, flags=re.IGNORECASE)  # Entferne einzelne Buchstaben
        title = re.sub(r'\s+', ' ', title)  # Nochmal extra Leerzeichen entfernen
        # Entferne Zahlen am Ende (z.B. "4 9 2 1 0 8 3 1")
        title = re.sub(r'\s+\d(\s+\d)*\s*$', '', title)
    else:
        title = None
    
    # Extrahiere Cue-Parameter
    cue_notes = []
    
    # Quantité de bille
    qty_match = re.search(r'Quantité de bille:\s*([^\n]+)', scene_text, re.IGNORECASE)
    if qty_match:
        cue_notes.append(f"Quantité de bille: {qty_match.group(1).strip()}")
    
    # Hauteur d'attaque (kann über mehrere Zeilen gehen, unterstützt verschiedene Apostrophe)
    # Unterstützt: gerader Apostroph ('), typografischer Apostroph ('), und andere Varianten
    height_match = re.search(r"Hauteur\s+d.atta?que:\s*([^\n]+)", scene_text, re.IGNORECASE | re.MULTILINE)
    if height_match:
        cue_notes.append(f"Hauteur d'attaque: {height_match.group(1).strip()}")
    
    # Effet
    effet_match = re.search(r'Effet:\s*([^\n]+)', scene_text, re.IGNORECASE)
    if effet_match:
        cue_notes.append(f"Effet: {effet_match.group(1).strip()}")
    
    # Energie
    energie_match = re.search(r'Energie:\s*([^\n]+)', scene_text, re.IGNORECASE)
    if energie_match:
        cue_notes.append(f"Energie: {energie_match.group(1).strip()}")
    
    # Extrahiere Text (alles nach den Parametern bis zur nächsten Szene oder Seitenende)
    # Suche nach englischem Text (beginnt meist mit Großbuchstaben)
    # Finde Position nach "Energie:" Parameter
    energie_pos = scene_text.find("Energie:")
    if energie_pos > 0:
        # Suche nach Text nach "Energie:" Parameter
        text_start_pos = scene_text.find("\n", energie_pos)
        remaining_text = scene_text[text_start_pos:] if text_start_pos > 0 else scene_text[energie_pos:]
        
        # Suche nach englischem Text (beginnt mit Großbuchstaben)
        # Unterstützt Zeilenumbrüche zwischen Wörtern
        text_patterns = [
            r'(If\s+ball\s+\d+\s+[^0-9]+?)(?=\d+\.\d+\.|$)',
            r'(If\s+[^0-9]+?)(?=\d+\.\d+\.|$)',
            r'(No\s+[^0-9]+?)(?=\d+\.\d+\.|$)',
            r'(This\s+[^0-9]+?)(?=\d+\.\d+\.|$)',
            r'(Ball\s+\d+\s+[^0-9]+?)(?=\d+\.\d+\.|$)',
            r'(The\s+[^0-9]+?)(?=\d+\.\d+\.|$)',
        ]
        
        original_excerpt = None
        for pattern in text_patterns:
            match = re.search(pattern, remaining_text, re.IGNORECASE | re.DOTALL)
            if match:
                original_excerpt = match.group(1).strip()
                # Bereinige den Text (entferne Zeilenumbrüche, extra Leerzeichen)
                original_excerpt = re.sub(r'\s+', ' ', original_excerpt)
                # Entferne einzelne Buchstaben am Ende (OCR-Artefakte)
                original_excerpt = re.sub(r'\s+[a-z]\s*$', '', original_excerpt)
                break
    else:
        original_excerpt = None
    
    return {
        "title": title,
        "cue_notes": cue_notes,
        "original_excerpt": original_excerpt,
    }


def update_yaml_file(yaml_path: Path, scene_info: dict) -> None:
    """Aktualisiert eine YAML-Datei mit extrahierten Informationen."""
    with yaml_path.open("r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    
    scene = data.get("scene", {})
    
    # Aktualisiere Titel
    if scene_info["title"]:
        scene["title"] = scene_info["title"]
    
    # Aktualisiere cue.notes
    if scene_info["cue_notes"]:
        if "cue" not in scene:
            scene["cue"] = {}
        scene["cue"]["notes"] = scene_info["cue_notes"]
    
    # Aktualisiere text.original_excerpt
    if scene_info["original_excerpt"]:
        if "text" not in scene:
            scene["text"] = {}
        scene["text"]["original_excerpt"] = scene_info["original_excerpt"]
    
    with yaml_path.open("w", encoding="utf-8") as fh:
        yaml.safe_dump(data, fh, allow_unicode=True, sort_keys=False, default_flow_style=False)


def main():
    """Hauptfunktion."""
    if not PDF_PATH.exists():
        print(f"Fehler: PDF nicht gefunden: {PDF_PATH}")
        return
    
    print("Extrahiere Text aus PDF für Width Gather Shots...")
    print()
    
    scene_num = 1
    
    with pdfplumber.open(PDF_PATH) as pdf:
        # Seiten 255-270: je 2 Szenen (oben/unten)
        for page_num in range(254, 270):  # 0-indexed: 254-269 = Seiten 255-270
            if page_num >= len(pdf.pages):
                print(f"  ⚠ Seite {page_num + 1} existiert nicht im PDF")
                continue
            
            page = pdf.pages[page_num]
            text = page.extract_text()
            
            if not text:
                print(f"  ⚠ Seite {page_num + 1}: Kein Text gefunden")
                continue
            
            # Extrahiere Informationen für beide Szenen
            for position in ["oben", "unten"]:
                scene_id = f"VS-width-02-{scene_num:02d}"
                yaml_path = YAML_DIR / f"{scene_id}.yaml"
                
                if not yaml_path.exists():
                    print(f"  ⚠ {scene_id}.yaml nicht gefunden, überspringe")
                    scene_num += 1
                    continue
                
                scene_info = extract_scene_info(text, position)
                
                update_yaml_file(yaml_path, scene_info)
                
                print(f"  ✓ {scene_id}.yaml ({position})")
                if scene_info["title"]:
                    print(f"      Titel: {scene_info['title'][:60]}...")
                
                scene_num += 1
        
        # Seite 271: letzte Szene
        if scene_num <= 33:
            page_num = 270  # 0-indexed, Seite 271
            if page_num < len(pdf.pages):
                page = pdf.pages[page_num]
                text = page.extract_text()
                
                scene_id = f"VS-width-02-{scene_num:02d}"
                yaml_path = YAML_DIR / f"{scene_id}.yaml"
                
                if yaml_path.exists():
                    scene_info = extract_scene_info(text, "oben")
                    update_yaml_file(yaml_path, scene_info)
                    print(f"  ✓ {scene_id}.yaml (oben)")
                    if scene_info["title"]:
                        print(f"      Titel: {scene_info['title'][:60]}...")
    
    print()
    print("✓ Text-Extraktion abgeschlossen!")


if __name__ == "__main__":
    main()

