"""Sahara Racers - character/car ability card art (630 x 880, standard poker ratio).

Builds one card front per car from its studio render (docs/previews/cars/<Car>_front.png):
gold girih frame in the car's colours, Arabic + English name, race number, art window,
ability panel (title + 3 text lines you can overwrite in Unreal with a Text Render / UMG).
Output: assets/common/textures/T_Card_<NN>_<Car>.png and docs/previews/cards.png

Run with plain Python (needs Pillow, arabic-reshaper, python-bidi):  python blender/card_art.py
"""
import math
import os
import sys

from PIL import Image, ImageDraw, ImageFilter, ImageFont, features

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
OUT = os.path.join(ROOT, "assets", "common", "textures")
PREV = os.path.join(ROOT, "docs", "previews")
BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
REG = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"

if features.check("raqm"):
    def ar(s):
        return s
else:
    import arabic_reshaper
    from bidi.algorithm import get_display

    def ar(s):
        return get_display(arabic_reshaper.reshape(s))

# ability flavour matched to each car's personality (placeholders - replace with your game's card text)
ABILITY = {
    "Falcon": ("Falcon Dive", "انقضاض الصقر", "Homing falcon strikes the leader."),
    "DuneFox": ("Dune Leap", "قفزة الكثبان", "Super-jump over hazards and rivals."),
    "NajdiGXR": ("Najdi Wall", "سور نجد", "Bull-bar shield shrugs off the next hit."),
    "HiluxRaider": ("Sand Storm", "عاصفة رملية", "Kicks up a blinding sandstorm behind."),
    "RiyadhMuscle": ("Nitro Roar", "زئير النيترو", "Long nitro burst with flame trail."),
    "NeomGlide": ("Pulse Field", "نبضة نيوم", "EMP ring slows every car nearby."),
    "AlUlaRally": ("Rock Slide", "انهيار صخري", "Drops a sand-trap on the racing line."),
    "JeddahGT": ("Sea Breeze", "نسيم البحر", "Slipstream boost for the whole lap."),
}


def star(d, cx, cy, r, col, width=4, fill=None):
    for rot in (0, 45):
        pts = [(cx + r * math.cos(math.radians(rot + 45 + 90 * k)), cy + r * math.sin(math.radians(rot + 45 + 90 * k))) for k in range(4)]
        d.polygon(pts, outline=col, width=width, fill=fill)


def centered(d, text, box, font, fill):
    l, t, r, b = d.textbbox((0, 0), text, font=font)
    d.text((box[0] + (box[2] - box[0] - (r - l)) / 2 - l, box[1] + (box[3] - box[1] - (b - t)) / 2 - t), text, font=font, fill=fill)


def card(spec, idx):
    W, H = 630, 880
    paint = tuple(int(255 * min(1, c * 1.0 + 0.05)) for c in spec["paint"])
    dark = tuple(int(c * 0.35) for c in paint)
    gold = (214, 172, 92)
    im = Image.new("RGB", (W, H), dark)
    d = ImageDraw.Draw(im)
    for y in range(H):   # vertical gradient in the car's colour
        t = y / H
        d.line([(0, y), (W, y)], fill=tuple(int(dark[i] * (1 - t) + paint[i] * 0.55 * t) for i in range(3)))
    for y in range(-40, H + 40, 70):   # faint girih lattice
        for x in range(-40, W + 40, 70):
            star(d, x + (35 if (y // 70) % 2 else 0), y, 26, tuple(min(255, c + 22) for c in dark), 2)
    # art window with the studio render
    art = os.path.join(PREV, "cars", f"{spec['name']}_front.png")
    win = (44, 128, W - 44, 560)
    d.rounded_rectangle(win, 18, fill=(20, 20, 24))
    if os.path.exists(art):
        a = Image.open(art).convert("RGB")
        aw, ah = a.size
        tw, th = win[2] - win[0], win[3] - win[1]
        scale = max(tw / (aw * 0.78), th / ah)
        a = a.resize((int(aw * scale), int(ah * scale)), Image.LANCZOS)
        cx = (a.width - tw) // 2
        cy = (a.height - th) // 2
        a = a.crop((cx, cy, cx + tw, cy + th))
        mask = Image.new("L", (tw, th), 0)
        ImageDraw.Draw(mask).rounded_rectangle((0, 0, tw, th), 18, fill=255)
        im.paste(a, (win[0], win[1]), mask)
    d.rounded_rectangle(win, 18, outline=gold, width=5)
    # title banner
    d.rounded_rectangle((30, 30, W - 30, 112), 16, fill=(18, 16, 22), outline=gold, width=4)
    centered(d, spec["name_display"], (110, 34, W - 200, 74), ImageFont.truetype(BOLD, 34), (245, 232, 200))
    centered(d, ar(spec["name_ar"]), (110, 70, W - 200, 110), ImageFont.truetype(BOLD, 32), gold)
    # number medallion
    d.ellipse((40, 36, 104, 100), fill=gold)
    centered(d, spec["number"], (40, 36, 104, 100), ImageFont.truetype(BOLD, 40), (25, 20, 15))
    star(d, W - 74, 71, 30, gold, 4, fill=(18, 16, 22))
    centered(d, "٠١٢٣٤٥٦٧٨٩"[int(spec["number"])], (W - 104, 41, W - 44, 101), ImageFont.truetype(BOLD, 30), gold)
    # ability panel
    title, title_ar, desc = ABILITY.get(spec["name"], ("Ability", "قدرة", "Describe the ability."))
    d.rounded_rectangle((30, 580, W - 30, H - 30), 18, fill=(245, 236, 214), outline=gold, width=5)
    d.ellipse((50, 600, 140, 690), fill=paint, outline=(60, 45, 25), width=4)
    star(d, 95, 645, 30, (250, 240, 215), 4)
    d.text((158, 602), title.upper(), font=ImageFont.truetype(BOLD, 34), fill=(60, 35, 15))
    d.text((158, 646), ar(title_ar), font=ImageFont.truetype(BOLD, 30), fill=(140, 90, 30))
    words, lines, cur = desc.split(), [], ""
    for wd in words:
        if len(cur + " " + wd) > 30:
            lines.append(cur)
            cur = wd
        else:
            cur = (cur + " " + wd).strip()
    lines.append(cur)
    for k, ln in enumerate(lines[:3]):
        d.text((56, 712 + k * 38), ln, font=ImageFont.truetype(REG, 28), fill=(50, 40, 30))
    d.rounded_rectangle((12, 12, W - 12, H - 12), 30, outline=gold, width=10)
    d.text((W - 210, H - 62), "SAHARA RACERS", font=ImageFont.truetype(BOLD, 18), fill=(150, 115, 60))
    name = f"T_Card_{spec['id']}_{spec['name']}.png"
    im.save(os.path.join(OUT, name))
    return im


def main():
    # cars.py imports bpy; read the CARS list without Blender by evaluating the specs block only
    src = open(os.path.join(HERE, "cars.py")).read()
    start = src.index("CARS = [")
    end = src.index("\n]\n", start) + 3
    ns = {"T": float}
    for fn in ("ex_falcon", "ex_dunefox", "ex_najdi", "ex_hilux", "ex_muscle", "ex_neom", "ex_rally", "ex_gt"):
        ns[fn] = None
    exec(src[start:end], ns)  # noqa: S102 - trusted repo source (data literals only)
    os.makedirs(OUT, exist_ok=True)
    pretty = {"DuneFox": "Dune Fox", "NajdiGXR": "Najdi GXR", "HiluxRaider": "Hilux Raider", "RiyadhMuscle": "Riyadh Muscle",
              "NeomGlide": "NEOM Glide", "AlUlaRally": "AlUla Rally", "JeddahGT": "Jeddah GT"}
    cards = []
    for i, s in enumerate(ns["CARS"]):
        s = dict(s)
        s["name_display"] = pretty.get(s["name"], s["name"])
        cards.append(card(s, i))
    sheet = Image.new("RGB", (4 * 330, 2 * 460), (24, 22, 28))
    for i, c in enumerate(cards):
        sheet.paste(c.resize((315, 440), Image.LANCZOS), (8 + (i % 4) * 330, 10 + (i // 4) * 460))
    sheet.save(os.path.join(PREV, "cards.png"))
    print("cards written")


if __name__ == "__main__":
    main()
