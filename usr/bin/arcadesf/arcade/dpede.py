#!/usr/bin/env python3
# digipede.py
"""
SERIF ARCADE - DIGIPEDE (Standalone Module)
Split from arcade1.py. Now boots into a slider-based config menu
before launch: SPEED / OBSTACLES / DIFFICULTY drive min-max formulas
that feed the existing randomizer-based spawn logic.
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
# ---------------------------------------------------------------------------
# Sliders run 0-10. resolve_config() maps slider positions onto min/max
# formulas for the actual gameplay values. Where the game already spawns
# things randomly, the slider shifts the RANGE rather than a fixed number,
# so runs stay varied but tunable.
# ===========================================================================
SLIDER_DEFS = [
    {"key": "speed",      "label": "SPEED",      "min": 0, "max": 10, "default": 5},
    {"key": "obstacles",  "label": "OBSTACLES",  "min": 0, "max": 10, "default": 5},
    {"key": "difficulty", "label": "DIFFICULTY", "min": 0, "max": 10, "default": 5},
]


def resolve_config(vals):
    s = vals["speed"] / 10.0
    o = vals["obstacles"] / 10.0
    d = vals["difficulty"] / 10.0

    step_interval = 0.20 - s * (0.20 - 0.06)          # faster centipede as SPEED rises
    density_lo = int(10 + o * 25)                      # mushroom count range widens/shifts up
    density_hi = int(density_lo + 10 + o * 10)
    segment_count = int(6 + d * 8)                      # longer centipede at higher DIFFICULTY
    lives = max(1, 5 - round(d * 3))

    return {
        "step_interval": round(step_interval, 3),
        "density_lo": density_lo,
        "density_hi": density_hi,
        "segment_count": segment_count,
        "lives": lives,
    }


def preview_text(cfg):
    return (f"SEG:{cfg['segment_count']:02d}  MUSHROOMS:{cfg['density_lo']}-{cfg['density_hi']}"
            f"  LIVES:{cfg['lives']}  STEP:{cfg['step_interval']:.2f}s")


# ===========================================================================
# DIGIPEDE
# ===========================================================================
class Digipede(ArcadeGame):
    name = "DIGIPEDE"
    CELL = 10
    COLS = INTERNAL_W // CELL
    ROWS = INTERNAL_H // CELL
    PLAYER_ZONE_ROWS = 5

    def __init__(self, app, config):
        super().__init__(app, config)
        self.reset()

    def reset(self):
        self.score = 0
        self.game_over = False
        self.lives = self.config["lives"]
        self.stage = 1
        self.mushrooms = {}
        self._start_stage(first=True)
        self._respawn_player()

    def _respawn_player(self):
        self.px = INTERNAL_W / 2
        self.py = (self.ROWS - 2) * self.CELL
        self.bullet = None
        self.fire_cooldown = 0.0
        self.hit_flash = 0.0

    def _seed_mushrooms(self, count):
        top_rows = self.ROWS - self.PLAYER_ZONE_ROWS
        added = 0
        attempts = 0
        while added < count and attempts < count * 20:
            attempts += 1
            c = random.randint(0, self.COLS - 1)
            r = random.randint(1, max(1, top_rows - 1))
            if (c, r) not in self.mushrooms:
                self.mushrooms[(c, r)] = 3
                added += 1

    def _start_stage(self, first=False):
        self.mushrooms = {}
        lo, hi = self.config["density_lo"], self.config["density_hi"]
        count = random.randint(lo, hi) + (self.stage - 1) * 2
        self._seed_mushrooms(count)
        self.step_interval = self.config["step_interval"]
        seg_count = self.config["segment_count"]
        start_col = self.COLS // 2 - seg_count // 2
        self.segments = []
        for i in range(seg_count):
            self.segments.append({
                "col": max(0, min(self.COLS - 1, start_col + i)),
                "row": 0,
                "dir": 1,
                "timer": self.step_interval,
            })

    def handle_event(self, event):
        super().handle_event(event)
        if self.game_over:
            return
        if event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE:
            self._try_fire()

    def _try_fire(self):
        if self.bullet is None and self.fire_cooldown <= 0:
            self.bullet = {"x": self.px, "y": self.py - 8}
            self.app.play_sfx("hit")

    def update(self, dt):
        if self.game_over:
            return

        self.fire_cooldown = max(0.0, self.fire_cooldown - dt)
        self.hit_flash = max(0.0, self.hit_flash - dt)

        keys = pygame.key.get_pressed()
        move = 130.0 * dt
        if keys[pygame.K_LEFT] or keys[pygame.K_a]: self.px -= move
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]: self.px += move
        if keys[pygame.K_UP] or keys[pygame.K_w]: self.py -= move
        if keys[pygame.K_DOWN] or keys[pygame.K_s]: self.py += move

        zone_top = (self.ROWS - self.PLAYER_ZONE_ROWS) * self.CELL
        self.px = max(8, min(INTERNAL_W - 8, self.px))
        self.py = max(zone_top, min(INTERNAL_H - 8, self.py))

        self._update_bullet(dt)
        self._update_segments(dt)
        self._check_player_collision()

        if not self.segments:
            self.stage += 1
            self._start_stage()

    def _update_bullet(self, dt):
        if self.bullet is None:
            return
        self.bullet["y"] -= 220.0 * dt
        if self.bullet["y"] < 0:
            self.bullet = None
            return

        bcol = int(self.bullet["x"] // self.CELL)
        brow = int(self.bullet["y"] // self.CELL)

        key = (bcol, brow)
        if key in self.mushrooms:
            self.mushrooms[key] -= 1
            if self.mushrooms[key] <= 0:
                del self.mushrooms[key]
                self.score += 5
            self.bullet = None
            self.app.play_sfx("bounce")
            return

        for seg in self.segments:
            if seg["col"] == bcol and seg["row"] == brow:
                self.segments.remove(seg)
                self.mushrooms[(bcol, brow)] = 1
                self.score += 10
                self.bullet = None
                self.app.play_sfx("score")
                return

    def _update_segments(self, dt):
        for seg in self.segments:
            seg["timer"] -= dt
            if seg["timer"] > 0:
                continue
            seg["timer"] = self.step_interval

            next_col = seg["col"] + seg["dir"]
            blocked = (next_col < 0 or next_col >= self.COLS or (next_col, seg["row"]) in self.mushrooms)
            if blocked:
                seg["row"] = min(self.ROWS - 1, seg["row"] + 1)
                seg["dir"] *= -1
            else:
                seg["col"] = next_col

    def _check_player_collision(self):
        pcol = int(self.px // self.CELL)
        prow = int(self.py // self.CELL)
        for seg in self.segments:
            if seg["col"] == pcol and seg["row"] == prow:
                self._lose_life()
                return

    def _lose_life(self):
        self.lives -= 1
        self.hit_flash = 0.4
        self.app.play_sfx("bounce")
        if self.lives <= 0:
            self.game_over = True
        else:
            self._respawn_player()

    def draw(self, surf):
        surf.fill(THEME["bg"])

        for (c, r), hp in self.mushrooms.items():
            x, y = c * self.CELL, r * self.CELL
            shade = 0.45 + 0.55 * (hp / 3.0)
            color = tuple(int(ch * shade) for ch in THEME["hot"])
            pygame.draw.rect(surf, color, (x + 1, y + 1, self.CELL - 2, self.CELL - 2))

        for seg in self.segments:
            cx = seg["col"] * self.CELL + self.CELL / 2
            cy = seg["row"] * self.CELL + self.CELL / 2
            draw_vrman(surf, cx, cy, radius=self.CELL // 2, facing=seg["dir"])

        if self.bullet:
            pygame.draw.line(surf, THEME["hot"], (self.bullet["x"], self.bullet["y"]), (self.bullet["x"], self.bullet["y"] + 5), 2)

        player_color = THEME["warn"] if self.hit_flash > 0 else THEME["hot"]
        draw_vrman(surf, self.px, self.py, radius=7, color=player_color)

        zone_top_px = (self.ROWS - self.PLAYER_ZONE_ROWS) * self.CELL
        pygame.draw.line(surf, THEME["dim"], (0, zone_top_px), (INTERNAL_W, zone_top_px), 1)

        hud = self.app.font_small.render(f"SCORE:{self.score}  LIVES:{self.lives}  STAGE:{self.stage}", True, THEME["hot"])
        surf.blit(hud, (6, 4))

        if self.game_over:
            t = self.app.font_big.render("GAME OVER", True, THEME["warn"])
            surf.blit(t, (INTERNAL_W // 2 - t.get_width() // 2, INTERNAL_H // 2 - 10))
            hint = self.app.font_small.render("ESC: MENU   R: RESTART", True, THEME["dim"])
            surf.blit(hint, (INTERNAL_W // 2 - hint.get_width() // 2, INTERNAL_H // 2 + 18))


# ---------------------------------------------------------------------------
# Standalone Application Engine (Menu + Game)
# ---------------------------------------------------------------------------
class StandaloneDigipede:
    def __init__(self):
        pygame.init()
        pygame.mixer.init(frequency=22050, size=-16, channels=2)
        self.screen = pygame.display.set_mode((WINDOW_W, WINDOW_H))
        pygame.display.set_caption("SERIF ARCADE - DIGIPEDE")
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
        self.game = Digipede(self, config)
        self.state = "PLAYING"
        self.play_sfx("select")

    def draw_menu(self, surf):
        surf.fill(THEME["bg"])
        title = self.font_big.render("DIGIPEDE", True, THEME["hot"])
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
            txt = f"{prefix}{s['label']:<11}{bar} {s['value']:>2}/{s['max']}"
            row = self.font_small.render(txt, True, color)
            surf.blit(row, (30, y))
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
    app = StandaloneDigipede()
    app.run()
