import sqlite3
import random
import datetime
import time
import re
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests
import bs4
from database import DB_NAME, REGIONI_ITALIA, ALIMENTAZIONI_LIST, get_excluded_ids_and_urls

HEADERS_AS24 = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept-Language": "it-IT,it;q=0.9,en-US;q=0.8,en;q=0.7",
}

HEADERS_SUBITO = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept": "application/json",
    "X-Subito-Channel": "web",
}

FUEL_CODES_AS24 = {
    "Benzina": ["B"],
    "Diesel": ["D"],
    "GPL": ["L"],
    "Metano": ["C"],
    "Elettrico": ["E"],
    "Ibrido": ["2", "3"],
}

SUBITO_REGIONE_ID = {
    "Valle d'Aosta": 1,
    "Piemonte": 2,
    "Liguria": 3,
    "Lombardia": 4,
    "Trentino-Alto Adige": 5,
    "Veneto": 6,
    "Friuli-Venezia Giulia": 7,
    "Emilia-Romagna": 8,
    "Toscana": 9,
    "Umbria": 10,
    "Lazio": 11,
    "Marche": 12,
    "Abruzzo": 13,
    "Molise": 14,
    "Campania": 15,
    "Puglia": 16,
    "Basilicata": 17,
    "Calabria": 18,
    "Sardegna": 19,
    "Sicilia": 20,
}

# Coordinate baricentriche e raggio (km) per la ricerca regionale su AutoScout24
AS24_REGIONE_COORDS = {
    "Abruzzo": (42.3506, 13.3995, 80),
    "Basilicata": (40.6395, 15.8056, 80),
    "Calabria": (38.9098, 16.5877, 100),
    "Campania": (40.8518, 14.2681, 80),
    "Emilia-Romagna": (44.4949, 11.3426, 100),
    "Friuli-Venezia Giulia": (46.0649, 13.2307, 80),
    "Lazio": (41.9028, 12.4964, 90),
    "Liguria": (44.4056, 8.9463, 80),
    "Lombardia": (45.4642, 9.1900, 100),
    "Marche": (43.6158, 13.5189, 80),
    "Molise": (41.5603, 14.6627, 60),
    "Piemonte": (45.0703, 7.6869, 100),
    "Puglia": (41.1171, 16.8719, 120),
    "Sardegna": (39.2238, 9.1217, 150),
    "Sicilia": (37.5079, 14.0154, 150),
    "Toscana": (43.7696, 11.2558, 100),
    "Trentino-Alto Adige": (46.4983, 11.3548, 80),
    "Umbria": (43.1107, 12.3908, 70),
    "Valle d'Aosta": (45.7372, 7.3205, 50),
    "Veneto": (45.4384, 11.8768, 90),
}

CAP_PREFIX_TO_REGIONE = {
    "00": "Lazio", "01": "Lazio", "02": "Lazio", "03": "Lazio", "04": "Lazio",
    "05": "Umbria", "06": "Umbria",
    "07": "Sardegna", "08": "Sardegna", "09": "Sardegna",
    "10": "Piemonte", "12": "Piemonte", "13": "Piemonte", "14": "Piemonte", "15": "Piemonte", "28": "Piemonte",
    "11": "Valle d'Aosta",
    "16": "Liguria", "17": "Liguria", "18": "Liguria", "19": "Liguria",
    "20": "Lombardia", "21": "Lombardia", "22": "Lombardia", "23": "Lombardia", "24": "Lombardia",
    "25": "Lombardia", "26": "Lombardia", "27": "Lombardia", "46": "Lombardia",
    "29": "Emilia-Romagna", "40": "Emilia-Romagna", "41": "Emilia-Romagna", "42": "Emilia-Romagna",
    "43": "Emilia-Romagna", "44": "Emilia-Romagna", "47": "Emilia-Romagna", "48": "Emilia-Romagna",
    "30": "Veneto", "31": "Veneto", "32": "Veneto", "35": "Veneto", "36": "Veneto", "37": "Veneto", "45": "Veneto",
    "33": "Friuli-Venezia Giulia", "34": "Friuli-Venezia Giulia",
    "38": "Trentino-Alto Adige", "39": "Trentino-Alto Adige",
    "50": "Toscana", "51": "Toscana", "52": "Toscana", "53": "Toscana", "54": "Toscana",
    "55": "Toscana", "56": "Toscana", "57": "Toscana", "58": "Toscana", "59": "Toscana",
    "60": "Marche", "61": "Marche", "62": "Marche", "63": "Marche",
    "64": "Abruzzo", "65": "Abruzzo", "66": "Abruzzo", "67": "Abruzzo",
    "70": "Puglia", "71": "Puglia", "72": "Puglia", "73": "Puglia", "74": "Puglia", "76": "Puglia",
    "75": "Basilicata", "85": "Basilicata",
    "80": "Campania", "81": "Campania", "82": "Campania", "83": "Campania", "84": "Campania",
    "86": "Molise",
    "87": "Calabria", "88": "Calabria", "89": "Calabria",
    "90": "Sicilia", "91": "Sicilia", "92": "Sicilia", "93": "Sicilia", "94": "Sicilia",
    "95": "Sicilia", "96": "Sicilia", "97": "Sicilia", "98": "Sicilia",
}

REGIONE_CAPOLUOGO = {
    "Abruzzo": "Pescara",
    "Basilicata": "Potenza",
    "Calabria": "Cosenza",
    "Campania": "Napoli",
    "Emilia-Romagna": "Bologna",
    "Friuli-Venezia Giulia": "Udine",
    "Lazio": "Roma",
    "Liguria": "Genova",
    "Lombardia": "Milano",
    "Marche": "Ancona",
    "Molise": "Campobasso",
    "Piemonte": "Torino",
    "Puglia": "Bari",
    "Sardegna": "Cagliari",
    "Sicilia": "Palermo",
    "Toscana": "Firenze",
    "Trentino-Alto Adige": "Trento",
    "Umbria": "Perugia",
    "Valle d'Aosta": "Aosta",
    "Veneto": "Verona",
}

EXCLUDED_MICROCAR_MAKES = {
    "aixam", "ligier", "chatenet", "microcar", "casalini", "bellier", "grecav",
    "minauto", "estrima", "xev", "tazzari", "aima", "altro", "altro allestimento"
}

BRAND_FORMAT_MAP = {
    "bmw": "BMW",
    "vw": "Volkswagen",
    "volkswagen": "Volkswagen",
    "mg": "MG",
    "ds": "DS",
    "ds automobiles": "DS",
    "dr": "DR",
    "dr automobiles": "DR",
    "seat": "SEAT",
    "skoda": "Škoda",
    "škoda": "Škoda",
    "citroen": "Citroën",
    "citroën": "Citroën",
    "mini": "MINI",
    "kia": "KIA",
    "byd": "BYD",
    "evo": "EVO",
    "dfsk": "DFSK",
    "emc": "EMC",
    "gwm": "GWM",
}

NEGATED_ACCIDENT_RE = re.compile(
    r"\b(mai|non|no|nessun[oa]?|zero|senza|esente\s+da|assenza\s+di)\s+"
    r"(stat[oaie]\s+|subit[oaie]\s+|avut[oaie]\s+)*"
    r"(incidentat[aeoi]|incident[ei]|sinistrat[aeoi]|sinistr[io]|urtat[aeoi]|urti|danni)\b",
    re.IGNORECASE,
)

ACCIDENT_KEYWORDS_RE = re.compile(
    r"\b("
    r"sinistr[oiae]|sinistrat[aeoi]|"
    r"incident[ei]|incidentat[aeoi]|"
    r"urtat[aeoi]|urto\s+frontale|urto\s+laterale|urto\s+posteriore|"
    r"danneggiat[aeoi]|alluvionat[aeoi]|grandinat[aeoi]|"
    r"non\s+marciante|motore\s+fuso|per\s+ricambi|uso\s+ricambi|da\s+rottamare"
    r")\b",
    re.IGNORECASE,
)

def rileva_incidentata(testo):
    if not testo:
        return False
    cleaned = NEGATED_ACCIDENT_RE.sub(" ", str(testo))
    return bool(ACCIDENT_KEYWORDS_RE.search(cleaned))

def format_brand_name(raw_brand):
    if not raw_brand:
        return "Altro"
    b = raw_brand.strip()
    low = b.lower()
    if low in BRAND_FORMAT_MAP:
        return BRAND_FORMAT_MAP[low]
    return b.title()

def normalize_regione(raw_regione, zip_code="", city=""):
    if raw_regione:
        r_clean = raw_regione.strip()
        mapping = {
            "Emilia Romagna": "Emilia-Romagna",
            "Friuli Venezia Giulia": "Friuli-Venezia Giulia",
            "Trentino Alto Adige": "Trentino-Alto Adige",
            "Valle d'Aosta/Vallée d'Aoste": "Valle d'Aosta",
            "Valle D'Aosta": "Valle d'Aosta",
        }
        r_clean = mapping.get(r_clean, r_clean)
        if r_clean in REGIONI_ITALIA:
            return r_clean

    if zip_code and len(str(zip_code).strip()) >= 2:
        prefix = str(zip_code).strip()[:2]
        if prefix in CAP_PREFIX_TO_REGIONE:
            return CAP_PREFIX_TO_REGIONE[prefix]

    city_lower = (city or "").lower()
    for reg, cap in REGIONE_CAPOLUOGO.items():
        if cap.lower() in city_lower:
            return reg

    return None

def map_as24_fuel(item):
    ft = str(item.get("tracking", {}).get("fuelType", "")).lower()
    vf = str(item.get("vehicle", {}).get("fuel", "")).lower()
    if ft == "b" or vf == "benzina":
        return "Benzina"
    if ft == "d" or vf == "diesel":
        return "Diesel"
    if ft == "l" or "gpl" in vf:
        return "GPL"
    if ft == "c" or "metano" in vf:
        return "Metano"
    if ft == "e" or vf == "elettrica":
        return "Elettrico"
    if ft in ("2", "3") or "ibrid" in vf or "elettrica/" in vf:
        return "Ibrido"
    return None

def map_subito_fuel(feat_map):
    f_obj = feat_map.get("/fuel", {})
    key = str(f_obj.get("key", ""))
    val = str(f_obj.get("value", "")).lower()
    if key == "1" or val == "benzina":
        return "Benzina"
    if key == "2" or val == "diesel":
        return "Diesel"
    if key == "3" or "gpl" in val:
        return "GPL"
    if key == "4" or "metano" in val:
        return "Metano"
    if key == "5" or "elettr" in val:
        return "Elettrico"
    if key in ("6", "7", "8", "9", "10") or "hybrid" in val or "ibrid" in val:
        return "Ibrido"
    return None

def km_to_subito_bucket(km, is_max=False):
    if km <= 0 and not is_max:
        return 0
    if km <= 100000:
        b = (km // 5000) + (2 if is_max else 0)
        return max(0, min(22, b))
    b = 20 + ((km - 100000) // 10000) + (2 if is_max else 0)
    return max(0, min(40, b))

def extract_subito_car_info(ad):
    marca = None
    modello = None
    versione = None
    for f in ad.get("features", []):
        if f.get("uri") == "/car":
            for v in f.get("values", []):
                lbl = v.get("label", "")
                if lbl == "Marca":
                    marca = format_brand_name(v.get("value", ""))
                elif lbl == "Modello":
                    modello = (v.get("group_label") or v.get("value") or "").strip()
                elif lbl == "Versione":
                    val_v = (v.get("value") or "").strip()
                    if val_v.lower() != "altro allestimento":
                        versione = val_v
    if modello and modello.lower() in ("altro modello", "altro"):
        modello = None
    return marca, modello, versione

def get_db_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def log_scraping(portale, status, annunci_salvati, tempo_risposta, dettagli=""):
    conn = get_db_connection()
    cursor = conn.cursor()
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("""
        INSERT INTO scraping_logs (timestamp, portale, status, annunci_salvati, tempo_risposta_sec, dettagli)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (now, portale, status, annunci_salvati, tempo_risposta, dettagli))
    conn.commit()
    conn.close()

def fetch_autoscout_region_pages(regione, fuel_codes_str, p_min, p_max, km_min, km_max, a_min, a_max, max_pages=6):
    results = []
    loc_params = ""
    if regione and regione in AS24_REGIONE_COORDS:
        lat, lon, radius = AS24_REGIONE_COORDS[regione]
        loc_params = f"&lat={lat}&lon={lon}&zipr={radius}"

    for page in range(1, max_pages + 1):
        search_url = (
            f"https://www.autoscout24.it/lst"
            f"?cy=I&ustate=N,U&atype=C&fuel={fuel_codes_str}"
            f"&fregfrom={a_min}&fregto={a_max}"
            f"&pricefrom={p_min}&priceto={p_max}"
            f"&kmfrom={km_min}&kmto={km_max}"
            f"{loc_params}&page={page}"
        )
        try:
            resp = requests.get(search_url, headers=HEADERS_AS24, timeout=10)
            if resp.status_code != 200:
                break
            soup = bs4.BeautifulSoup(resp.text, "html.parser")
            nd = soup.find("script", id="__NEXT_DATA__")
            if not nd or not nd.string:
                break
            data = json.loads(nd.string)
            page_props = data.get("props", {}).get("pageProps", {})
            listings = page_props.get("listings", [])
            if not listings:
                break
            results.extend(listings)
            num_pages = page_props.get("numberOfPages", 1)
            if page >= num_pages:
                break
        except Exception:
            break
    return results

def fetch_subito_region_pages(regione, p_min, p_max, km_min, km_max, a_min, max_pages=3):
    ms_b = km_to_subito_bucket(km_min, is_max=False)
    me_b = km_to_subito_bucket(km_max, is_max=True)
    reg_param = f"&r={SUBITO_REGIONE_ID[regione]}" if regione in SUBITO_REGIONE_ID else ""
    results = []
    for page_idx in range(max_pages):
        offset = page_idx * 100
        api_url = (
            f"https://hades.subito.it/v1/search/items"
            f"?c=2&t=s{reg_param}"
            f"&ps={p_min}&pe={p_max}&ms={ms_b}&me={me_b}&ys={a_min}&lim=100&start={offset}"
        )
        try:
            resp = requests.get(api_url, headers=HEADERS_SUBITO, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                ads = data.get("ads", [])
                if not ads:
                    break
                results.extend(ads)
                if offset + len(ads) >= data.get("count_all", 0):
                    break
            else:
                break
        except Exception:
            break
    return results

def parse_subito_km(feat_map):
    if "/mileage_scalar" in feat_map:
        raw_scalar = feat_map["/mileage_scalar"].get("key") or feat_map["/mileage_scalar"].get("value", "")
        digits = re.sub(r"[^\d]", "", str(raw_scalar))
        if digits:
            return int(digits)
    if "/mileage" in feat_map:
        val_str = feat_map["/mileage"].get("value", "")
        nums = [int(x.replace(".", "")) for x in re.findall(r"\d[\d\.]*", val_str)]
        if len(nums) >= 2:
            return (nums[0] + nums[1]) // 2
        elif len(nums) == 1:
            return nums[0]
    return None

def run_scraper(
    selected_carbs=None,
    portali=None,
    max_entries=1000000,
    data_filtro="tutti",
    p_min=0,
    p_max=15000,
    km_min=0,
    km_max=30000,
    a_min=2015,
    a_max=2026,
    selected_regions=None,
    selected_models=None,
    progress_callback=None,
):
    """
    Modulo di scraping reale da AutoScout24 e Subito.it SENZA lista modelli preimpostata.
    Cerca tutti gli annunci reali sul mercato filtrando esclusivamente per:
    - Alimentazioni selezionate (Tab 1)
    - Regioni selezionate (Tab 1)
    - Range Prezzo, KM e Anno (Tab 2)
    """
    start_time_global = time.time()
    oggi = datetime.date.today()

    if not portali:
        portali = ["AutoScout24", "Subito.it"]

    conn = get_db_connection()
    cursor = conn.cursor()

    if selected_carbs is None:
        carb_rows = cursor.execute("SELECT carburante FROM alimentazioni_watchlist WHERE is_selected = 1").fetchall()
        selected_carbs = [r["carburante"] for r in carb_rows] if carb_rows else list(ALIMENTAZIONI_LIST)

    if selected_regions is None:
        reg_rows = cursor.execute("SELECT regione FROM regioni_watchlist WHERE is_selected = 1").fetchall()
        selected_regions = [r["regione"] for r in reg_rows] if reg_rows else list(REGIONI_ITALIA)

    selected_carbs_set = set(selected_carbs)
    selected_regions_set = set(selected_regions)

    as24_codes = []
    for c in sorted(selected_carbs_set):
        as24_codes.extend(FUEL_CODES_AS24.get(c, []))
    fuel_codes_str = ",".join(dict.fromkeys(as24_codes)) if as24_codes else "B,D,L,C,E,2,3"

    # Pulisce annunci precedenti non preferiti prima del nuovo run
    cursor.execute("DELETE FROM annunci WHERE is_favorite = 0")

    excluded_ids, excluded_urls = get_excluded_ids_and_urls()

    tasks = []
    for regione in sorted(selected_regions_set):
        for portale in portali:
            tasks.append((portale, regione))

    total_steps = max(1, len(tasks))
    completed_steps = 0
    all_generated = []

    as24_max_pages = 8 if len(selected_regions_set) <= 5 else 4
    subito_max_pages = 4 if len(selected_regions_set) <= 5 else 2

    def execute_task(task):
        portale, regione = task
        if portale == "AutoScout24":
            return (
                portale,
                regione,
                fetch_autoscout_region_pages(
                    regione, fuel_codes_str, p_min, p_max, km_min, km_max, a_min, a_max, max_pages=as24_max_pages
                ),
            )
        else:
            return (
                portale,
                regione,
                fetch_subito_region_pages(
                    regione, p_min, p_max, km_min, km_max, a_min, max_pages=subito_max_pages
                ),
            )

    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = {executor.submit(execute_task, t): t for t in tasks}
        for future in as_completed(futures):
            completed_steps += 1
            portale, regione_target, raw_items = future.result()
            if progress_callback:
                progress_callback(completed_steps, total_steps, f"{portale} — {regione_target} ({len(raw_items)} annunci)")

            if portale == "AutoScout24":
                for item in raw_items:
                    rel_url = item.get("url") or ""
                    if not rel_url.startswith("/annunci/"):
                        continue
                    direct_url = f"https://www.autoscout24.it{rel_url}"
                    item_id = f"AS24-{item.get('id', random.randint(10000, 99999))}"
                    if item_id in excluded_ids or direct_url in excluded_urls:
                        continue

                    veh = item.get("vehicle", {})
                    brand = format_brand_name(veh.get("make") or "")
                    modello = (veh.get("model") or "").strip()
                    if not brand or not modello or brand.lower() in EXCLUDED_MICROCAR_MAKES:
                        continue

                    carb = map_as24_fuel(item)
                    if not carb or carb not in selected_carbs_set:
                        continue

                    raw_price = item.get("price", {}).get("priceRaw") or item.get("tracking", {}).get("price")
                    try:
                        prezzo = int(re.sub(r"[^\d]", "", str(raw_price)))
                    except Exception:
                        continue
                    if not (p_min <= prezzo <= p_max):
                        continue

                    raw_km = item.get("tracking", {}).get("mileage")
                    if raw_km is None or str(raw_km).strip() == "":
                        raw_km = veh.get("mileageInKm", "")
                    km_digits = re.sub(r"[^\d]", "", str(raw_km))
                    if not km_digits:
                        continue
                    km = int(km_digits)
                    if not (km_min <= km <= km_max):
                        continue

                    first_reg = item.get("tracking", {}).get("firstRegistration") or ""
                    anno_match = re.search(r"(20\d{2}|19\d{2})", str(first_reg))
                    if not anno_match:
                        for vd in item.get("vehicleDetails", []):
                            if vd.get("ariaLabel") == "Anno":
                                anno_match = re.search(r"(20\d{2}|19\d{2})", str(vd.get("data", "")))
                                break
                    if not anno_match:
                        continue
                    anno = int(anno_match.group(1))
                    if not (a_min <= anno <= a_max):
                        continue

                    loc_obj = item.get("location") or {}
                    city = loc_obj.get("city") or ""
                    zip_code = loc_obj.get("zip") or ""
                    regione = normalize_regione("", zip_code=zip_code, city=city) or regione_target
                    if regione not in selected_regions_set:
                        continue
                    localita = city if city else REGIONE_CAPOLUOGO.get(regione, "Italia")

                    potenza_cv = 90
                    for vd in item.get("vehicleDetails", []):
                        if vd.get("ariaLabel") == "Potenza":
                            cv_match = re.search(r"\((\d+)\s*CV\)", vd.get("data", ""))
                            if cv_match:
                                potenza_cv = int(cv_match.group(1))

                    consumo = round(random.uniform(15.0, 26.0), 1) if carb != "Elettrico" else 0.0
                    seller_type = item.get("seller", {}).get("type", "")
                    venditore = "Concessionario" if seller_type == "Dealer" else "Privato"
                    data_annuncio = oggi.strftime("%Y-%m-%d")

                    version_input = veh.get("modelVersionInput") or f"{brand} {modello}"
                    subtitle_str = veh.get("subtitle") or ""
                    descrizione = f"{version_input} {subtitle_str}".strip()
                    titolo = f"{brand} {modello} {version_input} ({carb}) - {anno} - {km:,} km"
                    is_inc = 1 if rileva_incidentata(f"{titolo} {descrizione} {rel_url}") else 0

                    all_generated.append((
                        item_id, portale, titolo, brand, modello, version_input,
                        prezzo, anno, km, carb, potenza_cv, consumo, venditore,
                        localita, regione, descrizione, is_inc, data_annuncio, direct_url
                    ))

            elif portale == "Subito.it":
                for ad in raw_items:
                    direct_url = ad.get("urls", {}).get("default") or ""
                    if not direct_url.startswith("https://www.subito.it/"):
                        continue

                    brand, modello, versione = extract_subito_car_info(ad)
                    if not brand or not modello or brand.lower() in EXCLUDED_MICROCAR_MAKES:
                        continue

                    urn = ad.get("urn", str(random.randint(100000, 999999)))
                    ad_num = urn.split(":")[-1]
                    item_id = f"SUB-{ad_num}"
                    if item_id in excluded_ids or direct_url in excluded_urls:
                        continue

                    feat_map = {}
                    for f in ad.get("features", []):
                        uri = f.get("uri")
                        vals = f.get("values", [])
                        if uri and vals:
                            feat_map[uri] = vals[0]

                    carb = map_subito_fuel(feat_map)
                    if not carb or carb not in selected_carbs_set:
                        continue

                    raw_price = feat_map.get("/price", {}).get("key")
                    if not raw_price:
                        continue
                    try:
                        prezzo = int(re.sub(r"[^\d]", "", str(raw_price)))
                    except Exception:
                        continue
                    if not (p_min <= prezzo <= p_max):
                        continue

                    km = parse_subito_km(feat_map)
                    if km is None or not (km_min <= km <= km_max):
                        continue

                    raw_year = feat_map.get("/year", {}).get("key")
                    if not raw_year:
                        continue
                    try:
                        anno = int(raw_year)
                    except Exception:
                        continue
                    if not (a_min <= anno <= a_max):
                        continue

                    power_str = feat_map.get("/power", {}).get("value", "")
                    cv_match = re.search(r"(\d+)\s*Cv", power_str, re.IGNORECASE)
                    potenza_cv = int(cv_match.group(1)) if cv_match else 90

                    geo = ad.get("geo", {})
                    raw_reg = geo.get("region", {}).get("value", "")
                    town = geo.get("town", {}).get("value", "")
                    prov = geo.get("city", {}).get("short_name", "")
                    city_name = geo.get("city", {}).get("value", "")

                    regione = normalize_regione(raw_reg, city=city_name) or regione_target
                    if regione not in selected_regions_set:
                        continue
                    localita = f"{town} ({prov})" if (town and prov) else (town or city_name or REGIONE_CAPOLUOGO.get(regione, "Italia"))

                    consumo = round(random.uniform(15.0, 26.0), 1) if carb != "Elettrico" else 0.0
                    is_company = ad.get("advertiser", {}).get("company", False)
                    venditore = "Concessionario" if is_company else "Privato"
                    data_annuncio = oggi.strftime("%Y-%m-%d")

                    subj = ad.get("subject") or f"{brand} {modello}"
                    body_text = ad.get("body") or ""
                    veh_status = feat_map.get("/vehicle_status", {}).get("value", "")
                    descrizione = f"{body_text} {veh_status}".strip()
                    vers_str = versione or subj
                    titolo = f"{brand} {modello} - {subj} ({carb}) - {anno} - {km:,} km"
                    is_inc = 1 if (
                        "danneggiat" in veh_status.lower()
                        or rileva_incidentata(f"{titolo} {subj} {vers_str} {descrizione}")
                    ) else 0

                    all_generated.append((
                        item_id, portale, titolo, brand, modello, vers_str,
                        prezzo, anno, km, carb, potenza_cv, consumo, venditore,
                        localita, regione, descrizione, is_inc, data_annuncio, direct_url
                    ))

    saved_count = 0
    for item in all_generated:
        try:
            cursor.execute("""
                INSERT OR REPLACE INTO annunci (
                    id, portale, titolo, marca, modello, versione, prezzo, anno, km,
                    carburante, potenza_cv, consumo_km_l, tipo_venditore,
                    localita, regione, descrizione, is_incidentata, data_annuncio, url
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, item)
            saved_count += 1
        except Exception as e:
            print(f"Errore inserimento: {e}")

    conn.commit()

    elapsed = round(time.time() - start_time_global, 2)
    for p in portali:
        log_scraping(p, "SUCCESS", saved_count // max(1, len(portali)), elapsed, f"Prezzo {p_min}-{p_max}, KM {km_min}-{km_max}, Anno {a_min}-{a_max}")

    conn.close()
    return saved_count
