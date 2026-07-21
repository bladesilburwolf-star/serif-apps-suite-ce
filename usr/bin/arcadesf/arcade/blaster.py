import pygame
import random
import math
import sys
import numpy as np

THEME = {"bg": (4, 10, 6), "hot": (0, 255, 128), "dim": (0, 110, 55), "warn": (255, 90, 90)}

class PhysicsBlasterStandalone:
    def __init__(self, screen, font_big, font_small):
        self.screen, self.font_big, self.font_small = screen, font_big, font_small
        self.in_config, self.game_over, self.cfg_index = True, False, 0
        self.sliders = {"GRAVITY": [70, 30, 150], "SPAWN_RATE": [22, 10, 40], "BOUNCE": [90, 50, 100]}
        self.cfg_order = ["GRAVITY", "SPAWN_RATE", "BOUNCE"]
        self.px, self.py, self.pw = 160.0, 228.0, 14
        self.projectiles, self.spheres = [], []
        self.spawn_timer, self.score, self.lives = 0.0, 0, 3

    def _start_game(self):
        self.in_config = False
        self.game_over = False
        self.score, self.lives = 0, 3
        self.projectiles.clear()
        self.spheres.clear()
        self.spawn_timer = 0.0

    def handle_event(self, event):
        if self.in_config:
            if event.type != pygame.KEYDOWN: return
            if event.key == pygame.K_UP: self.cfg_index = (self.cfg_index - 1) % len(self.cfg_order)
            elif event.key == pygame.K_DOWN: self.cfg_index = (self.cfg_index + 1) % len(self.cfg_order)
            elif event.key == pygame.K_LEFT: self.sliders[self.cfg_order[self.cfg_index]][0] -= 5
            elif event.key == pygame.K_RIGHT: self.sliders[self.cfg_order[self.cfg_index]][0] += 5
            elif event.key in (pygame.K_RETURN, pygame.K_SPACE): self._start_game()
            return
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE: self.in_config = True
            elif event.key in (pygame.K_SPACE, pygame.K_f) and not self.game_over:
                for a in [-0.2, 0.0, 0.2]:
                    self.projectiles.append({"x": self.px, "y": self.py - 6, "vx": math.sin(a) * 160.0, "vy": -math.cos(a) * 160.0, "radius": 2})
            elif self.game_over and event.key in (pygame.K_RETURN, pygame.K_SPACE): self._start_game()

    def update(self, dt):
        if self.in_config or self.game_over: return
        keys = pygame.key.get_pressed()
        move = 130.0 * dt
        if keys[pygame.K_LEFT] or keys[pygame.K_a]: self.px -= move
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]: self.px += move
        self.px = max(self.pw, min(320 - self.pw, self.px))

        gravity = self.sliders["GRAVITY"][0]
        rate = self.sliders["SPAWN_RATE"][0] / 10.0
        bounce_f = self.sliders["BOUNCE"][0] / 100.0

        self.spawn_timer += dt
        if self.spawn_timer >= rate:
            self.spawn_timer = 0.0
            self.spheres.append({"x": random.uniform(20, 300), "y": 10, "vx": random.uniform(-30, 30), "vy": 0.0, "radius": random.choice([10, 14, 18]), "hp": 3})

        for s in self.spheres[:]:
            s["vy"] += gravity * dt
            s["x"] += s["vx"] * dt
            s["y"] += s["vy"] * dt
            if s["x"] - s["radius"] < 0: s["x"] = s["radius"]; s["vx"] *= -1
            elif s["x"] + s["radius"] > 320: s["x"] = 320 - s["radius"]; s["vx"] *= -1
            if s["y"] + s["radius"] > 240: s["y"] = 240 - s["radius"]; s["vy"] = -abs(s["vy"]) * bounce_f

            if (s["x"] - self.px)**2 + (s["y"] - self.py)**2 < (s["radius"] + 8)**2:
                self.spheres.remove(s)
                self.lives -= 1
                if self.lives <= 0: self.game_over = True

        for p in self.projectiles[:]:
            p["x"] += p["vx"] * dt
            p["y"] += p["vy"] * dt
            if p["y"] < 0 or not (0 <= p["x"] <= 320):
                if p in self.projectiles: self.projectiles.remove(p)
                continue
            for s in self.spheres[:]:
                dx, dy = s["x"] - p["x"], s["y"] - p["y"]
                dist = math.hypot(dx, dy)
                if dist < (s["radius"] + p["radius"]):
                    norm = np.array([dx / dist, dy / dist])
                    p_vel = np.array([p["vx"], p["vy"]])
                    bounce = p_vel - 2 * np.dot(p_vel, norm) * norm
                    s["vx"] += norm[0] * 35.0
                    s["vy"] += norm[1] * 25.0
                    s["hp"] -= 1
                    self.score += 5
                    if p in self.projectiles: self.projectiles.remove(p)
                    if s["hp"] <= 0: self.spheres.remove(s); self.score += 25
                    break

    def draw(self, surf):
        surf.fill(THEME["bg"])
        if self.in_config:
            for index, key in enumerate(self.cfg_order):
                color = THEME["hot"] if index == self.cfg_index else THEME["dim"]
                surf.blit(self.font_small.render(f">> {key}: {self.sliders[key][0]}", True, color), (50, 80 + index * 25))
            return
        for s in self.spheres:
            pygame.draw.circle(surf, THEME["dim"], (int(s["x"]), int(s["y"])), s["radius"], 1)
            for h in range(s["hp"]):
                a = h * (math.pi * 2 / 3)
                pygame.draw.circle(surf, THEME["warn"], (int(s["x"] + math.cos(a)*(s["radius"]-4)), int(s["y"] + math.sin(a)*(s["radius"]-4))), 2)
        pygame.draw.circle(surf, THEME["hot"], (int(self.px), int(self.py)), 7)
        for p in self.projectiles: pygame.draw.circle(surf, THEME["hot"], (int(p["x"]), int(p["y"])), p["radius"])
        surf.blit(self.font_small.render(f"SCORE: {self.score}", True, THEME["hot"]), (10, 10))
        if self.game_over: surf.blit(self.font_big.render("CORE MELTDOWN", True, THEME["warn"]), (80, 100))

if __name__ == '__main__':
    pygame.init()
    window = pygame.display.set_mode((960, 720))
    canvas = pygame.Surface((320, 240))
    clock = pygame.time.Clock()
    game = PhysicsBlasterStandalone(canvas, pygame.font.SysFont("monospace", 14, True), pygame.font.SysFont("monospace", 10, True))
    while True:
        dt = clock.tick(60) / 1000.0
        for event in pygame.event.get():
            if event.type == pygame.QUIT: pygame.quit(); sys.exit()
            game.handle_event(event)
        game.update(dt)
        game.draw(canvas)
        window.blit(pygame.transform.scale(canvas, (960, 720)), (0, 0))
        pygame.display.flip()