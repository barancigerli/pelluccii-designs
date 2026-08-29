# Print-on-Demand Automatisierung (Shop: Pelluccii)

## Was das hier macht

1. `design_generator.py` rendert aus den Spruechen in `config.py` druckfertige
   Poster-PNGs (5400x7200 px = 300 DPI auf 18"x24")
2. `printful_upload.py` laedt sie zu Printful hoch und legt daraus Produkte an,
   die Printful automatisch in den verbundenen Etsy-Shop synct

## Aktueller Stand (eingerichtet und getestet)

| Einstellung | Wert |
|---|---|
| Printful-Store | Pelluccii (Etsy), ID `18676949` |
| Produkt | Enhanced Matte Paper Poster (in), Product-ID 1 |
| Groesse | 18" x 24", Variant-ID `1`, Einkauf $13.75 |
| Verkaufspreis | $31.99 (`RETAIL_PRICE` in `printful_upload.py`) |
| Designs | 116 Stueck = 6 Nischen x 29 Sprueche x 4 Stile |
| Aufloesung | 5400 x 7200 px, 300 DPI |
| Schriften | Google Fonts (OFL), lokal in `fonts/` |

## Dateien

```
pod_automation/
├── config.py              # Nischen, Sprueche, Poster-Stile, Variant-ID
├── design_generator.py    # rendert die PNGs + manifest.json
├── printful_upload.py     # laedt hoch und legt Produkte an
├── secrets.env            # API-Key + Store-ID (NICHT teilen)
├── fonts/                 # OFL-lizenzierte Schriften + Lizenztexte
└── output/                # generierte Designs, manifest.json, upload_log.json
```

## Zugangsdaten

Stehen in `secrets.env`, eine Zeile pro Wert, kein Leerzeichen um das `=`:

```
PRINTFUL_API_KEY=dein_token
PRINTFUL_STORE_ID=18676949
```

Umgebungsvariablen gleichen Namens haben Vorrang, falls gesetzt.
Die Datei gehoert nirgends hochgeladen oder geteilt.

## Designs generieren

```bash
python design_generator.py
```

Dauer ca. 4 Minuten fuer 116 Poster, Ergebnis ca. 35 MB in `output/`.
Vor dem Hochladen ein paar Dateien in `output/` anschauen.

## Hochladen

`DRY_RUN = True` in `printful_upload.py` ist die Standardeinstellung: das Skript
zeigt nur, was passieren wuerde, ohne echte Produkte anzulegen.

```bash
python printful_upload.py
```

Erst wenn die Ausgabe stimmt, `DRY_RUN = False` setzen und **zuerst nur wenige
Designs** hochladen:

```python
process_manifest(ids=[1, 30, 55])   # gezielte Auswahl, verschiedene Nischen und Stile
process_manifest(limit=3)           # alternativ die ersten 3 aus dem Manifest
```

Diese Produkte im Etsy-Shop pruefen (Bild, Titel, Preis, Groesse). Erst danach
den kompletten Batch fahren:

```python
process_manifest()
```

`output/upload_log.json` protokolliert, was hochgeladen wurde.

## Nischen und Stile erweitern

- **Neue Nische**: in `config.py` einen Eintrag zu `NICHES` hinzufuegen.
  Jeder Spruch wird automatisch in allen Stilen gerendert.
- **Neuer Stil**: einen Eintrag zu `STYLES` hinzufuegen. Felder: `name`, `bg`,
  `fg`, `accent`, `main` (Font, Gewicht), `eyebrow`, `upper`, `border`, `tracking`.
- **Andere Postergroesse**: `CATALOG_VARIANT_ID` in `config.py` aendern und
  `CANVAS_SIZE` auf Zoll x 300 anpassen. Das Seitenverhaeltnis muss zur Groesse
  passen, sonst beschneidet Printful. 18"x24" ist 3:4.

Verfuegbare Groessen auflisten:

```bash
python -c "from printful_upload import find_poster_variants; find_poster_variants()"
```

## Kalkulation

Bei 18"x24" und $31.99 Verkaufspreis:

| Posten | Betrag |
|---|---|
| Verkaufspreis | $31.99 |
| Printful Einkauf | -$13.75 |
| Etsy Listing | -$0.20 |
| Etsy Transaktion (6,5%) | -$2.08 |
| Zahlungsabwicklung (ca. 3% + $0.25) | -$1.21 |
| **Gewinn pro Verkauf** | **ca. $14.75** |

Versand ist hier nicht eingerechnet - je nach Einstellung zahlt ihn der Kaeufer
oder er geht von der Marge ab. Prozentsaetze sind Naeherungen und je nach
Etsy-Programm (z.B. Offsite Ads) hoeher.

## Wichtige Hinweise

- **Rate Limits**: Printful begrenzt Requests pro Minute. Das Skript pausiert
  2 Sekunden pro Produkt. Bei HTTP 429 die Pause erhoehen.
- **Listing-Gebuehren**: Etsy berechnet $0.20 pro Listing. 116 Designs = ca. $23,
  faellig unabhaengig davon, ob etwas verkauft wird.
- **Schriftlizenzen**: Die Fonts in `fonts/` stehen unter der SIL Open Font
  License (Lizenztexte liegen daneben) und duerfen kommerziell genutzt werden,
  auch fuer verkaufte Druckerzeugnisse. Bei eigenen Fonts immer die Lizenz
  pruefen - Windows-Systemfonts wie Arial sind dafuer nicht freigegeben.
- **Duplikate**: Jeder Listing-Titel enthaelt den Stilnamen und ist dadurch
  eindeutig. Ohne das entstuenden pro Spruch mehrere identische Listings, was
  Etsy abstraft.
