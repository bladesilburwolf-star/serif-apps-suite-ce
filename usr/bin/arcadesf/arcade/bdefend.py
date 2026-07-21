import pygame
import random
import sys

THEME = {"bg": (4, 10, 6), "hot": (0, 255, 128), "dim": (0, 110, 55), "warn": (255, 90, 90)}

class BitDefenderStandalone:
    def __init__(self, screen, font_big, font_small):
        self.screen, self.font_big, self.font_small = screen, font_big, font_small
        self.in_config, self.game_over, self.cfg_index = True, False, 0
        self.sliders = {"ALIENS": [5, 3, 8], "SPEED": [3, 1, 5]}
        self.cfg_order = ["ALIENS", "SPEED"]
        self.px, self.py, self.player_vy = 40.0, 120.0, 0.0
        self.lasers, self.aliens, self.datanodes = [], [], []
        self.spawn_timer, self.score, self.lives = 0.0, 0, 3

    def _start_game(self):
        self.in_config, self.game_over = False, False
        self.score, self.lives = 0, 3
        self.py, self.player_vy = 120.0, 0.0
        self.lasers.clear(); self.aliens.clear(); self.datanodes.clear()
        for i in range(self.sliders["ALIENS"][0]):
            self.datanodes.append({"x": 40 + i * 35, "y": 228, "held": False, "kidnapper": None})

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
                self.lasers.append({"x": self.px + 10, "y": self.py, "vx": 210.0})
            elif self.game_over and event.key in (pygame.K_RETURN, pygame.K_SPACE): self._start_game()

    def update(self, dt):
        if self.in_config or self.game_over: return
        keys = pygame.key.get_pressed()
        if keys[pygame.K_UP] or keys[pygame.K_w]: self.player_vy = -120.0
        elif keys[pygame.K_DOWN] or keys[pygame.K_s]: self.player_vy = 120.0
        else: self.player_vy *= 0.85
        self.py = max(10, min(216, self.py + self.player_vy * dt))

        self.spawn_timer += dt
        if self.spawn_timer >= 2.0:
            self.spawn_timer = 0.0
            free = [n for n in self.datanodes if not n["held"]]
            tx = random.choice(free)["x"] if free else random.uniform(40, 280)
            self.aliens.append({"x": random.uniform(180, 310), "y": 15, "tx": tx, "vy": 25.0 * self.sliders["SPEED"][0], "state": "DESCEND", "target_node": None})

        for l in self.lasers[:]:
            l["x"] += l["vx"] * dt
            if l["x"] > 320: self.lasers.remove(l)

        for a in self.aliens[:]:
            if a["state"] == "DESCEND":
                a["x"] += ((a["tx"] - a["x"]) * 1.5) * dt
                a["y"] += a["vy"] * dt
                for n in self.datanodes:
                    if not n["held"] and abs(n["x"] - a["x"]) < 10 and abs(n["y"] - a["y"]) < 10:
                        a["state"] = "ABDUCT"; a["target_node"] = n; n["held"] = True; n["kidnapper"] = a; break
            elif a["state"] == "ABDUCT":
                a["y"] -= 25.0 * dt
                if a["target_node"]: a["target_node"]["y"] = a["y"] + 6
                if a["y"] <= 12:
                    if a["target_node"] in self.datanodes: self.datanodes.remove(a["target_node"])
                    self.aliens.remove(a); self.lives -= 1
                    if self.lives <= 0 or not self.datanodes: self.game_over = True
                    continue

            for l in self.lasers[:]:
                if (a["x"] - l["x"])**2 + (a["y"] - l["y"])**2 < 100:
                    self.lasers.remove(l); self.score += 50
                    if a["state"] == "ABDUCT" and a["target_node"]: a["target_node"]["held"] = False; a["target_node"]["kidnapper"] = None
                    self.aliens.remove(a); break

    def draw(self, surf):
        surf.fill(THEME["bg"])
        if self.in_config:
            for index, key in enumerate(self.cfg_order):
                color = THEME["hot"] if index == self.cfg_index else THEME["dim"]
                surf.blit(self.font_small.render(f">> {key}: {self.sliders[key][0]}", True, color), (50, 80 + index * 25))
            return
        pygame.draw.line(surf, THEME["dim"], (0, 232), (320, 232), 1)
        for n in self.datanodes: pygame.draw.rect(surf, THEME["hot"] if not n["held"] else THEME["warn"], (int(n["x"]-3), int(n["y"]-3), 6, 6), 1)
        for a in self.aliens: pygame.draw.polygon(surf, THEME["warn"], [(int(a["x"]), int(a["y"]-4)), (int(a["x"]+6), int(a["y"])), (int(a["x"]), int(a["y"]+4)), (int(a["x"]-6), int(a["y"]))], 1)
        pygame.draw.circle(surf, THEME["hot"], (int(self.px), int(self.py)), 6)
        for l in self.lasers: pygame.draw.line(surf, THEME["hot"], (int(l["x"]), int(l["y"])), (int(l["x"]+6), int(l["y"])), 2)
        if self.game_over: surf.blit(self.font_big.render("NETWORK OVERRUN", True, THEME["warn"]), (60, 100))

if __name__ == '__main__':
    pygame.init()
    window = pygame.display.set_mode((960, 720))
    canvas = pygame.Surface((320, 240))
    clock = pygame.time.Clock()
    game = BitDefenderStandalone(canvas, pygame.font.SysFont("monospace", 14, True), pygame.font.SysFont("monospace", 10, True))
    while True:
        dt = clock.tick(60) / 1000.0
        for event in pygame.event.get():
            if event.type == pygame.QUIT: pygame.quit(); sys.exit()
            game.handle_event(event)
        game.update(dt)
        game.draw(canvas)
        window.blit(pygame.transform.scale(canvas, (960, 720)), (0, 0))
        pygame.display.flip()