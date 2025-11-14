from __future__ import annotations

import sys
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import typer
import yaml

from src.db.session import session_scope
from src.db.schemas import SceneModel, GhostBallModel
from src.services.ingest import import_scenes, load_scene_yaml

app = typer.Typer(help="Interactive tools for capturing and importing billiards scenes")

# Standard-Kalibrierungspunkte für Vollbild (long_gather)
# Diese Werte sind für alle Bilder aus dem Gretillat-Datensatz identisch
# Da die Abbildungen perpendicular sind:
# - x_ursprung = x_kurze_bande (beide bei x=0)
# - y_ursprung = y_lange_bande (beide bei y=0)
# Berechnet aus mehreren Beispiel-Kalibrierungen:
# - x_ursprung: 185.1, 182.5, 185.2 → Durchschnitt: 184.27
# - x_kurze_bande: 184.2, 183.9, 186.5 → Durchschnitt: 184.87
# - Mittelwert x: (184.27 + 184.87) / 2 = 184.57
# - y_ursprung: 1187.5, 1184.4, 1190.6 → Durchschnitt: 1187.5
# - y_lange_bande: 1184.7, 1183.4, 1190.1 → Durchschnitt: 1186.07
# - Mittelwert y: (1187.5 + 1186.07) / 2 = 1186.79
DEFAULT_CALIBRATION_POINTS_FULL = np.array([
    [184.57, 1186.79],  # Ursprung (0,0) - x und y als Mittelwerte
    [623.7, 1186.79],   # lange Bande (40,0) - y = y_ursprung
    [184.57, 303.7],    # kurze Bande (0,80) - x = x_ursprung
])

# Standard-Kalibrierungspunkte für Viertelbillard (width_gather)
# Nur unteres Viertel wird gezeigt, daher dritter Punkt bei (0,20) statt (0,80)
# TODO: Diese Werte müssen noch kalibriert werden - vorläufige Schätzung
DEFAULT_CALIBRATION_POINTS_QUARTER = np.array([
    [184.57, 1186.79],  # Ursprung (0,0) - x und y als Mittelwerte (wie Vollbild)
    [623.7, 1186.79],   # lange Bande (40,0) - y = y_ursprung (wie Vollbild)
    [184.57, 965.0],    # zweiter Diamant (0,20) - x = x_ursprung, y geschätzt
])


try:
    import cv2

    HAS_CV2 = True
except ImportError:  # pragma: no cover
    HAS_CV2 = False

import matplotlib.pyplot as plt  # noqa: E402

try:
    import select  # type: ignore[attr-defined]
except ImportError:  # pragma: no cover
    select = None  # type: ignore[assignment]


class CaptureSession:
    def __init__(self, image: np.ndarray) -> None:
        self.image = image
        self.fig, self.ax = plt.subplots(figsize=(6, 9))
        self.ax.imshow(image)
        self.ax.set_title("Kalibrierung starten")
        plt.show(block=False)
        typer.echo("-- Toolbar nutzen (Zoom/Pan). Mit Enter bestätigen, wenn bereit --")
        input()
        self._lines: Dict[str, list] = {}
        self._last_points: Dict[str, List[np.ndarray]] = {}
        self._start_points: Dict[str, np.ndarray] = {}
        self._last_key: Optional[str] = None
        self.fig.canvas.mpl_connect("key_press_event", self._on_key_press)

    def _on_key_press(self, event) -> None:
        self._last_key = event.key

    def pop_key(self) -> Optional[str]:
        key = self._last_key
        self._last_key = None
        return key

    def add_point_to_trace(self, ball: str, point: np.ndarray) -> None:
        history = self._last_points.setdefault(ball, [])
        history.append(point.copy())

        if len(history) == 1:
            start = self._start_points.get(ball)
            artists: list = []
            if start is not None:
                line, = self.ax.plot([start[0], point[0]], [start[1], point[1]], c="red", linewidth=1.5)
                artists.append(line)
            scatter = self.ax.scatter(point[0], point[1], c="red", s=40)
            artists.append(scatter)
            self._lines.setdefault(ball, []).extend(artists)
        else:
            prev = history[-2]
            line, = self.ax.plot([prev[0], point[0]], [prev[1], point[1]], c="red", linewidth=1.5)
            scatter = self.ax.scatter(point[0], point[1], c="red", s=40)
            self._lines.setdefault(ball, []).extend([line, scatter])
        plt.draw()

    def remove_last_point(self, ball: str) -> None:
        history = self._last_points.get(ball)
        if not history:
            return
        history.pop()
        to_remove = self._lines.get(ball, [])
        if to_remove:
            artists = to_remove[-2:] if len(history) >= 1 else to_remove[-1:]
            for artist in artists:
                artist.remove()
            self._lines[ball] = to_remove[: -len(artists)]
        plt.draw()

    def reset_trace(self, ball: str, start_point: Optional[List[float]] = None) -> None:
        for artist in self._lines.get(ball, []):
            artist.remove()
        self._lines[ball] = []
        self._last_points[ball] = []
        if start_point is not None:
            self._start_points[ball] = np.array(start_point, dtype=float)
        elif ball in self._start_points:
            del self._start_points[ball]
        plt.draw()

    def wait_for_point_or_key(
        self,
        prompt: str,
        refine_ball: bool = False,
        ball_name: Optional[str] = None,
    ) -> tuple[str, Any]:
        self.ax.set_title(prompt)
        plt.draw()
        while True:
            if self._last_key is not None:
                key = self.pop_key()
                return "key", key
            # Längerer Timeout, damit Klicks nicht verpasst werden
            click = plt.ginput(1, timeout=1.0)
            if click:
                raw = np.array(click[0], dtype=float)
                typer.secho(f"{prompt}: Pixel=({raw[0]:.1f}, {raw[1]:.1f})", fg=typer.colors.GREEN)
                if refine_ball:
                    refined = _refine(self.image, raw, ball_name=ball_name)
                    # Prüfe, ob Korrektur übersprungen wurde (z.B. Verschiebung zu groß)
                    if np.allclose(raw, refined, atol=0.1):
                        typer.secho(
                            f" → Originalposition verwendet (Korrektur übersprungen)",
                            fg=typer.colors.YELLOW,
                        )
                    else:
                        typer.secho(
                            f" → verfeinert: Pixel=({refined[0]:.1f}, {refined[1]:.1f})",
                            fg=typer.colors.BRIGHT_GREEN,
                        )
                    return "point", refined
                return "point", raw
            if select is not None:
                ready, _, _ = select.select([sys.stdin], [], [], 0)
                if ready:
                    line = sys.stdin.readline().strip()
                    if line == "":
                        return "key", "enter"
                    lowered = line.lower()
                    if lowered in {"q", "quit"}:
                        return "key", "q"
                    if lowered in {"u", "undo"}:
                        return "key", "backspace"
            plt.pause(0.01)

    def get_point(
        self,
        prompt: str,
        refine_ball: bool = False,
        allow_skip: bool = False,
        ball_name: Optional[str] = None,
    ) -> Optional[np.ndarray]:
        self.ax.set_title(prompt)
        plt.draw()
        click = plt.ginput(1, timeout=0)
        if not click:
            if allow_skip:
                typer.echo("    → beendet.")
                return None
            raise typer.BadParameter("Keine Eingabe erhalten, bitte erneut starten")
        raw = np.array(click[0], dtype=float)
        typer.secho(f"{prompt}: Pixel=({raw[0]:.1f}, {raw[1]:.1f})", fg=typer.colors.GREEN)
        if refine_ball:
            refined = _refine(self.image, raw, ball_name=ball_name)
            # Prüfe, ob Korrektur übersprungen wurde (z.B. Verschiebung zu groß)
            if np.allclose(raw, refined, atol=0.1):
                typer.secho(
                    f" → Originalposition verwendet (Korrektur übersprungen)",
                    fg=typer.colors.YELLOW,
                )
            else:
                typer.secho(
                    f" → verfeinert: Pixel=({refined[0]:.1f}, {refined[1]:.1f})",
                    fg=typer.colors.BRIGHT_GREEN,
                )
            return refined
        return raw

    def close(self) -> None:
        plt.close(self.fig)


def _compute_matrix(calib: np.ndarray, table_coords: Optional[np.ndarray] = None) -> np.ndarray:
    """Berechnet Transformationsmatrix von Pixel- zu Tisch-Koordinaten.
    
    Args:
        calib: Pixel-Koordinaten der 3 Kalibrierungspunkte (3x2)
        table_coords: Tisch-Koordinaten der 3 Kalibrierungspunkte (3x2).
                     Standard: [[0,0], [40,0], [0,80]] für Vollbild
    """
    pixel = np.column_stack((calib, np.ones(3)))
    if table_coords is None:
        table_coords = np.array([[0.0, 0.0], [40.0, 0.0], [0.0, 80.0]])
    mx, *_ = np.linalg.lstsq(pixel, table_coords[:, 0], rcond=None)
    my, *_ = np.linalg.lstsq(pixel, table_coords[:, 1], rcond=None)
    return np.vstack([mx, my])


def _extract_page_number(page: int | str | None) -> int | None:
    """Extrahiert die Seitennummer aus einem page-Wert.
    
    Args:
        page: Seitenzahl als Integer oder String (z.B. "270", "270 oben", "270 unten")
    
    Returns:
        Seitennummer als Integer oder None
    """
    if page is None:
        return None
    if isinstance(page, int):
        return page
    # Extrahiere Zahl aus String (z.B. "270 oben" -> 270)
    import re
    match = re.search(r'\d+', str(page))
    if match:
        return int(match.group())
    return None


def _pixel_to_table(matrix: np.ndarray, point: np.ndarray) -> tuple[float, float]:
    vec = np.array([point[0], point[1], 1.0])
    tx = matrix @ vec
    return float(tx[0]), float(tx[1])


def _clamp_to_table(table_coords: Tuple[float, float], table_size: Tuple[float, float] = (40.0, 80.0)) -> Tuple[float, float]:
    """Begrenzt Tisch-Koordinaten auf den gültigen Bereich (0..table_w, 0..table_h)."""
    x, y = table_coords
    table_w, table_h = table_size
    x = max(0.0, min(x, table_w))
    y = max(0.0, min(y, table_h))
    return (x, y)


def _snap_to_grid(table_coords: Tuple[float, float], table_size: Tuple[float, float] = (40.0, 80.0)) -> Tuple[float, float]:
    """Snappt Tisch-Koordinaten auf markante Linien, wenn sie innerhalb von 0.6 Diamonds liegen.
    
    Koordinatensystem: (0,0) = linke untere Ecke, x = horizontal, y = vertikal
    Snaplinien:
    - Ursprung (0, 0)
    - Diamantlinien lange Seite (y-Richtung, parallel zur kurzen Bande): 10, 20, 30, 40, 50, 60, 70
    - Diamantlinien kurze Seite (x-Richtung, parallel zur langen Bande): 10, 20, 30
    - Klein-Cadre vertikal (x-Koordinaten, parallel zur langen Bande): Kleine Seite gedrittelt (1/3 und 2/3 der Tischbreite)
    - Klein-Cadre horizontal (y-Koordinaten, parallel zur kurzen Bande): CadreAbstand = Tischbreite/3 von unten und oben
    """
    x, y = table_coords
    table_w, table_h = table_size
    
    # Aggressiveres Snapping: Abstand kleiner 0.6 Diamonds wird gesnappt
    snap_threshold = 0.6
    
    # Snapping auf Ursprung (0, 0)
    if abs(x) <= snap_threshold:
        x = 0.0
    if abs(y) <= snap_threshold:
        y = 0.0
    
    # Diamantlinien lange Seite (y-Richtung): 10, 20, 30, 40, 50, 60, 70
    diamond_lines_y = [10.0, 20.0, 30.0, 40.0, 50.0, 60.0, 70.0]
    for line_y in diamond_lines_y:
        if abs(y - line_y) <= snap_threshold:
            y = line_y
            break
    
    # Diamantlinien kurze Seite (x-Richtung): 10, 20, 30
    diamond_lines_x = [10.0, 20.0, 30.0]
    for line_x in diamond_lines_x:
        if abs(x - line_x) <= snap_threshold:
            x = line_x
            break
    
    # Klein-Cadre horizontal (x-Richtung): Kleine Seite wird gedrittelt
    # Linien bei 1/3 und 2/3 der Tischbreite
    klein_cadre_x = [table_w / 3.0, 2.0 * table_w / 3.0]
    for line_x in klein_cadre_x:
        if abs(x - line_x) <= snap_threshold:
            x = line_x
            break
    
    # Klein-Cadre vertikal (y-Richtung): CadreAbstand = Tischbreite/3
    # Von oben im CadreAbstand eine Linie, von unten im CadreAbstand eine Linie
    cadre_abstand = table_w / 3.0
    klein_cadre_y = [cadre_abstand, table_h - cadre_abstand]
    for line_y in klein_cadre_y:
        if abs(y - line_y) <= snap_threshold:
            y = line_y
            break
    
    return (x, y)


def _round_pair(coords: Tuple[float, float]) -> List[float]:
    return [round(coords[0], 2), round(coords[1], 2)]


DigitTemplateKey = Tuple[int, bool]
DIGIT_TEMPLATE_CACHE: Dict[DigitTemplateKey, np.ndarray] = {}


def _ball_digit(ball_name: Optional[str]) -> Optional[int]:
    if not ball_name:
        return None
    if ball_name.upper().startswith("B") and len(ball_name) >= 2:
        try:
            return int(ball_name[1])
        except ValueError:
            return None
    return None


def _get_digit_template(digit: int, inverted: bool) -> np.ndarray:
    key: DigitTemplateKey = (digit, inverted)
    cached = DIGIT_TEMPLATE_CACHE.get(key)
    if cached is not None:
        return cached

    size = 48
    canvas = np.full((size, size), 0.6 if not inverted else 0.4, dtype=np.float32)
    face_color = 0.95 if not inverted else 0.05
    stroke_color = 0.1 if not inverted else 0.9

    center = size // 2
    cv2.circle(canvas, (center, center), center - 2, face_color, thickness=-1, lineType=cv2.LINE_AA)
    cv2.circle(canvas, (center, center), center - 2, stroke_color, thickness=2, lineType=cv2.LINE_AA)

    text = str(digit)
    font = cv2.FONT_HERSHEY_SIMPLEX
    font_scale = 1.1
    thickness = 3
    text_size, baseline = cv2.getTextSize(text, font, font_scale, thickness)
    text_x = max((size - text_size[0]) // 2, 0)
    text_y = min((size + text_size[1]) // 2, size - baseline)
    cv2.putText(
        canvas,
        text,
        (text_x, text_y),
        font,
        font_scale,
        stroke_color,
        thickness,
        lineType=cv2.LINE_AA,
    )
    template = cv2.GaussianBlur(canvas, (3, 3), 0)
    DIGIT_TEMPLATE_CACHE[key] = template
    return template


def _refine_with_digit(gray_patch: np.ndarray, x0: int, y0: int, ball_name: str) -> Optional[np.ndarray]:
    if not HAS_CV2:
        return None
    digit = _ball_digit(ball_name)
    if digit is None:
        return None
    patch = gray_patch.astype(np.float32)
    if patch.size == 0:
        return None
    patch_norm = cv2.normalize(patch, None, 0.0, 1.0, cv2.NORM_MINMAX)

    best_score = -1.0
    best_center: Optional[Tuple[float, float]] = None
    for inverted in (False, True):
        template = _get_digit_template(digit, inverted)
        th, tw = template.shape
        if patch_norm.shape[0] < th or patch_norm.shape[1] < tw:
            continue
        result = cv2.matchTemplate(patch_norm, template, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = cv2.minMaxLoc(result)
        if max_val > best_score:
            best_score = max_val
            best_center = (max_loc[0] + tw / 2, max_loc[1] + th / 2)

    if best_center is not None and best_score >= 0.4:
        return np.array([x0 + best_center[0], y0 + best_center[1]])
    return None


def _capture_new_points(
    session: CaptureSession,
    matrix: np.ndarray,
    ball_name: str,
    start_index: int = 0,
    table_size: Tuple[float, float] = (40.0, 80.0),
) -> tuple[List[Dict[str, Any]], bool]:
    typer.echo(
        "  Punkte nacheinander anklicken. Enter (Plot oder Terminal) beendet, Backspace/U undo, q = Abbruch."
    )
    session._last_points.setdefault(ball_name, [])
    created: List[Dict[str, Any]] = []
    idx = start_index
    aborted = False
    while True:
        prompt = f"{ball_name} Punkt {idx + 1}"
        action, payload = session.wait_for_point_or_key(prompt, ball_name=ball_name)
        if action == "key":
            key = payload
            if key in {"enter", "return"}:
                break
            if key in {"q", "escape"}:
                typer.echo("    → Eingabe abgebrochen.")
                created.clear()
                aborted = True
                break
            if key in {"backspace", "u"}:
                if created:
                    created.pop()
                    session.remove_last_point(ball_name)
                    idx = max(start_index, idx - 1)
                    typer.secho("      letzter Punkt entfernt.", fg=typer.colors.YELLOW)
                else:
                    typer.secho("      kein Punkt zum Entfernen.", fg=typer.colors.YELLOW)
                continue
            continue

        point = payload
        if point is None:
            continue

        # Transformiere zu Tisch-Koordinaten, begrenze auf Tischbereich (kein Snapping für Trajektorie-Punkte)
        table_coords = _pixel_to_table(matrix, point)
        clamped_coords = _clamp_to_table(table_coords, table_size)
        coords = _round_pair(clamped_coords)
        
        # Prüfe, ob begrenzt wurde
        if not np.allclose(table_coords, clamped_coords, atol=0.01):
            typer.secho(f"      → auf Tischbereich begrenzt: {coords}", fg=typer.colors.YELLOW)
        
        session.add_point_to_trace(ball_name, point)
        created.append(
            {
                "point": coords,
                "path_type": "line",
                "event": None,
                "notes": None,
            }
        )
        typer.secho(f"      → gesetzt auf {coords}", fg=typer.colors.CYAN)
        idx += 1
    return created, aborted


def _refine(image: np.ndarray, point: np.ndarray, radius: int = 35, ball_name: Optional[str] = None) -> np.ndarray:
    x, y = map(int, point)
    h, w = image.shape[:2]
    
    # Maximale akzeptable Verschiebung: 1/4 Ballbreite (entspricht der Maus-Genauigkeit)
    # Größere Verschiebungen deuten auf falsche Erkennung hin (z.B. virtuelle Bälle)
    max_shift = radius / 4.0
    
    x0, x1 = max(x - radius, 0), min(x + radius, w)
    y0, y1 = max(y - radius, 0), min(y + radius, h)
    patch = image[y0:y1, x0:x1]
    if patch.size == 0:
        return point
    gray = patch.mean(axis=2).astype(np.uint8)
    if HAS_CV2:
        blur = cv2.medianBlur(gray, 5)
        circles = cv2.HoughCircles(
            blur,
            cv2.HOUGH_GRADIENT,
            dp=1.2,
            minDist=radius * 0.8,
            param1=80,
            param2=15,
            minRadius=int(radius * 0.3),
            maxRadius=int(radius * 1.1),
        )
        if circles is not None:
            cx, cy, _ = circles[0][0]
            refined_point = np.array([x0 + cx, y0 + cy])
            # Prüfe Verschiebung: Nur akzeptieren, wenn weniger als 1/4 Ballbreite
            shift = np.linalg.norm(refined_point - point)
            if shift > max_shift:
                return point
            return refined_point
        if ball_name is not None:
            digit_match = _refine_with_digit(gray, x0, y0, ball_name)
            if digit_match is not None:
                # Prüfe Verschiebung: Nur akzeptieren, wenn weniger als 1/4 Ballbreite
                shift = np.linalg.norm(digit_match - point)
                if shift > max_shift:
                    return point
                return digit_match
    thresh = gray.mean()
    mask = gray < thresh
    coords = np.column_stack(np.nonzero(mask))
    if coords.size == 0:
        return point
    cy, cx = coords.mean(axis=0)
    refined_point = np.array([x0 + cx, y0 + cy])
    
    # Prüfe Verschiebung: Nur akzeptieren, wenn weniger als 1/4 Ballbreite
    shift = np.linalg.norm(refined_point - point)
    if shift > max_shift:
        return point
    
    return refined_point


@app.command()
def capture(
    yaml_path: Path = typer.Argument(..., help="Pfad zur Szenen-YAML-Datei"),
    image_path: Optional[Path] = typer.Argument(None, help="Pfad zum Tischbild (PNG, optional - wird aus YAML-Seitenzahl abgeleitet)"),
    manual_calibration: bool = typer.Option(False, "--manual-calibration", "-m", help="Manuelle Kalibrierung durchführen (Standard: automatische Kalibrierung)")
) -> None:
    """Aktualisiert Ball- und Trajektoriedaten einer Szene per interaktivem Anklicken."""

    scene_model = load_scene_yaml(yaml_path)
    
    # Bildpfad automatisch aus Seitenzahl ableiten, falls nicht angegeben
    if image_path is None:
        if scene_model.source.page is None:
            raise typer.BadParameter("Kein Bildpfad angegeben und keine Seitenzahl in YAML vorhanden")
        
        # Extrahiere Seitennummer (kann String wie "270 oben" sein)
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
        typer.echo(f"Bild automatisch aus Seitenzahl abgeleitet: {image_path} (Seite: {scene_model.source.page})")
    
    image = np.array(plt.imread(image_path))

    session = CaptureSession(image)
    try:
        # Bestimme Kalibrierungstyp basierend auf Scene-ID
        scene_id = scene_model.id
        is_quarter = scene_id.startswith("VS-width")
        
        if is_quarter:
            # Viertelbillard: dritter Punkt bei (0,20) statt (0,80)
            default_calib_points = DEFAULT_CALIBRATION_POINTS_QUARTER
            table_coords = np.array([[0.0, 0.0], [40.0, 0.0], [0.0, 20.0]])
            calib_prompt_3 = "Kalibrierung 3: zweiter Diamant (0,20)"
        else:
            # Vollbild: dritter Punkt bei (0,80)
            default_calib_points = DEFAULT_CALIBRATION_POINTS_FULL
            table_coords = np.array([[0.0, 0.0], [40.0, 0.0], [0.0, 80.0]])
            calib_prompt_3 = "Kalibrierung 3: kurze Bande (0,80)"
        
        # Standardmäßig automatische Kalibrierung verwenden, nur bei --manual-calibration manuell
        if manual_calibration:
            calibration_prompts = [
                "Kalibrierung 1: Ursprung (0,0)",
                "Kalibrierung 2: lange Bande (40,0)",
                calib_prompt_3,
            ]
            calib_points = [session.get_point(prompt) for prompt in calibration_prompts]
            calib_points = np.array(calib_points)
        else:
            typer.secho(
                "Verwende Standard-Kalibrierungspunkte:\n"
                f"  Ursprung (0,0): Pixel=({default_calib_points[0][0]:.1f}, {default_calib_points[0][1]:.1f})\n"
                f"  lange Bande (40,0): Pixel=({default_calib_points[1][0]:.1f}, {default_calib_points[1][1]:.1f})\n"
                f"  {calib_prompt_3.split(':')[1].strip()}: Pixel=({default_calib_points[2][0]:.1f}, {default_calib_points[2][1]:.1f})",
                fg=typer.colors.GREEN,
            )
            calib_points = default_calib_points
        
        matrix = _compute_matrix(calib_points, table_coords)

        ball_order = ["B1", "B2", "B3"]
        capture_targets = [(name, f"Ball {name}", True) for name in ball_order]
        capture_targets.append(("GHOST", "Ghost Ball", True))
        ball_points: Dict[str, np.ndarray] = {}
        for name, prompt, refine in capture_targets:
            point = session.get_point(prompt, refine_ball=refine, ball_name=name if refine else None)
            ball_points[name] = point
        ball_pixel_map = {name: ball_points[name] for name in ball_order if name in ball_points}

        # Tischgröße für Snap-Funktion
        table_size = (scene_model.table.size_units[0], scene_model.table.size_units[1])
        
        updates: dict[str, tuple[float, float]] = {}
        for name in ball_order + ["GHOST"]:
            point = ball_points[name]
            table_coords = _pixel_to_table(matrix, point)
            clamped_coords = _clamp_to_table(table_coords, table_size)
            
            # Ghost Ball wird nicht gesnappt - verwende Originalposition
            if name == "GHOST":
                final_coords = clamped_coords
            else:
                final_coords = _snap_to_grid(clamped_coords, table_size)
            
            updates[name] = (round(final_coords[0], 2), round(final_coords[1], 2))
            
            # Prüfe, ob begrenzt wurde
            if not np.allclose(table_coords, clamped_coords, atol=0.01):
                typer.secho(f"{name}: Koordinaten auf Tischbereich begrenzt ({table_coords[0]:.2f}, {table_coords[1]:.2f} → {clamped_coords[0]:.2f}, {clamped_coords[1]:.2f})", fg=typer.colors.YELLOW)
            # Prüfe, ob gesnappt wurde (nur für echte Bälle)
            elif name != "GHOST" and not np.allclose(clamped_coords, final_coords, atol=0.01):
                typer.secho(f"{name}: Tisch-Koordinaten {final_coords[0]:.2f}, {final_coords[1]:.2f} (gesnappt)", fg=typer.colors.MAGENTA)
            else:
                typer.secho(f"{name}: Tisch-Koordinaten {final_coords[0]:.2f}, {final_coords[1]:.2f}", fg=typer.colors.CYAN)

        scene_dict = scene_model.model_dump(mode="json")
        for name in ball_order:
            scene_dict['balls'][name]['position'] = list(updates[name])

        if 'ghost_ball' not in scene_dict or scene_dict['ghost_ball'] is None:
            scene_dict['ghost_ball'] = GhostBallModel(position=list(updates['GHOST'])).model_dump(mode='json')
        else:
            scene_dict['ghost_ball']['position'] = list(updates['GHOST'])

        trajectory: Optional[Dict[str, List[Dict[str, Any]]]] = scene_dict.get("trajectory")
        if trajectory:
            typer.echo("\n-- Trajektorien erfassen --")
            for ball_name, segments in trajectory.items():
                typer.echo(f"\nBall {ball_name}:")
                start_point_px = ball_pixel_map.get(ball_name)
                session.reset_trace(ball_name, start_point=start_point_px.tolist() if start_point_px is not None else None)
                original_segments = [dict(seg) for seg in segments]
                if segments:
                    typer.echo("  Vorhandene Trajektorie wird überschrieben. Enter ohne Klick behält die alte Fassung.")
                new_segments, aborted = _capture_new_points(session, matrix, ball_name, table_size=table_size)
                if new_segments:
                    trajectory[ball_name] = new_segments
                    typer.secho("    → Trajektorie aktualisiert.", fg=typer.colors.CYAN)
                else:
                    if segments:
                        if aborted:
                            typer.secho("    → Eingabe abgebrochen, ursprüngliche Trajektorie bleibt.", fg=typer.colors.YELLOW)
                            trajectory[ball_name] = original_segments
                        else:
                            typer.echo("    → unverändert.")
                    else:
                        if aborted:
                            typer.echo("    → keine Trajektorie gesetzt (abgebrochen).")
                        else:
                            typer.echo("    → keine Punkte erfasst.")
    finally:
        session.close()

    scene_model = SceneModel.model_validate(scene_dict)

    with yaml_path.open("w") as fh:
        yaml.safe_dump(
            {"scene": scene_model.model_dump(mode="json")},
            fh,
            allow_unicode=True,
            sort_keys=False,
        )
    typer.secho(f"YAML aktualisiert: {yaml_path}", fg=typer.colors.GREEN)

    with session_scope() as session:
        import_scenes(session, [yaml_path])
        typer.secho("Szenendatenbank aktualisiert.", fg=typer.colors.GREEN)

    typer.secho("Capture fertig.", fg=typer.colors.BRIGHT_WHITE)


def ingest_yaml(paths: List[Path]) -> None:
    with session_scope() as session:
        import_scenes(session, paths)
        typer.secho(f"{len(paths)} Szenen importiert.", fg=typer.colors.GREEN)


@app.command("ingest")
def ingest_command(
    yaml_paths: List[Path] = typer.Argument(..., help="Eine oder mehrere Szenen-YAML-Dateien")
) -> None:
    ingest_yaml(yaml_paths)


if __name__ == "__main__":
    app()
