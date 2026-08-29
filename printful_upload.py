"""
Printful API Integration.

Nimmt die generierten Designs (manifest.json) und erstellt daraus
automatisiert Produkte im Printful-Account. Printful synct diese
Produkte dann automatisch in deinen verbundenen Etsy/Shopify-Shop.

VORAUSSETZUNGEN:
1. Printful-Account erstellen: https://www.printful.com
2. API-Key holen: Printful Dashboard -> Settings -> API -> "Create token"
3. Etsy oder Shopify Store in Printful unter "Stores" verbinden
4. Store-ID herausfinden (siehe get_store_id() unten)

WICHTIG: Dieses Skript macht ECHTE API-Calls, die ECHTE Produkte in
deinem Shop anlegen. Erst mit DRY_RUN = True testen!

Aufruf:
    python3 printful_upload.py
"""

import json
import os
import time

import requests

import config


def _load_secrets(path="secrets.env"):
    """Liest PRINTFUL_API_KEY / PRINTFUL_STORE_ID aus einer lokalen Datei,
    damit der Key nirgends im Code oder im Chatverlauf landet.
    Format pro Zeile:  SCHLUESSEL=wert
    Umgebungsvariablen haben Vorrang, falls gesetzt."""
    values = {}
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, _, val = line.partition("=")
                values[key.strip()] = val.strip().strip('"').strip("'")
    return values


_SECRETS = _load_secrets()

# ---- KONFIGURATION ----
PRINTFUL_API_KEY = os.environ.get("PRINTFUL_API_KEY") or _SECRETS.get("PRINTFUL_API_KEY", "")
STORE_ID = os.environ.get("PRINTFUL_STORE_ID") or _SECRETS.get("PRINTFUL_STORE_ID", "")

# Printful Katalog-Varianten-ID fuer das Produkt, das du bedrucken willst.
# WICHTIG: Diese Zahl ist ein Platzhalter - hol dir die echte ID mit
# find_poster_variants() (siehe unten im Skript), sobald dein API-Key
# eingetragen ist. Poster gibt es bei Printful in mehreren Groessen
# (z.B. 30x40cm, 40x50cm, 50x70cm) - jede hat eine eigene Variant-ID.
CATALOG_VARIANT_ID = getattr(config, "CATALOG_VARIANT_ID", None)

# Verkaufspreis in der Shop-Waehrung. Der Etsy-Shop rechnet in EUR:
# 29.50 EUR entspricht rund $31.99. Etsy zeigt deutschen Besuchern
# zusaetzlich 19% MwSt, also 35.09 EUR.
RETAIL_PRICE = "29.50"

BASE_URL = "https://api.printful.com"

# Oeffentlicher Ort der Design-Dateien. Printful holt sich die Bilder von hier,
# ein direkter Upload ist ueber die API nicht moeglich. Wert kommt aus
# secrets.env (PUBLIC_BASE_URL), damit Nutzername/Repo nicht im Code stehen.
PUBLIC_BASE_URL = os.environ.get("PUBLIC_BASE_URL") or _SECRETS.get("PUBLIC_BASE_URL", "")

# Auf True stellen fuer echten Live-Betrieb. Solange False: nur Simulation/Ausgabe.
DRY_RUN = True


def get_headers():
    return {
        "Authorization": f"Bearer {PRINTFUL_API_KEY}",
        "Content-Type": "application/json",
        "X-PF-Store-Id": str(STORE_ID),
    }


def get_store_id():
    """Hilfsfunktion: listet alle mit deinem Account verbundenen Stores auf,
    damit du die STORE_ID herausfinden kannst."""
    resp = requests.get(f"{BASE_URL}/stores", headers=get_headers())
    resp.raise_for_status()
    stores = resp.json().get("result", [])
    for store in stores:
        print(f"Store: {store['name']}  ->  ID: {store['id']}")
    return stores


def find_poster_variants(keyword="poster"):
    """
    Hilfsfunktion: durchsucht den Printful-Katalog nach Postern und zeigt dir
    alle passenden Produkte samt IDs. Damit findest du die echte CATALOG_VARIANT_ID
    fuer die Poster-Groesse, die du verkaufen willst - keine geratenen IDs.

    Aufruf einmalig vor dem ersten Upload:
        python3 -c "from printful_upload import find_poster_variants; find_poster_variants()"
    """
    headers = {"Authorization": f"Bearer {PRINTFUL_API_KEY}"}
    resp = requests.get(f"{BASE_URL}/products", headers=headers)
    resp.raise_for_status()
    products = resp.json().get("result", [])

    matches = [p for p in products if keyword.lower() in p["title"].lower()]

    if not matches:
        print(f"Keine Produkte mit '{keyword}' im Namen gefunden.")
        return []

    print(f"\n{len(matches)} Poster-Produkte gefunden:\n")
    for product in matches:
        product_id = product["id"]
        print(f"Produkt: {product['title']}  (Product-ID: {product_id})")

        variant_resp = requests.get(
            f"{BASE_URL}/products/{product_id}", headers=headers
        )
        variant_resp.raise_for_status()
        variants = variant_resp.json()["result"].get("variants", [])

        for v in variants:
            print(f"    Variant-ID: {v['id']}  ->  {v['name']}  ({v.get('size', '')})")
        print()

    print("Kopiere die passende Variant-ID (nicht die Product-ID!) in config.py -> CATALOG_VARIANT_ID")
    return matches


def design_url(filename):
    """Baut die oeffentliche URL einer Design-Datei.

    Printfuls API nimmt KEINE Datei-Uploads entgegen - weder v1 noch v2
    akzeptieren Binaerdaten. Beide erwarten eine oeffentlich erreichbare
    URL, die Printful dann selbst abruft. Deshalb liegen die Designs in
    einem oeffentlichen GitHub-Repository und werden von dort verlinkt.
    """
    return f"{PUBLIC_BASE_URL.rstrip('/')}/{filename}"


def upload_design_file(image_path):
    """
    Meldet eine Design-Datei bei Printful an und gibt die File-ID zurueck,
    die dann beim Produkt-Erstellen referenziert wird. Printful laedt die
    Datei anhand der uebergebenen URL selbst herunter.
    """
    filename = os.path.basename(image_path)
    url = design_url(filename)

    if DRY_RUN:
        print(f"  [DRY RUN] Wuerde Datei anmelden: {url}")
        return "dry_run_file_id"

    resp = requests.post(
        f"{BASE_URL}/files",
        headers=get_headers(),
        json={"type": "default", "url": url},
    )
    resp.raise_for_status()
    return resp.json()["result"]["id"]


def create_product(design_entry, file_id):
    """
    Erstellt ein Sync-Produkt in Printful, das automatisch mit dem
    verbundenen Etsy/Shopify-Store synchronisiert wird.
    """
    if CATALOG_VARIANT_ID is None:
        raise ValueError(
            "CATALOG_VARIANT_ID ist noch nicht gesetzt! "
            "Fuehre erst find_poster_variants() aus und trag die echte ID in config.py ein."
        )

    payload = {
        "sync_product": {
            "name": design_entry["suggested_title"],
        },
        "sync_variants": [
            {
                "variant_id": CATALOG_VARIANT_ID,
                "retail_price": RETAIL_PRICE,
                "files": [
                    {
                        "type": "default",
                        "id": file_id,
                    }
                ],
            }
        ],
    }

    if DRY_RUN:
        print(f"  [DRY RUN] Wuerde Produkt erstellen: {design_entry['suggested_title']}")
        print(f"  [DRY RUN] Payload: {json.dumps(payload, indent=2)}")
        return {"dry_run": True}

    resp = requests.post(
        f"{BASE_URL}/store/products", headers=get_headers(), json=payload
    )
    resp.raise_for_status()
    return resp.json()


def process_manifest(manifest_path="output/manifest.json", limit=None, ids=None):
    """
    Verarbeitet das Manifest und erstellt fuer jedes Design ein Produkt.
    limit: nur die ersten N Designs verarbeiten.
    ids:   nur diese Design-IDs verarbeiten. Fuer den ersten Live-Test
           besser als limit, weil man damit gezielt verschiedene Nischen
           und Stile auswaehlen kann statt dreimal denselben Spruch.
    """
    if not DRY_RUN and not PUBLIC_BASE_URL:
        raise ValueError(
            "PUBLIC_BASE_URL ist nicht gesetzt. Printful kann die Designs nur "
            "von einer oeffentlichen URL abholen - trag sie in secrets.env ein."
        )

    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    if ids:
        wanted = set(ids)
        manifest = [e for e in manifest if e["id"] in wanted]
    elif limit:
        manifest = manifest[:limit]

    results = []
    for entry in manifest:
        image_path = os.path.join("output", entry["filename"])
        print(f"\nVerarbeite Design {entry['id']}: {entry['text']}")

        try:
            file_id = upload_design_file(image_path)
            result = create_product(entry, file_id)
            results.append({"design_id": entry["id"], "status": "success", "result": result})

            # Rate-Limiting beachten! Printful erlaubt begrenzte Requests pro Minute.
            # Bei echtem Betrieb (DRY_RUN=False) IMMER eine Pause einbauen.
            if not DRY_RUN:
                time.sleep(2)

        except requests.exceptions.RequestException as e:
            # Printful packt den eigentlichen Grund in den Response-Body.
            # Ohne diese Ausgabe sieht man nur "400 Bad Request" und raet.
            detail = ""
            resp = getattr(e, "response", None)
            if resp is not None:
                detail = f" | {resp.text[:300]}"
            print(f"  FEHLER bei Design {entry['id']}: {e}{detail}")
            results.append({
                "design_id": entry["id"],
                "status": "error",
                "error": str(e),
                "detail": detail.strip(" |"),
            })

    # Ergebnis-Log speichern, um zu tracken was schon hochgeladen wurde
    log_path = os.path.join("output", "upload_log.json")
    with open(log_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    success_count = sum(1 for r in results if r["status"] == "success")
    print(f"\n{success_count}/{len(results)} Produkte erfolgreich verarbeitet.")
    print(f"Log gespeichert: {log_path}")


if __name__ == "__main__":
    if DRY_RUN:
        print("=== DRY RUN MODUS: Es werden KEINE echten API-Calls gemacht ===\n")

    # Erster Live-Test: drei Designs aus drei verschiedenen Nischen UND
    # drei verschiedenen Stilen - aussagekraeftiger als die ersten drei
    # aus dem Manifest, die alle denselben Spruch zeigen wuerden.
    process_manifest(ids=[1, 30, 55])
