#!/usr/bin/env python3
# amber-voxel-test.py
"""
SERIF APPS - 2.5D AMBER VOXEL TEST (CONSOLE EDITION)
Features:
- First-person movement through a 2.5D high-tilt voxel world.
- Depth-buffered painter's algorithm for block sorting.
- Beautiful monochrome Amber CRT scanline filter.
- Wireframe / Rendered view toggling (V Key).
- Toggleable Interactive Command Console (TAB Key).
"""

import sys
import math
import random
import pygame

# ---------------------------------------------------------------------------
# Graphics Config
# ---------------------------------------------------------------------------
INTERNAL_W, INTERNAL_H = 320, 240
SCALE = 3
WINDOW_W, WINDOW_H = INTERNAL_W * SCALE, INTERNAL_H * SCALE
FPS = 60

# Palette: Rich Amber Monochrome
AMBER_DARK = (24, 8, 0)
AMBER_DIM  = (140, 50, 0)
AMBER_HOT  = (255, 110, 0)
AMBER_GLOW = (255, 180, 50)

# ---------------------------------------------------------------------------
# World Map & Generation
# ---------------------------------------------------------------------------
MAP_SIZE = 16
world_blocks = {}

def generate_world():
    world_blocks.clear()
    for x in range(MAP_SIZE):
        for z in range(MAP_SIZE):
            height = int(2 + math.sin(x * 0.4) * 1.5 + math.cos(z * 0.4) * 1.5)
            for y in range(height + 1):
                if y == height:
                    world_blocks[(x, y, z)] = "TOP"
                else:
                    world_blocks[(x, y, z)] = "SUB"

generate_world()

# ---------------------------------------------------------------------------
# Player / Camera State
# ---------------------------------------------------------------------------
px, py, pz = MAP_SIZE / 2.0, 3.5, MAP_SIZE / 2.0
yaw = 0.0          
pitch = -0.35      

# ---------------------------------------------------------------------------
# Helper Projection Math
# ---------------------------------------------------------------------------
def project_vertex(vx, vy, vz, cos_y, sin_y, cos_p, sin_p):
    dx = vx - px
    dy = vy - py
    dz = vz - pz

    rx = dx * cos_y - dz * sin_y
    rz = dx * sin_y + dz * cos_y

    ry = dy * cos_p - rz * sin_p
    trans_z = dy * sin_p + rz * cos_p

    if trans_z < 0.1:
        return None

    fov = 180.0  
    sx = int((rx * fov) / trans_z + 160)  
    sy = int((ry * fov) / trans_z + 120)  
    
    return sx, sy, trans_z

# ---------------------------------------------------------------------------
# Main App
# ---------------------------------------------------------------------------
class AmberVoxelEngine:
    def __init__(self):
        pygame.init()
        self.window = pygame.display.set_mode((WINDOW_W, WINDOW_H))
        pygame.display.set_caption("SERIF APPS - 2.5D AMBER VOXEL ENGINE")
        self.internal = pygame.Surface((INTERNAL_W, INTERNAL_H))
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("Courier New", 9, bold=True)
        self.running = True
        self.wireframe_mode = False  

        # Console Subsystem State
        self.console_active = False
        self.console_input = ""
        self.console_log = ["SERIF CONSOLE V1.0", "TYPE /help FOR COMMANDS."]

    def handle_input(self, dt):
        global px, py, pz, yaw
        # Completely freeze player input if the console is open
        if self.console_active:
            return

        keys = pygame.key.get_pressed()
        
        rot_speed = 2.0 * dt
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            yaw -= rot_speed
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            yaw += rot_speed

        move_speed = 3.5 * dt
        dx = math.sin(yaw) * move_speed
        dz = math.cos(yaw) * move_speed

        if keys[pygame.K_UP] or keys[pygame.K_w]:
            px += dx
            pz += dz
        if keys[pygame.K_DOWN] or keys[pygame.K_s]:
            px -= dx
            pz -= dz

        if keys[pygame.K_SPACE]:
            py += move_speed
        if keys[pygame.K_LSHIFT]:
            py = max(1.0, py - move_speed)

    def execute_command(self, cmd_str):
        """Processes terminal prompt entries."""
        cmd = cmd_str.strip().lower()
        if not cmd:
            return

        self.console_log.append(f"> {cmd_str}")

        if cmd == "/help":
            self.console_log.append("AVAILABLE COMMANDS:")
            self.console_log.append(" /wire  - TOGGLE WIREFRAME")
            self.console_log.append(" /seed  - REGENERATE MAP")
            self.console_log.append(" /clear - CLEAR LOG")
        elif cmd == "/wire":
            self.wireframe_mode = not self.wireframe_mode
            self.console_log.append(f"WIREFRAME MODE: {self.wireframe_mode}")
        elif cmd == "/seed":
            generate_world()
            self.console_log.append("NEW WORLD MATRIX GENERATED.")
        elif cmd == "/clear":
            self.console_log = []
        else:
            self.console_log.append(f"ERROR: UNKNOWN COMMAND '{cmd}'")

    def draw_world(self, surf):
        surf.fill(AMBER_DARK)
        visible_faces = []

        cube_verts = [
            (0, 0, 0), (1, 0, 0), (1, 1, 0), (0, 1, 0),  
            (0, 0, 1), (1, 0, 1), (1, 1, 1), (0, 1, 1)   
        ]

        face_indices = [
            (0, 1, 2, 3), (1, 5, 6, 2), (5, 4, 7, 6),  
            (4, 0, 3, 7), (3, 2, 6, 7), (4, 5, 1, 0)   
        ]

        cos_y, sin_y = math.cos(-yaw), math.sin(-yaw)
        cos_p, sin_p = math.cos(-pitch), math.sin(-pitch)

        for (bx, by, bz), b_type in world_blocks.items():
            dist_sq = (bx - px)**2 + (bz - pz)**2
            if dist_sq > 144:  
                continue

            proj_v = []
            valid = True
            for vx, vy, vz in cube_verts:
                res = project_vertex(bx + vx, by + vy, bz + vz, cos_y, sin_y, cos_p, sin_p)
                if res is None:
                    valid = False
                    break
                proj_v.append(res)

            if not valid:
                continue

            for f_idx, face in enumerate(face_indices):
                z_depth = sum(proj_v[idx][2] for idx in face) * 0.25
                points = [(proj_v[idx][0], proj_v[idx][1]) for idx in face]

                if f_idx == 4:     
                    color = AMBER_HOT
                    outline = AMBER_GLOW
                elif f_idx in (0, 2): 
                    color = AMBER_DIM
                    outline = AMBER_HOT
                else:              
                    color = AMBER_DARK
                    outline = AMBER_DIM

                visible_faces.append((z_depth, points, color, outline))

        visible_faces.sort(key=lambda x: x[0], reverse=True)

        for _, points, color, outline in visible_faces:
            if not self.wireframe_mode:
                pygame.draw.polygon(surf, color, points)
            pygame.draw.polygon(surf, outline, points, 1) 

    def draw_console(self, surf):
        """Renders the command drop-down terminal console interface."""
        if not self.console_active:
            return

        # Semi-transparent console tray background
        console_surf = pygame.Surface((INTERNAL_W, 110))
        console_surf.fill(AMBER_DARK)
        console_surf.set_alpha(235)
        surf.blit(console_surf, (0, 0))
        
        # Border dividing wireframe engine and terminal interface
        pygame.draw.line(surf, AMBER_HOT, (0, 110), (INTERNAL_W, 110), 1)

        # Print history log lines (shows up to the last 7 lines)
        start_y = 10
        for line in self.console_log[-7:]:
            txt = self.font.render(line, True, AMBER_DIM)
            surf.blit(txt, (10, start_y))
            start_y += 12

        # Draw interactive user prompt input row
        input_txt = self.font.render(f"CONSOLE_> {self.console_input}_", True, AMBER_HOT)
        surf.blit(input_txt, (10, 95))

    def apply_crt_shader(self, target_surf):
        scanlines = pygame.Surface((WINDOW_W, WINDOW_H), pygame.SRCALPHA)
        for y in range(0, WINDOW_H, SCALE):
            pygame.draw.rect(scanlines, (0, 0, 0, 110), (0, y, WINDOW_W, 1))
        target_surf.blit(scanlines, (0, 0))

        bezel = pygame.Surface((WINDOW_W, WINDOW_H), pygame.SRCALPHA)
        for i in range(12):
            alpha = int((12 - i) * 15)
            pygame.draw.rect(bezel, (0, 0, 0, alpha), (i, i, WINDOW_W - i*2, WINDOW_H - i*2), 1)
        target_surf.blit(bezel, (0, 0))

    def run(self):
        while self.running:
            dt = self.clock.tick(FPS) / 1000.0

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        self.running = False
                    
                    elif event.key == pygame.K_TAB:
                        # Toggle console state and wipe out active string buffers
                        self.console_active = not self.console_active
                        self.console_input = ""
                    
                    elif self.console_active:
                        # Process keyboard entry string builds inside the terminal prompt
                        if event.key == pygame.K_RETURN:
                            self.execute_command(self.console_input)
                            self.console_input = ""
                        elif event.key == pygame.K_BACKSPACE:
                            self.console_input = self.console_input[:-1]
                        else:
                            # Direct unicode key translation for typing text cleanly
                            if len(self.console_input) < 30 and event.unicode.isprintable():
                                self.console_input += event.unicode
                    
                    else:
                        # Standard Gameplay Keys
                        if event.key == pygame.K_r: 
                            generate_world()
                        elif event.key == pygame.K_v: 
                            self.wireframe_mode = not self.wireframe_mode

            self.handle_input(dt)
            self.draw_world(self.internal)
            
            # Render the overlay on top of the map projection
            self.draw_console(self.internal)

            # Draw Mini-HUD on internal surface (Moved down slightly if console covers it)
            hud_y = 116 if self.console_active else 5
            hud_bg = pygame.Surface((85, 46))
            hud_bg.fill(AMBER_DARK)
            self.internal.blit(hud_bg, (5, hud_y))
            pygame.draw.rect(self.internal, AMBER_HOT, (5, hud_y, 85, 46), 1)

            mode_str = "WIRE" if self.wireframe_mode else "SOLID"
            pos_txt = self.font.render(f"POS: {px:.1f},{pz:.1f}", True, AMBER_HOT)
            fps_txt = self.font.render(f"FPS: {int(self.clock.get_fps())}", True, AMBER_DIM)
            reg_txt = self.font.render("TAB:TERM", True, AMBER_HOT)
            mod_txt = self.font.render(f"V: {mode_str}", True, AMBER_GLOW)
            
            self.internal.blit(pos_txt, (8, hud_y + 2))
            self.internal.blit(fps_txt, (8, hud_y + 11))
            self.internal.blit(reg_txt, (8, hud_y + 20))
            self.internal.blit(mod_txt, (8, hud_y + 29))

            # Scale up to window size and apply post-processing
            scaled = pygame.transform.scale(self.internal, (WINDOW_W, WINDOW_H))
            self.apply_crt_shader(scaled)

            self.window.blit(scaled, (0, 0))
            pygame.display.flip()

        pygame.quit()

if __name__ == "__main__":
    AmberVoxelEngine().run()