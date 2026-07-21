import pygame
import random
import math
import sys
import numpy as np

# --- CONTEXT THEME ---
THEME = {
    "bg": (4, 10, 6),
    "hot": (0, 255, 128),
    "dim": (0, 110, 55),
    "panel": (0, 22, 11),
    "warn": (255, 90, 90),
}

def draw_vrman(surf, cx, cy, radius=6, color=None, rotation=0.0):
    color = color or THEME["hot"]
    cx, cy = int(cx), int(cy)
    pygame.draw.circle(surf, color, (cx, cy), radius)
    pygame.draw.circle(surf, THEME["bg"], (cx, cy), radius, 1)
    rad = math.radians(rotation)
    cos_r, sin_r = math.cos(rad), math.sin(rad)
    v_dx, v_dy = cos_r * (radius - 2), sin_r * (radius - 2)
    pygame.draw.line(surf, (8, 8, 14), (cx - v_dx, cy - v_dy), (cx + v_dx, cy + v_dy), max(3, radius // 2))
    ax, ay = cx + int((radius + 1) * cos_r), cy + int((radius + 1) * sin_r)
    bx, by = cx + int((radius + 7) * cos_r), cy + int((radius + 7) * sin_r)
    pygame.draw.line(surf, color, (ax, ay), (bx, by), 2)

class DigiCrossfireStandalone:
    name = "DIGI CROSSFIRE"

    def __init__(self, screen, font_big, font_small):
        self.screen = screen
        self.font_big = font_big
        self.font_small = font_small
        
        self.in_config = True
        self.game_over = False
        self.cfg_index = 0
        self.score = 0
        
        self.sliders = {
            "RADIUS": [45, 30, 65],
            "DIFFICULTY": [3, 1, 5],
            "SPAWN_RATE": [16, 8, 24]  # divided by 10 dynamically
        }
        self.cfg_order = ["RADIUS", "DIFFICULTY", "SPAWN_RATE"]

        self.grid_x, self.grid_y = 160, 120
        self.pos_index = 0
        self.projectiles = []
        self.enemies = []
        self.spawn_timer = 0.0
        self.lives = 3
        self.message = "CONFIG MATRIX ACTIVE"

    def _start_simulation(self):
        self.in_config = False
        self.game_over = False
        self.score = 0
        self.lives = 3
        self.pos_index = 0
        self.projectiles.clear()
        self.enemies.clear()
        self.spawn_timer = 0.0
        self.message = "WASD/ARROWS: ROTATE   SPACE/F: FIRE BLASTER"

    def handle_event(self, event):
        if self.in_config:
            if event.type != pygame.KEYDOWN: return
            if event.key == pygame.K_ESCAPE:
                pygame.quit()
                sys.exit()
            elif event.key in (pygame.K_UP, pygame.K_w):
                self.cfg_index = (self.cfg_index - 1) % len(self.cfg_order)
            elif event.key in (pygame.K_DOWN, pygame.K_s):
                self.cfg_index = (self.cfg_index + 1) % len(self.cfg_order)
            elif event.key in (pygame.K_LEFT, pygame.K_a):
                key = self.cfg_order[self.cfg_index]
                self.sliders[key][0] = max(self.sliders[key][1], self.sliders[key][0] - (5 if key == "RADIUS" else 1))
            elif event.key in (pygame.K_RIGHT, pygame.K_d):
                key = self.cfg_order[self.cfg_index]
                self.sliders[key][0] = min(self.sliders[key][2], self.sliders[key][0] + (5 if key == "RADIUS" else 1))
            elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                self._start_simulation()
            return

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.in_config = True
                return
            if self.game_over and event.key in (pygame.K_RETURN, pygame.K_SPACE):
                self._start_simulation()
                return
                
            if not self.game_over:
                if event.key in (pygame.K_LEFT, pygame.K_a): self.pos_index = 2
                elif event.key in (pygame.K_RIGHT, pygame.K_d): self.pos_index = 0
                elif event.key in (pygame.K_UP, pygame.K_w): self.pos_index = 3
                elif event.key in (pygame.K_DOWN, pygame.K_s): self.pos_index = 1
                elif event.key in (pygame.K_SPACE, pygame.K_f):
                    angle = self.pos_index * (math.pi / 2)
                    radius = self.sliders["RADIUS"][0]
                    px = self.grid_x + math.cos(angle) * radius
                    py = self.grid_y + math.sin(angle) * radius
                    self.projectiles.append({"x": px, "y": py, "vx": math.cos(angle) * 220.0, "vy": math.sin(angle) * 220.0})

    def update(self, dt):
        if self.in_config or self.game_over: return

        rate = self.sliders["SPAWN_RATE"][0] / 10.0
        diff = self.sliders["DIFFICULTY"][0]
        radius = self.sliders["RADIUS"][0]

        self.spawn_timer += dt
        if self.spawn_timer >= rate:
            self.spawn_timer = 0.0
            side = random.randint(0, 3)
            angle = side * (math.pi / 2)
            ex = self.grid_x + math.cos(angle) * 180.0
            ey = self.grid_y + math.sin(angle) * 180.0
            speed = random.uniform(30.0 + diff * 5, 60.0 + diff * 10)
            self.enemies.append({"x": ex, "y": ey, "vx": -math.cos(angle) * speed, "vy": -math.sin(angle) * speed})

        for p in self.projectiles[:]:
            p["x"] += p["vx"] * dt
            p["y"] += p["vy"] * dt
            if not (0 <= p["x"] <= 320 and 0 <= p["y"] <= 240): self.projectiles.remove(p)

        for e in self.enemies[:]:
            e["x"] += e["vx"] * dt
            e["y"] += e["vy"] * dt
            if (e["x"] - self.grid_x)**2 + (e["y"] - self.grid_y)**2 <= radius**2:
                self.enemies.remove(e)
                self.lives -= 1
                if self.lives <= 0: self.game_over = True
                continue

            for p in self.projectiles[:]:
                if (e["x"] - p["x"])**2 + (e["y"] - p["y"])**2 < 81:
                    if p in self.projectiles: self.projectiles.remove(p)
                    if e in self.enemies: self.enemies.remove(e)
                    self.score += 10
                    break

    def draw(self, surf):
        surf.fill(THEME["bg"])
        radius = self.sliders["RADIUS"][0]

        if self.in_config:
            t_big = self.font_big.render("DIGI CROSSFIRE CONFIG", True, THEME["hot"])
            surf.blit(t_big, (160 - t_big.get_width() // 2, 20))
            for index, key in enumerate(self.cfg_order):
                val = self.sliders[key][0]
                is_sel = index == self.cfg_index
                color = THEME["hot"] if is_sel else THEME["dim"]
                marker = ">> " if is_sel else "   "
                lbl = self.font_small.render(f"{marker}{key:<12} [{val}]", True, color)
                surf.blit(lbl, (50, 80 + index * 25))
            return

        pygame.draw.circle(surf, THEME["dim"], (self.grid_x, self.grid_y), radius, 1)
        pygame.draw.line(surf, THEME["dim"], (self.grid_x - radius - 20, self.grid_y), (self.grid_x + radius + 20, self.grid_y), 1)
        pygame.draw.line(surf, THEME["dim"], (self.grid_x, self.grid_y - radius - 20), (self.grid_x, self.grid_y + radius + 20), 1)

        current_angle = self.pos_index * (math.pi / 2)
        px = self.grid_x + math.cos(current_angle) * radius
        py = self.grid_y + math.sin(current_angle) * radius
        draw_vrman(surf, px, py, radius=6, rotation=math.degrees(current_angle))

        for p in self.projectiles: pygame.draw.circle(surf, THEME["hot"], (int(p["x"]), int(p["y"])), 2)
        for e in self.enemies:
            cx, cy = int(e["x"]), int(e["y"])
            pygame.draw.polygon(surf, THEME["warn"], [(cx, cy - 5), (cx + 5, cy), (cx, cy + 5), (cx - 5, cy)], 1)

        surf.blit(self.font_small.render(f"SCORE: {self.score}", True, THEME["hot"]), (10, 10))
        surf.blit(self.font_small.render(f"SHIELD: {self.lives}", True, THEME["warn"]), (240, 10))
        if self.game_over:
            over = self.font_big.render("GAME OVER", True, THEME["warn"])
            surf.blit(over, (160 - over.get_width() // 2, 100))

if __name__ == '__main__':
    pygame.init()
    window = pygame.display.set_mode((960, 720))
    canvas = pygame.Surface((320, 240))
    clock = pygame.time.Clock()
    f_big = pygame.font.SysFont("monospace", 14, bold=True)
    f_small = pygame.font.SysFont("monospace", 10, bold=True)
    game = DigiCrossfireStandalone(canvas, f_big, f_small)
    while True:
        dt = clock.tick(60) / 1000.0
        for event in pygame.event.get():
            if event.type == pygame.QUIT: pygame.quit(); sys.exit()
            game.handle_event(event)
        game.update(dt)
        game.draw(canvas)
        window.blit(pygame.transform.scale(canvas, (960, 720)), (0, 0))
        pygame.display.flip()