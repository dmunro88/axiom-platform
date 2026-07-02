"""Build deterministic, conspicuously fictional media for the DEMO-001 fixture."""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "tests" / "fixtures" / "DEMO-001" / "assets"
SIZE = (1200, 720)
NAVY = "#17324d"
BLUE = "#2b6f9f"
GOLD = "#e4a73a"
PALE = "#eef3f7"
INK = "#23313d"


def font(size, bold=False):
    names = ["arialbd.ttf" if bold else "arial.ttf", "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"]
    for name in names:
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            pass
    return ImageFont.load_default()


def base_card(title, subtitle):
    image = Image.new("RGB", SIZE, PALE)
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, 0, SIZE[0], 105), fill=NAVY)
    draw.text((48, 25), "FICTIONAL QA FIXTURE", font=font(42, True), fill="white")
    draw.text((48, 130), title, font=font(48, True), fill=INK)
    draw.text((50, 192), subtitle, font=font(25), fill=BLUE)
    draw.rectangle((0, 680, SIZE[0], 720), fill=GOLD)
    draw.text((48, 686), "NOT APPRAISAL EVIDENCE  •  DEMO-001", font=font(20, True), fill=NAVY)
    return image, draw


def save_map(relative, title, points):
    image, draw = base_card(title, "Abstract diagram — locations and geometry are invented")
    for x in range(80, 1180, 150):
        draw.line((x, 245, x - 100, 650), fill="#c8d6df", width=8)
    for y in range(270, 650, 90):
        draw.line((30, y, 1170, y + 25), fill="#d6e0e6", width=7)
    draw.line(points, fill=BLUE, width=18, joint="curve")
    for index, (x, y) in enumerate(points[::2], 1):
        draw.ellipse((x - 18, y - 18, x + 18, y + 18), fill=GOLD, outline=NAVY, width=4)
        draw.text((x + 25, y - 18), f"QA {index}", font=font(20, True), fill=NAVY)
    target = ASSETS / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    image.save(target, optimize=True)


def save_building(relative, title, variant):
    image, draw = base_card(title, "Synthetic illustration — no real property is depicted")
    left = 120 + variant * 25
    draw.rectangle((left, 340, 1010, 620), fill="#a9bac6", outline=NAVY, width=8)
    draw.polygon(((left, 340), (360, 255), (1010, 340)), fill="#7f96a5", outline=NAVY)
    for x in range(left + 70, 940, 150):
        draw.rectangle((x, 405, x + 90, 500), fill="#dceaf2", outline=BLUE, width=5)
    draw.rectangle((790, 490, 940, 620), fill="#657b88", outline=NAVY, width=5)
    draw.line((80, 620, 1120, 620), fill=GOLD, width=10)
    target = ASSETS / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    image.save(target, optimize=True)


def save_sketch():
    image, draw = base_card("BUILDING SKETCH", "Not to scale — dimensions are invented")
    polygon = ((230, 300), (900, 300), (900, 500), (730, 500), (730, 610), (230, 610))
    draw.polygon(polygon, fill="white", outline=NAVY)
    draw.line(polygon + (polygon[0],), fill=NAVY, width=10)
    draw.text((440, 430), "12,000 SF\nFICTIONAL", font=font(38, True), fill=BLUE, align="center")
    draw.text((430, 265), "100' (QA)", font=font(24), fill=INK)
    draw.text((915, 390), "60' (QA)", font=font(24), fill=INK)
    target = ASSETS / "building-sketch.png"
    target.parent.mkdir(parents=True, exist_ok=True)
    image.save(target, optimize=True)


def main():
    maps = {
        "maps/regional.png": ("REGIONAL MAP", [(120, 570), (300, 430), (520, 490), (720, 330), (1060, 400)]),
        "maps/aerial.png": ("AERIAL MAP", [(110, 380), (330, 560), (570, 390), (780, 530), (1080, 300)]),
        "maps/parcel.png": ("PARCEL MAP", [(150, 300), (450, 300), (510, 570), (190, 600), (150, 300)]),
        "maps/sca-sale-location.png": ("SALE COMPARABLE LOCATIONS", [(100, 520), (330, 350), (600, 560), (840, 330), (1100, 500)]),
        "maps/land-sale-location.png": ("LAND SALE LOCATIONS", [(130, 410), (380, 570), (620, 330), (850, 520), (1080, 350)]),
        "maps/lease-comp-location.png": ("LEASE COMPARABLE LOCATIONS", [(100, 300), (350, 500), (560, 290), (790, 550), (1100, 390)]),
    }
    for relative, (title, points) in maps.items():
        save_map(relative, title, points)
    save_sketch()
    save_building("photos/subject/01-front.png", "SUBJECT — FRONT", 0)
    save_building("photos/subject/02-side.png", "SUBJECT — SIDE", 1)
    save_building("photos/lease-comps/01-demo.png", "LEASE COMP 1", 2)
    save_building("photos/lease-comps/02-demo.png", "LEASE COMP 2", 3)
    print(f"Built 11 synthetic QA images under {ASSETS}")


if __name__ == "__main__":
    main()
