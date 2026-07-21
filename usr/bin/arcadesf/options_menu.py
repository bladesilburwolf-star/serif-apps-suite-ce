#!/usr/bin/env python3
# options_menu.py
"""
SERIF ARCADE SYSTEM CONTROL PANEL - EXPANDED
A globally shared diagnostic / configurations overlay hook for managing 
display upscales, sound mixers, external shaders, and runtime color matrices.
"""
import sys
import pygame

class OptionsMenu:
    def __init__(self, font_small, font_big, current_theme):
        self.font_small = font_small
        self.font_big = font_big
        self.theme = current_theme
        
        # Expanded State Arrays
        self.menu_items = [
            {"label": "MASTER VOLUME", "type": "slider", "val": 0.7, "key": "vol_master"},
            {"label": "SFX VOLUME", "type": "slider", "val": 0.6, "key": "vol_sfx"},
            {"label": "DISPLAY UPSCALE", "type": "toggle", "opts": [1, 2, 3, 4], "idx": 2, "key": "scale"}, 
            {"label": "GLSL SHADER", "type": "toggle", "opts": ["NONE", "CRT-SCANLINES", "AMBER-PHOSPHOR", "CURVED-GLASS"], "idx": 0, "key": "shader"},
            {"label": "COLOR PALETTE", "type": "toggle", "opts": ["MATRIX GREEN", "AMBER RUSH", "CYBERPUNK NEON", "MONO GREY"], "idx": 0, "key": "palette"},
            {"label": "FRAME LIMIT (FPS)", "type": "toggle", "opts": [30, 60, 120, 999], "idx": 1, "key": "fps"},
            {"label": "DISENGAGE SYSTEM", "type": "action", "action": "quit"}
        ]
        self.selected_idx = 0
        self.is_active = False

        # Palette definition matrix mapping back to global setups
        self.palettes = {
            "MATRIX GREEN": {"bg": (4, 10, 6), "hot": (0, 255, 128), "dim": (0, 110, 55), "panel": (0, 22, 11), "warn": (255, 90, 90)},
            "AMBER RUSH":   {"bg": (12, 5, 0), "hot": (255, 140, 0), "dim": (140, 60, 0), "panel": (30, 12, 0), "warn": (255, 70, 70)},
            "CYBERPUNK NEON":{"bg": (10, 2, 15), "hot": (255, 0, 180), "dim": (110, 0, 130), "panel": (25, 4, 35), "warn": (0, 240, 255)},
            "MONO GREY":    {"bg": (15, 15, 15), "hot": (230, 230, 230), "dim": (90, 90, 90), "panel": (35, 35, 35), "warn": (240, 40, 40)}
        }

    def handle_event(self, event):
        if not self.is_active:
            return None

        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_UP, pygame.K_w):
                self.selected_idx = (self.selected_idx - 1) % len(self.menu_items)
            elif event.key in (pygame.K_DOWN, pygame.K_s):
                self.selected_idx = (self.selected_idx + 1) % len(self.menu_items)
                
            item = self.menu_items[self.selected_idx]
            
            # Slide settings left or right
            if item["type"] == "slider":
                if event.key in (pygame.K_LEFT, pygame.K_a):
                    item["val"] = max(0.0, item["val"] - 0.05)
                elif event.key in (pygame.K_RIGHT, pygame.K_d):
                    item["val"] = min(1.0, item["val"] + 0.05)
                    
            # Cycle toggle options left or right
            elif item["type"] == "toggle":
                if event.key in (pygame.K_LEFT, pygame.K_a, pygame.K_RIGHT, pygame.K_d):
                    mod = 1 if event.key in (pygame.K_RIGHT, pygame.K_d) else -1
                    item["idx"] = (item["idx"] + mod) % len(item["opts"])
                    
                    # Live update local UI themes instantly if color option changes
                    if item["key"] == "palette":
                        selected_palette_name = item["opts"][item["idx"]]
                        self.theme = self.palettes[selected_palette_name]
                    
            elif item["type"] == "action":
                if event.key in (pygame.K_RETURN, pygame.K_SPACE):
                    if item["action"] == "quit":
                        pygame.quit()
                        sys.exit()
                        
            if event.key in (pygame.K_ESCAPE, pygame.K_TAB):
                self.is_active = False
                return "SAVE_AND_SYNC"
                
        return None

    def get_setting(self, key):
        """Helper to let the main hub extract variable statuses."""
        for item in self.menu_items:
            if item.get("key") == key:
                if item["type"] == "slider":
                    return item["val"]
                elif item["type"] == "toggle":
                    return item["opts"][item["idx"]]
        return None

    def draw(self, surf):
        # Draw translucent background panel
        overlay = pygame.Surface((surf.get_width(), surf.get_height()))
        overlay.fill(self.theme["panel"])
        overlay.set_alpha(235)
        surf.blit(overlay, (0, 0))

        # Header Title
        title = self.font_big.render("SYSTEM DIAGNOSTICS & SETUP", True, self.theme["hot"])
        surf.blit(title, (surf.get_width() // 2 - title.get_width() // 2, 15))
        
        # Draw Menu Items
        for i, item in enumerate(self.menu_items):
            is_sel = (i == self.selected_idx)
            color = self.theme["hot"] if is_sel else self.theme["dim"]
            prefix = " > " if is_sel else "   "
            
            val_str = ""
            if item["type"] == "slider":
                blocks = int(item["val"] * 10)
                val_str = f"[{'#' * blocks}{'-' * (10 - blocks)}] {int(item['val']*100)}%"
            elif item["type"] == "toggle":
                val_str = f"< {item['opts'][item['idx']]} >"
            elif item["type"] == "action":
                val_str = "[ PRESS ENTER ]"
                
            lbl = self.font_small.render(f"{prefix}{item['label']}", True, color)
            val = self.font_small.render(val_str, True, color)
            
            # Position layout distribution rows
            row_y = 55 + i * 22
            surf.blit(lbl, (20, row_y))
            surf.blit(val, (surf.get_width() - val.get_width() - 20, row_y))

        # Bottom UI Action Bar Hints
        hint = self.font_small.render("WS: NAV | AD: ADJUST | TAB: SAVE & EXIT", True, self.theme["dim"])
        surf.blit(hint, (surf.get_width() // 2 - hint.get_width() // 2, surf.get_height() - 20))