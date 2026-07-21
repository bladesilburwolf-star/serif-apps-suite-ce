#!/usr/bin/env python3
# axiombreakout.py
"""
SERIF ARCADE - AXIOM BREAKOUT (Standalone Module)
Split from arcade1.py. Now boots into a slider-based config menu
before launch: BALL SPEED / BRICK DENSITY / DIFFICULTY (paddle width)
drive min-max formulas that feed the existing brick-skip randomizer.
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
    {"key": "speed",      "label": "BALL SPEED",    "min": 0, "max": 10, "default": 5},
    {"key": "obstacles",  "label": "BRICK DENSITY", "min": 0, "max": 10, "default": 5},
    {"key": "difficulty", "label": "DIFFICULTY",    "min": 0, "max": 10, "default": 5},
]


def resolve_config(vals):
    sp = vals["speed"] / 10.0
    o = vals["obstacles"] / 10.0
    d = vals["difficulty"] / 10.0

    ball_speed = round(70 + sp * 80, 1)
    skip_prob = round(0.50 - o * 0.45, 3)          # higher BRICK DENSITY = fewer gaps in the wall
    paddle_w = int(50 - d * 28)                      # higher DIFFICULTY = narrower paddle
    lives = max(1, 5 - round(d * 3))

    return {
        "ball_speed": ball_speed,
        "skip_prob": skip_prob,
        "paddle_w": paddle_w,
        "lives": lives,
    }


def preview_text(cfg):
    return (f"SPEED:{cfg['ball_speed']:.0f}px/s  GAPS:{cfg['skip_prob']:.0%}"
            f"  PADDLE:{cfg['paddle_w']}px  SHIELDS:{cfg['lives']}")


# ===========================================================================
# AXIOM BREAKOUT
# ===========================================================================
class AxiomBreakout(ArcadeGame):
    name = "AXIOM BREAKOUT"

    def __init__(self, app, config):
        super().__init__(app, config)
        self.reset()

    def reset(self):
        self.score = 0
        self.lives = self.config["lives"]
        self.game_over = False
        self.stage = 1
        self.pw = self.config["paddle_w"]
        self.ph = 5
        self.px = INTERNAL_W // 2
        self.py = INTERNAL_H - 20
        self.ball_radius = 3
        self._reset_ball()
        self._build_bricks()

    def _build_bricks(self):
        self.brick_rows, self.brick_cols = 4, 8
        self.brick_w, self.brick_h = 34, 8
        self.ox, self.oy = 24, 40
        self.bricks = []
        skip_prob = self.config["skip_prob"]
        for r in range(self.brick_rows):
            for c in range(self.brick_cols):
                if random.random() < skip_prob: continue
                hp = 3 - (r // 2)
                self.bricks.append({
                    "rect": pygame.Rect(self.ox + c * (self.brick_w + 2), self.oy + r * (self.brick_h + 2), self.brick_w, self.brick_h),
                    "hp": max(1, hp)
                })

    def _reset_ball(self):
        self.ball_x = INTERNAL_W // 2
        self.ball_y = INTERNAL_H // 2 + 10
        speed = self.config["ball_speed"]
        sign = random.choice([-1.0, 1.0])
        self.ball_vx = sign * speed * 0.62
        self.ball_vy = speed * 0.79
        self.served = False

    def handle_event(self, event):
        super().handle_event(event)
        if event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE and not self.served and not self.game_over:
            self.served = True

    def update(self, dt):
        if self.game_over: return
        keys = pygame.key.get_pressed()
        move = 150.0 * dt
        if keys[pygame.K_LEFT] or keys[pygame.K_a]: self.px -= move
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]: self.px += move
        self.px = max(self.pw // 2 + 4, min(INTERNAL_W - self.pw // 2 - 4, self.px))

        if not self.served:
            self.ball_x, self.ball_y = self.px, self.py - 8
            return

        self.ball_x += self.ball_vx * dt
        self.ball_y += self.ball_vy * dt

        if self.ball_x <= self.ball_radius or self.ball_x >= INTERNAL_W - self.ball_radius:
            self.ball_vx *= -1; self.app.play_sfx("bounce")
        if self.ball_y <= self.ball_radius + 15:
            self.ball_vy *= -1; self.app.play_sfx("bounce")

        paddle_rect = pygame.Rect(self.px - self.pw // 2, self.py, self.pw, self.ph)
        ball_rect = pygame.Rect(self.ball_x - self.ball_radius, self.ball_y - self.ball_radius, self.ball_radius * 2, self.ball_radius * 2)

        if self.ball_vy > 0 and ball_rect.colliderect(paddle_rect):
            self.ball_vy = -abs(self.ball_vy) * 1.02
            self.ball_vx = ((self.ball_x - self.px) / (self.pw / 2)) * 110.0
            self.app.play_sfx("hit")

        for b in self.bricks[:]:
            if ball_rect.colliderect(b["rect"]):
                b["hp"] -= 1; self.score += 15; self.ball_vy *= -1; self.app.play_sfx("score")
                if b["hp"] <= 0: self.bricks.remove(b)
                break

        if self.ball_y > INTERNAL_H + 10:
            self.lives -= 1; self.app.play_sfx("bounce")
            if self.lives <= 0: self.game_over = True
            else: self._reset_ball()

        if not self.bricks and not self.game_over:
            self.score += 500; self.stage += 1; self._build_bricks(); self._reset_ball()

    def draw(self, surf):
        surf.fill(THEME["bg"])
        pygame.draw.line(surf, THEME["dim"], (0, 16), (INTERNAL_W, 16), 1)
        for b in self.bricks:
            color = THEME["hot"] if b["hp"] == 1 else (THEME["warn"] if b["hp"] == 3 else (200, 180, 50))
            pygame.draw.rect(surf, color, b["rect"], 1)

        pygame.draw.rect(surf, THEME["hot"], (self.px - self.pw // 2, self.py, self.pw, self.ph))
        draw_vrman(surf, self.px, self.py + self.ph // 2, radius=6)
        pygame.draw.circle(surf, THEME["hot"], (int(self.ball_x), int(self.ball_y)), self.ball_radius)

        hud = self.app.font_small.render(f"SCORE:{self.score:05d}  SHIELDS:{self.lives}  STAGE:{self.stage}", True, THEME["hot"])
        surf.blit(hud, (6, 3))

        if self.game_over:
            t = self.app.font_big.render("GAME OVER", True, THEME["warn"])
            surf.blit(t, (INTERNAL_W // 2 - t.get_width() // 2, INTERNAL_H // 2 - 10))
            hint = self.app.font_small.render("ESC: MENU   R: RESTART", True, THEME["dim"])
            surf.blit(hint, (INTERNAL_W // 2 - hint.get_width() // 2, INTERNAL_H // 2 + 18))


# ---------------------------------------------------------------------------
# Standalone Application Engine (Menu + Game)
# ---------------------------------------------------------------------------
class StandaloneAxiomBreakout:
    def __init__(self):
        pygame.init()
        pygame.mixer.init(frequency=22050, size=-16, channels=2)
        self.screen = pygame.display.set_mode((WINDOW_W, WINDOW_H))
        pygame.display.set_caption("SERIF ARCADE - AXIOM BREAKOUT")
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
        self.game = AxiomBreakout(self, config)
        self.state = "PLAYING"
        self.play_sfx("select")

    def draw_menu(self, surf):
        surf.fill(THEME["bg"])
        title = self.font_big.render("AXIOM BREAKOUT", True, THEME["hot"])
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
    app = StandaloneAxiomBreakout()
    app.run()
