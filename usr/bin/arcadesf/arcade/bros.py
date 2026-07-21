import pygame
import random
import math
import sys

# --- HACKER BROS CONTEXT THEME ---
THEME = {
    "bg": (10, 10, 12),       # Dark terminal void
    "dim": (0, 150, 70),      # Matrix terminal green
    "hot": (50, 255, 150),    # Overclocked neon green
    "warn": (255, 0, 80)      # Intrusive firewall red
}

class HackerBrosStandalone:
    """Hacker Bros: Dual-Node Network Infiltration Sandbox."""
    name = "HACKER BROS"

    def __init__(self, screen, font_big, font_small):
        self.screen = screen
        self.font_big = font_big
        self.font_small = font_small
        
        self.in_config = True
        self.game_over = False
        self.cfg_index = 0
        self.score = 0
        
        # Configuration Slider Values [Current, Min, Max]
        self.sliders = {
            "NODES": [2, 1, 4],          # Number of automated firewall nodes
            "DIFFICULTY": [3, 1, 5],     # Data transmission and obstacle speed
            "DECAY": [2, 0, 5],          # Speed at which terminal integrity drops
            "GEOMETRY": [1, 1, 3]        # 1: Symmetric Hub, 2: Bifurcated LAN, 3: Overlapped Stack
        }
        self.cfg_order = ["NODES", "DIFFICULTY", "DECAY", "GEOMETRY"]

        # Engine Tracking Variables
        self.stage = 1
        self.integrity = 100.0
        self.packets = []
        self.firewalls = []
        self.room_title = ""
        self.objective = ""
        
        # Player (Hacker Droplet) Positioning Matrix
        self.x, self.y = 160.0, 200.0
        self.shoot_cooldown = 0.0
        
        self.message = "CONFIG MATRIX ACTIVE"
        self.glitch_flash = 0.

    def _key(self, keys, *codes):
        return any(keys[c] for c in codes)

    def _start_simulation(self):
        self.in_config = False
        self.stage = 1
        self.integrity = 100.0
        self.score = 0
        self.x, self.y = 160.0, 200.0
        self.packets.clear()
        self.message = "WASD/ARROWS: PORT NAV   SPACE: INJECT PACKET"
        self._generate_procedural_network()

    def _generate_procedural_network(self):
        self.packets.clear()
        self.firewalls.clear()
        
        nodes_count = self.sliders["NODES"][0]
        diff = self.sliders["DIFFICULTY"][0]
        geom_type = self.sliders["GEOMETRY"][0]
        
        prefixes = ["RECON", "PROXY", "ROOTKIT", "KERNEL", "SOCKET"]
        suffixes = ["BREACH", "TUNNEL", "SPOOF", "DAEMON", "BYPASS"]
        geom_labels = {1: "SYMMETRIC HUB", 2: "BIFURCATED LAN", 3: "OVERLAPPED STACK"}
        
        self.room_title = f"STAGE {self.stage:02d}: {random.choice(prefixes)}-{random.choice(suffixes)}"
        self.objective = f"Infiltrate {nodes_count} node tracks using {geom_labels[geom_type]} framework."

        # Setup automated firewall tracking defenses
        for i in range(nodes_count):
            if geom_type == 1:
                fx = 60 + (i * (200 // max(1, nodes_count)))
                fy = 60 + (i % 2 * 30)
            elif geom_type == 2:
                fx = 40 if i % 2 == 0 else 260
                fy = 50 + (i * 25)
            else:
                fx = random.randint(50, 250)
                fy = random.randint(50, 120)
                
            self.firewalls.append({
                "x": fx, "y": fy,
                "dir": 1,
                "range": random.randint(40, 90),
                "start_x": fx,
                "speed": 30.0 + (diff * 12.0)
            })
            
        self.message = "NETWORK INTRUSION LINK ESTABLISHED"

    def handle_event(self, event):
        if event.type != pygame.KEYDOWN: return
        
        if self.in_config:
            if event.key == pygame.K_ESCAPE:
                pygame.quit()
                sys.exit()
            elif event.key in (pygame.K_UP, pygame.K_w):
                self.cfg_index = (self.cfg_index - 1) % len(self.cfg_order)
            elif event.key in (pygame.K_DOWN, pygame.K_s):
                self.cfg_index = (self.cfg_index + 1) % len(self.cfg_order)
            elif event.key in (pygame.K_LEFT, pygame.K_a):
                key = self.cfg_order[self.cfg_index]
                self.sliders[key][0] = max(self.sliders[key][1], self.sliders[key][0] - 1)
            elif event.key in (pygame.K_RIGHT, pygame.K_d):
                key = self.cfg_order[self.cfg_index]
                self.sliders[key][0] = min(self.sliders[key][2], self.sliders[key][0] + 1)
            elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                self._start_simulation()
            return

        if event.key == pygame.K_ESCAPE:
            self.in_config = True
            self.message = "DECOMPILE OPERATIONS SUSPENDED"
            return

        if self.game_over and event.key in (pygame.K_RETURN, pygame.K_SPACE):
            self.in_config = True
            self.game_over = False
            return

    def update(self, dt):
        if self.in_config or self.game_over: return
        
        keys = pygame.key.get_pressed()
        diff = self.sliders["DIFFICULTY"][0]
        decay = self.sliders["DECAY"][0]
        
        # 1. Passive Node Terminal Decay Calculus
        self.integrity -= (1.5 + (decay * 0.85)) * dt
        if self.integrity <= 0.0:
            self.integrity = 0.0
            self.game_over = True
            self.message = "CONNECTION TIMEOUT: TRACE DETECTED"
            return

        # 2. Player Movement Vector Processing
        speed = 90.0
        dx = (self._key(keys, pygame.K_RIGHT, pygame.K_d) - self._key(keys, pygame.K_LEFT, pygame.K_a)) * speed * dt
        dy = (self._key(keys, pygame.K_DOWN, pygame.K_s) - self._key(keys, pygame.K_UP, pygame.K_w)) * speed * dt
        
        self.x = max(10, min(310, self.x + dx))
        self.y = max(40, min(230, self.y + dy))

        # 3. Fire Matrix / Input Injection
        if self.shoot_cooldown > 0.0:
            self.shoot_cooldown = max(0.0, self.shoot_cooldown - dt)
            
        if keys[pygame.K_SPACE] and self.shoot_cooldown == 0.0:
            self.packets.append({"x": self.x, "y": self.y - 6, "speed": 160.0})
            self.shoot_cooldown = 0.2
            self.message = "DATA PACKET INJECTED"

        # 4. Simulate Packets
        for p in self.packets[:]:
            p["y"] -= p["speed"] * dt
            if p["y"] < 20:
                if p in self.packets: self.packets.remove(p)
                
        # 5. Simulate Firewall Node Sentry Systems
        for f in self.firewalls:
            f["x"] += f["speed"] * f["dir"] * dt
            if abs(f["x"] - f["start_x"]) > f["range"]:
                f["dir"] *= -1
                f["x"] = f["start_x"] + f["range"] * f["dir"]

            # Collision Check: Player hits a Firewall Node
            if math.hypot(self.x - f["x"], self.y - f["y"]) < 10:
                self.integrity = max(0.0, self.integrity - 25.0 * diff * dt)
                self.message = "WARNING: PACKET LOSS UNDERWAY"
                if self.integrity <= 0.0:
                    self.game_over = True
                    self.message = "SYSTEM TERMINATED BY FIREWALL"

            # Collision Check: Packet destroys a Firewall Node
            for p in self.packets[:]:
                if math.hypot(p["x"] - f["x"], p["y"] - f["y"]) < 8:
                    if p in self.packets: self.packets.remove(p)
                    self.firewalls.remove(f)
                    self.score += 400
                    self.message = "FIREWALL SENTRY TERMINATED"
                    break

        # 6. Check Room Success Routing Completion
        if not self.firewalls and not self.game_over:
            self.stage += 1
            self.integrity = min(100.0, self.integrity + 20.0)
            self.glitch_flash = 0.3
            self._generate_procedural_network()
            self.message = f"NODE SECTOR BREACH SUCCESSFUL"

        self.glitch_flash = max(0, self.glitch_flash - dt)

    def draw(self, surf):
        surf.fill(THEME["bg"] if self.glitch_flash <= 0.0 else THEME["hot"])
        if self.glitch_flash > 0.0: return
        
        # --- DRAW SECTOR 1: OVERLAY MENU CONFIG MATRIX ---
        if self.in_config:
            t_big = self.font_big.render("HACKER BROS OPERATION", True, THEME["hot"])
            surf.blit(t_big, (160 - t_big.get_width() // 2, 20))
            t_sm = self.font_small.render("TUNNEL PROXY EXPLOIT CALIBRATION", True, THEME["dim"])
            surf.blit(t_sm, (160 - t_sm.get_width() // 2, 42))
            
            geom_modes = {1: "SYMMETRIC HUB", 2: "BIFURCATED LAN", 3: "OVERLAPPED STACK"}
            
            for index, key in enumerate(self.cfg_order):
                val, _, _ = self.sliders[key]
                is_sel = index == self.cfg_index
                color = THEME["hot"] if is_sel else THEME["dim"]
                marker = ">> " if is_sel else "   "
                
                if key == "GEOMETRY":
                    display_val = geom_modes[val]
                else:
                    display_val = f"[{'■' * val}{' ' * (self.sliders[key][2] - val)}] ({val})"
                    
                line_str = f"{marker}{key:<12} {display_val}"
                lbl = self.font_small.render(line_str, True, color)
                surf.blit(lbl, (35, 80 + (index * 24)))
                
            t_help1 = self.font_small.render("W/S ARROWS: NAV   A/D: SLIDE   SPACE: COMPILE ROUTINE", True, THEME["dim"])
            surf.blit(t_help1, (160 - t_help1.get_width() // 2, 195))
            t_help2 = self.font_small.render("ESC: DISCONNECT FROM HOST TERMINAL", True, THEME["warn"])
            surf.blit(t_help2, (160 - t_help2.get_width() // 2, 212))
            return

        # --- DRAW SECTOR 2: DATA SYSTEM INFILTRATION SCREEN ---
        # Draw decorative server network traces
        for f in self.firewalls:
            pygame.draw.line(surf, (15, 35, 25), (f["start_x"] - f["range"], f["y"]), (f["start_x"] + f["range"], f["y"]), 1)
            # Render Firewall Threat Boundary Circles
            pygame.draw.circle(surf, THEME["warn"], (int(f["x"]), int(f["y"])), 6, 1)

        # Draw Active Droplet Data Packets
        for p in self.packets:
            pygame.draw.rect(surf, THEME["hot"], (int(p["x"] - 1), int(p["y"] - 3), 2, 6))

        # Draw Player Vector Frame (Data Droplet Cluster)
        px, py = int(self.x), int(self.y)
        pygame.draw.polygon(surf, THEME["hot"], [(px, py - 6), (px + 5, py + 4), (px - 5, py + 4)], 1)
        pygame.draw.circle(surf, THEME["dim"], (px, py + 1), 2, 0)

        # UI Diagnostic Dash Overlay Layer
        title = self.font_big.render("HACKER BROS: ROOT ACCESS STREAM", True, THEME["hot"])
        surf.blit(title, (160 - title.get_width() // 2, 7))
        surf.blit(self.font_small.render(self.room_title, True, THEME["hot"]), (8, 30))
        surf.blit(self.font_small.render(self.objective, True, THEME["dim"]), (8, 42))
        
        # Display Network Link Core Integrity Status Bar
        pygame.draw.rect(surf, (30, 10, 15), (200, 32, 110, 8), 0)
        pygame.draw.rect(surf, THEME["warn"] if self.integrity < 35 else THEME["dim"], (200, 32, int(self.integrity * 1.1), 8), 0)
        pygame.draw.rect(surf, THEME["hot"], (200, 32, 110, 8), 1)
        
        surf.blit(self.font_small.render(f"INDEX {self.score:06d}   INTEGRITY: {int(self.integrity)}%", True, THEME["hot"]), (8, 224))
        
        if self.message:
            msg = self.font_small.render(self.message, True, THEME["warn"] if "WARNING" in self.message or "TIMEOUT" in self.message or "TERMINATED" in self.message else THEME["hot"])
            surf.blit(msg, (160 - msg.get_width() // 2, 207))

        if self.game_over:
            surf.fill(THEME["bg"])
            g_over1 = self.font_big.render("CONNECTION CLOSED: ROOT DROPPED", True, THEME["warn"])
            surf.blit(g_over1, (160 - g_over1.get_width() // 2, 90))
            g_over2 = self.font_small.render(f"TOTAL EXPLOITS COMPILED METRIC: {self.score:05d}", True, THEME["dim"])
            surf.blit(g_over2, (160 - g_over2.get_width() // 2, 115))
            g_over3 = self.font_small.render("PRESS ENTER TO RETREAT TO SYSTEM CONFIG TERMINAL", True, THEME["hot"])
            surf.blit(g_over3, (160 - g_over3.get_width() // 2, 160))


# --- ISOLATED EXECUTION ENVIRONMENT BOOTSTRAPPER ---
if __name__ == '__main__':
    pygame.init()
    GAME_W, GAME_H = 320, 240
    SCALE = 3
    window = pygame.display.set_mode((GAME_W * SCALE, GAME_H * SCALE))
    pygame.display.set_caption("Hacker Bros Connection Sandbox")
    
    canvas = pygame.Surface((GAME_W, GAME_H))
    clock = pygame.time.Clock()
    
    f_big = pygame.font.SysFont("monospace", 13, bold=True)
    f_small = pygame.font.SysFont("monospace", 9, bold=True)
    
    game = HackerBrosStandalone(canvas, f_big, f_small)
    
    while True:
        dt = clock.tick(60) / 1000.0
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            game.handle_event(event)
            
        game.update(dt)
        game.draw(canvas)
        
        scaled_surf = pygame.transform.scale(canvas, (GAME_W * SCALE, GAME_H * SCALE))
        window.blit(scaled_surf, (0, 0))
        pygame.display.flip()