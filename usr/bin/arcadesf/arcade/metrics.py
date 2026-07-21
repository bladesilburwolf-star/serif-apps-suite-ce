import pygame
import random
import sys

# --- METRICS MATRIX THEME ---
THEME = {
    "bg": (10, 12, 15),       # Dark analytical slate
    "dim": (0, 100, 150),     # Processed data blue
    "hot": (0, 200, 255),     # Matrix telemetry cyan
    "warn": (255, 140, 0)     # Data exception orange
}

# Classic block geometry configurations
SHAPES = {
    "I": [[1, 1, 1, 1]],
    "O": [[1, 1], [1, 1]],
    "T": [[0, 1, 0], [1, 1, 1]],
    "L": [[1, 0], [1, 0], [1, 1]],
    "Z": [[1, 1, 0], [0, 1, 1]]
}

class MetricsStandalone:
    """Metrics: Matrix Block Telemetry Sandbox."""
    name = "METRICS"

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
            "GRID_WIDTH": [10, 8, 14],    # Width of the simulation grid array
            "DIFFICULTY": [3, 1, 5],      # Baseline drop speed mechanics
            "GARBAGE": [1, 0, 4],         # Pre-allocated broken lines at boot
            "GEOMETRY": [1, 1, 3]         # 1: Standard Shapes, 2: Heavy Blocks, 3: Corrupted Monoliths
        }
        self.cfg_order = ["GRID_WIDTH", "DIFFICULTY", "GARBAGE", "GEOMETRY"]

        # Engine Tracking Grid Matrices
        self.cols = 10
        self.rows = 20
        self.grid = []
        
        self.stage = 1
        self.lines_cleared = 0
        self.room_title = ""
        self.objective = ""
        
        # Falling Block Variables
        self.current_piece = None
        self.piece_x = 0
        self.piece_y = 0
        self.drop_timer = 0.0
        
        self.message = "CONFIG MATRIX ACTIVE"
        self.clear_flash = 0.

    def _generate_procedural_matrix(self):
        self.cols = self.sliders["GRID_WIDTH"][0]
        self.rows = 20
        self.grid = [[0] * self.cols for _ in range(self.rows)]
        
        self.score = 0
        self.lines_cleared = 0
        self.stage = 1
        self.game_over = False
        self.in_config = False
        
        diff = self.sliders["DIFFICULTY"][0]
        garbage_rows = self.sliders["GARBAGE"][0]
        geom_type = self.sliders["GEOMETRY"][0]
        
        # Metadata Randomizer
        prefixes = ["LOGIC", "QUANTUM", "ALGORITHM", "ANALYTIC", "SPECTRAL"]
        suffixes = ["STACK", "ARRAY", "COMPILER", "STORAGE", "PIPELINE"]
        geom_labels = {1: "STANDARD MATRIX", 2: "HEAVY STRUCT ARCH", 3: "CORRUPTED VOLTAGE"}
        
        self.room_title = f"STAGE {self.stage:02d}: {random.choice(prefixes)}-{random.choice(suffixes)}"
        self.objective = f"Decompile blocks via {self.cols}x{self.rows} {geom_labels[geom_type]} grid array."
        
        # Inject Procedural Data Garbage Lines
        if garbage_rows > 0:
            for r in range(self.rows - garbage_rows, self.rows):
                for c in range(self.cols):
                    if random.random() < 0.75:
                        self.grid[r][c] = 1
                # Ensure it's not a pre-cleared line
                empty_spot = random.randint(0, self.cols - 1)
                self.grid[r][empty_spot] = 0
                
        self._spawn_piece()
        self.message = "GRID PARSING INITIALIZED"

    def _spawn_piece(self):
        geom_type = self.sliders["GEOMETRY"][0]
        shape_keys = list(SHAPES.keys())
        chosen_key = random.choice(shape_keys)
        base_shape = SHAPES[chosen_key]
        
        # Geometry modifications based on sliders
        if geom_type == 2:   # Heavy blocks add a reinforced core point
            self.current_piece = [row[:] for row in base_shape]
            self.current_piece[0][0] = 2
        elif geom_type == 3: # Corrupted pieces have randomly truncated nodes
            self.current_piece = [row[:] for row in base_shape]
            if len(self.current_piece) > 1 and len(self.current_piece[0]) > 1:
                self.current_piece[random.randint(0, len(self.current_piece)-1)][random.randint(0, len(self.current_piece[0])-1)] = 0
        else:
            self.current_piece = base_shape
            
        self.piece_x = self.cols // 2 - len(self.current_piece[0]) // 2
        self.piece_y = 0
        
        if self._check_collision(self.piece_x, self.piece_y, self.current_piece):
            self.game_over = True
            self.message = "STACK OVERFLOW: MEMORY CORRUPTED"

    def _check_collision(self, nx, ny, shape):
        for r, row in enumerate(shape):
            for c, val in enumerate(row):
                if val:
                    grid_x = nx + c
                    grid_y = ny + r
                    if grid_x < 0 or grid_x >= self.cols or grid_y >= self.rows:
                        return True
                    if grid_y >= 0 and self.grid[grid_y][grid_x]:
                        return True
        return False

    def _rotate_piece(self):
        # Transpose and reverse rows to calculate clean 90-degree vector rotation
        rotated = [list(x) for x in zip(*self.current_piece[::-1])]
        if not self._check_collision(self.piece_x, self.piece_y, rotated):
            self.current_piece = rotated

    def _lock_piece(self):
        for r, row in enumerate(self.current_piece):
            for c, val in enumerate(row):
                if val and self.piece_y + r >= 0:
                    self.grid[self.piece_y + r][self.piece_x + c] = val
                    
        # Check and clear full logic tracks
        cleared_this_turn = 0
        for r in range(self.rows):
            if all(self.grid[r]):
                del self.grid[r]
                self.grid.insert(0, [0] * self.cols)
                cleared_this_turn += 1
                
        if cleared_this_turn > 0:
            self.lines_cleared += cleared_this_turn
            self.score += [0, 100, 300, 600, 1200][min(cleared_this_turn, 4)] * self.stage
            self.clear_flash = 0.25
            self.message = f"COMPILED {cleared_this_turn} LOGIC LINES"
            
            # Dynamic difficulty check loop
            if self.lines_cleared >= self.stage * 5:
                self.stage += 1
                self.message = f"PARSING SPEED EXPANDED TO STAGE {self.stage:02d}"
                
        self._spawn_piece()

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
                self._generate_procedural_matrix()
            return

        if event.key == pygame.K_ESCAPE:
            self.in_config = True
            self.message = "METRICS PIPELINE STOPPED"
            return

        if self.game_over and event.key in (pygame.K_RETURN, pygame.K_SPACE):
            self.in_config = True
            self.game_over = False
            return

        # Play-mode core mechanics configuration
        if not self.game_over:
            if event.key in (pygame.K_LEFT, pygame.K_a):
                if not self._check_collision(self.piece_x - 1, self.piece_y, self.current_piece):
                    self.piece_x -= 1
            elif event.key in (pygame.K_RIGHT, pygame.K_d):
                if not self._check_collision(self.piece_x + 1, self.piece_y, self.current_piece):
                    self.piece_x += 1
            elif event.key in (pygame.K_UP, pygame.K_w, pygame.K_SPACE):
                self._rotate_piece()

    def update(self, dt):
        if self.in_config or self.game_over: return
        
        keys = pygame.key.get_pressed()
        
        # Drop interval processing engine calculated using dynamic constants
        base_speed = max(0.05, 0.65 - (self.sliders["DIFFICULTY"][0] * 0.1) - (self.stage * 0.04))
        if keys[pygame.K_DOWN] or keys[pygame.K_s]:
            base_speed = 0.03 # Force high-speed diagnostics manual dropping

        self.drop_timer += dt
        if self.drop_timer >= base_speed:
            self.drop_timer = 0.0
            if not self._check_collision(self.piece_x, self.piece_y + 1, self.current_piece):
                self.piece_y += 1
            else:
                self._lock_piece()

        self.clear_flash = max(0.0, self.clear_flash - dt)

    def draw(self, surf):
        surf.fill(THEME["bg"] if self.clear_flash <= 0.0 else THEME["hot"])
        if self.clear_flash > 0.0: return
        
        # --- DRAW SECTOR 1: OVERLAY MENU CONFIG MATRIX ---
        if self.in_config:
            t_big = self.font_big.render("METRICS SCHEMATIC ANALYZER", True, THEME["hot"])
            surf.blit(t_big, (160 - t_big.get_width() // 2, 20))
            t_sm = self.font_small.render("CALIBRATE SIMULATION PARSING FIELDS", True, THEME["dim"])
            surf.blit(t_sm, (160 - t_sm.get_width() // 2, 42))
            
            geom_modes = {1: "STANDARD VECTOR", 2: "SOLID REINFORCED", 3: "CORRUPTED SEGMENT"}
            
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
                
            t_help1 = self.font_small.render("W/S ARROWS: CHOOSE   A/D: CHANGE   SPACE: ANALYZE", True, THEME["dim"])
            surf.blit(t_help1, (160 - t_help1.get_width() // 2, 195))
            t_help2 = self.font_small.render("ESC: CLOSE DATA TERMINAL CONNECTION", True, THEME["warn"])
            surf.blit(t_help2, (160 - t_help2.get_width() // 2, 212))
            return

        # --- DRAW SECTOR 2: DATA SYSTEM VISUALIZER ---
        # Calculate viewport constraints based on chosen col widths to center the grid perfectly
        block_size = 9
        gw = self.cols * block_size
        gh = self.rows * block_size
        start_x = 160 - gw // 2
        start_y = 120 - gh // 2 + 10
        
        # Draw background container framework boundaries
        pygame.draw.rect(surf, (15, 20, 25), (start_x, start_y, gw, gh), 0)
        pygame.draw.rect(surf, THEME["dim"], (start_x - 1, start_y - 1, gw + 2, gh + 2), 1)
        
        # Render static matrix block array
        for r in range(self.rows):
            for c in range(self.cols):
                cell = self.grid[r][c]
                if cell:
                    bx = start_x + c * block_size
                    by = start_y + r * block_size
                    color = THEME["warn"] if cell == 2 else THEME["dim"]
                    pygame.draw.rect(surf, color, (bx + 1, by + 1, block_size - 2, block_size - 2), 1)

        # Render active floating logic block array
        if self.current_piece:
            for r, row in enumerate(self.current_piece):
                for c, val in enumerate(row):
                    if val:
                        grid_x = self.piece_x + c
                        grid_y = self.piece_y + r
                        if 0 <= grid_x < self.cols and 0 <= grid_y < self.rows:
                            bx = start_x + grid_x * block_size
                            by = start_y + grid_y * block_size
                            pygame.draw.rect(surf, THEME["hot"], (bx + 1, by + 1, block_size - 2, block_size - 2), 0)

        # Draw UI diagnostics bar overlay layer
        title = self.font_big.render("METRICS ARCHIVE PIPELINE", True, THEME["hot"])
        surf.blit(title, (160 - title.get_width() // 2, 7))
        surf.blit(self.font_small.render(self.room_title, True, THEME["hot"]), (8, 30))
        surf.blit(self.font_small.render(self.objective, True, THEME["dim"]), (8, 42))
        
        surf.blit(self.font_small.render(f"INDEX {self.score:06d}   LINES COMPILED {self.lines_cleared:03d}", True, THEME["hot"]), (8, 224))
        
        if self.message:
            msg = self.font_small.render(self.message, True, THEME["warn"] if "OVERFLOW" in self.message or "STOPPED" in self.message else THEME["hot"])
            surf.blit(msg, (160 - msg.get_width() // 2, 207))

        if self.game_over:
            surf.fill(THEME["bg"])
            g_over1 = self.font_big.render("CORE MEMORY STACK OVERFLOW", True, THEME["warn"])
            surf.blit(g_over1, (160 - g_over1.get_width() // 2, 90))
            g_over2 = self.font_small.render(f"TOTAL PARSED BLOCKS SCORE INDEX: {self.score:05d}", True, THEME["dim"])
            surf.blit(g_over2, (160 - g_over2.get_width() // 2, 115))
            g_over3 = self.font_small.render("PRESS ENTER TO RETREAT TO SYSTEM CONFIG TERMINAL", True, THEME["hot"])
            surf.blit(g_over3, (160 - g_over3.get_width() // 2, 160))


# --- ISOLATED EXECUTION ENVIRONMENT BOOTSTRAPPER ---
if __name__ == '__main__':
    pygame.init()
    GAME_W, GAME_H = 320, 240
    SCALE = 3
    window = pygame.display.set_mode((GAME_W * SCALE, GAME_H * SCALE))
    pygame.display.set_caption("Metrics Logic Array Sandbox")
    
    canvas = pygame.Surface((GAME_W, GAME_H))
    clock = pygame.time.Clock()
    
    f_big = pygame.font.SysFont("monospace", 13, bold=True)
    f_small = pygame.font.SysFont("monospace", 9, bold=True)
    
    game = MetricsStandalone(canvas, f_big, f_small)
    
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