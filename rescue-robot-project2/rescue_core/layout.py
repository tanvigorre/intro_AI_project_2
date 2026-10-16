from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import re
import warnings

from .location import GridLocation


TERRAIN_COSTS = {
    ".": 1,
    "R": 1,
    "B": 1,
    "S": 1,
    "m": 2,
    "r": 3,
    "w": 4,
    "g": 2,
    "c": 1,
}

TERRAIN_NAMES = {
    ".": "clear floor",
    "R": "robot start",
    "B": "triage base",
    "S": "survivor marker",
    "m": "sand",
    "r": "rubble",
    "w": "standing water",
    "g": "smoke haze",
    "c": "charging pad",
    "#": "blocked wall",
}

HAZARD_NAMES = {
    "F": "wind-driven fire/smoke front",
    "C": "secondary-collapse wavefront",
}


@dataclass(frozen=True)
class RescueLayout:
    name: str
    grid: tuple[str, ...]
    start: GridLocation
    base: GridLocation
    survivors: tuple[GridLocation, ...]
    hazards: tuple[GridLocation, ...]
    hazard_kinds: tuple[str, ...]
    initial_battery: int = 40
    max_turns: int = 40
    description: str = ""
    wind: str = "E"

    @property
    def height(self) -> int:
        return len(self.grid)

    @property
    def width(self) -> int:
        return max((len(row) for row in self.grid), default=0)

    def in_bounds(self, loc: GridLocation) -> bool:
        return 0 <= loc.row < self.height and 0 <= loc.col < len(self.grid[loc.row])

    def tile_at(self, loc: GridLocation) -> str:
        if not self.in_bounds(loc):
            return "#"
        return self.grid[loc.row][loc.col]

    def is_wall(self, loc: GridLocation) -> bool:
        return self.tile_at(loc) == "#"

    def is_charger(self, loc: GridLocation) -> bool:
        return self.tile_at(loc) == "c"

    def movement_cost(self, loc: GridLocation) -> int:
        return TERRAIN_COSTS.get(self.tile_at(loc), 1)

    def hazard_can_enter(self, loc: GridLocation) -> bool:
        return self.in_bounds(loc) and not self.is_wall(loc) and loc != self.base


def load_layout(path: str | Path) -> RescueLayout:
    path = Path(path)
    raw_lines = path.read_text(encoding="utf-8").splitlines()
    metadata: dict[str, str] = {}
    grid_lines: list[str] = []

    metadata_pattern = re.compile(r"^\s*([A-Za-z_][A-Za-z0-9_]*):\s*(.*)$")

    for raw in raw_lines:
        line = raw.rstrip("\n")
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("//") or stripped.startswith("# "):
            continue
        match = metadata_pattern.match(line)
        if match and not grid_lines:
            key, value = match.groups()
            metadata[key.strip().lower()] = value.strip()
            continue
        if match and grid_lines:
            raise ValueError(f"Metadata line {line!r} appears after the map grid started in {path}.")
        grid_lines.append(line)

    if not grid_lines:
        raise ValueError(f"Layout file {path} does not contain a map grid.")

    known_keys = {"name", "battery", "max_turns", "description", "wind"}
    for key in sorted(set(metadata) - known_keys):
        warnings.warn(f"Ignoring unknown mission metadata key {key!r} in {path}.", RuntimeWarning)

    def read_int_metadata(key: str, default: str) -> int:
        raw_value = metadata.get(key, default)
        try:
            return int(raw_value)
        except ValueError as exc:
            raise ValueError(f"Mission metadata {key!r} in {path} must be an integer; got {raw_value!r}.") from exc

    wind = metadata.get("wind", "E").upper()
    if wind not in {"N", "S", "E", "W"}:
        warnings.warn(f"Invalid wind value {wind!r} in {path}; using 'E'.", RuntimeWarning)
        wind = "E"

    start: GridLocation | None = None
    base: GridLocation | None = None
    survivors: list[GridLocation] = []
    hazards: list[GridLocation] = []
    hazard_kinds: list[str] = []
    normalized: list[str] = []

    for r, line in enumerate(grid_lines):
        row_chars: list[str] = []
        for c, ch in enumerate(line):
            loc = GridLocation(r, c)
            if ch == "R":
                if start is not None:
                    raise ValueError("A rescue layout may contain only one R start tile.")
                start = loc
                row_chars.append(".")
            elif ch == "B":
                if base is not None:
                    raise ValueError("A rescue layout may contain only one B base tile.")
                base = loc
                row_chars.append("B")
            elif ch == "S":
                survivors.append(loc)
                row_chars.append(".")
            elif ch in HAZARD_NAMES:
                hazards.append(loc)
                hazard_kinds.append(ch)
                row_chars.append(".")
            else:
                row_chars.append(ch)
        normalized.append("".join(row_chars))

    if start is None:
        raise ValueError("A rescue layout must include an R start tile.")
    if base is None:
        base = start

    return RescueLayout(
        name=metadata.get("name", path.stem.replace("_", " ").title()),
        grid=tuple(normalized),
        start=start,
        base=base,
        survivors=tuple(survivors),
        hazards=tuple(hazards),
        hazard_kinds=tuple(hazard_kinds),
        initial_battery=read_int_metadata("battery", "40"),
        max_turns=read_int_metadata("max_turns", "40"),
        description=metadata.get("description", ""),
        wind=wind,
    )
