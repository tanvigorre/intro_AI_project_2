from __future__ import annotations
from pathlib import Path

from .layout import load_layout


def resolve_map_path(name: str | Path) -> Path:
    path = Path(name)
    if path.exists():
        return path
    if path.suffix == "":
        path = path.with_suffix(".mission")
    candidate = Path(__file__).resolve().parent.parent / "maps" / path.name
    if candidate.exists():
        return candidate
    raise FileNotFoundError(f"Could not find rescue layout {name!r}.")


def available_maps() -> list[str]:
    maps_dir = Path(__file__).resolve().parent.parent / "maps"
    if not maps_dir.exists():
        return []
    return sorted(path.stem for path in maps_dir.glob("*.mission"))
