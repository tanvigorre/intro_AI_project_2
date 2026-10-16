from __future__ import annotations
from dataclasses import dataclass


@dataclass(frozen=True, order=True)
class GridLocation:
    row: int
    col: int

    def moved(self, dr: int, dc: int) -> "GridLocation":
        return GridLocation(self.row + dr, self.col + dc)

    def manhattan_distance(self, other: "GridLocation") -> int:
        return abs(self.row - other.row) + abs(self.col - other.col)
