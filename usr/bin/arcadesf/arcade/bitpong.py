#!/usr/bin/env python3
# bitpong.py
"""
SERIF ARCADE - BIT PONG (Standalone Module)
Split from arcade1.py. Now boots into a slider-based config menu
before launch: BALL SPEED / PADDLE SIZE / DIFFICULTY (CPU skill)
drive min-max formulas that feed the gameplay values.
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
    {"key": "speed",      "label": "BALL SPEED",  "min": 0, "max": 10, "default": 5},
    {"key": "paddle",     "label": "PADDLE SIZE", "min": 0, "max": 10, "default": 5},
    {"key": "difficulty", "label": "DIFFICULTY",  "min": 0, "max": 10, "default": 5},
]


def resolve_config(vals):
    sp = vals["speed"] / 10.0
    pz = vals["paddle"] / 10.0
    d = vals["difficulty"] / 10.0

    ball_speed = round(60 + sp * 80, 1)          # base ball launch speed
    paddle_h = int(56 - pz * 32)                  # bigger PADDLE SIZE value = smaller paddle (harder)
    cpu_speed = round(60 + d * 100, 1)             # CPU reaction speed
    win_score = 7

    return {
        "ball_speed": ball_speed,
        "paddle_h": paddle_h,
        "cpu_speed": cpu_speed,
        "win_score": win_score,
    }


def preview_text(cfg):
    return f"BALL:{cfg['ball_speed']:.0f}px/s  PADDLE:{cfg['paddle_h']}px  CPU:{cfg['cpu_speed']:.0f}px/s  WIN:{cfg['win_score']}"


# ===========================================================================
# BIT PONG
# ===========================================================================
class BitPong(ArcadeGame):
    name = "BIT PONG"

    def __init__(self, app, config):
        super().__init__(app, config)
        self.reset()

    def reset(self):
        self.score = 0
        self.opp_score = 0
        self.game_over = False
        self.win_score = self.config["win_score"]
        self.paddle_w = 4
        self.paddle_h = self.config["paddle_h"]
        self.player_x = 14
        self.cpu_x = INTERNAL_W - 14 - self.paddle_w
        self.player_y = INTERNAL_H / 2 - self.paddle_h / 2
        self.cpu_y = INTERNAL_H / 2 - self.paddle_h / 2
        self._reset_ball()

    def _reset_ball(self):
        self.ball_x = INTERNAL_W / 2
        self.ball_y = INTERNAL_H / 2
        angle = random.uniform(-0.4, 0.4) + (math.pi if random.random() < 0.5 else 0.0)
        speed = self.config["ball_speed"]
        self.ball_vx = math.cos(angle) * speed
        self.ball_vy = math.sin(angle) * speed

    def update(self, dt):
        if self.game_over: return

        keys = pygame.key.get_pressed()
        move = 140.0 * dt
        if keys[pygame.K_UP] or keys[pygame.K_w]: self.player_y -= move
        if keys[pygame.K_DOWN] or keys[pygame.K_s]: self.player_y += move
        self.player_y = max(0, min(INTERNAL_H - self.paddle_h, self.player_y))

        target = self.ball_y - self.paddle_h / 2
        cpu_move = self.config["cpu_speed"] * dt
        if self.cpu_y < target: self.cpu_y = min(self.cpu_y + cpu_move, target)
        elif self.cpu_y > target: self.cpu_y = max(self.cpu_y - cpu_move, target)
        self.cpu_y = max(0, min(INTERNAL_H - self.paddle_h, self.cpu_y))

        self.ball_x += self.ball_vx * dt
        self.ball_y += self.ball_vy * dt

        if self.ball_y <= 2:
            self.ball_y = 2; self.ball_vy *= -1; self.app.play_sfx("bounce")
        elif self.ball_y >= INTERNAL_H - 2:
            self.ball_y = INTERNAL_H - 2; self.ball_vy *= -1; self.app.play_sfx("bounce")

        if (self.ball_vx < 0 and self.player_x <= self.ball_x <= self.player_x + self.paddle_w + 3 and
                self.player_y <= self.ball_y <= self.player_y + self.paddle_h):
            self.ball_vx = abs(self.ball_vx) * 1.05
            self.ball_vy += (self.ball_y - (self.player_y + self.paddle_h / 2)) * 2.0
            self.app.play_sfx("hit")

        if (self.ball_vx > 0 and self.cpu_x - 3 <= self.ball_x <= self.cpu_x + self.paddle_w and
                self.cpu_y <= self.ball_y <= self.cpu_y + self.paddle_h):
            self.ball_vx = -abs(self.ball_vx) * 1.05
            self.ball_vy += (self.ball_y - (self.cpu_y + self.paddle_h / 2)) * 2.0
            self.app.play_sfx("hit")

        if self.ball_x < -8:
            self.opp_score += 1; self.app.play_sfx("score"); self._reset_ball()
        elif self.ball_x > INTERNAL_W + 8:
            self.score += 1; self.app.play_sfx("score"); self._reset_ball()

        if self.score >= self.win_score or self.opp_score >= self.win_score:
            self.game_over = True

    def draw(self, surf):
        surf.fill(THEME["bg"])
        for y in range(0, INTERNAL_H, 10):
            pygame.draw.rect(surf, THEME["dim"], (INTERNAL_W // 2 - 1, y, 2, 5))

        pygame.draw.rect(surf, THEME["hot"], (self.player_x, self.player_y, self.paddle_w, self.paddle_h))
        draw_vrman(surf, self.player_x + self.paddle_w / 2, self.player_y + self.paddle_h / 2, radius=6)
        pygame.draw.rect(surf, THEME["dim"], (self.cpu_x, self.cpu_y, self.paddle_w, self.paddle_h))
        pygame.draw.circle(surf, THEME["hot"], (int(self.ball_x), int(self.ball_y)), 3)

        score_txt = self.app.font_big.render(str(self.score), True, THEME["hot"])
        surf.blit(score_txt, (INTERNAL_W // 2 - 30, 10))
        opp_txt = self.app.font_big.render(str(self.opp_score), True, THEME["dim"])
        surf.blit(opp_txt, (INTERNAL_W // 2 + 18, 10))

        if self.game_over:
            msg = "YOU WIN" if self.score > self.opp_score else "YOU LOSE"
            t = self.app.font_big.render(msg, True, THEME["hot"] if "WIN" in msg else THEME["warn"])
            surf.blit(t, (INTERNAL_W // 2 - t.get_width() // 2, INTERNAL_H // 2 - 10))
            hint = self.app.font_small.render("ESC: MENU   R: RESTART", True, THEME["dim"])
            surf.blit(hint, (INTERNAL_W // 2 - hint.get_width() // 2, INTERNAL_H // 2 + 18))


# ---------------------------------------------------------------------------
# Standalone Application Engine (Menu + Game)
# ---------------------------------------------------------------------------
class StandaloneBitPong:
    def __init__(self):
        pygame.init()
        pygame.mixer.init(frequency=22050, size=-16, channels=2)
        self.screen = pygame.display.set_mode((WINDOW_W, WINDOW_H))
        pygame.display.set_caption("SERIF ARCADE - BIT PONG")
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
        self.game = BitPong(self, config)
        self.state = "PLAYING"
        self.play_sfx("select")

    def draw_menu(self, surf):
        surf.fill(THEME["bg"])
        title = self.font_big.render("BIT PONG", True, THEME["hot"])
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
            txt = f"{prefix}{s['label']:<12}{bar} {s['value']:>2}/{s['max']}"
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
    app = StandaloneBitPong()
    app.run()
