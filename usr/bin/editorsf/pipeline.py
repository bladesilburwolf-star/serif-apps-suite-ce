# pipeline.py
from PIL import Image, ImageChops, ImageFilter, ImageOps

def process_filters(raw_image, filters, theme_colors):
    img_out = raw_image.copy()
    w, h = img_out.size

    # 0. Pre-Filter: Monochrome Conversion (Order of Operations Initialization)
    if filters.get("monochrome"):
        r, g, b, a = img_out.split()
        rgb_img = Image.merge("RGB", (r, g, b)).convert("L").convert("RGB")
        r, g, b = rgb_img.split()
        img_out = Image.merge("RGBA", (r, g, b, a))

    # 1. Color Balance Tuning (Acts as a Channel Mixer if Monochrome is Active)
    bal_r = filters.get("color_r", 100) / 100.0
    bal_g = filters.get("color_g", 100) / 100.0
    bal_b = filters.get("color_b", 100) / 100.0
    if bal_r != 1.0 or bal_g != 1.0 or bal_b != 1.0:
        r, g, b, a = img_out.split()
        rgb_img = Image.merge("RGB", (r, g, b))
        matrix = (
            bal_r, 0,     0,     0,
            0,     bal_g, 0,     0,
            0,     0,     bal_b, 0
        )
        rgb_img = rgb_img.convert("RGB", matrix)
        r, g, b = rgb_img.split()
        img_out = Image.merge("RGBA", (r, g, b, a))

    # 2. Forensic Threat Detect
    if filters.get("threat_detect"):
        edges = img_out.convert("L").filter(ImageFilter.FIND_EDGES)
        hot_hex = theme_colors["hot"].lstrip("#")
        r_tint, g_tint, b_tint = tuple(int(hot_hex[i:i+2], 16) for i in (0, 2, 4))
        tinted_edges = ImageOps.colorize(edges, (0, 0, 0), (r_tint, g_tint, b_tint)).convert("RGBA")
        img_out = ImageChops.screen(img_out, tinted_edges)

    # 3. Forensic Thermal Spectrum Map
    if filters.get("thermal"):
        gray_src = img_out.convert("L")
        hot_hex = theme_colors["hot"].lstrip("#")
        r_t, g_t, b_t = tuple(int(hot_hex[i:i+2], 16) for i in (0, 2, 4))
        thermal_map = ImageOps.colorize(gray_src, (0, 0, 0), (128, 0, 0), (r_t, g_t, b_t)).convert("RGBA")
        img_out = ImageChops.screen(img_out, thermal_map)

    # 4. High Pass / Sharp
    if filters.get("high_pass"):
        img_out = img_out.filter(ImageFilter.SHARPEN).filter(ImageFilter.EDGE_ENHANCE)

    # 5. Chromatic Aberration Shift
    if filters.get("chromatic_sep") and w > 4 and h > 4:
        r, g, b, a = img_out.split()
        r_offset = ImageChops.offset(r, 6, 0)
        b_offset = ImageChops.offset(b, -6, 0)
        img_out = Image.merge("RGBA", (r_offset, g, b_offset, a))

    return img_out