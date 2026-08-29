"""
Zentrale Konfiguration fuer den Design-Generator.
Hier traegst du deine Nische, Texte und Design-Varianten ein.
"""

# ---- NISCHEN / TEXTE ----
# Statt einer einzelnen Nische verwaltet diese Struktur mehrere Mikro-Nischen
# gleichzeitig. Der Shop (Pelluccii) bleibt dadurch allgemein/breit, waehrend
# jedes einzelne Listing trotzdem hochspezifisch auf eine Zielgruppe zugeschnitten
# ist - genau das Prinzip, das wir besprochen haben: allgemeiner Shop-Name,
# spezifische Produkte darunter.
#
# Jede Nische hat: einen Namen (fuer Titel-Generierung) und eine Liste an Texten.
# Weitere Nischen kannst du einfach als neue Eintraege ergaenzen - das Skript
# verarbeitet sie automatisch alle.
NICHES = {
    "dog lover": [
        "Dog mom since forever",
        "My dog is my therapist",
        "Life is better with a dog",
        "Professional dog mom",
        "Rescue dog mama",
        "Not all heroes wear capes some wear collars",
        "Sorry I can't I have a dog",
    ],
    "cat lover": [
        "Cat mom club member",
        "My cat runs this house",
        "Life is better with a cat",
        "Professional cat mom",
        "Rescue cat mama",
        "Ruled by a cat and loving it",
    ],
    "nurse": [
        "Emergency room nurse and proud of it",
        "Nurse life caffeine and compassion",
        "Not all heroes wear capes some wear scrubs",
        "Nurse mode activated",
    ],
    "coffee lover": [
        "But first coffee",
        "Coffee then adulting",
        "Powered by coffee and chaos",
        "Coffee is always a good idea",
    ],
    "plant parent": [
        "Plant mom since forever",
        "Talk to your plants they are listening",
        "Green thumb in progress",
        "Plants make me happy you not so much",
    ],
    "motivational": [
        "Progress not perfection",
        "Small steps still count",
        "Bloom where you are planted",
        "Do it scared",
    ],
}

# ---- POSTER-STILE ----
# Jeder Stil ist eine fertig komponierte Gestaltung, nicht nur eine Farbe.
# Das ersetzt das alte Farbe-x-Font-Raster: weniger, dafuer verkaufsfaehige
# Varianten statt sechs fast identischer Listings pro Spruch.
#
# main:     (Fontdatei, Gewicht) fuer den Hauptspruch
# eyebrow:  (Fontdatei, Gewicht) fuer die kleine Zeile darueber
# upper:    Hauptspruch in Grossbuchstaben setzen
# border:   duenner Rahmen innen
# tracking: Buchstabenabstand des Hauptspruchs (Anteil der Schriftgroesse)

FONT_DIR = "fonts"
MONTSERRAT = FONT_DIR + "/Montserrat[wght].ttf"
PLAYFAIR = FONT_DIR + "/PlayfairDisplay[wght].ttf"
BEBAS = FONT_DIR + "/BebasNeue-Regular.ttf"

STYLES = [
    {
        "name": "Minimalist White",
        "bg": (252, 251, 249),
        "fg": (28, 28, 28),
        "accent": (168, 162, 154),
        "main": (MONTSERRAT, "Bold"),
        "eyebrow": (MONTSERRAT, "Medium"),
        "upper": True,
        "border": True,
        "tracking": 0.02,
    },
    {
        "name": "Modern Black",
        "bg": (18, 18, 18),
        "fg": (246, 244, 240),
        "accent": (122, 118, 112),
        "main": (BEBAS, None),
        "eyebrow": (MONTSERRAT, "Medium"),
        "upper": True,
        "border": False,
        "tracking": 0.01,
    },
    {
        "name": "Boho Beige",
        "bg": (240, 231, 219),
        "fg": (92, 63, 43),
        "accent": (176, 148, 122),
        "main": (PLAYFAIR, "Bold"),
        "eyebrow": (MONTSERRAT, "Medium"),
        "upper": False,
        "border": True,
        "tracking": 0.0,
    },
    {
        "name": "Sage Botanical",
        "bg": (223, 229, 218),
        "fg": (52, 71, 54),
        "accent": (129, 149, 128),
        "main": (PLAYFAIR, "SemiBold"),
        "eyebrow": (MONTSERRAT, "Medium"),
        "upper": True,
        "border": True,
        "tracking": 0.04,
    },
]

# ---- CANVAS EINSTELLUNGEN ----
# 18"x24" bei 300 DPI = Druckqualitaet fuer Printful Variant-ID 1.
# Seitenverhaeltnis 3:4 passt exakt zu dieser Postergroesse.
CANVAS_SIZE = (5400, 7200)

# ---- OUTPUT ----
OUTPUT_DIR = "output"

# ---- PRINTFUL ----
# Echte Variant-ID der gewuenschten Poster-Groesse.
CATALOG_VARIANT_ID = 1  # Enhanced Matte Paper Poster (in), 18"x24"
