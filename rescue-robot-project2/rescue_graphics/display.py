from __future__ import annotations
import math
import os
import random
import time
import warnings

from rescue_core.actions import SHORT_ACTION
from rescue_core.game import RescueGameState
from rescue_core.runner import advance_hazards
from rescue_core.layout import RescueLayout


TILE = 48
PADDING = 24
HUD = 170
MIN_WIDTH = 900
_ACTIVE_LAYOUT: RescueLayout | None = None

COLORS = {
    "bg": (17, 24, 32),
    "panel": (24, 34, 45),
    "grid": (53, 67, 83),
    "wall": (43, 48, 55),
    "wall_edge": (31, 37, 45),
    "clear": (224, 232, 238),
    "clear_alt": (216, 226, 233),
    "base": (78, 172, 120),
    "base_light": (177, 247, 207),
    "rubble": (168, 160, 137),
    "rubble_dark": (78, 73, 63),
    "rubble_light": (211, 202, 174),
    "sand": (226, 185, 102),
    "sand_dark": (58, 41, 26),
    "sand_light": (255, 218, 147),
    "sand_mid": (241, 199, 111),
    "sand_shadow": (117, 80, 39),
    "water": (78, 147, 194),
    "water_light": (155, 210, 236),
    "smoke": (131, 141, 151),
    "charge": (77, 180, 126),
    "charge_light": (177, 247, 207),
    "robot_yellow": (247, 190, 56),
    "robot_yellow_dark": (195, 134, 32),
    "robot_body": (244, 202, 97),
    "robot_panel": (210, 143, 48),
    "robot_tread": (44, 48, 53),
    "robot_tread_light": (91, 96, 103),
    "robot_eye": (245, 249, 255),
    "robot_pupil": (28, 38, 50),
    "robot_glint": (255, 255, 255),
    "fire": (220, 87, 56),
    "fire_light": (255, 190, 70),
    "collapse": (199, 72, 91),
    "survivor": (255, 211, 106),
    "survivor_done": (92, 174, 113),
    "survivor_clothes": (89, 149, 223),
    "route": (61, 169, 255),
    "route_dark": (26, 112, 187),
    "text": (240, 243, 247),
    "muted": (179, 188, 198),
    "battery_bg": (61, 70, 82),
    "battery": (91, 214, 120),
    "battery_mid": (245, 194, 66),
    "battery_low": (238, 92, 92),
}


def _require_pygame():
    os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
    warnings.filterwarnings(
        "ignore",
        message="pkg_resources is deprecated as an API.*",
        category=UserWarning,
        module="pygame.pkgdata",
    )
    try:
        import pygame
    except Exception as exc:
        raise RuntimeError("pygame is required for graphics. Install it with: python3.13 -m pip install pygame") from exc
    return pygame


def _window_size(layout: RescueLayout):
    grid_width = PADDING * 2 + layout.width * TILE
    return max(MIN_WIDTH, grid_width), PADDING * 2 + layout.height * TILE + HUD


def _grid_left(layout: RescueLayout | None = None):
    layout = layout or _ACTIVE_LAYOUT
    if layout is None:
        return PADDING
    width, _ = _window_size(layout)
    return max(PADDING, (width - layout.width * TILE) // 2)


def _rect(loc):
    return (_grid_left() + loc.col * TILE, PADDING + loc.row * TILE, TILE, TILE)


def _center(loc):
    x, y, w, h = _rect(loc)
    return x + w // 2, y + h // 2


def _tile_color(ch, row=0, col=0):
    if ch == "#":
        return COLORS["wall"]
    if ch == "B":
        return COLORS["base_light"]
    if ch == "r":
        return COLORS["rubble"]
    if ch == "m":
        return COLORS["sand"]
    if ch == "w":
        return COLORS["water"]
    if ch == "g":
        return COLORS["smoke"]
    if ch == "c":
        return COLORS["charge"]
    return COLORS["clear"] if (row + col) % 2 == 0 else COLORS["clear_alt"]


def _draw_tile_details(pygame, surface, ch, rect):
    x, y, w, h = rect
    if ch == "#":
        pygame.draw.rect(surface, COLORS["wall_edge"], rect, 2, border_radius=4)
        pygame.draw.line(surface, (58, 66, 76), (x + 8, y + 12), (x + w - 10, y + 12), 2)
        pygame.draw.line(surface, (32, 37, 44), (x + 10, y + h - 10), (x + w - 8, y + h - 10), 2)
    elif ch == "B":
        pygame.draw.circle(surface, (230, 255, 236), (x + w // 2, y + h // 2), 18)
        pygame.draw.circle(surface, COLORS["base"], (x + w // 2, y + h // 2), 17, 3)
        pygame.draw.line(surface, COLORS["base"], (x + 17, y + 24), (x + 31, y + 24), 5)
        pygame.draw.line(surface, COLORS["base"], (x + 24, y + 17), (x + 24, y + 31), 5)
    elif ch == "r":
        pygame.draw.ellipse(surface, COLORS["rubble_dark"], (x + 6, y + 36, 37, 7))
        stones = [
            ([(x + 8, y + 35), (x + 13, y + 22), (x + 22, y + 20), (x + 27, y + 36), (x + 16, y + 41)], COLORS["rubble_light"]),
            ([(x + 23, y + 36), (x + 31, y + 23), (x + 42, y + 26), (x + 39, y + 41), (x + 27, y + 41)], COLORS["rubble"]),
            ([(x + 16, y + 24), (x + 24, y + 10), (x + 35, y + 16), (x + 31, y + 30), (x + 20, y + 31)], COLORS["rubble_light"]),
            ([(x + 27, y + 23), (x + 37, y + 13), (x + 44, y + 22), (x + 38, y + 32), (x + 29, y + 30)], COLORS["rubble"]),
            ([(x + 11, y + 40), (x + 22, y + 34), (x + 31, y + 40), (x + 24, y + 45), (x + 12, y + 45)], (141, 132, 109)),
        ]
        for points, color in stones:
            shadow = [(px + 2, py + 2) for px, py in points]
            pygame.draw.polygon(surface, COLORS["rubble_dark"], shadow)
            pygame.draw.polygon(surface, color, points)
            pygame.draw.polygon(surface, COLORS["rubble_dark"], points, 2)
        crack_color = (104, 96, 82)
        pygame.draw.line(surface, crack_color, (x + 17, y + 25), (x + 22, y + 32), 2)
        pygame.draw.line(surface, crack_color, (x + 25, y + 14), (x + 31, y + 21), 2)
        pygame.draw.line(surface, crack_color, (x + 31, y + 27), (x + 38, y + 29), 2)
        pygame.draw.line(surface, crack_color, (x + 17, y + 39), (x + 23, y + 36), 2)
    elif ch == "m":
        # Sand dunes: the same yellow terrain icon used in Project 1.
        pygame.draw.ellipse(surface, COLORS["sand_shadow"], (x + 5, y + 39, 38, 6))
        rear_dune = [
            (x + 9, y + 31), (x + 15, y + 22), (x + 20, y + 21),
            (x + 25, y + 27), (x + 30, y + 25), (x + 36, y + 15),
            (x + 43, y + 18), (x + 46, y + 31), (x + 46, y + 42),
            (x + 9, y + 42),
        ]
        front_dune = [
            (x + 2, y + 39), (x + 10, y + 31), (x + 18, y + 29),
            (x + 27, y + 35), (x + 35, y + 28), (x + 46, y + 37),
            (x + 46, y + 44), (x + 2, y + 44),
        ]
        pygame.draw.polygon(surface, COLORS["sand_mid"], rear_dune)
        pygame.draw.lines(surface, COLORS["sand_dark"], False, rear_dune[:8], 3)
        pygame.draw.polygon(surface, COLORS["sand_light"], [(x + 16, y + 39), (x + 25, y + 28), (x + 35, y + 39)])
        pygame.draw.polygon(surface, COLORS["sand_mid"], front_dune)
        pygame.draw.lines(surface, COLORS["sand_dark"], False, front_dune[:6], 3)
        pygame.draw.line(surface, COLORS["sand_dark"], (x + 11, y + 38), (x + 22, y + 34), 2)
        pygame.draw.line(surface, COLORS["sand_dark"], (x + 29, y + 37), (x + 40, y + 35), 2)
        for px, py, radius in [(9, 38, 2), (18, 34, 2), (28, 31, 2), (39, 37, 2)]:
            pygame.draw.circle(surface, COLORS["sand_dark"], (x + px, y + py), radius)
    elif ch == "w":
        for i in range(3):
            yy = y + 16 + i * 8
            pygame.draw.arc(surface, COLORS["water_light"], (x + 8, yy, 16, 8), 0, math.pi, 2)
            pygame.draw.arc(surface, COLORS["water_light"], (x + 23, yy, 16, 8), 0, math.pi, 2)
    elif ch == "g":
        for i in range(3):
            yy = y + 14 + i * 8
            pygame.draw.arc(surface, (214, 221, 226), (x + 8 + i * 4, yy, 26, 10), 0, math.pi, 2)
    elif ch == "c":
        pygame.draw.circle(surface, COLORS["charge_light"], (x + w//2, y + h//2), 14)
        pygame.draw.circle(surface, COLORS["charge"], (x + w//2, y + h//2), 16, 3)
        bolt = [(x+24, y+11), (x+17, y+25), (x+24, y+24), (x+20, y+37), (x+32, y+20), (x+25, y+21)]
        pygame.draw.polygon(surface, (255, 245, 135), bolt)


def _draw_tile(pygame, surface, layout, loc):
    rect = pygame.Rect(_rect(loc))
    ch = layout.tile_at(loc)
    pygame.draw.rect(surface, _tile_color(ch, loc.row, loc.col), rect, border_radius=4)
    _draw_tile_details(pygame, surface, ch, rect)
    pygame.draw.rect(surface, COLORS["grid"], rect, 1, border_radius=4)


def _draw_route_marker(pygame, surface, loc, prev_loc=None, next_loc=None):
    x, y, w, h = _rect(loc)
    cx, cy = x + w // 2, y + h // 2
    if prev_loc and next_loc:
        dr = next_loc.row - prev_loc.row
        dc = next_loc.col - prev_loc.col
    elif next_loc:
        dr = next_loc.row - loc.row
        dc = next_loc.col - loc.col
    elif prev_loc:
        dr = loc.row - prev_loc.row
        dc = loc.col - prev_loc.col
    else:
        dr, dc = 0, 1
    if dr == 0 and dc == 0:
        if next_loc:
            dr = next_loc.row - loc.row
            dc = next_loc.col - loc.col
        elif prev_loc:
            dr = loc.row - prev_loc.row
            dc = loc.col - prev_loc.col
    if dr == 0 and dc == 0:
        return
    if abs(dc) >= abs(dr):
        if dc >= 0:
            pts = [(cx + 9, cy), (cx - 5, cy - 7), (cx - 5, cy + 7)]
        else:
            pts = [(cx - 9, cy), (cx + 5, cy - 7), (cx + 5, cy + 7)]
    else:
        if dr >= 0:
            pts = [(cx, cy + 9), (cx - 7, cy - 5), (cx + 7, cy - 5)]
        else:
            pts = [(cx, cy - 9), (cx - 7, cy + 5), (cx + 7, cy + 5)]
    pygame.draw.circle(surface, (218, 239, 255), (cx, cy), 10)
    pygame.draw.polygon(surface, COLORS["route"], pts)
    pygame.draw.circle(surface, COLORS["route_dark"], (cx, cy), 10, 1)


def _draw_survivor(pygame, surface, loc, rescued=False):
    x, y, w, h = _rect(loc)
    cx, cy = x + w // 2, y + h // 2
    if rescued:
        pygame.draw.circle(surface, (230, 255, 236), (cx, cy), 18)
        pygame.draw.circle(surface, COLORS["survivor_done"], (cx, cy), 17, 3)
        pygame.draw.line(surface, COLORS["survivor_done"], (cx - 8, cy), (cx - 2, cy + 7), 4)
        pygame.draw.line(surface, COLORS["survivor_done"], (cx - 2, cy + 7), (cx + 10, cy - 8), 4)
        return
    pygame.draw.circle(surface, COLORS["survivor"], (cx, y + 16), 7)
    pygame.draw.rect(surface, COLORS["survivor_clothes"], (cx - 8, y + 23, 16, 15), border_radius=6)
    pygame.draw.line(surface, COLORS["survivor_clothes"], (cx - 8, y + 28), (cx - 15, y + 25), 3)
    pygame.draw.line(surface, COLORS["survivor_clothes"], (cx + 8, y + 28), (cx + 15, y + 25), 3)
    cross = (238, 246, 245)
    pygame.draw.circle(surface, (225, 74, 84), (x + w - 12, y + 13), 7)
    pygame.draw.line(surface, cross, (x+w-12, y+9), (x+w-12, y+17), 2)
    pygame.draw.line(surface, cross, (x+w-16, y+13), (x+w-8, y+13), 2)


def _draw_robot(pygame, surface, loc):
    x, y, w, h = _rect(loc)
    cx = x + w // 2
    pygame.draw.rect(surface, COLORS["robot_tread"], (x + 5, y + 28, 10, 14), border_radius=5)
    pygame.draw.rect(surface, COLORS["robot_tread"], (x + w - 15, y + 28, 10, 14), border_radius=5)
    for off in (8, 13, 32, 37):
        pygame.draw.circle(surface, COLORS["robot_tread_light"], (x + off, y + 35), 2)
    body = pygame.Rect(x + 12, y + 23, w - 24, 18)
    pygame.draw.rect(surface, COLORS["robot_yellow_dark"], body.move(0, 2), border_radius=6)
    pygame.draw.rect(surface, COLORS["robot_body"], body, border_radius=6)
    pygame.draw.rect(surface, COLORS["robot_panel"], (x + 16, y + 27, 10, 8), border_radius=2)
    pygame.draw.rect(surface, (126, 198, 102), (x + 28, y + 28, 5, 3), border_radius=1)
    pygame.draw.rect(surface, (236, 88, 72), (x + 35, y + 28, 5, 3), border_radius=1)
    pygame.draw.rect(surface, COLORS["robot_yellow_dark"], (cx - 3, y + 18, 6, 7), border_radius=2)
    pygame.draw.line(surface, COLORS["robot_tread"], (cx - 7, y + 15), (cx - 15, y + 10), 2)
    pygame.draw.line(surface, COLORS["robot_tread"], (cx + 7, y + 15), (cx + 15, y + 10), 2)
    for ex, ey in ((cx - 9, y + 14), (cx + 9, y + 14)):
        pygame.draw.circle(surface, (121, 126, 130), (ex, ey), 9)
        pygame.draw.circle(surface, COLORS["robot_eye"], (ex, ey), 7)
        pygame.draw.circle(surface, COLORS["robot_pupil"], (ex + 1, ey + 1), 3)
        pygame.draw.circle(surface, COLORS["robot_glint"], (ex - 2, ey - 2), 2)
    pygame.draw.circle(surface, (255, 223, 82), (x + w - 12, y + 18), 3)
    pygame.draw.line(surface, (255, 223, 82), (x + w - 12, y + 12), (x + w - 12, y + 8), 1)


def _draw_hazard(pygame, surface, loc, kind):
    x, y, w, h = _rect(loc)
    cx, cy = x + w // 2, y + h // 2
    if kind == "F":
        pygame.draw.circle(surface, (255, 237, 204), (cx, cy), 20)
        pygame.draw.polygon(surface, COLORS["fire_light"], [(cx, cy - 16), (cx - 12, cy + 14), (cx + 13, cy + 14)])
        pygame.draw.polygon(surface, COLORS["fire"], [(cx + 5, cy - 9), (cx - 8, cy + 13), (cx + 10, cy + 13)])
        pygame.draw.polygon(surface, (255, 236, 133), [(cx - 2, cy - 4), (cx - 5, cy + 11), (cx + 4, cy + 11)])
    else:
        pygame.draw.circle(surface, (255, 226, 233), (cx, cy), 21)
        slab = [(x + 7, y + 34), (x + 15, y + 22), (x + 28, y + 18), (x + 42, y + 28), (x + 39, y + 42), (x + 13, y + 42)]
        pygame.draw.polygon(surface, COLORS["rubble_dark"], [(px + 2, py + 2) for px, py in slab])
        pygame.draw.polygon(surface, COLORS["rubble_light"], slab)
        pygame.draw.polygon(surface, COLORS["rubble_dark"], slab, 2)
        pygame.draw.line(surface, COLORS["collapse"], (x + 25, y + 19), (x + 20, y + 29), 3)
        pygame.draw.line(surface, COLORS["collapse"], (x + 20, y + 29), (x + 29, y + 34), 3)
        pygame.draw.line(surface, COLORS["collapse"], (x + 29, y + 34), (x + 25, y + 42), 3)
        pygame.draw.polygon(surface, COLORS["collapse"], [(cx + 12, cy - 18), (cx + 1, cy + 2), (cx + 23, cy + 2)])
        pygame.draw.line(surface, (255, 244, 190), (cx + 12, cy - 11), (cx + 12, cy - 3), 2)
        pygame.draw.circle(surface, (255, 244, 190), (cx + 12, cy), 2)


def _draw_battery_bar(pygame, surface, state, x, y, width=165, height=16):
    pygame.draw.rect(surface, COLORS["battery_bg"], (x, y, width, height), border_radius=6)
    ratio = max(0, min(1, state.battery / max(1, state.layout.initial_battery)))
    fill = int(width * ratio)
    color = COLORS["battery_low"] if ratio < 0.25 else COLORS["battery_mid"] if ratio < 0.55 else COLORS["battery"]
    pygame.draw.rect(surface, color, (x, y, fill, height), border_radius=6)
    pygame.draw.rect(surface, COLORS["muted"], (x, y, width, height), 1, border_radius=6)
    pygame.draw.rect(surface, COLORS["muted"], (x + width + 2, y + 4, 5, height - 8), border_radius=2)


def _draw_legend_chip(pygame, surface, font, x, y, label, color, kind="square"):
    icon_y = y + 2
    if kind == "circle":
        pygame.draw.circle(surface, color, (x + 7, icon_y + 7), 7)
    elif kind == "arrow":
        pygame.draw.line(surface, color, (x, icon_y + 7), (x + 15, icon_y + 7), 3)
        pygame.draw.polygon(surface, color, [(x + 16, icon_y + 7), (x + 9, icon_y + 2), (x + 9, icon_y + 12)])
    elif kind == "charge":
        pygame.draw.rect(surface, color, (x, icon_y, 15, 15), border_radius=3)
        pygame.draw.polygon(surface, (255, 245, 135), [(x + 8, icon_y + 2), (x + 4, icon_y + 8), (x + 8, icon_y + 8), (x + 6, icon_y + 13), (x + 12, icon_y + 6), (x + 8, icon_y + 6)])
    elif kind == "triangle":
        pygame.draw.polygon(surface, color, [(x + 8, icon_y), (x, icon_y + 15), (x + 16, icon_y + 15)])
    elif kind == "collapse":
        pygame.draw.polygon(surface, COLORS["rubble_light"], [(x, icon_y + 13), (x + 5, icon_y + 4), (x + 14, icon_y + 6), (x + 16, icon_y + 14)])
        pygame.draw.line(surface, color, (x + 7, icon_y + 4), (x + 5, icon_y + 12), 2)
        pygame.draw.polygon(surface, color, [(x + 13, icon_y), (x + 7, icon_y + 10), (x + 19, icon_y + 10)])
    else:
        pygame.draw.rect(surface, color, (x, icon_y, 15, 15), border_radius=3)
        pygame.draw.rect(surface, COLORS["grid"], (x, icon_y, 15, 15), 1, border_radius=3)
    text = font.render(label, True, COLORS["muted"])
    surface.blit(text, (x + 20, y))
    return x + 26 + text.get_width()


def _draw_color_legend(pygame, surface, font, x, y):
    title = font.render("Key:", True, COLORS["text"])
    surface.blit(title, (x, y))
    row_x = x + title.get_width() + 12
    row_x = _draw_legend_chip(pygame, surface, font, row_x, y, "bot", COLORS["robot_yellow"], "circle")
    row_x = _draw_legend_chip(pygame, surface, font, row_x, y, "route", COLORS["route"], "arrow")
    row_x = _draw_legend_chip(pygame, surface, font, row_x, y, "survivor", COLORS["survivor"], "circle")
    row_x = _draw_legend_chip(pygame, surface, font, row_x, y, "fire", COLORS["fire"], "triangle")
    _draw_legend_chip(pygame, surface, font, row_x, y, "collapse", COLORS["collapse"], "collapse")

    row_x = x
    row_y = y + 22
    row_x = _draw_legend_chip(pygame, surface, font, row_x, row_y, "sand 2", COLORS["sand"])
    row_x = _draw_legend_chip(pygame, surface, font, row_x, row_y, "rubble 3", COLORS["rubble_light"])
    row_x = _draw_legend_chip(pygame, surface, font, row_x, row_y, "water 4", COLORS["water"])
    row_x = _draw_legend_chip(pygame, surface, font, row_x, row_y, "smoke 2", COLORS["smoke"])
    row_x = _draw_legend_chip(pygame, surface, font, row_x, row_y, "base", COLORS["base"])
    _draw_legend_chip(pygame, surface, font, row_x, row_y, "charge", COLORS["charge"], "charge")


def _draw_scene(pygame, screen, state: RescueGameState, path=(), message=""):
    global _ACTIVE_LAYOUT
    layout = state.layout
    _ACTIVE_LAYOUT = layout
    screen.fill(COLORS["bg"])
    for r, row in enumerate(layout.grid):
        for c, _ in enumerate(row):
            _draw_tile(pygame, screen, layout, type(state.robot)(r, c))
    route = list(path)
    for i, loc in enumerate(route):
        if loc != state.robot:
            prev_loc = route[i - 1] if i > 0 else None
            next_loc = route[i + 1] if i + 1 < len(route) else None
            _draw_route_marker(pygame, screen, loc, prev_loc, next_loc)
    for loc in layout.survivors:
        _draw_survivor(pygame, screen, loc, rescued=loc not in state.remaining_survivors)
    for loc, kind in zip(state.hazards, layout.hazard_kinds):
        _draw_hazard(pygame, screen, loc, kind)
    _draw_robot(pygame, screen, state.robot)

    width, _ = _window_size(layout)
    hud_y = PADDING + layout.height * TILE + 12
    panel_w = width - PADDING * 2
    pygame.draw.rect(screen, COLORS["panel"], (PADDING, hud_y - 6, panel_w, HUD - 18), border_radius=10)

    title_font = pygame.font.SysFont("arial", 17, bold=True)
    info_font = pygame.font.SysFont("arial", 14)
    legend_font = pygame.font.SysFont("arial", 12)
    left_x = PADDING + 14
    top_y = hud_y + 4
    status = "WIN" if state.is_win() else "LOSS" if state.is_loss() else "ACTIVE"
    line1 = (
        f"STATUS: {status}    SCORE: {state.score:.1f}    "
        f"BATTERY: {state.battery}/{layout.initial_battery}    "
        f"TURN: {state.turns}/{layout.max_turns}"
    )
    screen.blit(title_font.render(line1, True, COLORS["text"]), (left_x, top_y))
    line2 = f"MAP: {layout.name}    Survivors left: {len(state.remaining_survivors)}/{len(layout.survivors)}    Hazards: {len(state.hazards)}"
    screen.blit(info_font.render(line2, True, COLORS["text"]), (left_x, top_y + 28))
    _draw_battery_bar(pygame, screen, state, left_x, top_y + 56, width=210, height=18)
    _draw_color_legend(pygame, screen, legend_font, left_x + 240, top_y + 55)
    bottom_line = message or state.last_event
    if bottom_line:
        screen.blit(info_font.render(bottom_line, True, COLORS["text"]), (left_x, top_y + 124))
    pygame.display.flip()


def animate(frames: list[RescueGameState], delay: float = 0.12):
    pygame = _require_pygame()
    pygame.init()
    screen = pygame.display.set_mode(_window_size(frames[0].layout))
    pygame.display.set_caption("Rescue Robot Project 2")
    clock = pygame.time.Clock()
    delay_ms = max(0, int(delay * 1000))

    def should_quit():
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return True
            if event.type == pygame.KEYDOWN and event.key in (pygame.K_ESCAPE, pygame.K_q):
                return True
        return False

    path = []
    for state in frames:
        if should_quit():
            pygame.quit()
            return
        if not path or path[-1] != state.robot:
            path.append(state.robot)
        _draw_scene(pygame, screen, state, path=path)
        frame_start = pygame.time.get_ticks()
        while pygame.time.get_ticks() - frame_start < delay_ms:
            if should_quit():
                pygame.quit()
                return
            clock.tick(60)
    pygame.display.set_caption("Rescue Robot Project 2 - complete (press Q or Esc to close)")
    _draw_scene(pygame, screen, frames[-1], path=path, message="Animation complete. Press Q or Esc to close.")
    while True:
        if should_quit():
            pygame.quit()
            return
        clock.tick(30)


def manual_play(layout: RescueLayout, hazard_policy: str = "adversarial", seed: int = 7):
    pygame = _require_pygame()
    pygame.init()
    rng = random.Random(seed)
    screen = pygame.display.set_mode(_window_size(layout))
    pygame.display.set_caption("Manual RescueBot Control")
    hazard_model = "stationary" if hazard_policy == "stationary" else "adversarial"
    state = RescueGameState.initial_state(layout, hazard_model=hazard_model)
    path = [state.robot]
    keymap = {
        pygame.K_UP: "North", pygame.K_w: "North",
        pygame.K_DOWN: "South", pygame.K_s: "South",
        pygame.K_RIGHT: "East", pygame.K_d: "East",
        pygame.K_LEFT: "West", pygame.K_a: "West",
        pygame.K_SPACE: "Stop",
    }
    _draw_scene(pygame, screen, state, path=path, message="Use arrows/WASD. Hazards move after you do.")
    clock = pygame.time.Clock()
    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                return
            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_ESCAPE, pygame.K_q):
                    pygame.quit()
                    return
                if event.key == pygame.K_r:
                    state = RescueGameState.initial_state(layout, hazard_model=hazard_model)
                    path = [state.robot]
                elif event.key in keymap and not (state.is_win() or state.is_loss()):
                    action = keymap[event.key]
                    if action in state.get_legal_actions(0):
                        state = state.generate_successor(0, action)
                        if not path or path[-1] != state.robot:
                            path.append(state.robot)
                        state = advance_hazards(state, hazard_policy, rng)
                        if not path or path[-1] != state.robot:
                            path.append(state.robot)
        _draw_scene(pygame, screen, state, path=path)
        clock.tick(30)
