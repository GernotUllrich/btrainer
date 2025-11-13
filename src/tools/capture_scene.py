from __future__ import annotations

from pathlib import Path
from typing import List

import numpy as np
import typer
import yaml

from src.db.session import session_scope
from src.db.schemas import SceneModel, GhostBallModel
from src.services.ingest import import_scenes, load_scene_yaml

app = typer.Typer(help="Interactive tools for capturing and importing billiards scenes")


try:
    import cv2
    HAS_CV2 = True
except ImportError:  # pragma: no cover
    HAS_CV2 = False

import matplotlib.pyplot as plt  # noqa: E402


def _collect_points(image: np.ndarray, prompts: List[str]) -> np.ndarray:
    fig, ax = plt.subplots(figsize=(6, 9))
    ax.imshow(image)
    ax.set_title(prompts[0])
    plt.show(block=False)
    typer.echo("-- Toolbar nutzen (Zoom/Pan). Mit Enter bestätigen, wenn bereit --")
    input()
    points: list[tuple[float, float]] = []
    for prompt in prompts:
        ax.set_title(prompt)
        plt.draw()
        click = plt.ginput(1, timeout=0)
        if not click:
            raise typer.BadParameter("Keine Eingabe erhalten, bitte erneut starten")
        x, y = float(click[0][0]), float(click[0][1])
        points.append((x, y))
        typer.secho(f"{prompt}: Pixel=({x:.1f}, {y:.1f})", fg=typer.colors.GREEN)
    plt.close(fig)
    return np.array(points, dtype=float)


def _compute_matrix(calib: np.ndarray) -> np.ndarray:
    pixel = np.column_stack((calib, np.ones(3)))
    table = np.array([[0.0, 0.0], [40.0, 0.0], [0.0, 80.0]])
    mx, *_ = np.linalg.lstsq(pixel, table[:, 0], rcond=None)
    my, *_ = np.linalg.lstsq(pixel, table[:, 1], rcond=None)
    return np.vstack([mx, my])


def _pixel_to_table(matrix: np.ndarray, point: np.ndarray) -> tuple[float, float]:
    vec = np.array([point[0], point[1], 1.0])
    tx = matrix @ vec
    return float(tx[0]), float(tx[1])


def _refine(image: np.ndarray, point: np.ndarray, radius: int = 35) -> np.ndarray:
    x, y = map(int, point)
    h, w = image.shape[:2]
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
            return np.array([x0 + cx, y0 + cy])
    thresh = gray.mean()
    mask = gray < thresh
    coords = np.column_stack(np.nonzero(mask))
    if coords.size == 0:
        return point
    cy, cx = coords.mean(axis=0)
    return np.array([x0 + cx, y0 + cy])


@app.command()
def capture(
    yaml_path: Path = typer.Argument(..., help="Pfad zur Szenen-YAML-Datei"),
    image_path: Path = typer.Argument(..., help="Pfad zum Tischbild (PNG)")
) -> None:
    """Aktualisiert Ballpositionen einer Szene per interaktivem Anklicken."""

    scene_model = load_scene_yaml(yaml_path)
    image = np.array(plt.imread(image_path))

    prompts = [
        "Kalibrierung 1: Ursprung (0,0)",
        "Kalibrierung 2: lange Bande (40,0)",
        "Kalibrierung 3: kurze Bande (0,80)",
    ]
    ball_order = ["B1", "B2", "B3"]
    prompts += [f"Ball {name}" for name in ball_order]
    prompts.append("Ghost Ball")

    points = _collect_points(image, prompts)
    matrix = _compute_matrix(points[:3])
    ball_pixels = points[3:]

    updates: dict[str, tuple[float, float]] = {}
    for name, raw_point in zip(ball_order + ["GHOST"], ball_pixels, strict=False):
        refined = _refine(image, raw_point)
        coords = _pixel_to_table(matrix, refined)
        updates[name] = (round(coords[0], 2), round(coords[1], 2))
        typer.secho(f"{name}: Tisch-Koordinaten {coords[0]:.2f}, {coords[1]:.2f}", fg=typer.colors.CYAN)

    scene_dict = scene_model.model_dump(mode="json")
    for name in ball_order:
        scene_dict['balls'][name]['position'] = list(updates[name])

    if 'ghost_ball' not in scene_dict or scene_dict['ghost_ball'] is None:
        scene_dict['ghost_ball'] = GhostBallModel(position=list(updates['GHOST'])).model_dump(mode='json')
    else:
        scene_dict['ghost_ball']['position'] = list(updates['GHOST'])

    scene_model = SceneModel.model_validate(scene_dict)

    with yaml_path.open("w") as fh:
        yaml.safe_dump({"scene": scene_model.model_dump(mode="json")}, fh, allow_unicode=True, sort_keys=False)
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
