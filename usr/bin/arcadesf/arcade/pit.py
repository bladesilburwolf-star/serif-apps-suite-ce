import pygame
import random
import math
import sys

# --- STANDALONE CONTEXT THEME ---
THEME = {
    "bg": (10, 15, 12),       # Deep matrix slate
    "dim": (0, 120, 50),      # Classic terminal green
    "hot": (0, 255, 100),     # Bright neon green vector
    "warn": (255, 60, 60)     # Alert red
}

class CyberiaPitStandalone:
    """Ghostline Run: Isolated Debug & Calibration Module."""
    name = "CYBERIA PIT"

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
            "STAGES": [5, 1, 20],
            "DIFFICULTY": [2, 1, 5],
            "TRAPS": [2, 0, 5],
            "GEOMETRY": [1, 1, 3] # 1: Balanced, 2: Linear/Narrow, 3: Cluster/Chaos
        }
        self.cfg_order = ["STAGES", "DIFFICULTY", "TRAPS", "GEOMETRY"]

        # Engine Tracking Variables
        self.stage = 1
        self.deaths = 0
        self.collected = set()
        self.shards_in_room = []
        self.platforms = []
        self.pits = []
        self.room_title = ""
        self.objective = ""
        
        # Extended Player Movement Physics Matrix
        self.x, self.z, self.h, self.vy = 8., 20., 0., 0.
        self.jump_count = 0        # Tracks 1st, 2nd, 3rd, and 4th jump triggers
        self.fly_timer = 0.0       # Counts down from 10.0 seconds when fly mode is active
        
        self.message = "CONFIG MATRIX ACTIVE"
        self.portal_flash = 0.
        self.invulnerable = 0.

    def _key(self, keys, *codes):
        """Helper to check multiple mapped key inputs."""
        return any(keys[c] for c in codes)

    def _ground(self, x, z):
        for px, pz, w, d in self.platforms:
            if px <= x <= px + w and pz <= z <= pz + d:
                return True
        return False

    def _reset_room(self, message):
        self.x, self.z, self.h, self.vy = 8., 20., 0., 0.
        self.jump_count = 0
        self.fly_timer = 0.0
        self.message = message
        self.invulnerable = 1.0

    def _start_simulation(self):
        self.in_config = False
        self.stage = 1
        self.deaths = 0
        self.score = 0
        self.message = "MOVE: ARROWS/WASD   JUMP: SPACE"
        self._generate_procedural_room()

    def _generate_procedural_room(self):
        self.platforms = [(0, 0, 18, 40)] 
        self.pits = []
        self.shards_in_room = []
        self.collected.clear()

        diff = self.sliders["DIFFICULTY"][0]
        trap_intensity = self.sliders["TRAPS"][0]
        geom_type = self.sliders["GEOMETRY"][0]

        end_w = max(10, 24 - (diff * 2))
        end_x = 100 - end_w
        self.platforms.append((end_x, 0, end_w, 40))
        
        mid_start = 18
        mid_end = end_x
        mid_width = mid_end - mid_start

        if geom_type == 1:
            archetypes = [1, 2, 3, 6, 9, 13, 16, 17]
        elif geom_type == 2:
            archetypes = [7, 10, 11, 12, 13, 14]
        else:
            archetypes = [4, 5, 8, 15, 18]

        archetype = random.choice(archetypes)
        gap_mod = diff * 2 

        if archetype == 1:
            self.room_title = "FRACTURED BRIDGE"
            self.objective = "Cross staggered steps over the matrix gap."
            step1_w = max(10, random.randint(14, 18) - diff)
            step2_w = max(10, random.randint(14, 18) - diff)
            self.platforms.append((mid_start + 3, random.randint(0, 12), step1_w, 20))
            self.platforms.append((mid_start + 5 + step1_w + gap_mod, random.randint(15, 25), step2_w, 15))
            self.shards_in_room.append((mid_start + 3 + step1_w // 2, 10))
            self.shards_in_room.append((mid_start + 5 + step1_w + gap_mod + step2_w // 2, 20))
            
        elif archetype == 2:
            self.room_title = "PRISM SPLIT"
            self.objective = "Two parallel tracks. Higher risk paths layout."
            p_w = max(15, mid_width - gap_mod)
            self.platforms.append((mid_start + 2, 4, p_w, max(6, 12 - diff)))
            self.platforms.append((mid_start + 2, 26, p_w, max(6, 12 - diff)))
            self.shards_in_room.append((mid_start + 2 + p_w // 2, 8))
            self.shards_in_room.append((mid_start + 2 + p_w // 2, 30))
            
        elif archetype == 3:
            self.room_title = "SERVER COLUMN"
            self.objective = "Leap across isolated computer server pylons."
            num_pylons = random.randint(3, 4)
            p_w = max(7, 12 - diff)
            spacing = (mid_width - (num_pylons * p_w)) // (num_pylons + 1)
            for i in range(num_pylons):
                px = mid_start + spacing + i * (p_w + spacing)
                pz = random.randint(4, 24)
                self.platforms.append((px, pz, p_w, 14))
                if i % 2 == 0: self.shards_in_room.append((px + p_w // 2, pz + 7))

        elif archetype == 4:
            self.room_title = "BLACK-ICE CHASM"
            self.objective = "A massive gap leap. Gather forward momentum."
            island_w = max(12, random.randint(20, 28) - (diff * 2))
            island_x = mid_start + random.randint(4, max(5, mid_width - island_w - 4))
            self.platforms.append((island_x, 6, island_w, 28))
            self.shards_in_room.append((island_x + island_w // 2, 20))

        elif archetype == 5:
            self.room_title = "ZIG-ZAG ARRAY"
            self.objective = "Alternate left and right vectors to advance."
            step_w = max(8, 16 - diff)
            self.platforms.append((mid_start + 2, 2, step_w, 18))
            self.platforms.append((mid_start + 2 + step_w + gap_mod, 20, step_w, 18))
            self.platforms.append((mid_start + 2 + (step_w * 2) + (gap_mod * 2), 2, step_w, 18))
            self.shards_in_room.append((mid_start + 2 + step_w // 2, 10))
            self.shards_in_room.append((mid_start + 2 + (step_w * 2) + (gap_mod * 2) + step_w // 2, 10))

        elif archetype == 6:
            self.room_title = "DATA GRID LOCK"
            self.objective = "Dodge the localized warning barriers."
            self.platforms.append((mid_start, 0, mid_width, 40))

        elif archetype == 7:
            self.room_title = "THE LONG CORRIDOR"
            self.objective = "Extremely narrow pathway framework."
            c_d = max(4, 10 - diff)
            self.platforms.append((mid_start, 20 - c_d // 2, mid_width, c_d))
            self.shards_in_room.append((mid_start + mid_width // 2, 20))

        elif archetype == 8:
            self.room_title = "QUANTUM ARCHIPELAGO"
            self.objective = "Tiny matrix node units require precision micro-steps."
            node_size = max(5, 8 - diff)
            for i in range(4):
                px = mid_start + 4 + (i * (node_size + gap_mod))
                pz = random.randint(6, 30)
                self.platforms.append((px, pz, node_size, node_size))
                if i % 2 == 1: self.shards_in_room.append((px + node_size // 2, pz + node_size // 2))

        elif archetype == 9:
            self.room_title = "STAIRCASE PROTOCOL"
            self.objective = "Climb the expanding horizontal matrix stacks."
            self.platforms.append((mid_start + 2, 4, 12, 32))
            self.platforms.append((mid_start + 16, 10, 12, 20))
            self.shards_in_room.append((mid_start + 22, 20))

        elif archetype == 10:
            self.room_title = "THE DEEP VOID"
            self.objective = "Minimal edge bounds execution target."
            self.platforms.append((mid_start + 4, 12, max(8, 14 - diff), 16))
            self.shards_in_room.append((mid_start + 4, 20))

        elif archetype == 11:
            self.room_title = "CROSS COMPILER"
            self.objective = "Intersecting path architecture vectors."
            self.platforms.append((mid_start, 16, mid_width // 2 + 3, 8))
            self.platforms.append((mid_start + mid_width // 2 - 3, 6, mid_width // 2 + 5, 8))
            self.shards_in_room.append((mid_start + mid_width // 2, 20))

        elif archetype == 12:
            self.room_title = "PERIPHERAL FIELDS"
            self.objective = "Stick to the absolute outer perimeter bounds."
            thick = max(4, 10 - diff)
            self.platforms.append((mid_start, 0, mid_width, thick))
            self.platforms.append((mid_start, 40 - thick, mid_width, thick))
            self.shards_in_room.append((mid_start + mid_width // 2, thick // 2))

        elif archetype == 13:
            self.room_title = "PIPELINE INSPECTION"
            self.objective = "Travel down the thick central server trunk line."
            self.platforms.append((mid_start, 12, mid_width, 16))

        elif archetype == 14:
            self.room_title = "DIAGONAL SCANLINE"
            self.objective = "Angle your jumps across offset square blocks."
            b_s = max(6, 10 - diff)
            for i in range(3):
                self.platforms.append((mid_start + 4 + (i * (b_s + gap_mod)), 4 + (i * 10), b_s, b_s))
                self.shards_in_room.append((mid_start + 4 + (i * (b_s + gap_mod)) + 2, 4 + (i * 10) + 2))

        elif archetype == 15:
            self.room_title = "BUFFER OVERFLOW"
            self.objective = "Tons of structural debris fragments."
            for i in range(4):
                rx = mid_start + (i * 12) + random.randint(0, 4)
                rz = random.randint(4, 32)
                self.platforms.append((rx, rz, 6, 6))
                if i == 2: self.shards_in_room.append((rx + 3, rz + 3))

        elif archetype == 16:
            self.room_title = "CORE VENT"
            self.objective = "Navigate the scanning systems safely."
            self.platforms.append((mid_start, 0, mid_width, 40))

        elif archetype == 17:
            self.room_title = "THE STEADY RISE"
            self.objective = "Each structural tracking block scales downward."
            self.platforms.append((mid_start + 2, 4, 16, 32))
            self.platforms.append((mid_start + 22, 12, 14, 16))
            self.shards_in_room.append((mid_start + 29, 20))

        else:
            self.room_title = "ANOMALY SECTOR"
            self.objective = "Maximum randomized variable matrix parameters."
            self.platforms.append((mid_start + 4, random.randint(2, 10), 14, 14))
            self.platforms.append((mid_start + 22, random.randint(16, 26), 14, 14))
            self.shards_in_room.append((mid_start + 11, 20))

        if trap_intensity > 0:
            trap_w = 6 + diff
            for i in range(min(3, trap_intensity)):
                tx = mid_start + random.randint(4, max(5, mid_width - trap_w - 4))
                tz = random.randint(2, 28)
                if tx + trap_w < end_x:
                    self.pits.append((tx, tz, trap_w, 8))

        if not self.shards_in_room:
            self.shards_in_room.append((mid_start + mid_width // 2, 20))

        self.room_title = f"STAGE {self.stage:02d}: {self.room_title}"

    def handle_event(self, event):
        if event.type != pygame.KEYDOWN: return
        
        if self.in_config:
            if event.key in (pygame.K_ESCAPE,):
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
            self.message = "CONFIG MATRIX RETURNED"
            return

        if self.game_over and event.key in (pygame.K_RETURN, pygame.K_SPACE):
            self.in_config = True
            self.game_over = False
            return

        # --- MULTI-JUMP & OVERDRIVE FLY ENTRY TRRIGERS ---
        if not self.game_over and event.key in (pygame.K_SPACE, pygame.K_LCTRL):
            if self.fly_timer > 0.0:
                # If currently flying, Space boosts character altitude upward cleanly
                self.vy = 45.0
            else:
                if self.h == 0:
                    # Initial Ground Jump Baseline
                    self.vy = 92.0
                    self.jump_count = 1
                elif self.jump_count == 1:
                    # Double Jump Extension Vector
                    self.vy = 85.0
                    self.jump_count = 2
                    self.message = "DOUBLE JUMP ACTIVE"
                elif self.jump_count == 2:
                    # Triple Jump Peak Vector
                    self.vy = 80.0
                    self.jump_count = 3
                    self.message = "TRIPLE JUMP ACTIVE"
                elif self.jump_count == 3:
                    # Fourth Input: Trigger Fly Matrix Protocol
                    self.fly_timer = 10.0
                    self.vy = 50.0
                    self.jump_count = 4
                    self.message = "FLY CORE SYSTEM INITIALIZED [10s]"

    def update(self, dt):
        if self.in_config or self.game_over: return
        
        keys = pygame.key.get_pressed()
        speed = 28.0 + (self.sliders["DIFFICULTY"][0] * 1.5)
        
        # Double tracking speeds if fly booster overdrive matrix is online
        if self.fly_timer > 0.0:
            speed *= 1.4
        
        dx = (self._key(keys, pygame.K_RIGHT, pygame.K_d) - self._key(keys, pygame.K_LEFT, pygame.K_a)) * speed * dt
        dz = (self._key(keys, pygame.K_DOWN, pygame.K_s) - self._key(keys, pygame.K_UP, pygame.K_w)) * speed * dt
        
        self.x = max(-2, min(102, self.x + dx))
        self.z = max(1, min(39, self.z + dz))
        
        if self.x > 100:
            if len(self.collected) == len(self.shards_in_room):
                if self.stage >= self.sliders["STAGES"][0]:
                    self.game_over = True
                    self.message = "UPLINK ARCHIVE SYSTEM ESCAPED COMPLETE"
                else:
                    self.stage += 1
                    self.portal_flash = .7
                    self._generate_procedural_room()
                    self.x = 3; self.z = 20; self.h = self.vy = 0
                    self.jump_count = 0
                    self.fly_timer = 0.0
            else:
                self.x = 99; self.message = "UPLINK LOCKED: RECOVER ALL SHARDS"
            return
            
        if self.x < 0:
            self.x = 1
            return

        # --- ADVANCED MOTION PROCESSING SIMULATION LOOP ---
        if self.fly_timer > 0.0:
            self.fly_timer = max(0.0, self.fly_timer - dt)
            
            # Apply slight atmospheric decay, letting the user fly higher manually using Space
            self.vy -= 110 * dt
            self.h = max(2.0, self.h + self.vy * dt) # Air suspension lower bound
            
            if self.fly_timer <= 0.0:
                self.message = "FLIGHT FUEL DEPLETED - SYSTEM FALLBACK"
                self.jump_count = 0 
            else:
                self.message = f"FLIGHT OVERDRIVE MATRIX ACTIVE: {self.fly_timer:.1f}s"
        else:
            # Standard Gravity Engine Simulation Model
            self.vy -= 235 * dt
            self.h += self.vy * dt
        
        if self.h <= 0:
            self.h = 0; self.vy = 0
            self.jump_count = 0 # Flush multi-jump index tracking states upon touchdown
            
            in_pit = any(px <= self.x <= px + w and pz <= self.z <= pz + d for px, pz, w, d in self.pits)
            if not self._ground(self.x, self.z) or in_pit:
                self.deaths += 1
                self._reset_room("SIGNAL FALL - RETRY")
                
        for index, (ix, iz) in enumerate(self.shards_in_room):
            if index not in self.collected and (self.x-ix)**2 + (self.z-iz)**2 < 16:
                self.collected.add(index)
                self.score += 250
                self.message = "MEMORY SHARD RECOVERED"
                
        self.portal_flash = max(0, self.portal_flash-dt)
        self.invulnerable = max(0, self.invulnerable-dt)

    def _project(self, x, z, height=0):
        return int(20 + x * 2.45 + z * .70), int(204 - z * 1.16 - height * 1.15)

    def _box(self, surf, x, z, w, d, color):
        a=self._project(x,z); b=self._project(x+w,z); c=self._project(x+w,z+d); e=self._project(x,z+d)
        pygame.draw.polygon(surf, color, (a,b,c,e), 1)
        for p in (a,b,c,e): pygame.draw.line(surf, color, p, (p[0],p[1]+7), 1)

    def draw(self, surf):
        surf.fill(THEME["bg"])
        
        # --- DRAW SECTOR 1: CONFIGURATION OVERLAY MATRIX ---
        if self.in_config:
            t_big = self.font_big.render("CYBERIA CONFIG INTERFACE", True, THEME["hot"])
            surf.blit(t_big, (160 - t_big.get_width() // 2, 20))
            t_sm = self.font_small.render("CALIBRATE PROCEDURAL PIPELINE", True, THEME["dim"])
            surf.blit(t_sm, (160 - t_sm.get_width() // 2, 42))
            
            geom_modes = {1: "BALANCED FRAME", 2: "LINEAR VECTOR", 3: "CHAOS VECTOR"}
            
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
                
            t_help1 = self.font_small.render("A/D ARROWS: ADJUST   ENTER: INITIALIZE STREAM", True, THEME["dim"])
            surf.blit(t_help1, (160 - t_help1.get_width() // 2, 195))
            t_help2 = self.font_small.render("ESC: EXIT ISOLATION PROGRAM", True, THEME["warn"])
            surf.blit(t_help2, (160 - t_help2.get_width() // 2, 212))
            return

        # --- DRAW SECTOR 2: LIVE VECTOR RUN ---
        for z in range(0, 41, 5): pygame.draw.line(surf, (0,48,25), self._project(0,z), self._project(100,z), 1)
        for x in range(0, 101, 10): pygame.draw.line(surf, (0,38,20), self._project(x,0), self._project(x,40), 1)
        
        for px, pz, w, d in self.platforms: self._box(surf, px, pz, w, d, THEME["dim"])
        for px, pz, w, d in self.pits:
            a = self._project(px, pz); b = self._project(px+w, pz+d)
            pygame.draw.rect(surf, THEME["warn"], (min(a[0],b[0]), min(a[1],b[1]), abs(b[0]-a[0]), abs(b[1]-a[1])), 1)
            
        for i, (ix, iz) in enumerate(self.shards_in_room):
            if i not in self.collected:
                sx, sy = self._project(ix, iz, 7 + math.sin(pygame.time.get_ticks() / 180 + i) * 2)
                pygame.draw.polygon(surf, THEME["hot"], [(sx, sy-5), (sx+4, sy), (sx, sy+5), (sx-4, sy)], 1)
                
        sx, sy = self._project(99, 20, 7)
        pygame.draw.circle(surf, THEME["hot"], (sx, sy), 8, 1)
        surf.blit(self.font_small.render("OUT", True, THEME["dim"]), (sx-5, sy-18))
        
        # Dynamic player graphic adjustments if active flying configuration state is verified
        px, py = self._project(self.x, self.z, self.h + 7)
        if not (self.invulnerable and int(self.invulnerable * 12) % 2):
            if self.fly_timer > 0.0:
                # Give player vector a wider flying matrix profile frame
                pygame.draw.circle(surf, THEME["warn"], (px, py), 7, 1)
                pygame.draw.line(surf, THEME["hot"], (px-8, py), (px+8, py), 1)
            else:
                pygame.draw.circle(surf, THEME["hot"], (px, py), 6, 0)
                pygame.draw.circle(surf, THEME["bg"], (px, py), 3, 0)
            
        title = self.font_big.render("CYBERIA PIT: RUN MATRIX", True, THEME["hot"])
        surf.blit(title, (160 - title.get_width() // 2, 7))
        surf.blit(self.font_small.render(self.room_title, True, THEME["hot"]), (8, 30))
        surf.blit(self.font_small.render(self.objective, True, THEME["dim"]), (8, 42))
        
        total = len(self.shards_in_room)
        surf.blit(self.font_small.render(f"SHARDS {len(self.collected)}/{total}  SCORE {self.score:05d}  FALLS {self.deaths}", True, THEME["hot"]), (8, 224))
        
        if self.message:
            msg = self.font_small.render(self.message, True, THEME["warn"] if "LOCKED" in self.message or "FALL" in self.message or "DEPLETED" in self.message else THEME["hot"])
            surf.blit(msg, (160 - msg.get_width() // 2, 207))
            
        if self.game_over:
            surf.fill(THEME["bg"])
            g_over1 = self.font_big.render("COMPILATION ARCHIVE SUCCESSFUL", True, THEME["hot"])
            surf.blit(g_over1, (160 - g_over1.get_width() // 2, 90))
            g_over2 = self.font_small.render(f"FINAL SCORE: {self.score:05d}   TOTAL RECORDED FALLS: {self.deaths}", True, THEME["dim"])
            surf.blit(g_over2, (160 - g_over2.get_width() // 2, 115))
            g_over3 = self.font_small.render("PRESS ENTER TO RETREAT TO GENERATION HUB", True, THEME["hot"])
            surf.blit(g_over3, (160 - g_over3.get_width() // 2, 160))

# --- ISOLATED EXECUTION ENVIRONMENT BOOTSTRAPPER ---
if __name__ == '__main__':
    pygame.init()
    GAME_W, GAME_H = 320, 240
    SCALE = 3
    window = pygame.display.set_mode((GAME_W * SCALE, GAME_H * SCALE))
    pygame.display.set_caption("Cyberia Pit Sandbox Environment")
    
    canvas = pygame.Surface((GAME_W, GAME_H))
    clock = pygame.time.Clock()
    
    f_big = pygame.font.SysFont("monospace", 14, bold=True)
    f_small = pygame.font.SysFont("monospace", 10, bold=True)
    
    game = CyberiaPitStandalone(canvas, f_big, f_small)
    
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