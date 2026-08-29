"""
Motiv-Generator: erzeugt bildliche Hintergruende ueber fal.ai (Flux) und
bringt sie auf Druckaufloesung.

Ablauf pro Motiv:
    1. Flux dev rendert 1344x1792 (Hochformat 3:4)
    2. aura-sr skaliert 4x auf 5376x7168
    3. Raender werden beschnitten - dort landen regelmaessig
       Pseudo-Buchstaben, ein typischer Artefakt von Bildmodellen
    4. Ergebnis wird auf exakt CANVAS_SIZE gebracht und abgelegt

Kosten grob 9 Cent pro Motiv (Stand der Tests).

Aufruf:
    python motif_generator.py            # erzeugt alle fehlenden Motive
    python motif_generator.py --only kurdish-heritage
"""

import io
import os
import sys
import time

import requests
from PIL import Image

import config
from design_generator import slugify
from printful_upload import _load_secrets

FAL_KEY = os.environ.get("FAL_KEY") or _load_secrets().get("FAL_KEY", "")
MOTIF_DIR = os.path.join(config.OUTPUT_DIR, "motifs")

# Anteil, der ringsum weggeschnitten wird. Bildmodelle setzen an die Raender
# gern erfundene Schrift und Signaturen - lieber grosszuegig abschneiden.
EDGE_CROP = 0.035

# Gemeinsamer Stil-Zusatz. Bewusst KEIN Kuenstlername im Prompt: "im Stil
# von <lebender Kuenstler>" ist der schnellste Weg in eine Abmahnung.
STYLE_SUFFIX = (
    "vintage screen-printed travel poster illustration, bold flat shapes, "
    "muted terracotta indigo ochre and cream palette, grainy risograph paper "
    "texture, large calm empty area at the top third of the composition, "
    "absolutely no text, no letters, no words, no signature, no watermark"
)

# Motive pro Nische. Bewusst Gegenstaende, Textilien, Landschaften und Essen
# statt Menschen in Tracht - Klischee-Figuren verkaufen schlechter und
# koennen verletzend wirken. Ausnahme ist das kurdische Motiv, das der
# Shop-Inhaber ausdruecklich so wollte.
MOTIFS = {
    "kurdish heritage": "an elderly woman smoking a cigar, seated cross-legged on an ornate kilim carpet, patterned textiles hanging behind her",
    "irish heritage": "misty green sea cliffs above the atlantic, a dry stone wall winding into fog",
    "italian heritage": "a still life of lemons, an espresso cup and a folded checkered cloth on a worn wooden table",
    "mexican heritage": "hand-painted talavera tiles and a bundle of marigolds in a clay pot",
    "greek heritage": "whitewashed stone steps with blue shutters and an olive branch in the foreground",
    "polish heritage": "symmetrical paper-cut folk florals and roosters in the wycinanki tradition",
    "portuguese heritage": "blue and white azulejo tiles behind a bowl of grilled sardines and bread",
    "nigerian heritage": "indigo adire resist-dyed textile patterns layered behind a clay water pot",
    "filipino heritage": "banana leaves and woven banig mats with a jeepney-inspired ornamental pattern",
    "armenian heritage": "a carved khachkar stone cross with intertwined ornament, apricots on a cloth",
    "german heritage": "a half-timbered village street under dark pine forest hills, bread and beer stein on a sill",
    "dog lover": "a calm shaggy dog resting on a woven blanket beside a worn armchair, warm afternoon light",
    "cat lover": "a cat curled asleep on a stack of books next to a steaming cup, houseplants behind",
    "nurse": "a still life of a stethoscope, a clipboard and a small vase of wildflowers on a clinic windowsill",
    "coffee lover": "a moka pot, a chipped ceramic cup and scattered coffee beans on a scratched wooden counter",
    "plant parent": "a crowded windowsill of potted monstera, ferns and trailing ivy against morning light",
    "motivational": "a lone hiker silhouette on a ridge above layered mountain ranges at sunrise",
}


def fal_post(model, payload, timeout=600):
    """Ruft ein fal-Modell auf und gibt die JSON-Antwort zurueck."""
    if not FAL_KEY:
        raise RuntimeError(
            "FAL_KEY fehlt. Trag ihn in secrets.env ein: FAL_KEY=<key_id>:<key_secret>"
        )
    resp = requests.post(
        f"https://fal.run/{model}",
        headers={"Authorization": f"Key {FAL_KEY}", "Content-Type": "application/json"},
        json=payload,
        timeout=timeout,
    )
    if resp.status_code != 200:
        raise RuntimeError(f"{model} -> HTTP {resp.status_code}: {resp.text[:300]}")
    return resp.json()


def generate_motif(niche_name, scene, overwrite=False):
    """Erzeugt ein druckfertiges Motiv fuer eine Nische."""
    os.makedirs(MOTIF_DIR, exist_ok=True)
    out_path = os.path.join(MOTIF_DIR, f"{slugify(niche_name)}.jpg")
    if os.path.exists(out_path) and not overwrite:
        print(f"  uebersprungen (existiert): {os.path.basename(out_path)}")
        return out_path

    prompt = f"{scene}, {STYLE_SUFFIX}"

    started = time.time()
    gen = fal_post("fal-ai/flux/dev", {
        "prompt": prompt,
        "image_size": {"width": 1344, "height": 1792},
        "num_images": 1,
        "num_inference_steps": 28,
    })
    src_url = gen["images"][0]["url"]

    up = fal_post("fal-ai/aura-sr", {"image_url": src_url, "upscaling_factor": 4})
    up_img = up.get("image") or up["images"][0]

    raw = requests.get(up_img["url"], timeout=300).content
    img = Image.open(io.BytesIO(raw)).convert("RGB")

    # Raender weg, dann exakt auf Zielformat bringen
    w, h = img.size
    dx, dy = int(w * EDGE_CROP), int(h * EDGE_CROP)
    img = img.crop((dx, dy, w - dx, h - dy)).resize(config.CANVAS_SIZE, Image.LANCZOS)
    # JPEG statt PNG: bei fotografischen Inhalten spart das rund 90%
    # Speicher ohne sichtbaren Qualitaetsverlust im Druck.
    img.save(out_path, "JPEG", quality=92, dpi=(300, 300), subsampling=0)

    print(f"  {os.path.basename(out_path)}  ({time.time()-started:.0f}s)")
    return out_path


def generate_all(only=None, overwrite=False):
    todo = MOTIFS if only is None else {k: v for k, v in MOTIFS.items() if slugify(k) == only}
    if not todo:
        print(f"Keine Nische passt zu '{only}'. Verfuegbar: "
              + ", ".join(slugify(k) for k in MOTIFS))
        return
    print(f"{len(todo)} Motive, grob {len(todo) * 0.09:.2f} USD")
    for niche_name, scene in todo.items():
        generate_motif(niche_name, scene, overwrite=overwrite)


if __name__ == "__main__":
    only = None
    if "--only" in sys.argv:
        only = sys.argv[sys.argv.index("--only") + 1]
    generate_all(only=only, overwrite="--overwrite" in sys.argv)
