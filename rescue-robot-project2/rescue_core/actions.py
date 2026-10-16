from __future__ import annotations

ACTIONS = {
    "North": (-1, 0),
    "South": (1, 0),
    "East": (0, 1),
    "West": (0, -1),
    "Stop": (0, 0),
}

ACTION_ORDER = ("North", "South", "East", "West", "Stop")
SHORT_ACTION = {
    "North": "N",
    "South": "S",
    "East": "E",
    "West": "W",
    "Stop": ".",
}
