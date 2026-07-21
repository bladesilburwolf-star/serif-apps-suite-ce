import pygame
import random
import math
import sys

# --- CYBERPUNK WINDS MATRIX THEME ---
THEME = {
    "bg": (12, 10, 18),       # Dark neon violet grid floor
    "dim": (140, 0, 140),     # Cyberpunk magenta vector lines
    "hot": (255, 0, 128),     # High-voltage neon pink
    "warn": (0, 255, 240)     # Neon cyan / system data alert
}

class CyberpunkWindsStandalone:
    """Cyberpunk Winds: Tempest Tube-Vector Sandbox."""
    name = "CYBERPUNK WINDS"

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
            "SECTORS": [8, 4, 16],       # Number of edges forming the tube ring
            "DIFFICULTY": [3, 1, 5],      # Enemy projectile density & health
            "SPEED": [3, 1, 5],           # Scaling factor for node approach speed
            "GEOMETRY": [1, 1, 3]         # 1: Perfect Circle, 2: Oval Warp, 3: Hyper-Octagon
        }
        self.cfg_order = ["SECTORS", "DIFFICULTY", "SPEED", "GEOMETRY"]

        # Engine Tracking Variables
        self.stage = 1
        self.lives = 3
        self.projectiles = []
        self.enemies = []
        self.room_title = ""
        self.objective = ""
        
        # Player Mechanics (Angular positioning around the grid track)
        self.player_angle = 0.0          # Angle in radians around the ring
        self.shoot_cooldown = 0.0
        
        self.message = "CONFIG MATRIX ACTIVE"
        self.glitch_flash = 0.
        self.invulnerable = 0.

    def _reset_simulation(self):
        self.player_angle = 0.0
        self.projectiles.clear()
        self.enemies.clear()
        self.shoot_cooldown = 0.0
        self.invulnerable = 1.0

    def _start_simulation(self):
        self.in_config = False
        self.stage = 1
        self.lives = 3
        self.score = 0
        self.message = "MOUSE: ROTATE SHIP   LEFT CLICK: FIRE BLASTER"
        self._generate_procedural_tunnel()

    def _generate_procedural_tunnel(self):
        self._reset_simulation()
        
        diff = self.sliders["DIFFICULTY"][0]
        speed_cfg = self.sliders["SPEED"][0]
        geom_type = self.sliders["GEOMETRY"][0]
        sectors = self.sliders["SECTORS"][0]
        
        prefixes = ["NEO", "CHROME", "CYBER", "VIRTUAL", "SYNTH"]
        suffixes = ["VORTEX", "STORM", "HIGHWAY", "ARRAY", "CHASM"]
        geom_labels = {1: "STANDARD TRACK", 2: "COMPRESSED GRID", 3: "HYPER CYLINDER"}
        
        self.room_title = f"STAGE {self.stage:02d}: {random.choice(prefixes)}-{random.choice(suffixes)}"
        self.objective = f"Clear core node fragments using {sectors}-sided {geom_labels[geom_type]} matrix."

        # Procedurally spawn automated node entities deep within the tunnel core lines
        num_enemies = 4 + (diff * 2)
        for i in range(num_enemies):
            target_sector = random.randint(0, sectors - 1)
            depth = random.uniform(180, 240)  # Spawns far away in perspective 3D depth
            self.enemies.append({
                "sector": target_sector,
                "depth": depth,
                "hp": 1 if diff < 3 else 2,
                "speed": (10.0 + (speed_cfg * 8.0)) # Scales strictly with the new SPEED slider
            })

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
                self.sliders[key][0] = max(self.sliders[key][1], self.sliders[key][0] - 1)
            elif event.key in (pygame.K_RIGHT, pygame.K_d):
                key = self.cfg_order[self.cfg_index]
                self.sliders[key][0] = min(self.sliders[key][2], self.sliders[key][0] + 1)
            elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                self._start_simulation()
            return

        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.in_config = True
            self.message = "MATRIX ROUTINE ABORTED"
            return

        if self.game_over and event.type == pygame.KEYDOWN and event.key in (pygame.K_RETURN, pygame.K_SPACE):
            self.in_config = True
            self.game_over = False
            return

    def update(self, dt):
        if self.in_config or self.game_over: return
        
        sectors = self.sliders["SECTORS"][0]
        speed_cfg = self.sliders["SPEED"][0]
        
        # 1. Mouse Control Angular Mechanics
        mx, my = pygame.mouse.get_pos()
        # Calculate angle relative to the center of the viewport (scaled up coordinates)
        cx, cy = (160 * 3), (115 * 3) 
        self.player_angle = math.atan2(my - cy, mx - cx)
        self.player_angle %= (2 * math.pi)
        
        # 2. Left Click Fire Mechanics
        mouse_buttons = pygame.mouse.get_pressed()
        if self.shoot_cooldown > 0.0:
            self.shoot_cooldown = max(0.0, self.shoot_cooldown - dt)
            
        if mouse_buttons[0] and self.shoot_cooldown == 0.0:
            current_sector = int((self.player_angle / (2 * math.pi)) * sectors) % sectors
            self.projectiles.append({"sector": current_sector, "depth": 15.0, "from_player": True})
            self.shoot_cooldown = 0.15
            self.message = "BLASTER ARRAY INTERFACED"

        # 3. Simulate Projectiles
        for p in self.projectiles[:]:
            if p["from_player"]:
                p["depth"] += 200.0 * dt  
                if p["depth"] > 240: self.projectiles.remove(p)
            else:
                p["depth"] -= (40.0 + (speed_cfg * 10.0)) * dt # Bullet speed scales with slider
                if p["depth"] < 5:
                    if p in self.projectiles: self.projectiles.remove(p)
                    p_sector = int((self.player_angle / (2 * math.pi)) * sectors) % sectors
                    if p["sector"] == p_sector and self.invulnerable <= 0.0:
                        self.lives -= 1
                        self.invulnerable = 1.5
                        self.message = "CRITICAL CHASSIS DAMAGED"
                        if self.lives <= 0:
                            self.game_over = True
                            self.message = "SYSTEM CRASH: DATA DESTROYED"

        # 4. Simulate Cyber-Enemies
        for e in self.enemies[:]:
            e["depth"] -= e["speed"] * dt
            
            if random.random() < 0.010 * self.sliders["DIFFICULTY"][0]:
                self.projectiles.append({"sector": e["sector"], "depth": e["depth"], "from_player": False})
            
            if e["depth"] < 10:
                self.enemies.remove(e)
                p_sector = int((self.player_angle / (2 * math.pi)) * sectors) % sectors
                if e["sector"] == p_sector and self.invulnerable <= 0.0:
                    self.lives -= 1
                    self.invulnerable = 1.5
                    self.message = "NODE IMPACT RECOGNIZED"
                    if self.lives <= 0:
                        self.game_over = True
                        self.message = "GRID RECONSTRUCTION TERMINATED"
            else:
                for p in self.projectiles[:]:
                    if p["from_player"] and p["sector"] == e["sector"] and abs(p["depth"] - e["depth"]) < 12:
                        if p in self.projectiles: self.projectiles.remove(p)
                        e["hp"] -= 1
                        if e["hp"] <= 0:
                            if e in self.enemies: self.enemies.remove(e)
                            self.score += 500
                            self.message = "GRID ANOMALY SHREDDED"

        # 5. Advance Progress Routing
        if not self.enemies and not self.game_over:
            self.stage += 1
            self.glitch_flash = 0.4
            self._generate_procedural_tunnel()
            self.message = f"TUNNEL DEEP SECTOR {self.stage:02d} SECURED"

        self.glitch_flash = max(0, self.glitch_flash - dt)
        self.invulnerable = max(0, self.invulnerable - dt)

    def _get_vector_node(self, sector, depth):
        sectors = self.sliders["SECTORS"][0]
        geom_type = self.sliders["GEOMETRY"][0]
        
        scale = 30.0 / (depth + 1.0)
        cx, cy = 160, 115
        
        angle = (sector / sectors) * (2 * math.pi)
        
        x_mod = 1.4 if geom_type == 2 else 1.0
        y_mod = 0.7 if geom_type == 2 else 1.0
        
        if geom_type == 3: 
            angle = (angle + math.pi / sectors) if sector % 2 == 0 else angle

        rx = math.cos(angle) * 350 * scale * x_mod
        ry = math.sin(angle) * 350 * scale * y_mod
        return int(cx + rx), int(cy + ry)

    def draw(self, surf):
        surf.fill(THEME["bg"] if self.glitch_flash <= 0.0 else THEME["hot"])
        if self.glitch_flash > 0.0: return
        
        sectors = self.sliders["SECTORS"][0]

        # --- DRAW SECTOR 1: OVERLAY MENU CONFIG MATRIX ---
        if self.in_config:
            t_big = self.font_big.render("CYBERPUNK WINDS ENGINE", True, THEME["hot"])
            surf.blit(t_big, (160 - t_big.get_width() // 2, 20))
            t_sm = self.font_small.render("TEMPEST CONTROLLER CALIBRATION", True, THEME["dim"])
            surf.blit(t_sm, (160 - t_sm.get_width() // 2, 42))
            
            geom_modes = {1: "CIRCULAR TUBE", 2: "ELLIPTIC GRID", 3: "WARPED CYLINDER"}
            
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
                
            t_help1 = self.font_small.render("W/S ARROWS: SELECT   A/D: ADJUST   SPACE: LINK", True, THEME["dim"])
            surf.blit(t_help1, (160 - t_help1.get_width() // 2, 195))
            t_help2 = self.font_small.render("ESC: REJECT MATRIX CONTEXT", True, THEME["warn"])
            surf.blit(t_help2, (160 - t_help2.get_width() // 2, 212))
            return

        # --- DRAW SECTOR 2: ACTIVE VECTOR GRAPHICS ENGINE ---
        depth_steps = [15, 45, 90, 150, 220]
        for d in depth_steps:
            ring_pts = [self._get_vector_node(s, d) for s in range(sectors)]
            pygame.draw.polygon(surf, THEME["dim"], ring_pts, 1)

        for s in range(sectors):
            p_near = self._get_vector_node(s, 12)
            p_far = self._get_vector_node(s, 230)
            pygame.draw.line(surf, (45, 0, 55), p_near, p_far, 1)

        # Draw Active Node Projectiles
        for p in self.projectiles:
            px, py = self._get_vector_node(p["sector"], p["depth"])
            color = THEME["hot"] if p["from_player"] else THEME["warn"]
            pygame.draw.circle(surf, color, (px, py), 2 if p["from_player"] else 3, 0)

        # Draw Enemy Core Fragments
        for e in self.enemies:
            ex, ey = self._get_vector_node(e["sector"], e["depth"])
            pygame.draw.polygon(surf, THEME["warn"], [(ex, ey-4), (ex+4, ey), (ex, ey+4), (ex-4, ey)], 1)

        # Draw Player Vector Sprite (Enhanced visibility wedge hull shape)
        p_sec = int((self.player_angle / (2 * math.pi)) * sectors) % sectors
        px, py = self._get_vector_node(p_sec, 13) # Renders right on the outermost edge boundary
        
        if not (self.invulnerable and int(self.invulnerable * 12) % 2):
            # Calculate the structural tangent angle for drawing a clean wedge vector sprite
            tangent = (p_sec / sectors) * (2 * math.pi)
            left_wing = (int(px + math.cos(tangent - 0.25) * 8), int(py + math.sin(tangent - 0.25) * 8))
            right_wing = (int(px + math.cos(tangent + 0.25) * 8), int(py + math.sin(tangent + 0.25) * 8))
            nose_cone = (int(px - math.cos(tangent) * 4), int(py - math.sin(tangent) * 4))
            
            # Render a high-visibility structural triangle hull profile
            pygame.draw.polygon(surf, THEME["hot"], [nose_cone, left_wing, right_wing], 0)
            pygame.draw.polygon(surf, THEME["warn"], [nose_cone, left_wing, right_wing], 1)
            
            # Target line down into the core center grid line
            p_target = self._get_vector_node(p_sec, 40)
            pygame.draw.line(surf, THEME["hot"], (px, py), p_target, 1)

        # UI Diagnostics Bar Render Layer
        title = self.font_big.render("CYBERPUNK WINDS: TERMINAL ACTIVE", True, THEME["hot"])
        surf.blit(title, (160 - title.get_width() // 2, 7))
        surf.blit(self.font_small.render(self.room_title, True, THEME["hot"]), (8, 30))
        surf.blit(self.font_small.render(self.objective, True, THEME["dim"]), (8, 42))
        
        surf.blit(self.font_small.render(f"SHARDS {self.score:05d}   NODES SHIELD: {'I' * self.lives}", True, THEME["hot"]), (8, 224))
        
        if self.message:
            msg = self.font_small.render(self.message, True, THEME["warn"] if "CRITICAL" in self.message or "SYSTEM" in self.message else THEME["hot"])
            surf.blit(msg, (160 - msg.get_width() // 2, 207))

        if self.game_over:
            surf.fill(THEME["bg"])
            g_over1 = self.font_big.render("SIMULATION ABEND TERMINATION", True, THEME["hot"])
            surf.blit(g_over1, (160 - g_over1.get_width() // 2, 90))
            g_over2 = self.font_small.render(f"FINAL SHARD CORRELATION INDEX: {self.score:05d}", True, THEME["dim"])
            surf.blit(g_over2, (160 - g_over2.get_width() // 2, 115))
            g_over3 = self.font_small.render("PRESS ENTER TO RETREAT TO SYSTEM CONFIG TERMINAL", True, THEME["hot"])
            surf.blit(g_over3, (160 - g_over3.get_width() // 2, 160))


# --- ISOLATED EXECUTION ENVIRONMENT BOOTSTRAPPER ---
if __name__ == '__main__':
    pygame.init()
    GAME_W, GAME_H = 320, 240
    SCALE = 3
    window = pygame.display.set_mode((GAME_W * SCALE, GAME_H * SCALE))
    pygame.display.set_caption("Cyberpunk Winds Mouse Control Sandbox")
    
    canvas = pygame.Surface((GAME_W, GAME_H))
    clock = pygame.time.Clock()
    
    f_big = pygame.font.SysFont("monospace", 13, bold=True)
    f_small = pygame.font.SysFont("monospace", 9, bold=True)
    
    game = CyberpunkWindsStandalone(canvas, f_big, f_small)
    
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