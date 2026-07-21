#!/usr/bin/env python3
# arcade_hub.py
"""
SERIF ARCADE MEGA-HUB: REBORN
A simplified 4-wall room layout featuring a 3x5 grid of terminal screens 
on the main display wall, fully interactable via mouse input.
"""
import os
import sys
import math
import random
import pygame
import numpy as np

# ---------------------------------------------------------------------------
# Global Settings & Palettes
# ---------------------------------------------------------------------------
INTERNAL_W, INTERNAL_H = 320, 240   # Retro native resolution
SCALE = 3                           # Integer upscale factor
WINDOW_W, WINDOW_H = INTERNAL_W * SCALE, INTERNAL_H * SCALE

PALETTES = {
    "Classic Green": {
        "bg": (4, 10, 6),
        "hot": (0, 255, 128),
        "dim": (0, 110, 55),
        "panel": (0, 22, 11),
        "warn": (255, 90, 90),
        "amber": (255, 110, 0),
    },
    "Cyberpunk Neon": {
        "bg": (12, 2, 18),
        "hot": (255, 0, 128),
        "dim": (110, 0, 70),
        "panel": (25, 0, 20),
        "warn": (0, 255, 255),
        "amber": (255, 180, 0),
    },
    "Monochrome Terminal": {
        "bg": (10, 10, 10),
        "hot": (240, 240, 240),
        "dim": (100, 100, 100),
        "panel": (25, 25, 25),
        "warn": (180, 180, 180),
        "amber": (220, 140, 40),
    }
}

# Active runtime configuration
THEME = dict(PALETTES["Classic Green"])
FPS = 60

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


# ===========================================================================
# SHARED GLOBAL OPTIONS MENU (Toggles & Sliders)
# ===========================================================================
class GlobalOptionsMenu:
    def __init__(self, font_small, font_big):
        self.font_small = font_small
        self.font_big = font_big
        self.is_active = False
        self.selected_idx = 0
        self.palette_names = list(PALETTES.keys())
        self.current_palette_idx = 0
        self.fps_options = [30, 60, 120]
        self.current_fps_idx = 1
        self.sfx_volume = 80 # Value from 0 to 100

    def handle_event(self, event):
        if not self.is_active:
            if event.type == pygame.KEYDOWN and event.key == pygame.K_TAB:
                self.is_active = True
                return True
            return False

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_TAB or event.key == pygame.K_ESCAPE:
                self.is_active = False
                return True
            
            # Navigate Menu Rows
            elif event.key in (pygame.K_UP, pygame.K_w):
                self.selected_idx = (self.selected_idx - 1) % 4
            elif event.key in (pygame.K_DOWN, pygame.K_s):
                self.selected_idx = (self.selected_idx + 1) % 4
                
            # Modify Toggles / Sliders
            elif event.key in (pygame.K_LEFT, pygame.K_a):
                self._adjust_setting(-1)
            elif event.key in (pygame.K_RIGHT, pygame.K_d):
                self._adjust_setting(1)
        return True

    def _adjust_setting(self, direction):
        global THEME, FPS
        if self.selected_idx == 0: # Palette Choice Toggle
            self.current_palette_idx = (self.current_palette_idx + direction) % len(self.palette_names)
            THEME.update(PALETTES[self.palette_names[self.current_palette_idx]])
        elif self.selected_idx == 1: # FPS Limit Toggle
            self.current_fps_idx = (self.current_fps_idx + direction) % len(self.fps_options)
            FPS = self.fps_options[self.current_fps_idx]
        elif self.selected_idx == 2: # SFX Volume Slider
            self.sfx_volume = max(0, min(100, self.sfx_volume + direction * 10))

    def draw(self, surf):
        # Semi-transparent overlay backdrop
        overlay = pygame.Surface((INTERNAL_W, INTERNAL_H), pygame.SRCALPHA)
        overlay.fill((THEME["bg"][0], THEME["bg"][1], THEME["bg"][2], 230))
        surf.blit(overlay, (0, 0))

        # Menu Box Frame
        box_rect = pygame.Rect(40, 30, INTERNAL_W - 80, INTERNAL_H - 60)
        pygame.draw.rect(surf, THEME["panel"], box_rect)
        pygame.draw.rect(surf, THEME["hot"], box_rect, 1)

        title = self.font_big.render("GLOBAL CONFIG SYSTEM", True, THEME["hot"])
        surf.blit(title, (INTERNAL_W//2 - title.get_width()//2, 40))

        options_data = [
            ("COLOR THEME", f"< {self.palette_names[self.current_palette_idx]} >"),
            ("ENGINE FPS", f"< {self.fps_options[self.current_fps_idx]} Hz >"),
            ("SFX VOLUME", f"[{'#' * (self.sfx_volume // 10)}{'-' * (10 - self.sfx_volume // 10)}] {self.sfx_volume}%"),
            ("BACK TO CORE", "[ PRESS ESC / TAB ]")
        ]

        for i, (label, val) in enumerate(options_data):
            is_sel = (i == self.selected_idx)
            color = THEME["hot"] if is_sel else THEME["dim"]
            
            # Cursor Indicator
            prefix = " > " if is_sel else "   "
            
            lbl_txt = self.font_small.render(f"{prefix}{label}", True, color)
            val_txt = self.font_small.render(val, True, THEME["warn"] if is_sel and i != 3 else color)
            
            row_y = 80 + (i * 28)
            surf.blit(lbl_txt, (55, row_y))
            surf.blit(val_txt, (180, row_y))


class ArcadeGame:
    name = "UNSET"
    def __init__(self, app):
        self.app = app
        self.score = 0
        self.game_over = False
    def handle_event(self, event):
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.app.go_to_game_select()
    def update(self, dt): pass
    def draw(self, surf): pass


# ===========================================================================
# ARCADE MODULES RUNTIME EMULATORS
# ===========================================================================
class Digipede(ArcadeGame):
    name = "DIGIPEDE"
    CELL, COLS, ROWS, PLAYER_ZONE_ROWS, STEP_INTERVAL, SEGMENT_COUNT, FIELD_DENSITY = 10, 32, 24, 5, 0.13, 10, 26
    def __init__(self, app):
        super().__init__(app)
        self.lives, self.stage, self.mushrooms = 3, 1, {}
        self._start_stage(first=True)
        self._respawn_player()
    def _respawn_player(self):
        self.px, self.py, self.bullet, self.fire_cooldown, self.hit_flash = INTERNAL_W / 2, (self.ROWS - 2) * self.CELL, None, 0.0, 0.0
    def _seed_mushrooms(self, count):
        top_rows = self.ROWS - self.PLAYER_ZONE_ROWS
        added = 0
        while added < count:
            c, r = random.randint(0, self.COLS - 1), random.randint(1, max(1, top_rows - 1))
            if (c, r) not in self.mushrooms:
                self.mushrooms[(c, r)] = 3
                added += 1
    def _start_stage(self, first=False):
        self.mushrooms = {}
        self._seed_mushrooms(self.FIELD_DENSITY)
        self.step_interval = self.STEP_INTERVAL
        start_col = self.COLS // 2 - self.SEGMENT_COUNT // 2
        self.segments = [{"col": max(0, min(self.COLS - 1, start_col + i)), "row": 0, "dir": 1, "timer": self.step_interval} for i in range(self.SEGMENT_COUNT)]
    def handle_event(self, event):
        super().handle_event(event)
        if not self.game_over and event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE:
            if self.bullet is None and self.fire_cooldown <= 0:
                self.bullet = {"x": self.px, "y": self.py - 8}
                self.app.play_sfx("hit")
    def update(self, dt):
        if self.game_over: return
        self.fire_cooldown, self.hit_flash = max(0.0, self.fire_cooldown - dt), max(0.0, self.hit_flash - dt)
        keys = pygame.key.get_pressed()
        move = 130.0 * dt
        if keys[pygame.K_LEFT] or keys[pygame.K_a]: self.px -= move
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]: self.px += move
        if keys[pygame.K_UP] or keys[pygame.K_w]: self.py -= move
        if keys[pygame.K_DOWN] or keys[pygame.K_s]: self.py += move
        self.px = max(8, min(INTERNAL_W - 8, self.px))
        self.py = max((self.ROWS - self.PLAYER_ZONE_ROWS) * self.CELL, min(INTERNAL_H - 8, self.py))
        if self.bullet:
            self.bullet["y"] -= 220.0 * dt
            if self.bullet["y"] < 0: self.bullet = None
            else:
                bcol, brow = int(self.bullet["x"] // self.CELL), int(self.bullet["y"] // self.CELL)
                if (bcol, brow) in self.mushrooms:
                    self.mushrooms[(bcol, brow)] -= 1
                    if self.mushrooms[(bcol, brow)] <= 0: del self.mushrooms[(bcol, brow)]; self.score += 5
                    self.bullet = None; self.app.play_sfx("bounce")
                else:
                    for seg in self.segments:
                        if seg["col"] == bcol and seg["row"] == brow:
                            self.segments.remove(seg); self.mushrooms[(bcol, brow)] = 1; self.score += 10
                            self.bullet = None; self.app.play_sfx("score"); break
        for seg in self.segments:
            seg["timer"] -= dt
            if seg["timer"] <= 0:
                seg["timer"] = self.step_interval
                nc = seg["col"] + seg["dir"]
                if nc < 0 or nc >= self.COLS or (nc, seg["row"]) in self.mushrooms:
                    seg["row"] = min(self.ROWS - 1, seg["row"] + 1); seg["dir"] *= -1
                else: seg["col"] = nc
        pcol, prow = int(self.px // self.CELL), int(self.py // self.CELL)
        for seg in self.segments:
            if seg["col"] == pcol and seg["row"] == prow:
                self.lives -= 1; self.hit_flash = 0.4; self.app.play_sfx("bounce")
                if self.lives <= 0: self.game_over = True
                else: self._respawn_player()
                break
        if not self.segments: self.stage += 1; self._start_stage()
    def draw(self, surf):
        surf.fill(THEME["bg"])
        for (c, r), hp in self.mushrooms.items():
            pygame.draw.rect(surf, tuple(int(ch * (0.45 + 0.55 * (hp / 3.0))) for ch in THEME["hot"]), (c * self.CELL + 1, r * self.CELL + 1, self.CELL - 2, self.CELL - 2))
        for seg in self.segments: draw_vrman(surf, seg["col"] * self.CELL + self.CELL/2, seg["row"] * self.CELL + self.CELL/2, radius=self.CELL//2, facing=seg["dir"])
        if self.bullet: pygame.draw.line(surf, THEME["hot"], (self.bullet["x"], self.bullet["y"]), (self.bullet["x"], self.bullet["y"] + 5), 2)
        draw_vrman(surf, self.px, self.py, radius=7, color=THEME["warn"] if self.hit_flash > 0 else THEME["hot"])
        pygame.draw.line(surf, THEME["dim"], (0, (self.ROWS - self.PLAYER_ZONE_ROWS) * self.CELL), (INTERNAL_W, (self.ROWS - self.PLAYER_ZONE_ROWS) * self.CELL), 1)
        surf.blit(self.app.font_small.render(f"SCORE:{self.score}  LIVES:{self.lives}  STAGE:{self.stage}", True, THEME["hot"]), (6, 4))
        if self.game_over:
            t = self.app.font_big.render("GAME OVER", True, THEME["warn"])
            surf.blit(t, (INTERNAL_W // 2 - t.get_width() // 2, INTERNAL_H // 2 - 10))

class CyPac(ArcadeGame):
    name = "CYPAC"
    CELL, COLS, ROWS, TUNNEL_ROW = 10, 32, 24, 12
    DIRS = {"up": (0, -1), "down": (0, 1), "left": (-1, 0), "right": (1, 0)}
    KEY_DIR = {pygame.K_UP: "up", pygame.K_w: "up", pygame.K_DOWN: "down", pygame.K_s: "down", pygame.K_LEFT: "left", pygame.K_a: "left", pygame.K_RIGHT: "right", pygame.K_d: "right"}
    GHOST_COLORS = [(255, 90, 90), (255, 170, 60), (140, 255, 255)]
    PLAYER_SPAWN, GHOST_SPAWNS = (16, 17), [(12, 10), (19, 10), (16, 7)]
    def __init__(self, app):
        super().__init__(app)
        self.lives, self.stage = 3, 1
        self._build_walls()
        self._start_stage(first=True)
    def _build_walls(self):
        self.walls = set()
        for c in range(self.COLS):
            for r in range(self.ROWS):
                if r == 0 or r == self.ROWS - 1: self.walls.add((c, r))
                elif (c == 0 or c == self.COLS - 1) and r != self.TUNNEL_ROW: self.walls.add((c, r))
        for x in range(14, 18):
            for y in range(9, 15): self.walls.add((x, y))
    def _start_stage(self, first=False):
        self.pellets = set((c, r) for c in range(1, self.COLS - 1) for r in range(1, self.ROWS - 1) if (c, r) not in self.walls)
        self.player = {"col": self.PLAYER_SPAWN[0], "row": self.PLAYER_SPAWN[1], "dir": "left", "queued": "left", "timer": 0.0}
        self.ghosts = [{"col": gc, "row": gr, "dir": "up", "spawn": (gc, gr), "timer": 0.0, "step": 0.19} for (gc, gr) in self.GHOST_SPAWNS]
    def handle_event(self, event):
        super().handle_event(event)
        if not self.game_over and event.type == pygame.KEYDOWN and event.key in self.KEY_DIR:
            self.player["queued"] = self.KEY_DIR[event.key]
    def update(self, dt):
        if self.game_over: return
        p = self.player
        p["timer"] -= dt
        if p["timer"] <= 0:
            p["timer"] = 0.14
            dqx, dqy = self.DIRS[p["queued"]]
            nx, ny = p["col"] + dqx, p["row"] + dqy
            if ny == self.TUNNEL_ROW: nx %= self.COLS
            if (nx, ny) not in self.walls and 0 <= ny < self.ROWS: p["dir"] = p["queued"]
            dx, dy = self.DIRS[p["dir"]]
            cx, cy = p["col"] + dx, p["row"] + dy
            if cy == self.TUNNEL_ROW: cx %= self.COLS
            if (cx, cy) not in self.walls and 0 <= cy < self.ROWS: p["col"], p["row"] = cx, cy
            self.pellets.discard((p["col"], p["row"]))
        for g in self.ghosts:
            g["timer"] -= dt
            if g["timer"] <= 0:
                g["timer"] = g["step"]
                rev = {"up": "down", "down": "up", "left": "right", "right": "left"}[g["dir"]]
                cands = [n for n, (dx, dy) in self.DIRS.items() if n != rev and (g["col"]+dx, g["row"]+dy) not in self.walls]
                if cands:
                    g["dir"] = random.choice(cands)
                    g["col"] += self.DIRS[g["dir"]][0]
                    g["row"] += self.DIRS[g["dir"]][1]
            if g["col"] == p["col"] and g["row"] == p["row"]:
                self.lives -= 1; self.app.play_sfx("bounce")
                if self.lives <= 0: self.game_over = True
                else: p["col"], p["row"] = self.PLAYER_SPAWN
        if not self.pellets: self.stage += 1; self._start_stage()
    def draw(self, surf):
        surf.fill(THEME["bg"])
        for (c, r) in self.walls: pygame.draw.rect(surf, THEME["dim"], (c * self.CELL, r * self.CELL, self.CELL, self.CELL))
        for (c, r) in self.pellets: pygame.draw.circle(surf, THEME["hot"], (c * self.CELL + self.CELL//2, r * self.CELL + self.CELL//2), 1)
        for g in self.ghosts:
            cx, cy = g["col"] * self.CELL + self.CELL//2, g["row"] * self.CELL + self.CELL//2
            pygame.draw.circle(surf, self.GHOST_COLORS[self.ghosts.index(g)], (cx, cy), self.CELL//2)
        draw_vrman(surf, self.player["col"]*self.CELL + self.CELL//2, self.player["row"]*self.CELL + self.CELL//2, radius=self.CELL//2, facing=1)
        surf.blit(self.app.font_small.render(f"SCORE:{self.score}  LIVES:{self.lives}", True, THEME["hot"]), (6, 2))

class BitPong(ArcadeGame):
    name = "BIT PONG"
    def __init__(self, app):
        super().__init__(app)
        self.reset()
    def reset(self):
        self.score, self.opp_score, self.game_over, self.paddle_h, self.player_y, self.cpu_y = 0, 0, False, 40, 100, 100
        self.ball_x, self.ball_y, self.ball_vx, self.ball_vy = 160, 120, 100, 60
    def update(self, dt):
        if self.game_over: return
        keys = pygame.key.get_pressed()
        if keys[pygame.K_UP] or keys[pygame.K_w]: self.player_y -= 140.0 * dt
        if keys[pygame.K_DOWN] or keys[pygame.K_s]: self.player_y += 140.0 * dt
        self.player_y = max(0, min(INTERNAL_H - self.paddle_h, self.player_y))
        if self.cpu_y < self.ball_y - 20: self.cpu_y += 100.0 * dt
        else: self.cpu_y -= 100.0 * dt
        self.ball_x += self.ball_vx * dt; self.ball_y += self.ball_vy * dt
        if self.ball_y <= 2 or self.ball_y >= INTERNAL_H - 2: self.ball_vy *= -1; self.app.play_sfx("bounce")
        if self.ball_vx < 0 and 14 <= self.ball_x <= 20 and self.player_y <= self.ball_y <= self.player_y + self.paddle_h:
            self.ball_vx = abs(self.ball_vx) * 1.05; self.app.play_sfx("hit")
        if self.ball_vx > 0 and INTERNAL_W - 20 <= self.ball_x <= INTERNAL_W - 14 and self.cpu_y <= self.ball_y <= self.cpu_y + self.paddle_h:
            self.ball_vx = -abs(self.ball_vx) * 1.05; self.app.play_sfx("hit")
        if self.ball_x < 0: self.opp_score += 1; self.reset()
        elif self.ball_x > INTERNAL_W: self.score += 1; self.reset()
        if self.score >= 7 or self.opp_score >= 7: self.game_over = True
    def draw(self, surf):
        surf.fill(THEME["bg"])
        pygame.draw.rect(surf, THEME["hot"], (14, int(self.player_y), 4, self.paddle_h))
        pygame.draw.rect(surf, THEME["dim"], (INTERNAL_W - 18, int(self.cpu_y), 4, self.paddle_h))
        pygame.draw.circle(surf, THEME["hot"], (int(self.ball_x), int(self.ball_y)), 3)
        surf.blit(self.app.font_big.render(f"{self.score}   {self.opp_score}", True, THEME["hot"]), (130, 10))

class AxiomBreakout(ArcadeGame):
    name = "AXIOM BREAKOUT"
    def __init__(self, app):
        super().__init__(app)
        self.reset()
    def reset(self):
        self.score, self.lives, self.game_over, self.px, self.py = 0, 3, False, 160, 220
        self.ball_x, self.ball_y, self.ball_vx, self.ball_vy = 160, 150, 80, -90
        self.bricks = [{"rect": pygame.Rect(24 + c*36, 40 + r*10, 34, 8), "hp": 1} for r in range(4) for c in range(8)]
    def update(self, dt):
        if self.game_over: return
        keys = pygame.key.get_pressed()
        if keys[pygame.K_LEFT] or keys[pygame.K_a]: self.px -= 150.0 * dt
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]: self.px += 150.0 * dt
        self.px = max(20, min(INTERNAL_W - 20, self.px))
        self.ball_x += self.ball_vx * dt; self.ball_y += self.ball_vy * dt
        if self.ball_x <= 3 or self.ball_x >= INTERNAL_W - 3: self.ball_vx *= -1; self.app.play_sfx("bounce")
        if self.ball_y <= 20: self.ball_vy *= -1; self.app.play_sfx("bounce")
        paddle_rect = pygame.Rect(self.px - 18, self.py, 36, 5)
        if self.ball_vy > 0 and paddle_rect.collidepoint(self.ball_x, self.ball_y):
            self.ball_vy *= -1; self.ball_vx = ((self.ball_x - self.px)/18)*100; self.app.play_sfx("hit")
        for b in self.bricks[:]:
            if b["rect"].collidepoint(self.ball_x, self.ball_y):
                self.bricks.remove(b); self.ball_vy *= -1; self.score += 15; self.app.play_sfx("score"); break
        if self.ball_y > INTERNAL_H:
            self.lives -= 1
            if self.lives <= 0: self.game_over = True
            else: self.ball_x, self.ball_y, self.ball_vx, self.ball_vy = self.px, 150, 80, -90
    def draw(self, surf):
        surf.fill(THEME["bg"])
        for b in self.bricks: pygame.draw.rect(surf, THEME["hot"], b["rect"], 1)
        pygame.draw.rect(surf, THEME["hot"], (int(self.px - 18), self.py, 36, 5))
        pygame.draw.circle(surf, THEME["hot"], (int(self.ball_x), int(self.ball_y)), 3)
        surf.blit(self.app.font_small.render(f"SCORE:{self.score}  LIVES:{self.lives}", True, THEME["hot"]), (6, 3))

# (Dummy placeholder games loaded into grid to fulfill 15 unique array allocations)
class PlaceholderGame(ArcadeGame):
    def __init__(self, app, label): super().__init__(app); self.name = label
    def draw(self, surf):
        surf.fill(THEME["bg"])
        t = self.app.font_big.render(f"{self.name} CORE ACTIVE", True, THEME["hot"])
        surf.blit(t, (INTERNAL_W//2 - t.get_width()//2, INTERNAL_H//2))


# ===========================================================================
# 4-WALLED GRID-BASED CENTRALISED HUB
# ===========================================================================
class ArcadeMegaHub:
    def __init__(self):
        pygame.init()
        pygame.mixer.init(frequency=22050, size=-16, channels=2)
        self.screen = pygame.display.set_mode((WINDOW_W, WINDOW_H))
        pygame.display.set_caption("SERIF MEGA-ARCADE: INTEGRATED GRID TERMINAL")
        self.clock = pygame.time.Clock()
        self.virtual_canvas = pygame.Surface((INTERNAL_W, INTERNAL_H))

        self.font_small = pygame.font.SysFont("Courier", 10, bold=True)
        self.font_big = pygame.font.SysFont("Courier", 14, bold=True)

        self.options_menu = GlobalOptionsMenu(self.font_small, self.font_big)

        # Mapping full 3x5 matrix (15 screens total)
        self.screens_map = [
            {"name": "DIGIPEDE",        "class": Digipede,                 "type": "GAME",  "color": "hot"},
            {"name": "CYPAC",           "class": CyPac,                    "type": "GAME",  "color": "hot"},
            {"name": "BIT PONG",        "class": BitPong,                  "type": "GAME",  "color": "hot"},
            {"name": "AXIOM BREAKOUT",  "class": AxiomBreakout,            "type": "GAME",  "color": "hot"},
            {"name": "CROSSFIRE",       "class": lambda a: PlaceholderGame(a, "CROSSFIRE"), "type": "GAME", "color": "hot"},
            {"name": "XROIDS",          "class": lambda a: PlaceholderGame(a, "XROIDS"),    "type": "GAME", "color": "hot"},
            {"name": "BLASTER",         "class": lambda a: PlaceholderGame(a, "BLASTER"),   "type": "GAME", "color": "hot"},
            {"name": "BIT DEFENDER",    "class": lambda a: PlaceholderGame(a, "DEFENDER"),  "type": "GAME", "color": "hot"},
            {"name": "CYBER WINDS",     "class": lambda a: PlaceholderGame(a, "WINDS"),     "type": "GAME", "color": "hot"},
            {"name": "METRICS",         "class": lambda a: PlaceholderGame(a, "METRICS"),   "type": "GAME", "color": "hot"},
            {"name": "CYBERIA PIT",     "class": lambda a: PlaceholderGame(a, "CYBERIA"),   "type": "GAME", "color": "hot"},
            {"name": "HACKER BROS",     "class": lambda a: PlaceholderGame(a, "HACKER"),    "type": "GAME", "color": "hot"},
            {"name": "SYS DIAGNOSTIC",  "class": lambda a: PlaceholderGame(a, "DIAG"),      "type": "GAME", "color": "hot"},
            {"name": "NET GRAPH",       "class": lambda a: PlaceholderGame(a, "NET"),       "type": "GAME", "color": "hot"},
            {"name": "VOXEL CORE",      "class": None,                     "type": "VOXEL", "color": "amber"},
        ]

        self.state = "HUB_GRID" 
        self.current_game = None
        self.hovered_idx = -1

        # Grid Geometry Setup
        self.cols, self.rows = 5, 3
        self.scr_w, self.scr_h = 50, 40
        self.start_x, self.start_y = 25, 50
        self.gap_x, self.gap_y = 10, 12

    def play_sfx(self, sfx_type):
        try:
            # Volume control mapped scaling
            vol_multiplier = self.options_menu.sfx_volume / 100.0
            freq = 440 if sfx_type == "hit" else (220 if sfx_type == "bounce" else 650)
            duration = 0.06 if sfx_type != "score" else 0.18
            sample_rate = 22050
            n_samples = int(sample_rate * duration)
            buf = np.zeros((n_samples, 2), dtype=np.int16)
            for i in range(n_samples):
                t = i / sample_rate
                buf[i][0] = int((14000 * vol_multiplier) * math.sin(2 * math.pi * freq * t) * (1.0 - t/duration))
                buf[i][1] = buf[i][0]
            pygame.sndarray.make_sound(buf).play()
        except: pass

    def go_to_game_select(self):
        self.state = "HUB_GRID"
        self.current_game = None
        self.play_sfx("bounce")

    def launch_voxel_engine(self):
        print("[Voxel Portal Activated] Transferring core runtime to amber-voxel-minecraft.py...")
        pygame.quit()
        import subprocess
        try: subprocess.Popen([sys.executable, "amber-voxel-minecraft.py"])
        except Exception as e: print(f"Runtime transfer exception: {e}")
        sys.exit()

    def draw_grid_hub(self, surf):
        surf.fill(THEME["bg"])

        # 4-Walled Environment Perspective Outer Guide Framing Line details
        pygame.draw.lines(surf, THEME["dim"], True, [(5, 5), (INTERNAL_W-5, 5), (INTERNAL_W-5, INTERNAL_H-5), (5, INTERNAL_H-5)], 1)
        pygame.draw.rect(surf, (0, 30, 15), (self.start_x - 10, self.start_y - 15, (self.scr_w+self.gap_x)*5 + 10, (self.scr_h+self.gap_y)*3 + 15), 1)

        # Title Headings
        title = self.font_big.render("SERIF SYSTEM CORE INTEGRATED HUB", True, THEME["hot"])
        surf.blit(title, (INTERNAL_W//2 - title.get_width()//2, 18))

        # Scan coordinate grid elements
        for idx, scr in enumerate(self.screens_map):
            r = idx // self.cols
            c = idx % self.cols

            x = self.start_x + c * (self.scr_w + self.gap_x)
            y = self.start_y + r * (self.scr_h + self.gap_y)
            rect = pygame.Rect(x, y, self.scr_w, self.scr_h)

            is_hovered = (idx == self.hovered_idx)
            base_color = THEME[scr["color"]]
            color = base_color if is_hovered else tuple(int(ch * 0.4) for ch in base_color)

            # Draw Screen Backing Matrix Chassis
            pygame.draw.rect(surf, THEME["panel"] if scr["color"] == "hot" else (18, 8, 0), rect)
            pygame.draw.rect(surf, color, rect, 2 if is_hovered else 1)

            # Abstract screen lines inside monitor
            pygame.draw.line(surf, tuple(int(ch * 0.25) for ch in color), (x, y + self.scr_h//2), (x + self.scr_w, y + self.scr_h//2))

            # Cutout shortened text tracking tags to fit screens perfectly
            display_name = scr["name"][:9]
            lbl = self.font_small.render(display_name, True, color)
            surf.blit(lbl, (x + self.scr_w//2 - lbl.get_width()//2, y + self.scr_h//2 - lbl.get_height()//2))

        # Bottom Hints Bar
        footer = self.font_small.render("MOUSE CHOICE SELECT | TAB: GLOBAL SETTINGS", True, THEME["dim"])
        surf.blit(footer, (INTERNAL_W//2 - footer.get_width()//2, INTERNAL_H - 20))

    def run(self):
        while True:
            dt = min(self.clock.tick(FPS) / 1000.0, 0.1)

            # Read mouse position coordinates and translate down to matching canvas scales
            mx, my = pygame.mouse.get_pos()
            rx, ry = mx // SCALE, my // SCALE

            # Reset cursor focus index checks
            if self.state == "HUB_GRID" and not self.options_menu.is_active:
                self.hovered_idx = -1
                for idx in range(len(self.screens_map)):
                    r = idx // self.cols
                    c = idx % self.cols
                    x = self.start_x + c * (self.scr_w + self.gap_x)
                    y = self.start_y + r * (self.scr_h + self.gap_y)
                    if pygame.Rect(x, y, self.scr_w, self.scr_h).collidepoint(rx, ry):
                        self.hovered_idx = idx
                        break

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()

                # Process event logs to global controls before shifting state runs
                if self.options_menu.handle_event(event):
                    continue

                if self.state == "HUB_GRID" and event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if self.hovered_idx != -1:
                        target_scr = self.screens_map[self.hovered_idx]
                        if target_scr["type"] == "VOXEL":
                            self.launch_voxel_engine()
                        else:
                            self.current_game = target_scr["class"](self)
                            self.state = "PLAYING"
                            self.play_sfx("score")

                elif self.state == "PLAYING" and self.current_game:
                    self.current_game.handle_event(event)

            # Render Screen Tree Nodes
            if self.state == "HUB_GRID":
                self.draw_grid_hub(self.virtual_canvas)
            else:
                self.current_game.update(dt)
                self.current_game.draw(self.virtual_canvas)

            if self.options_menu.is_active:
                self.options_menu.draw(self.virtual_canvas)

            pygame.transform.scale(self.virtual_canvas, (WINDOW_W, WINDOW_H), self.screen)
            pygame.display.flip()

if __name__ == "__main__":
    app = ArcadeMegaHub()
    app.run()