#!/usr/bin/env python3
# cypac.py
"""
SERIF ARCADE - CYPAC (Standalone Module)
Split from arcade1.py. Now boots into a slider-based config menu
before launch: SPEED / MAZE DENSITY / DIFFICULTY drive min-max formulas
that feed the existing randomizer-based maze and ghost logic.
"""

import sys
import math
import random
import pygame
import numpy as np

# ---------------------------------------------------------------------------
# Graphics Config
# ---------------------------------------------------------------------------
INTERNAL_W, INTERNAL_H = 320, 240
SCALE = 3
WINDOW_W, WINDOW_H = INTERNAL_W * SCALE, INTERNAL_H * SCALE
FPS = 60

THEME = {
    "bg": (4, 10, 6),
    "hot": (0, 255, 128),
    "dim": (0, 110, 55),
    "panel": (0, 22, 11),
    "warn": (255, 90, 90),
}

# ---------------------------------------------------------------------------
# VRMan Primitive Drawing System
# ---------------------------------------------------------------------------
def draw_vrman(surf, cx, cy, radius=10, color=None, facing=1, rotation=0.0):
    color = color or THEME["hot"]
    cx, cy = int(cx), int(cy)

    pygame.draw.circle(surf, color, (cx, cy), radius)
    pygame.draw.circle(surf, THEME["bg"], (cx, cy), radius, 1)

    rad = math.radians(rotation)
    cos_r = math.cos(rad)
    sin_r = math.sin(rad)

    if rotation != 0.0:
        v_dx = cos_r * (radius - 2)
        v_dy = sin_r * (radius - 2)
        pygame.draw.line(surf, (8, 8, 14), (cx - v_dx, cy - v_dy), (cx + v_dx, cy + v_dy), max(3, radius // 2))
    else:
        band_h = max(2, radius // 2)
        band_rect = pygame.Rect(cx - radius, cy - radius // 2, radius * 2, band_h)
        pygame.draw.rect(surf, (8, 8, 14), band_rect)

    if rotation != 0.0:
        ax = cx + int((radius + 1) * cos_r)
        ay = cy + int((radius + 1) * sin_r)
        bx = cx + int((radius + 7) * cos_r)
        by = cy + int((radius + 7) * sin_r)
        pygame.draw.line(surf, color, (ax, ay), (bx, by), 2)
    else:
        ax = cx + int(radius * facing)
        ay = cy
        pygame.draw.line(surf, color, (ax, ay), (ax + 6 * facing, ay - 6), 2)


# ---------------------------------------------------------------------------
# Base Class
# ---------------------------------------------------------------------------
class ArcadeGame:
    name = "UNSET"

    def __init__(self, app, config):
        self.app = app
        self.config = config
        self.score = 0
        self.game_over = False

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.app.go_to_menu()
        if self.game_over and event.type == pygame.KEYDOWN and event.key == pygame.K_r:
            self.reset()

    def reset(self):
        pass

    def update(self, dt):
        pass

    def draw(self, surf):
        pass


# ===========================================================================
# CONFIG MENU DEFINITIONS
# ===========================================================================
SLIDER_DEFS = [
    {"key": "speed",      "label": "SPEED",         "min": 0, "max": 10, "default": 5},
    {"key": "obstacles",  "label": "MAZE DENSITY",   "min": 0, "max": 10, "default": 5},
    {"key": "difficulty", "label": "DIFFICULTY",     "min": 0, "max": 10, "default": 5},
]


def resolve_config(vals):
    s = vals["speed"] / 10.0
    o = vals["obstacles"] / 10.0
    d = vals["difficulty"] / 10.0

    player_step = 0.22 - s * (0.22 - 0.09)             # faster player/ghosts as SPEED rises
    ghost_step = round(player_step * 1.36, 4)
    segs_lo = int(14 + o * 20)                          # denser maze wall segments
    segs_hi = int(segs_lo + 6 + o * 8)
    wander_chance = round(0.30 - d * 0.25, 3)           # ghosts chase more precisely at high DIFFICULTY
    frightened_time = round(8.0 - d * 5.0, 2)
    lives = max(1, 5 - round(d * 3))

    return {
        "player_step": round(player_step, 4),
        "ghost_step": ghost_step,
        "segs_lo": segs_lo,
        "segs_hi": segs_hi,
        "wander_chance": wander_chance,
        "frightened_time": frightened_time,
        "lives": lives,
    }


def preview_text(cfg):
    return (f"WALLS:{cfg['segs_lo']}-{cfg['segs_hi']}  CHASE:{1 - cfg['wander_chance']:.0%}"
            f"  FRIGHT:{cfg['frightened_time']:.1f}s  LIVES:{cfg['lives']}")


# ===========================================================================
# CYPAC
# ===========================================================================
class CyPac(ArcadeGame):
    name = "CYPAC"
    CELL = 10
    COLS = INTERNAL_W // CELL
    ROWS = INTERNAL_H // CELL
    TUNNEL_ROW = 12

    DIRS = {"up": (0, -1), "down": (0, 1), "left": (-1, 0), "right": (1, 0)}
    KEY_DIR = {
        pygame.K_UP: "up", pygame.K_w: "up",
        pygame.K_DOWN: "down", pygame.K_s: "down",
        pygame.K_LEFT: "left", pygame.K_a: "left",
        pygame.K_RIGHT: "right", pygame.K_d: "right",
    }
    GHOST_COLORS = [(255, 90, 90), (255, 170, 60), (140, 255, 255)]
    PLAYER_SPAWN = (16, 17)
    GHOST_SPAWNS = [(12, 10), (19, 10), (16, 7)]

    def __init__(self, app, config):
        super().__init__(app, config)
        self._protected_cells = self._compute_protected_cells()
        self._base_walls = self._build_base_walls()
        self.reset()

    def reset(self):
        self.score = 0
        self.game_over = False
        self.lives = self.config["lives"]
        self.stage = 1
        self.walls = self._generate_random_walls()
        self._start_stage(first=True)

    def _compute_protected_cells(self):
        protected = set()
        for (c, r) in [self.PLAYER_SPAWN] + self.GHOST_SPAWNS:
            for dc in (-1, 0, 1):
                for dr in (-1, 0, 1):
                    protected.add((c + dc, r + dr))
        return protected

    def _build_base_walls(self):
        walls = set()
        for c in range(self.COLS):
            for r in range(self.ROWS):
                if r == 0 or r == self.ROWS - 1: walls.add((c, r))
                elif c == 0 or c == self.COLS - 1:
                    if r != self.TUNNEL_ROW: walls.add((c, r))
        self._fill_block(walls, 14, 9, 4, 6)
        return walls

    def _fill_block(self, walls, c, r, w, h):
        for x in range(c, c + w):
            for y in range(r, r + h): walls.add((x, y))

    def _generate_random_walls(self):
        segs_lo, segs_hi = self.config["segs_lo"], self.config["segs_hi"]
        for attempt in range(40):
            walls = set(self._base_walls)
            num_segments = random.randint(segs_lo, segs_hi)
            for _ in range(num_segments):
                horizontal = random.random() < 0.5
                length = random.randint(2, 4)
                if horizontal:
                    r = random.randint(2, self.ROWS - 3)
                    c = random.randint(1, self.COLS - 1 - length)
                    cells = [(c + i, r) for i in range(length)]
                else:
                    c = random.randint(2, self.COLS - 3)
                    r = random.randint(1, self.ROWS - 1 - length)
                    cells = [(c, r + i) for i in range(length)]
                if any(cell in self._protected_cells for cell in cells): continue
                walls.update(cells)
            if self._maze_connected(walls): return walls
        return set(self._base_walls)

    def _maze_connected(self, walls):
        open_cells = {(c, r) for c in range(self.COLS) for r in range(self.ROWS) if (c, r) not in walls}
        if self.PLAYER_SPAWN not in open_cells: return False
        seen = {self.PLAYER_SPAWN}
        frontier = [self.PLAYER_SPAWN]
        while frontier:
            c, r = frontier.pop()
            neighbors = [(c + 1, r), (c - 1, r), (c, r + 1), (c, r - 1)]
            if r == self.TUNNEL_ROW:
                neighbors.append(((c + 1) % self.COLS, r))
                neighbors.append(((c - 1) % self.COLS, r))
            for nc, nr in neighbors:
                if 0 <= nc < self.COLS and 0 <= nr < self.ROWS and (nc, nr) in open_cells and (nc, nr) not in seen:
                    seen.add((nc, nr))
                    frontier.append((nc, nr))
        return len(seen) == len(open_cells)

    def _start_stage(self, first=False):
        if not first: self.walls = self._generate_random_walls()
        self.pellets = set()
        self.power_pellets = set()
        for c in range(1, self.COLS - 1):
            for r in range(1, self.ROWS - 1):
                if (c, r) in self.walls: continue
                self.pellets.add((c, r))

        corners = [(1, 1), (self.COLS - 2, 1), (1, self.ROWS - 2), (self.COLS - 2, self.ROWS - 2)]
        for cell in corners:
            if cell in self.walls: continue
            self.power_pellets.add(cell)
            self.pellets.discard(cell)

        pc, pr = self.PLAYER_SPAWN
        self.player = {"col": pc, "row": pr, "dir": "left", "queued": "left", "timer": 0.0}
        self.pellets.discard(self.PLAYER_SPAWN)

        self.ghosts = []
        for (gc, gr) in self.GHOST_SPAWNS:
            self.ghosts.append({
                "col": gc, "row": gr, "dir": "up", "spawn": (gc, gr),
                "timer": 0.0, "step": self.config["ghost_step"],
            })
            self.pellets.discard((gc, gr))

        self.player_step = self.config["player_step"]
        self.frightened_timer = 0.0
        self.ghost_eat_streak = 0

    def _passable(self, col, row):
        if row == self.TUNNEL_ROW and (col < 0 or col >= self.COLS): return True
        if col < 0 or col >= self.COLS or row < 0 or row >= self.ROWS: return False
        return (col, row) not in self.walls

    def _wrap(self, col, row):
        if row == self.TUNNEL_ROW: col = col % self.COLS
        return col, row

    def handle_event(self, event):
        super().handle_event(event)
        if event.type == pygame.KEYDOWN and event.key in self.KEY_DIR:
            self.player["queued"] = self.KEY_DIR[event.key]

    def update(self, dt):
        if self.game_over: return
        self.frightened_timer = max(0.0, self.frightened_timer - dt)
        self._update_player(dt)
        self._update_ghosts(dt)
        self._check_ghost_collisions()
        if not self.pellets and not self.power_pellets:
            self.stage += 1
            self._start_stage()

    def _update_player(self, dt):
        p = self.player
        p["timer"] -= dt
        if p["timer"] > 0: return
        p["timer"] = self.player_step

        dqx, dqy = self.DIRS[p["queued"]]
        if self._passable(p["col"] + dqx, p["row"] + dqy): p["dir"] = p["queued"]

        dx, dy = self.DIRS[p["dir"]]
        if self._passable(p["col"] + dx, p["row"] + dy):
            p["col"], p["row"] = self._wrap(p["col"] + dx, p["row"] + dy)

        cell = (p["col"], p["row"])
        if cell in self.pellets:
            self.pellets.discard(cell)
            self.score += 1
        elif cell in self.power_pellets:
            self.power_pellets.discard(cell)
            self.score += 5
            self.frightened_timer = self.config["frightened_time"]
            self.ghost_eat_streak = 0
            self.app.play_sfx("select")

    def _update_ghosts(self, dt):
        px, py = self.player["col"], self.player["row"]
        for g in self.ghosts:
            g["timer"] -= dt
            if g["timer"] > 0: continue
            g["timer"] = g["step"] * (1.3 if self.frightened_timer > 0 else 1.0)

            reverse = {"up": "down", "down": "up", "left": "right", "right": "left"}[g["dir"]]
            candidates = []
            for name, (dx, dy) in self.DIRS.items():
                if name == reverse: continue
                if self._passable(g["col"] + dx, g["row"] + dy): candidates.append(name)
            if not candidates:
                candidates = [reverse] if self._passable(g["col"] + self.DIRS[reverse][0], g["row"] + self.DIRS[reverse][1]) else []
            if not candidates: continue

            if self.frightened_timer > 0 or random.random() < self.config["wander_chance"]:
                choice = random.choice(candidates)
            else:
                def dist(name):
                    dx, dy = self.DIRS[name]
                    return (g["col"] + dx - px) ** 2 + (g["row"] + dy - py) ** 2
                choice = min(candidates, key=dist)

            g["dir"] = choice
            dx, dy = self.DIRS[choice]
            g["col"], g["row"] = self._wrap(g["col"] + dx, g["row"] + dy)

    def _check_ghost_collisions(self):
        for g in self.ghosts:
            if g["col"] == self.player["col"] and g["row"] == self.player["row"]:
                if self.frightened_timer > 0:
                    self.ghost_eat_streak += 1
                    self.score += 50 * self.ghost_eat_streak
                    g["col"], g["row"] = g["spawn"]
                    self.app.play_sfx("score")
                else:
                    self._lose_life()
                return

    def _lose_life(self):
        self.lives -= 1
        self.app.play_sfx("bounce")
        if self.lives <= 0:
            self.game_over = True
        else:
            self.player["col"], self.player["row"] = self.PLAYER_SPAWN
            self.player["dir"] = self.player["queued"] = "left"
            for g in self.ghosts: g["col"], g["row"] = g["spawn"]

    def draw(self, surf):
        surf.fill(THEME["bg"])
        for (c, r) in self.walls:
            pygame.draw.rect(surf, THEME["dim"], (c * self.CELL, r * self.CELL, self.CELL, self.CELL))
        for (c, r) in self.pellets:
            pygame.draw.circle(surf, THEME["hot"], (c * self.CELL + self.CELL // 2, r * self.CELL + self.CELL // 2), 1)

        pulse = 2 + int(1.5 * abs(math.sin(pygame.time.get_ticks() / 200.0)))
        for (c, r) in self.power_pellets:
            pygame.draw.circle(surf, THEME["hot"], (c * self.CELL + self.CELL // 2, r * self.CELL + self.CELL // 2), pulse)

        for g in self.ghosts:
            cx, cy = g["col"] * self.CELL + self.CELL // 2, g["row"] * self.CELL + self.CELL // 2
            color = self.GHOST_COLORS[self.ghosts.index(g) % len(self.GHOST_COLORS)]
            body_color = (60, 70, 200) if self.frightened_timer > 0 else color
            pygame.draw.circle(surf, body_color, (cx, cy - 1), self.CELL // 2)
            pygame.draw.rect(surf, body_color, (cx - self.CELL // 2, cy - 1, self.CELL, self.CELL // 2 + 2))
            eye_color = (255, 255, 255) if self.frightened_timer <= 0 else (200, 200, 255)
            pygame.draw.circle(surf, eye_color, (cx - 2, cy - 2), 2)
            pygame.draw.circle(surf, eye_color, (cx + 2, cy - 2), 2)

        px, py = self.player["col"] * self.CELL + self.CELL // 2, self.player["row"] * self.CELL + self.CELL // 2
        facing = 1 if self.player["dir"] in ("right", "up") else -1
        draw_vrman(surf, px, py, radius=self.CELL // 2, facing=facing)

        hud = self.app.font_small.render(f"SCORE:{self.score}  LIVES:{self.lives}  STAGE:{self.stage}", True, THEME["hot"])
        surf.blit(hud, (6, 2))

        if self.game_over:
            t = self.app.font_big.render("GAME OVER", True, THEME["warn"])
            surf.blit(t, (INTERNAL_W // 2 - t.get_width() // 2, INTERNAL_H // 2 - 10))
            hint = self.app.font_small.render("ESC: MENU   R: RESTART", True, THEME["dim"])
            surf.blit(hint, (INTERNAL_W // 2 - hint.get_width() // 2, INTERNAL_H // 2 + 18))


# ---------------------------------------------------------------------------
# Standalone Application Engine (Menu + Game)
# ---------------------------------------------------------------------------
class StandaloneCyPac:
    def __init__(self):
        pygame.init()
        pygame.mixer.init(frequency=22050, size=-16, channels=2)
        self.screen = pygame.display.set_mode((WINDOW_W, WINDOW_H))
        pygame.display.set_caption("SERIF ARCADE - CYPAC")
        self.clock = pygame.time.Clock()

        self.virtual_canvas = pygame.Surface((INTERNAL_W, INTERNAL_H))

        self.font_small = pygame.font.SysFont("Courier", 12, bold=True)
        self.font_big = pygame.font.SysFont("Courier", 20, bold=True)

        self.sliders = [dict(s, value=s["default"]) for s in SLIDER_DEFS]
        self.menu_index = 0
        self.state = "MENU"
        self.game = None
        self.running = True

    def play_sfx(self, sfx_type):
        """Mathematical sound oscillator generator."""
        sample_rate = 22050
        if sfx_type == "hit":
            duration, freq = 0.05, 440
        elif sfx_type == "bounce":
            duration, freq = 0.08, 220
        elif sfx_type == "score":
            duration, freq = 0.15, 880
        elif sfx_type == "select":
            duration, freq = 0.10, 580
        else:
            return

        n_samples = int(sample_rate * duration)
        buf = np.zeros((n_samples, 2), dtype=np.int16)
        for i in range(n_samples):
            t = i / sample_rate
            val = int(16384 * math.sin(2 * math.pi * freq * t) * (1.0 - t / duration))
            buf[i][0] = val
            buf[i][1] = val

        try:
            sound = pygame.sndarray.make_sound(buf)
            sound.play()
        except Exception:
            pass

    def go_to_menu(self):
        self.state = "MENU"
        self.game = None
        self.play_sfx("bounce")

    def start_game(self):
        vals = {s["key"]: s["value"] for s in self.sliders}
        config = resolve_config(vals)
        self.game = CyPac(self, config)
        self.state = "PLAYING"
        self.play_sfx("select")

    def draw_menu(self, surf):
        surf.fill(THEME["bg"])
        title = self.font_big.render("CYPAC", True, THEME["hot"])
        surf.blit(title, (INTERNAL_W // 2 - title.get_width() // 2, 16))
        sub = self.font_small.render("CONFIGURE RUN", True, THEME["dim"])
        surf.blit(sub, (INTERNAL_W // 2 - sub.get_width() // 2, 42))

        bar_len = 16
        y = 78
        for i, s in enumerate(self.sliders):
            selected = (i == self.menu_index)
            color = THEME["hot"] if selected else THEME["dim"]
            prefix = "> " if selected else "  "
            filled = int((s["value"] - s["min"]) / (s["max"] - s["min"]) * bar_len)
            bar = "[" + "#" * filled + "-" * (bar_len - filled) + "]"
            txt = f"{prefix}{s['label']:<13}{bar} {s['value']:>2}/{s['max']}"
            row = self.font_small.render(txt, True, color)
            surf.blit(row, (24, y))
            y += 22

        vals = {s["key"]: s["value"] for s in self.sliders}
        cfg = resolve_config(vals)
        preview = self.font_small.render(preview_text(cfg), True, THEME["dim"])
        surf.blit(preview, (INTERNAL_W // 2 - preview.get_width() // 2, y + 14))

        hint = self.font_small.render("UP/DN:SELECT  L/R:ADJUST  ENTER:START  ESC:QUIT", True, THEME["dim"])
        surf.blit(hint, (INTERNAL_W // 2 - hint.get_width() // 2, INTERNAL_H - 20))

    def run(self):
        while self.running:
            dt = self.clock.tick(FPS) / 1000.0

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                    break

                if self.state == "MENU":
                    if event.type == pygame.KEYDOWN:
                        if event.key in (pygame.K_UP, pygame.K_w):
                            self.menu_index = (self.menu_index - 1) % len(self.sliders)
                            self.play_sfx("hit")
                        elif event.key in (pygame.K_DOWN, pygame.K_s):
                            self.menu_index = (self.menu_index + 1) % len(self.sliders)
                            self.play_sfx("hit")
                        elif event.key in (pygame.K_LEFT, pygame.K_a):
                            s = self.sliders[self.menu_index]
                            s["value"] = max(s["min"], s["value"] - 1)
                            self.play_sfx("bounce")
                        elif event.key in (pygame.K_RIGHT, pygame.K_d):
                            s = self.sliders[self.menu_index]
                            s["value"] = min(s["max"], s["value"] + 1)
                            self.play_sfx("bounce")
                        elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                            self.start_game()
                        elif event.key == pygame.K_ESCAPE:
                            self.running = False

                elif self.state == "PLAYING":
                    self.game.handle_event(event)

            if self.state == "MENU":
                self.draw_menu(self.virtual_canvas)
            elif self.state == "PLAYING" and self.game:
                self.game.update(dt)
                self.game.draw(self.virtual_canvas)

            pygame.transform.scale(self.virtual_canvas, (WINDOW_W, WINDOW_H), self.screen)
            pygame.display.flip()

        pygame.quit()
        sys.exit()


if __name__ == "__main__":
    app = StandaloneCyPac()
    app.run()
