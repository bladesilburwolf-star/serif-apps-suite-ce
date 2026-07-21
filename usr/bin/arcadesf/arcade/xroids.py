import pygame
import random
import math
import sys

THEME = {"bg": (4, 10, 6), "hot": (0, 255, 128), "dim": (0, 110, 55), "warn": (255, 90, 90)}

def draw_vrman(surf, cx, cy, radius=6, rotation=0.0):
    cx, cy = int(cx), int(cy)
    pygame.draw.circle(surf, THEME["hot"], (cx, cy), radius)
    rad = math.radians(rotation)
    pygame.draw.line(surf, (8, 8, 14), (cx - math.cos(rad)*radius, cy - math.sin(rad)*radius), (cx + math.cos(rad)*radius, cy + math.sin(rad)*radius), 2)

class XroidsStandalone:
    def __init__(self, screen, font_big, font_small):
        self.screen, self.font_big, self.font_small = screen, font_big, font_small
        self.in_config, self.game_over, self.cfg_index = True, False, 0
        self.sliders = {"ASTEROIDS": [4, 2, 8], "SPEED": [3, 1, 5], "FRICTION": [99, 90, 100]}
        self.cfg_order = ["ASTEROIDS", "SPEED", "FRICTION"]
        self.px, self.py = 160.0, 120.0
        self.vx, self.vy, self.angle = 0.0, 0.0, 0.0
        self.bullets, self.asteroids = [], []
        self.invuln_timer = 1.5
        self.score, self.lives = 0, 3

    def _start_game(self):
        self.in_config = False
        self.game_over = False
        self.score, self.lives = 0, 3
        self.px, self.py = 160.0, 120.0
        self.vx, self.vy = 0.0, 0.0
        self.bullets.clear()
        self.asteroids.clear()
        for _ in range(self.sliders["ASTEROIDS"][0]): self.spawn_asteroid(size=3)

    def spawn_asteroid(self, size=3, x=None, y=None):
        if x is None:
            x = random.uniform(0, 320)
            y = random.uniform(0, 240)
        speed = random.uniform(15.0, 35.0) * (self.sliders["SPEED"][0] * 0.4)
        ang = random.uniform(0, math.pi * 2)
        radius = size * 5
        self.asteroids.append({
            "x": x, "y": y, "vx": math.cos(ang) * speed, "vy": math.sin(ang) * speed,
            "size": size, "radius": radius, "num_pts": random.randint(5, 8),
            "pts_offset": [random.uniform(radius * 0.7, radius * 1.3) for _ in range(8)]
        })

    def handle_event(self, event):
        if self.in_config:
            if event.type != pygame.KEYDOWN: return
            if event.key == pygame.K_UP: self.cfg_index = (self.cfg_index - 1) % len(self.cfg_order)
            elif event.key == pygame.K_DOWN: self.cfg_index = (self.cfg_index + 1) % len(self.cfg_order)
            elif event.key == pygame.K_LEFT: self.sliders[self.cfg_order[self.cfg_index]][0] -= 1
            elif event.key == pygame.K_RIGHT: self.sliders[self.cfg_order[self.cfg_index]][0] += 1
            elif event.key in (pygame.K_RETURN, pygame.K_SPACE): self._start_game()
            return
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE: self.in_config = True
            elif event.key in (pygame.K_SPACE, pygame.K_f) and not self.game_over:
                rad = math.radians(self.angle)
                self.bullets.append({"x": self.px + math.cos(rad)*8, "y": self.py + math.sin(rad)*8, "vx": math.cos(rad)*200.0 + self.vx, "vy": math.sin(rad)*200.0 + self.vy, "life": 1.2})
            elif self.game_over and event.key in (pygame.K_RETURN, pygame.K_SPACE): self._start_game()

    def update(self, dt):
        if self.in_config or self.game_over: return
        keys = pygame.key.get_pressed()
        if keys[pygame.K_LEFT] or keys[pygame.K_a]: self.angle -= 180.0 * dt
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]: self.angle += 180.0 * dt
        if keys[pygame.K_UP] or keys[pygame.K_w]:
            rad = math.radians(self.angle)
            self.vx += math.cos(rad) * 110.0 * dt
            self.vy += math.sin(rad) * 110.0 * dt
        
        fric = self.sliders["FRICTION"][0] / 100.0
        self.vx *= fric
        self.vy *= fric
        self.px = (self.px + self.vx * dt) % 320
        self.py = (self.py + self.vy * dt) % 240
        if self.invuln_timer > 0.0: self.invuln_timer -= dt

        for b in self.bullets[:]:
            b["x"] = (b["x"] + b["vx"] * dt) % 320
            b["y"] = (b["y"] + b["vy"] * dt) % 240
            b["life"] -= dt
            if b["life"] <= 0: self.bullets.remove(b)

        for a in self.asteroids[:]:
            a["x"] = (a["x"] + a["vx"] * dt) % 320
            a["y"] = (a["y"] + a["vy"] * dt) % 240
            for b in self.bullets[:]:
                if (a["x"] - b["x"])**2 + (a["y"] - b["y"])**2 < (a["radius"] + 2)**2:
                    if b in self.bullets: self.bullets.remove(b)
                    self.score += (4 - a["size"]) * 20
                    if a["size"] > 1:
                        self.spawn_asteroid(a["size"] - 1, a["x"], a["y"])
                        self.spawn_asteroid(a["size"] - 1, a["x"], a["y"])
                    if a in self.asteroids: self.asteroids.remove(a)
                    break

        if self.invuln_timer <= 0.0:
            for a in self.asteroids:
                if (a["x"] - self.px)**2 + (a["y"] - self.py)**2 < (a["radius"] + 6)**2:
                    self.lives -= 1
                    if self.lives <= 0: self.game_over = True
                    else: self.px, self.py = 160, 120; self.vx, self.vy = 0, 0; self.invuln_timer = 1.5
                    break

    def draw(self, surf):
        surf.fill(THEME["bg"])
        if self.in_config:
            for index, key in enumerate(self.cfg_order):
                color = THEME["hot"] if index == self.cfg_index else THEME["dim"]
                surf.blit(self.font_small.render(f">> {key}: {self.sliders[key][0]}", True, color), (50, 80 + index * 25))
            return
        for a in self.asteroids:
            pts = []
            for j in range(a["num_pts"]):
                theta = j * (2 * math.pi / a["num_pts"])
                pts.append((int(a["x"] + math.cos(theta) * a["pts_offset"][j]), int(a["y"] + math.sin(theta) * a["pts_offset"][j])))
            pygame.draw.polygon(surf, THEME["dim"], pts, 1)
        for b in self.bullets: pygame.draw.circle(surf, THEME["hot"], (int(b["x"]), int(b["y"])), 1)
        if self.invuln_timer <= 0.0 or int(self.invuln_timer * 10) % 2 == 0: draw_vrman(surf, self.px, self.py, radius=6, rotation=self.angle)
        surf.blit(self.font_small.render(f"SCORE: {self.score}", True, THEME["hot"]), (10, 10))
        if self.game_over: surf.blit(self.font_big.render("DESTROYED", True, THEME["warn"]), (100, 100))

if __name__ == '__main__':
    pygame.init()
    window = pygame.display.set_mode((960, 720))
    canvas = pygame.Surface((320, 240))
    clock = pygame.time.Clock()
    game = XroidsStandalone(canvas, pygame.font.SysFont("monospace", 14, True), pygame.font.SysFont("monospace", 10, True))
    while True:
        dt = clock.tick(60) / 1000.0
        for event in pygame.event.get():
            if event.type == pygame.QUIT: pygame.quit(); sys.exit()
            game.handle_event(event)
        game.update(dt)
        game.draw(canvas)
        window.blit(pygame.transform.scale(canvas, (960, 720)), (0, 0))
        pygame.display.flip()