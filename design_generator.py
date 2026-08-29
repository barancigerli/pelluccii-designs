"""
Design-Generator fuer Print-on-Demand.

Nimmt die Sprueche aus config.py und rendert sie in mehreren fertig
komponierten Poster-Stilen als druckfertige PNGs (300 DPI).

Layout pro Poster:
    - kleine, gesperrte Zeile oben (die Nische, als Eyebrow)
    - kurze Trennlinie
    - Hauptspruch, automatisch auf die groesstmoegliche passende
      Schriftgroesse skaliert und umgebrochen
    - Akzentlinie unten
    - optionaler duenner Innenrahmen

Aufruf:
    python design_generator.py

Ergebnis:
    output/design_0001.png, output/design_0002.png, ...
    output/manifest.json  (Metadaten zu jedem generierten Design)
"""

import json
import os
import re

from PIL import Image, ImageDraw, ImageFont

import config


def slugify(text):
    """Macht aus einem Text einen dateinamentauglichen Baustein."""
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", text.lower())).strip("-")


def design_filename(niche_name, text, style_name):
    """Stabiler Dateiname aus Nische, Spruch und Stil.

    WICHTIG: Frueher waren die Dateien fortlaufend nummeriert
    (design_0001.png). Sobald eine Nische oder ein Stil dazukam,
    verschob sich die Nummerierung - und weil Printful die Designs
    per URL referenziert, haetten bestehende Listings still ein
    anderes Motiv bekommen. Der Name haengt jetzt am Inhalt und
    aendert sich nicht mehr.
    """
    return f"{slugify(niche_name)}_{slugify(text)}_{slugify(style_name)}.png"


def load_font(spec, size):
    """Laedt eine Schrift. spec ist (Pfad, Gewichtsname) - der Gewichtsname
    gilt nur fuer Variable Fonts (z.B. "Bold") und wird sonst ignoriert."""
    path, variation = spec
    font = ImageFont.truetype(path, size)
    if variation:
        try:
            font.set_variation_by_name(variation)
        except Exception:
            # Statische Schrift oder Pillow ohne Variable-Font-Support:
            # dann gilt einfach das Standardgewicht.
            pass
    return font


def tracked_width(draw, text, font, tracking_px):
    """Breite eines Textes inklusive zusaetzlichem Buchstabenabstand."""
    if not text:
        return 0
    total = sum(draw.textlength(ch, font=font) for ch in text)
    return total + tracking_px * (len(text) - 1)


def draw_tracked(draw, xy, text, font, fill, tracking_px):
    """Zeichnet Text Zeichen fuer Zeichen, um Buchstabenabstand zu erlauben.
    Pillow kann Letter-Spacing nicht von sich aus."""
    x, y = xy
    for ch in text:
        draw.text((x, y), ch, font=font, fill=fill)
        x += draw.textlength(ch, font=font) + tracking_px


def wrap_text_to_fit(draw, text, font, max_width, tracking_px=0):
    """Bricht Text in mehrere Zeilen um, damit er in max_width passt."""
    words = text.split()
    lines = []
    current = []
    for word in words:
        candidate = current + [word]
        if tracked_width(draw, " ".join(candidate), font, tracking_px) <= max_width or not current:
            current = candidate
        else:
            lines.append(" ".join(current))
            current = [word]
    if current:
        lines.append(" ".join(current))
    return lines


def fit_main_text(draw, text, spec, tracking_ratio, max_width, max_height, start_size):
    """Sucht die groesste Schriftgroesse, bei der der Spruch in den
    vorgesehenen Textblock passt. Verhindert, dass lange Sprueche
    ueber den Rand laufen oder kurze verloren wirken."""
    size = start_size
    while size > 20:
        font = load_font(spec, size)
        tracking_px = size * tracking_ratio
        lines = wrap_text_to_fit(draw, text, font, max_width, tracking_px)
        line_height = size * 1.16
        block_height = line_height * len(lines)
        widest = max(tracked_width(draw, l, font, tracking_px) for l in lines)
        if block_height <= max_height and widest <= max_width and len(lines) <= 5:
            return font, lines, size, tracking_px, line_height
        size = int(size * 0.94)
    font = load_font(spec, size)
    return font, [text], size, size * tracking_ratio, size * 1.16


def draw_kilim_border(draw, width, height, colors):
    """Zeichnet eine Bordüre aus wiederholten Rauten- und Zackenmotiven,
    wie man sie von Kelim-Teppichen kennt. Rein geometrisch aufgebaut,
    also kein fremdes Bildmaterial und keine Lizenzfrage.

    colors: drei RGB-Tupel, die sich im Motiv abwechseln.
    """
    inset = int(width * 0.048)
    band = int(width * 0.042)
    outer = [inset, inset, width - inset, height - inset]

    # Grundband
    draw.rectangle(outer, outline=colors[0], width=max(2, int(width * 0.004)))
    inner = [inset + band, inset + band, width - inset - band, height - inset - band]
    draw.rectangle(inner, outline=colors[0], width=max(2, int(width * 0.003)))

    # Rautenkette entlang der vier Seiten. Die Schrittweite wird so gewaehlt,
    # dass die Motive an den Ecken sauber aufgehen statt abgeschnitten zu werden.
    size = band * 0.62
    mid = band / 2.0

    def diamond(cx, cy, r, fill):
        draw.polygon([(cx, cy - r), (cx + r, cy), (cx, cy + r), (cx - r, cy)], fill=fill)

    span_x = inner[2] - inner[0]
    count_x = max(3, int(span_x / (size * 2.1)))
    step_x = span_x / count_x
    for i in range(count_x + 1):
        cx = inner[0] + i * step_x
        c = colors[i % len(colors)]
        diamond(cx, inset + mid, size * 0.5, c)
        diamond(cx, height - inset - mid, size * 0.5, colors[(i + 1) % len(colors)])

    span_y = inner[3] - inner[1]
    count_y = max(3, int(span_y / (size * 2.1)))
    step_y = span_y / count_y
    for i in range(count_y + 1):
        cy = inner[1] + i * step_y
        c = colors[i % len(colors)]
        diamond(inset + mid, cy, size * 0.5, c)
        diamond(width - inset - mid, cy, size * 0.5, colors[(i + 1) % len(colors)])


def create_design(text, niche_name, style, canvas_size, personal_line=None):
    """Rendert ein einzelnes Poster und gibt es als PIL Image zurueck.

    personal_line: optionaler Text, den der Kaeufer bei der Bestellung
    angibt (Name, Datum). Steht er drin, wird er unten mitgedruckt - das
    macht das Poster zu echter Einzelanfertigung, nicht zu einer
    vorgetaeuschten.
    """
    width, height = canvas_size
    img = Image.new("RGB", canvas_size, style["bg"])
    draw = ImageDraw.Draw(img)

    fg = style["fg"]
    accent = style["accent"]

    # --- Bordüre ---
    if style.get("pattern") == "kilim":
        draw_kilim_border(draw, width, height, style["pattern_colors"])
    if style["border"]:
        inset = int(width * 0.055)
        line_w = max(2, int(width * 0.0018))
        draw.rectangle(
            [inset, inset, width - inset, height - inset],
            outline=accent,
            width=line_w,
        )

    # --- Eyebrow: die Nische, klein und gesperrt ---
    eyebrow_text = niche_name.upper()
    eyebrow_size = int(width * 0.026)
    eyebrow_font = load_font(style["eyebrow"], eyebrow_size)
    eyebrow_tracking = eyebrow_size * 0.32
    eyebrow_w = tracked_width(draw, eyebrow_text, eyebrow_font, eyebrow_tracking)
    eyebrow_y = int(height * 0.150)
    draw_tracked(
        draw,
        ((width - eyebrow_w) / 2, eyebrow_y),
        eyebrow_text,
        eyebrow_font,
        accent,
        eyebrow_tracking,
    )

    # --- kurze Trennlinie unter dem Eyebrow ---
    rule_y = eyebrow_y + int(eyebrow_size * 2.4)
    rule_half = int(width * 0.045)
    rule_w = max(2, int(width * 0.0016))
    draw.line(
        [(width / 2 - rule_half, rule_y), (width / 2 + rule_half, rule_y)],
        fill=accent,
        width=rule_w,
    )

    # --- Hauptspruch ---
    main_text = text.upper() if style["upper"] else text
    max_text_width = width - 2 * int(width * 0.155)
    max_text_height = height * 0.44
    font, lines, size, tracking_px, line_height = fit_main_text(
        draw,
        main_text,
        style["main"],
        style["tracking"],
        max_text_width,
        max_text_height,
        start_size=int(width * 0.165),
    )

    block_height = line_height * len(lines)
    # Optische Mitte liegt leicht ueber der geometrischen - sonst wirkt
    # das Poster kopflastig, wenn es spaeter gerahmt an der Wand haengt.
    y = height * 0.545 - block_height / 2

    for line in lines:
        line_w = tracked_width(draw, line, font, tracking_px)
        draw_tracked(draw, ((width - line_w) / 2, y), line, font, fg, tracking_px)
        y += line_height

    # --- Akzentlinie unten ---
    bottom_y = int(height * 0.845)
    bottom_half = int(width * 0.075)
    draw.line(
        [(width / 2 - bottom_half, bottom_y), (width / 2 + bottom_half, bottom_y)],
        fill=accent,
        width=rule_w,
    )

    # --- Personalisierung ---
    if personal_line:
        p_size = int(width * 0.030)
        p_font = load_font(style["eyebrow"], p_size)
        p_track = p_size * 0.18
        p_text = personal_line.strip()
        p_w = tracked_width(draw, p_text, p_font, p_track)
        draw_tracked(
            draw,
            ((width - p_w) / 2, bottom_y + int(p_size * 1.1)),
            p_text,
            p_font,
            fg,
            p_track,
        )

    return img


def generate_all_designs():
    """Erstellt fuer jede Nische x Spruch x Stil ein Poster."""
    os.makedirs(config.OUTPUT_DIR, exist_ok=True)

    manifest = []
    counter = 1

    for niche_name, texts in config.NICHES.items():
        for text in texts:
            for style in config.STYLES:
                img = create_design(
                    text=text,
                    niche_name=niche_name,
                    style=style,
                    canvas_size=config.CANVAS_SIZE,
                )

                filename = design_filename(niche_name, text, style["name"])
                # dpi-Angabe mitspeichern, damit Druckdienste die physische
                # Groesse direkt aus der Datei lesen koennen.
                img.save(os.path.join(config.OUTPUT_DIR, filename), "PNG", dpi=(300, 300))

                manifest.append({
                    "id": counter,
                    "filename": filename,
                    "niche": niche_name,
                    "text": text,
                    "style": style["name"],
                    # "Wall Art Poster" bleibt als SEO-Keyword konstant, die
                    # Nische steuert das spezifische Wording. Der Stilname am
                    # Ende macht jedes Listing eindeutig - sonst entstuenden
                    # mehrere identische Titel fuer denselben Spruch.
                    "suggested_title": (
                        f"{text} - {niche_name.title()} Wall Art Poster "
                        f"| {style['name']} Typography Print"
                    ),
                })

                counter += 1

    manifest_path = os.path.join(config.OUTPUT_DIR, "manifest.json")
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    print(f"{len(manifest)} Designs erstellt in '{config.OUTPUT_DIR}/'")
    print(f"{len(config.NICHES)} Nischen x {len(config.STYLES)} Stile")
    print(f"Manifest gespeichert: {manifest_path}")
    return manifest


if __name__ == "__main__":
    generate_all_designs()
