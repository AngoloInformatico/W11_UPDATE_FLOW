"""
Script per la generazione dell'icona ufficiale di W11 Update Flow.
Crea 'Icona/icon.ico' (multi-risoluzione: 256, 128, 64, 48, 32, 16 px)
e le versioni PNG per il web e la barra delle applicazioni.

Created by Alex Lignola - © 2026 W11 Update Flow - All rights reserved.
"""
from __future__ import annotations

import math
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parent.parent
ICON_DIR = ROOT / "Icona"
WEB_DIR = ROOT / "web"
ICON_DIR.mkdir(parents=True, exist_ok=True)


def draw_master_icon(size: int = 512) -> Image.Image:
    # Immagine RGBA ad alta risoluzione
    im = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(im)

    pad = int(size * 0.05)
    w = size - 2 * pad
    r = int(size * 0.22)  # raggio curvatura rounded square

    # Sfondo sfumato su canvas scuro
    # Disegniamo la sagoma rounded rectangle
    base_mask = Image.new("L", (size, size), 0)
    d_mask = ImageDraw.Draw(base_mask)
    d_mask.rounded_rectangle([pad, pad, pad + w, pad + w], radius=r, fill=255)

    # Gradiente di sfondo: grafite profonda (#0F1218 -> #161A22)
    bg = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    for y in range(size):
        ratio = y / size
        # da rgb(15, 18, 24) a rgb(26, 32, 42)
        r_col = int(15 + ratio * 14)
        g_col = int(18 + ratio * 16)
        b_col = int(24 + ratio * 22)
        line_draw = ImageDraw.Draw(bg)
        line_draw.line([(0, y), (size, y)], fill=(r_col, g_col, b_col, 255))
    bg.putalpha(base_mask)
    im.alpha_composite(bg)

    # Bordo sottile di luce
    border_draw = ImageDraw.Draw(im)
    border_draw.rounded_rectangle(
        [pad, pad, pad + w, pad + w],
        radius=r,
        outline=(200, 240, 75, 70),
        width=int(size * 0.015)
    )

    # Disegniamo l'elemento centrale: Windows 11 Flow Logo
    # 4 riquadri iconici di Windows con accento signal lime (#C8F04B)
    # e una freccia/arco di flusso dinamico attorno che simboleggia l'aggiornamento
    cx, cy = size // 2, size // 2
    pane_gap = int(size * 0.032)
    pane_w = int(size * 0.16)
    pane_h = int(size * 0.16)
    pane_r = int(size * 0.035)

    # Coordinate 4 quadranti Windows:
    # 1: Top-Left, 2: Top-Right, 3: Bottom-Left, 4: Bottom-Right
    x_left = cx - pane_w - pane_gap // 2
    x_right = cx + pane_gap // 2
    y_top = cy - pane_h - pane_gap // 2
    y_bottom = cy + pane_gap // 2

    # Top-Left Pane (Signal Lime primario)
    border_draw.rounded_rectangle(
        [x_left, y_top, x_left + pane_w, y_top + pane_h],
        radius=pane_r,
        fill=(200, 240, 75, 255)
    )

    # Top-Right Pane (Signal Lime 85% opacity)
    border_draw.rounded_rectangle(
        [x_right, y_top, x_right + pane_w, y_top + pane_h],
        radius=pane_r,
        fill=(180, 225, 60, 240)
    )

    # Bottom-Left Pane (Signal Lime 70% opacity)
    border_draw.rounded_rectangle(
        [x_left, y_bottom, x_left + pane_w, y_bottom + pane_h],
        radius=pane_r,
        fill=(160, 205, 50, 220)
    )

    # Bottom-Right Pane (Signal Lime brillante con punto di flusso)
    border_draw.rounded_rectangle(
        [x_right, y_bottom, x_right + pane_w, y_bottom + pane_h],
        radius=pane_r,
        fill=(210, 250, 85, 255)
    )

    # Arco di aggiornamento esterno "Flow Arc" con freccia direzionale
    # Raggio arco attorno ai quadranti
    arc_layer = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    arc_draw = ImageDraw.Draw(arc_layer)

    arc_box = [cx - int(size * 0.34), cy - int(size * 0.34), cx + int(size * 0.34), cy + int(size * 0.34)]
    arc_width = int(size * 0.045)

    # Arco superiore da 170° a 360° (senso orario)
    arc_draw.arc(arc_box, start=140, end=350, fill=(200, 240, 75, 240), width=arc_width)

    # Freccia alla fine dell'arco (in alto a destra, ~350°)
    arrow_x = cx + int(size * 0.34 * math.cos(math.radians(350)))
    arrow_y = cy + int(size * 0.34 * math.sin(math.radians(350)))
    arrow_size = int(size * 0.055)

    pts = [
        (arrow_x + int(arrow_size * 0.9), arrow_y - int(arrow_size * 0.2)),
        (arrow_x - int(arrow_size * 0.6), arrow_y - int(arrow_size * 0.9)),
        (arrow_x - int(arrow_size * 0.2), arrow_y + int(arrow_size * 0.8)),
    ]
    arc_draw.polygon(pts, fill=(200, 240, 75, 255))

    # Arco inferiore di ritorno da 320° a 140°
    arc_draw.arc(arc_box, start=320, end=140, fill=(75, 180, 240, 190), width=arc_width)
    arrow_x2 = cx + int(size * 0.34 * math.cos(math.radians(140)))
    arrow_y2 = cy + int(size * 0.34 * math.sin(math.radians(140)))
    pts2 = [
        (arrow_x2 - int(arrow_size * 0.9), arrow_y2 + int(arrow_size * 0.2)),
        (arrow_x2 + int(arrow_size * 0.6), arrow_y2 + int(arrow_size * 0.9)),
        (arrow_x2 + int(arrow_size * 0.2), arrow_y2 - int(arrow_size * 0.8)),
    ]
    arc_draw.polygon(pts2, fill=(75, 180, 240, 240))

    # Glow soffuso dell'arco
    glow = arc_layer.filter(ImageFilter.GaussianBlur(int(size * 0.02)))
    im.alpha_composite(glow)
    im.alpha_composite(arc_layer)

    return im


def generate():
    print("[*] Generazione icona ad alta risoluzione...")
    master = draw_master_icon(512)

    # 1. Salva PNG ad alta risoluzione in Icona/icon.png
    png_path = ICON_DIR / "icon.png"
    master.save(png_path, "PNG", optimize=True)
    print(f"[OK] Creato {png_path}")

    # 2. Copia in web/icon.png e web/favicon.ico per l'app e il browser
    web_png = WEB_DIR / "icon.png"
    master.resize((128, 128), Image.Resampling.LANCZOS).save(web_png, "PNG")
    print(f"[OK] Creato {web_png}")

    # 3. Genera file multi-risoluzione .ico (256, 128, 64, 48, 32, 16)
    sizes = [(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)]
    ico_images = [master.resize(s, Image.Resampling.LANCZOS) for s in sizes]

    ico_path = ICON_DIR / "icon.ico"
    ico_images[0].save(
        ico_path,
        format="ICO",
        sizes=sizes,
        append_images=ico_images[1:]
    )
    print(f"[OK] Creato {ico_path} con {len(sizes)} risoluzioni!")

    # Copia anche in web/favicon.ico
    web_ico = WEB_DIR / "favicon.ico"
    ico_images[0].save(
        web_ico,
        format="ICO",
        sizes=[(64, 64), (32, 32), (16, 16)],
        append_images=[ico_images[2], ico_images[4], ico_images[5]]
    )
    print(f"[OK] Creato {web_ico}")


if __name__ == "__main__":
    generate()
