#!/usr/bin/env python3
"""BC.Transporter - versione Terminale (solo stdlib, output colorato).

Stessi endpoint dell'app Flutter BCTransporterMobileApp, usabili da console.

Uso:
    python bc_cli.py                       -> menu interattivo colorato
    python bc_cli.py --help                -> aiuto
    python bc_cli.py treni --cerca "bari" [--paese IT]
    python bc_cli.py treni --partenze <id> [--paese IT] [--arrivi]
    python bc_cli.py treni --treno <num> --stazione <id> [--paese IT]
    python bc_cli.py treni --trip <tripId> [--paese IT]
    python bc_cli.py treni --numero <testo>
    python bc_cli.py treni --fal <stationId>
    python bc_cli.py bus --providers
    python bc_cli.py bus --linee <provider> [--paese it]
    python bc_cli.py bus --fermate <provider> [--paese it]
    python bc_cli.py bus --partenze <provider> <stopId> [--paese it]
    python bc_cli.py bus --veicoli <provider> [--paese it]
    python bc_cli.py voli --area
    python bc_cli.py voli --aeroporto <IATA> [--arrivi]
    python bc_cli.py flixbus --stazioni "bari" | --partenze <id> | --trip <id>
    python bc_cli.py regionali --lista IT
    python bc_cli.py regionali --stazioni IT it/trains/trenord [--cerca milano]
    python bc_cli.py regionali --partenze IT it/trains/trenord <stationId> [--arrivi]
    python bc_cli.py regionali --news IT it/trains/trenord
    python bc_cli.py regionali --trip IT it/trains/trenord <tripId>
    python bc_cli.py strade --news [--paese it] | --pedaggi | --servizi [--highway A1]
    python bc_cli.py meteo --cerca roma | --ora Roma 41.9 12.5
    python bc_cli.py social --feed | --topic <id> | --online | --leaderboard
    python bc_cli.py auth --login <email> <pw> | --register <e> <p> <nick> | --stato
    python bc_cli.py preferiti --lista | --treno <num> <org> <dest>
    python bc_cli.py config --show | --stats-general | --loghi
    python bc_cli.py offline --lista | --size | --save <tipo> <id> <file>
    python bc_cli.py treni --live | --match <tripId> | --routing DA A --date X --time Y

Globale: --no-color
"""

import argparse
import json
import sys
import urllib.parse
import urllib.request

# Windows: la console legacy usa cp1252 e crasha su emoji/box-drawing.
# Forziamo UTF-8 (Windows Terminal lo supporta).
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

BASE = "https://betacloud-transporter.is-cool.dev"
TRAINBOARD = "https://prod.cuzimmartin.dev/api"
FLIX = "https://prod.cuzimmartin.dev/api/flixbus"
HEADERS = {"User-Agent": "BC.Transporter"}

USE_COLOR = sys.stdout.isatty()

# -- Colori ANSI (adatti al dominio) ------------------------------------------
R, G, Y, B, M, C_, W, DIM, BOLD, RESET = (
    "\033[31m", "\033[32m", "\033[33m", "\033[34m", "\033[35m",
    "\033[36m", "\033[37m", "\033[2m", "\033[1m", "\033[0m",
)

def paint(s, code):
    return f"{code}{s}{RESET}" if USE_COLOR else str(s)

def ok(s):    return paint(s, G)
def err(s):   return paint(s, R)
def warn(s):  return paint(s, Y)
def info(s):  return paint(s, C_)
def bold(s):  return paint(s, BOLD)
def dim(s):   return paint(s, DIM)
def title(s): return paint(s, BOLD + B)
def c_train(s): return paint(s, BOLD + G)   # treni = verde
def c_bus(s):   return paint(s, BOLD + Y)   # bus = giallo
def c_plane(s): return paint(s, BOLD + C_)  # aerei = ciano
def c_fal(s):   return paint(s, BOLD + M)   # FAL = magenta

def p_title(s): print(f"\n{title('━━ ' + s + ' ━━')}")
def p_ok(s):    print(f"{ok('✔')} {s}")
def p_err(s):   print(f"{err('✘')} {s}")
def p_warn(s):  print(f"{warn('!')} {s}")
def p_info(s):  print(f"{info('›')} {s}")
def p_dim(s):   print(dim(s))

# -- HTTP ---------------------------------------------------------------------
def get_json(url, timeout=15):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=timeout) as res:
        return json.loads(res.read().decode("utf-8") or "{}")

def as_list(v):
    if isinstance(v, list):
        return v
    if isinstance(v, dict) and isinstance(v.get("data"), list):
        return v["data"]
    return []

def post_json(url, payload, timeout=15, token=None):
    data = json.dumps(payload).encode("utf-8")
    headers = dict(HEADERS)
    headers["Content-Type"] = "application/json; charset=utf-8"
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as res:
        return json.loads(res.read().decode("utf-8") or "{}")

def api_delete(url, payload=None, token=None, timeout=10):
    data = json.dumps(payload or {}).encode("utf-8")
    headers = dict(HEADERS)
    headers["Content-Type"] = "application/json; charset=utf-8"
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, data=data, headers=headers, method="DELETE")
    with urllib.request.urlopen(req, timeout=timeout) as res:
        return res.status, json.loads(res.read().decode("utf-8") or "{}")

def api_patch(url, payload, token=None, timeout=10):
    data = json.dumps(payload).encode("utf-8")
    headers = dict(HEADERS)
    headers["Content-Type"] = "application/json; charset=utf-8"
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, data=data, headers=headers, method="PATCH")
    with urllib.request.urlopen(req, timeout=timeout) as res:
        return json.loads(res.read().decode("utf-8") or "{}")

# -- Stesse logiche di supporto dell'app --------------------------------------
# ApiService.fetchConfig: 3 retry + backoff + fallback default (api_service.dart)
def fetch_config():
    import time
    last = None
    for attempt in range(1, 4):
        try:
            return get_json(f"{BASE}/api/config/transports", timeout=15)
        except Exception as e:
            last = e
            time.sleep(attempt)
    return {"transports": [
        {"id": "default_train", "name": "Trainboard", "type": "train"},
        {"id": "default_bus", "name": "AMTAB Bari", "type": "bus"},
        {"id": "default_plane", "name": "FlightRadar", "type": "plane"}],
        "_fallback": True, "_error": str(last)}

# BusRepository._calculateDistance/_calculateArrivalEstimate (Haversine)
def haversine_km(lat1, lon1, lat2, lon2):
    import math
    R_ = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1))
         * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2)
    return R_ * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

def arrival_estimate(bus_lat, bus_lon, stop_lat, stop_lon, speed):
    if (bus_lat, bus_lon) == (0.0, 0.0) or (stop_lat, stop_lon) == (0.0, 0.0):
        return None
    dist = haversine_km(bus_lat, bus_lon, stop_lat, stop_lon)
    if dist < 0.1 or (dist < 0.2 and (speed or 0) < 10):
        return "In arrivo"
    v = 20.0 * 0.6 + (speed * 0.4 if (speed or 0) > 2 else 0)
    v = min(60.0, max(5.0, v if (speed or 0) > 2 else 20.0))
    mins = -(-dist / v * 60 // 1)  # ceil
    mins = int(mins)
    if mins > 60:
        return None
    return "In arrivo" if mins < 1 else f"~{mins} min"

# File locali: sessione auth, preferiti, cache offline (stessa forma dei repo)
import os
HOME = os.path.expanduser("~")
SESS_FILE = os.path.join(HOME, ".bc_cli_session.json")
FAV_FILE = os.path.join(HOME, ".bc_cli_favorites.json")
CACHE_DIR = os.path.join(HOME, ".bc_cli_cache")

def load_json_file(path, default):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default

def save_json_file(path, obj):
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(obj, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        p_err(f"Scrittura {path}: {e}")
        return False

def session():
    return load_json_file(SESS_FILE, {})

def fav_all():
    return load_json_file(FAV_FILE, [])

def cache_path(ttype, ident):
    safe = "".join(c if c.isalnum() or c in "-_." else "_" for c in ident)
    return os.path.join(CACHE_DIR, f"{ttype}_{safe}.json")

def fmt_time(t):
    if t is None:
        return "—"
    try:
        from datetime import datetime, timezone
        if isinstance(t, (int, float)):
            ms = int(t * 1000) if t < 1e11 else int(t)
            dt = datetime.fromtimestamp(ms / 1000)
            return dt.strftime("%H:%M")
        dt = datetime.fromisoformat(str(t).replace("Z", "+00:00"))
        return dt.strftime("%H:%M")
    except Exception:
        return str(t)

def delay_badge(d):
    try:
        n = int(d or 0)
    except (TypeError, ValueError):
        n = 0
    if n <= 0:
        return ok("in orario")
    if n < 5:
        return warn(f"+{n} min")
    return err(f"+{n} min")

# -- Categorie treno colorate (stessa logica di TrainDeparture.fromJson) --------
import re
CAT_FIXED = {
    # Alta velocità → rosso
    "FR": R, "AV": R, "ICE": R, "TGV": R, "ES": R, "FB": R, "OUIGO": R,
    "ETR": R, "FRECCIA": R,
    # Lunga percorrenza → giallo/magenta
    "IC": Y, "EC": Y, "EN": Y, "RJ": Y, "NJ": M, "ICN": Y, "INTERCITY": Y,
    # Regionali → verde
    "REG": G, "R": G, "RE": G, "RB": G, "TER": G, "MAL": G,
    "RV": G, "REGIONALE": G, "REX": G, "IR": G, "OS": G,
    # Suburbane/metro → ciano/blu
    "S": C_, "U-BAHN": B, "METRO": B, "M": B,
    # Urbani → giallo/magenta
    "BUS": Y, "TRAM": M, "TRAMWAY": M, "O-BUS": Y,
    # Speciali
    "FAL": M,
}
CAT_PALETTE = [G, Y, C_, M, B, R]

def train_category(line, product=None):
    if product and str(product).strip():
        return str(product).strip().upper()
    s = str(line or "").strip()
    if not s:
        return ""
    tok = re.split(r"\s+", s)[0]
    clean = re.sub(r"[^A-Za-z0-9\-]", "", tok)
    if re.match(r"^S\d+$", clean, re.IGNORECASE):
        return "S"
    letters = re.sub(r"\d", "", clean).upper()
    if letters and re.search(r"[A-Z]", letters):
        return letters
    return clean.upper() or "?"

def cat_color(cat):
    cat = (cat or "?").upper()
    if cat in CAT_FIXED:
        code = CAT_FIXED[cat]
    else:
        code = CAT_PALETTE[sum(ord(c) for c in cat) % len(CAT_PALETTE)]
    return code

def cat_paint(cat, text=None):
    t = text if text is not None else cat
    if not USE_COLOR:
        return str(t)
    return f"{BOLD}{cat_color(cat)}{t}{RESET}"

def train_categories(refresh=True):
    p_title("🏷️ Categorie treno (mappa live mondiale)")
    try:
        data = get_json("https://data.cuzimmartin.dev/train-map?north=85&south=-5&east=91"
                        "&west=-64&duration=300&results=1000&polylines=false")
    except Exception as e:
        return p_err(f"Errore mappa live: {e}")
    from collections import Counter
    cnt = Counter()
    for m in (data.get("movements", []) if isinstance(data, dict) else []):
        if not isinstance(m, dict):
            continue
        line = m.get("line") if isinstance(m.get("line"), dict) else {}
        cat = train_category(line.get("name"), line.get("productName"))
        if cat:
            cnt[cat] += 1
    cats = {c: {"color": cat_color(c), "count": n} for c, n in cnt.most_common()}
    save_json_file(os.path.join(HOME, ".bc_cli_categories.json"), cats)
    for i, (c, n) in enumerate(cnt.most_common(60), 1):
        print(f"  {dim(str(i).rjust(3))}  {cat_paint(c, c.ljust(12))} {dim(str(n) + ' mezzi live')}")
    p_dim(f"Categorie distinte: {len(cnt)} (mostrate 60). Colori salvati e riusati nei tabelloni.")

def short(v, maxlen=34):
    s = str(v if v is not None else "—")
    return s if len(s) <= maxlen else s[: maxlen - 1] + "…"

def ask(prompt):
    try:
        return input(paint(prompt, C_)).strip()
    except (EOFError, KeyboardInterrupt):
        print()
        return ""

# -- TRENI --------------------------------------------------------------------
def fetch_stations(q, country):
    url = (f"{TRAINBOARD}/{country}/stations?query={urllib.parse.quote(q)}"
           f"&limit=10")
    return url, as_list(get_json(url))

def train_search(q, country):
    p_title(f'🚂 Stazioni · "{q}" [{country}]')
    try:
        url, lst = fetch_stations(q, country)
    except Exception as e:
        return p_err(f"Errore ricerca stazioni: {e}")
    p_dim(f"GET {url}")
    if not lst:
        return p_warn("Nessuna stazione trovata.")
    for i, e in enumerate(lst, 1):
        e = e if isinstance(e, dict) else {}
        sid = e.get("id") or e.get("stationId") or "?"
        name = e.get("name") or e.get("stationName") or "?"
        print(f"  {c_train(f'[{i}]')} {bold(name)}  {dim(f'id={sid}')}")
    p_dim(f"Usa l'id con: treni --partenze <id> --paese {country}")
    return lst

def vlen(s):
    return len(re.sub(r"\x1b\[[0-9;]*m", "", str(s)))

def pad_v(s, w):
    s = str(s)
    return s + " " * max(0, w - vlen(s))

def stop_name(v):
    if isinstance(v, dict):
        return str(v.get("stationName") or v.get("name") or "?")
    return str(v or "")

def parse_utc(t):
    try:
        if t is None:
            return None
        from datetime import datetime, timezone
        if isinstance(t, (int, float)):
            ms = int(t * 1000) if t < 1e11 else int(t)
            return datetime.fromtimestamp(ms / 1000, tz=timezone.utc)
        s = str(t).strip()
        if not s or s == "—":
            return None
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except Exception:
        return None

def stop_eff_time(s):
    return (parse_utc(s.get("estimatedDeparture")) or parse_utc(s.get("departure"))
            or parse_utc(s.get("time")) or parse_utc(s.get("estimatedArrival"))
            or parse_utc(s.get("arrival")))

def print_timeline(stops):
    items = [s for s in (stops or []) if isinstance(s, dict)]
    if not items:
        return p_warn("Nessuna fermata nella timeline.")
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    times = [stop_eff_time(s) for s in items]
    passed = [i for i, t in enumerate(times) if t is not None and t <= now]
    at = passed[-1] if passed else -1
    print(f"\n  {bold(f'Timeline ({len(items)} fermate):')}")
    for i, s in enumerate(items):
        name = s.get("station") or s.get("stop") or s.get("stationName") or s.get("name") or "?"
        arr = fmt_time(s.get("scheduledArrival") or s.get("arrival"))
        dep = fmt_time(s.get("scheduledDeparture") or s.get("departure") or s.get("time"))
        delay = s.get("delay") or s.get("arrivalDelay") or s.get("departureDelay") or 0
        cancelled = s.get("cancelled") or s.get("canceled") or s.get("isCancelled")
        if cancelled:
            mark = err("✖")
        elif i == 0:
            mark = ok("●")
        elif i == len(items) - 1:
            mark = info("■")
        else:
            mark = dim("○")
        times_ = f"{arr}/{dep}" if arr != dep else arr
        tail = f"  {delay_badge(delay)}" if delay else ""
        here = ""
        moving = False
        if at == -1 and i == 0:
            here = f"  {ok('🚂 non partito')}"
        elif at == len(items) - 1 and i == len(items) - 1:
            here = f"  {ok('🚂 arrivato')}"
        elif at == i and times[at] is not None:
            if (now - times[at]).total_seconds() <= 180:
                here = f"  {ok('🚂 qui')}"
            else:
                moving = True
        print(f"  {mark} {dim(times_.ljust(11))} {name}{tail}{here}")
        if i < len(items) - 1:
            if moving and at == i:
                print(f"  {dim('│')} {ok('🚂 ↓ in viaggio')}")
            else:
                print(f"  {dim('│')}")

def train_board(station_id, country, arrivi):
    ep = "arrivals" if arrivi else "departures"
    p_title(f"🚂 {'Arrivi' if arrivi else 'Partenze'} · {station_id} [{country}]")
    url = f"{TRAINBOARD}/{country}/{ep}?stationId={urllib.parse.quote(station_id)}"
    p_dim(f"GET {url}")
    try:
        lst = as_list(get_json(url))
    except Exception as e:
        return p_err(f"Errore tabellone: {e}")
    if not lst:
        return p_warn("Nessun treno trovato.")
    head_place = 'PROVENIENZA' if arrivi else 'DESTINAZIONE'
    rows = []
    data_rows = []
    for raw in lst[:30]:
        if not isinstance(raw, dict):
            continue
        e = raw.get("data") if isinstance(raw.get("data"), dict) else raw
        line = str(e.get("line") or e.get("category") or "")
        num = str(e.get("tripNumber") or e.get("trainNumber") or "")
        label = line if (num and num in line) else (line + " " + num).strip()
        cat = train_category(line, e.get("category"))
        place = short(str((e.get("origin") if arrivi else e.get("destination"))
                          or e.get("stationName") or "—"), 32)
        t = fmt_time(e.get("scheduledTime") or e.get("time"))
        plat = str(e.get("platform") or e.get("plannedPlatform") or "—")
        rows.append((t, cat_paint(cat, label), place, paint(plat, Y),
                     delay_badge(e.get("delay", 0))))
        data_rows.append(e)
    w = [len("N"), len("ORA"), len("TRENO"), len(head_place), len("BIN")]
    for i, r in enumerate(rows, 1):
        w = [max(w[0], len(str(i))), max(w[1], vlen(r[0])), max(w[2], vlen(r[1])),
             max(w[3], vlen(r[2])), max(w[4], vlen(r[3]))]
    print(f"  {dim(pad_v('N', w[0]))} {dim(pad_v('ORA', w[1]))} {dim(pad_v('TRENO', w[2]))} "
          f"{dim(pad_v(head_place, w[3]))} {dim(pad_v('BIN', w[4]))} {dim('STATO')}")
    for i, r in enumerate(rows, 1):
        print(f"  {c_train(pad_v(str(i), w[0]))} {bold(pad_v(r[0], w[1]))} {pad_v(r[1], w[2])} "
              f"{pad_v(r[2], w[3])} {pad_v(r[3], w[4])} {r[4]}")
    p_dim(f"Totale: {len(lst)} (mostrati max 30) · tasto 4 = timeline del treno")
    return data_rows

def train_details(numero, stazione, country):
    p_title(f"🚂 Dettaglio treno {numero} @ {stazione} [{country}]")
    url = (f"{TRAINBOARD}/{country}/details?trainNumber={urllib.parse.quote(numero)}"
           f"&stationId={urllib.parse.quote(stazione)}")
    p_dim(f"GET {url}")
    try:
        data = get_json(url)
    except Exception as e:
        return p_err(f"Errore dettaglio treno: {e}")
    e = (data.get("data") if isinstance(data, dict) else None) or data or {}
    print(f"  {bold('Categoria:')} {e.get('category') or e.get('line') or '—'}")
    print(f"  {bold('Origine:')} {stop_name(e.get('origin') or e.get('stationName')) or '—'}")
    print(f"  {bold('Destinazione:')} {stop_name(e.get('destination')) or '—'}")
    print(f"  {bold('Orario:')} {fmt_time(e.get('scheduledTime') or e.get('time'))}  "
          f"stimato {fmt_time(e.get('estimatedTime'))}  {delay_badge(e.get('delay', 0))}")
    print(f"  {bold('Binario:')} {e.get('platform') or '—'}")
    print_timeline(e.get("stops") or e.get("stopovers") or [])

def train_trip_data(trip_id, country):
    data = get_json(f"{TRAINBOARD}/{country}/trip?tripId={urllib.parse.quote(trip_id)}")
    return (data.get("data") if isinstance(data, dict) else None) or data or {}

def fetch_train_logos(source="official"):
    meta = load_json_file(os.path.join(CACHE_DIR, "_meta.json"), {})
    cache_file = os.path.join(CACHE_DIR, "train_logos.json")
    try:
        data = get_json(f"{BASE}/api/train-logos")
        src = ((data.get(source) if isinstance(data, dict) else None)
               or (data.get("official") if isinstance(data, dict) else None) or {})
        out = {}
        for k, v in src.items():
            if isinstance(v, dict):
                out[str(k).upper()] = {
                    fmt: (p if p.startswith("http") else BASE + p)
                    for fmt, p in v.items() if isinstance(p, str)}
        if out:
            os.makedirs(CACHE_DIR, exist_ok=True)
            save_json_file(cache_file, out)
            from datetime import datetime, timezone
            meta["train_logos"] = datetime.now(timezone.utc).isoformat()
            save_json_file(os.path.join(CACHE_DIR, "_meta.json"), meta)
            return out
    except Exception as e:
        p_dim(f"loghi live falliti, uso cache: {e}")
    return load_json_file(cache_file, {})

def logo_png_for(category, logos):
    cat = (category or "").upper()
    if cat in logos and logos[cat].get("png"):
        return logos[cat]["png"]
    for k, v in logos.items():
        if cat and (cat.startswith(k) or k.startswith(cat)) and v.get("png"):
            return v["png"]
    return None

CAT_HEX = {"FR": "#e53935", "AV": "#e53935", "ICE": "#e53935", "TGV": "#e53935",
           "IC": "#f9a825", "EC": "#f9a825", "EN": "#f9a825", "RJ": "#f9a825",
           "REG": "#43a047", "R": "#43a047", "RE": "#43a047", "RB": "#43a047",
           "S": "#00acc1", "BUS": "#f9a825", "TRAM": "#d81b60", "FAL": "#d81b60"}

def sheet_share_link(trip_id, country, trip):
    payload = {"tripId": trip_id, "country": country,
               "tripNumber": trip.get("tripNumber") or trip.get("trainNumber"),
               "origin": stop_name(trip.get("origin")),
               "destination": stop_name(trip.get("destination")),
               "platform": trip.get("platform"), "delay": trip.get("delay", 0),
               "scheduledTime": str(trip.get("scheduledTime") or ""),
               "estimatedTime": str(trip.get("estimatedTime") or ""),
               "stops": trip.get("stops") or trip.get("stopovers") or []}
    res = post_json(f"{BASE}/api/share-trip", payload)
    sid = res.get("shareId") if isinstance(res, dict) else None
    return f"{BASE}/share/?id={sid}" if sid else None

def collect_messages(trip):
    out = []
    for m in (trip.get("messages") or []):
        out.append(m if isinstance(m, dict) else {"text": str(m)})
    meta = trip.get("metadata") if isinstance(trip.get("metadata"), dict) else {}
    for k in ("messages", "alerts", "notes"):
        v = meta.get(k)
        if isinstance(v, list):
            out += [x if isinstance(x, dict) else {"text": str(x)} for x in v]
        elif isinstance(v, str) and v.strip():
            out.append({"text": v})
    for s in (trip.get("stops") or trip.get("stopovers") or []):
        if isinstance(s, dict):
            for m in (s.get("messages") or []):
                out.append(m if isinstance(m, dict) else {"text": str(m)})
    return out

def open_timeline_gui(trip_id, country):
    # Finestra grafica rinnovata con componenti moderni in stile Material/Fluent (solo stdlib)
    import tkinter as tk
    from tkinter import ttk, messagebox, simpledialog
    from datetime import datetime, timezone
    try:
        trip = train_trip_data(trip_id, country)
    except Exception as e:
        return p_err(f"Trip: {e}")
    stops = [s for s in (trip.get("stops") or trip.get("stopovers") or [])
             if isinstance(s, dict)]
    if not stops:
        return p_warn("Trip senza fermate.")

    # Palette colori moderna (Dark Theme curato)
    BG, SURFACE, CARD, TXT, SUB, TRACK = "#121212", "#1E1E1E", "#2A2A2A", "#F8F9FA", "#A0A0A0", "#333333"
    OK, WARN, ERR = "#2ECC71", "#F1C40F", "#E74C3C"
    GUI_CAT = {"FR": "#E74C3C", "AV": "#E74C3C", "ICE": "#E74C3C", "TGV": "#E74C3C",
               "IC": "#F39C12", "EC": "#F39C12", "EN": "#F39C12",
               "REG": "#27AE60", "R": "#27AE60", "RE": "#27AE60", "RB": "#27AE60",
               "S": "#00BCD4", "BUS": "#16A085", "TRAM": "#E91E63", "FAL": "#E91E63"}

    def cat_hex(c):
        c = (c or "").upper()
        return GUI_CAT.get(c, "#3498DB")

    def delay_hex(d):
        try:
            n = int(d or 0)
        except (TypeError, ValueError):
            n = 0
        return OK if n <= 0 else (WARN if n < 5 else ERR)

    def shade(hexcol, f):
        hexcol = hexcol.lstrip("#")
        r, g, b = (int(hexcol[i:i + 2], 16) for i in (0, 2, 4))
        r, g, b = (max(0, min(255, int(c * f))) for c in (r, g, b))
        return f"#{r:02x}{g:02x}{b:02x}"

    def mkbtn(parent, text, bg, fg="white", cmd=None, var=None):
        b = tk.Button(parent, text=text, textvariable=var,
                      font=("Segoe UI", 9, "bold"), bg=bg, fg=fg,
                      activebackground=shade(bg, 1.2), activeforeground=fg,
                      relief="flat", padx=10, pady=6, cursor="hand2",
                      bd=0, highlightthickness=0, command=cmd)
        b.bind("<Enter>", lambda e: b.configure(bg=shade(bg, 1.2)))
        b.bind("<Leave>", lambda e: b.configure(bg=bg))
        return b

    def position(sts):
        now = datetime.now(timezone.utc)
        eff = []
        for s in sts:
            eff.append(parse_utc(s.get("estimatedDeparture")) or parse_utc(s.get("departure"))
                       or parse_utc(s.get("time")) or parse_utc(s.get("estimatedArrival"))
                       or parse_utc(s.get("arrival")))
        at = -1
        for i, t in enumerate(eff):
            if t is not None and t <= now:
                at = i
        return at, now, eff

    line = str(trip.get("line") or trip.get("category") or "")
    num = str(trip.get("tripNumber") or trip.get("trainNumber") or "")
    cat = train_category(line, trip.get("category"))
    hexcol = cat_hex(cat)
    train_key = f"{cat}|{num}|{trip.get('scheduledTime') or ''}"
    client_id = f"cli-{os.getpid()}"
    logos = fetch_train_logos()
    png_url = logo_png_for(cat, logos)

    root = tk.Tk()
    root.title(f"BC.Transporter – {line} {num}".strip())
    root.geometry("580x780")
    root.configure(bg=BG)
    
    style = ttk.Style(root)
    try:
        style.theme_use("clam")
    except Exception:
        pass
    style.configure("TFrame", background=BG)
    style.configure("TLabel", background=BG, foreground=TXT, font=("Segoe UI", 10))
    style.configure("Small.TLabel", background=BG, foreground=SUB, font=("Segoe UI", 9))

    alive = {"on": True, "live": True}
    state = {"trip": trip}

    def on_close():
        alive["on"] = False
        try:
            post_json(f"{BASE}/api/train-presence/leave",
                      {"clientId": client_id, "trainKey": train_key})
        except Exception:
            pass
        root.destroy()
    root.protocol("WM_DELETE_WINDOW", on_close)

    # -- Header Superiore (Hero Banner) --
    head = tk.Frame(root, bg=hexcol)
    head.pack(fill="x")
    
    hrow = tk.Frame(head, bg=hexcol)
    hrow.pack(fill="x", padx=16, pady=(14, 6))
    
    logo_box = tk.Label(hrow, bg=SURFACE, padx=10, pady=8, relief="flat")
    logo_box.pack(side="left")
    if png_url:
        try:
            req = urllib.request.Request(png_url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=15) as res:
                raw = res.read()
            import tempfile
            fd, tmp = tempfile.mkstemp(suffix=".png")
            os.write(fd, raw)
            os.close(fd)
            img = tk.PhotoImage(file=tmp)
            os.remove(tmp)
            if img.width() > 110:
                img = img.subsample(max(1, img.width() // 110), 1)
            logo_box.configure(image=img)
            logo_box.image = img
        except Exception:
            logo_box.configure(text="🚂", font=("Segoe UI Emoji", 22), bg=hexcol, fg="white")
    else:
        logo_box.configure(text="🚂", font=("Segoe UI Emoji", 22), bg=hexcol, fg="white")

    hinfo = tk.Frame(hrow, bg=hexcol)
    hinfo.pack(side="left", padx=14)
    title_var = tk.StringVar(value=f"{line} {num}".strip())
    tk.Label(hinfo, textvariable=title_var, font=("Segoe UI", 22, "bold"),
             bg=hexcol, fg="white").pack(anchor="w")
    route_var = tk.StringVar()
    tk.Label(hinfo, textvariable=route_var, font=("Segoe UI", 11, "bold"),
             bg=hexcol, fg="#E0E0E0").pack(anchor="w", pady=(2, 0))

    # Badge di stato nell'header
    chips = tk.Frame(head, bg=hexcol)
    chips.pack(fill="x", padx=16, pady=(4, 12))
    
    delay_var = tk.StringVar()
    delay_lbl = tk.Label(chips, textvariable=delay_var, font=("Segoe UI", 9, "bold"),
                         fg="white", padx=10, pady=4)
    delay_lbl.pack(side="left")
    
    plat_var = tk.StringVar()
    tk.Label(chips, textvariable=plat_var, font=("Segoe UI", 9, "bold"),
             bg="#111111", fg="white", padx=10, pady=4).pack(side="left", padx=(8, 0))
             
    tk.Label(chips, text="● LIVE", font=("Segoe UI", 9, "bold"),
             bg="#111111", fg="#2ECC71", padx=10, pady=4).pack(side="left", padx=(8, 0))
             
    viewers_var = tk.StringVar(value="")
    tk.Label(chips, textvariable=viewers_var, font=("Segoe UI", 9, "bold"),
             bg=hexcol, fg="white").pack(side="left", padx=(8, 0))

    tk.Frame(head, bg=shade(hexcol, 0.7), height=3).pack(fill="x", side="bottom")

    # -- Barra inferiore fissa --
    upLbl_var = tk.StringVar(value="")
    live_var = tk.StringVar(value="⏱ LIVE on")
    bottom = tk.Frame(root, bg=SURFACE, padx=12, pady=10)
    bottom.pack(side="bottom", fill="x")
    
    mkbtn(bottom, "🔄 Aggiorna", hexcol, cmd=lambda: refresh()).pack(side="left")
    mkbtn(bottom, "", CARD, var=live_var,
          cmd=lambda: (alive.update(live=not alive["live"]),
                       live_var.set("⏱ LIVE on" if alive["live"] else "⏱ LIVE off"))
          ).pack(side="left", padx=(8, 0))
    mkbtn(bottom, "Chiudi", CARD, cmd=on_close).pack(side="right")
    tk.Label(bottom, textvariable=upLbl_var, font=("Segoe UI", 8), bg=SURFACE, fg=SUB).pack(side="right", padx=10)

    # -- Area Scrollabile Principale --
    scroll_host = tk.Frame(root, bg=BG)
    scroll_host.pack(side="top", fill="both", expand=True)
    
    outer = tk.Canvas(scroll_host, bg=BG, highlightthickness=0)
    vsb = ttk.Scrollbar(scroll_host, orient="vertical", command=outer.yview)
    outer.configure(yscrollcommand=vsb.set)
    
    vsb.pack(side="right", fill="y")
    outer.pack(side="left", fill="both", expand=True)
    
    body = tk.Frame(outer, bg=BG)
    outer.create_window((0, 0), window=body, anchor="nw", tags="bodywin")

    def _sync_scroll(_e=None):
        try:
            outer.configure(scrollregion=outer.bbox("all"))
            outer.itemconfigure("bodywin", width=outer.winfo_width())
        except Exception:
            pass
    body.bind("<Configure>", lambda e: _sync_scroll())

    def _wheel(e):
        try:
            outer.yview_scroll(int(-e.delta / 120), "units")
        except Exception:
            pass
    outer.bind_all("<MouseWheel>", _wheel)

    # -- Progresso Corsa --
    prog = tk.Frame(body, bg=BG)
    prog.pack(fill="x", padx=16, pady=(12, 4))
    prog_lbl_var = tk.StringVar()
    tk.Label(prog, textvariable=prog_lbl_var, font=("Segoe UI", 9, "bold"),
             bg=BG, fg=SUB).pack(anchor="w")
    bar = tk.Canvas(prog, height=6, bg=TRACK, highlightthickness=0)
    bar.pack(fill="x", pady=(6, 0))

    # -- Card Prossima Fermata --
    nxt = tk.Frame(body, bg=CARD, highlightbackground=hexcol, highlightthickness=1, padx=12, pady=10)
    nxt.pack(fill="x", padx=16, pady=8)
    tk.Label(nxt, text="PROSSIMA FERMATA", font=("Segoe UI", 8, "bold"),
             bg=CARD, fg=SUB).pack(anchor="w")
    next_var = tk.StringVar()
    tk.Label(nxt, textvariable=next_var, font=("Segoe UI", 12, "bold"),
             bg=CARD, fg=TXT, wraplength=500, justify="left").pack(anchor="w", pady=(2, 0))

    # -- Griglia Azioni Rapide (Card Interattive) --
    actions = tk.Frame(body, bg=BG)
    actions.pack(fill="x", padx=16, pady=4)
    tk.Label(actions, text="AZIONI RAPIDE", font=("Segoe UI", 9, "bold"),
             bg=BG, fg=hexcol).pack(anchor="w", pady=(0, 6))
             
    grid = tk.Frame(actions, bg=BG)
    grid.pack(fill="x")
    match_var = tk.StringVar(value="")
    stats_box = tk.Frame(body, bg=CARD)

    def toast(msg, bad=False):
        (messagebox.showwarning if bad else messagebox.showinfo)("BC.Transporter", msg)

    def do_stats():
        try:
            d = get_json(f"{BASE}/api/stats/train/{urllib.parse.quote(cat)}/"
                         f"{urllib.parse.quote(num)}")
        except Exception as e:
            return toast(f"Statistiche non disponibili: {e}", bad=True)
        rep = (d.get("data") if isinstance(d, dict) else None) or d or {}
        m = rep.get("metrics") if isinstance(rep, dict) else None or {}
        ins = rep.get("insights") if isinstance(rep, dict) else None or {}
        for w in stats_box.winfo_children():
            w.destroy()
        tk.Label(stats_box, text="STATISTICHE TRENO", font=("Segoe UI", 9, "bold"),
                 bg=CARD, fg=SUB).pack(anchor="w", padx=12, pady=(10, 4))
        for k, v in [("Affidabilità", str(m.get("reliabilityScore", "—"))),
                     ("Trend", str(m.get("behaviorTrend", "—"))),
                     ("Ritardo medio", f"{m.get('averageNetDelayChangeMinutes', '—')} min"),
                     ("Cancellazioni", f"{m.get('cancellationRatePercentage', '—')}%"),
                     ("Viaggi analizzati", str(m.get("totalTripsAnalyzed", "—"))),
                     ("Giorno peggiore", str(ins.get("worstDayOfWeek", "—"))),
                     ("Stazione critica", str(ins.get("criticalBottleneckStation", "—")))]:
            r = tk.Frame(stats_box, bg=CARD)
            r.pack(fill="x", padx=12, pady=2)
            tk.Label(r, text=k, font=("Segoe UI", 9), bg=CARD, fg=SUB).pack(side="left")
            tk.Label(r, text=v, font=("Segoe UI", 9, "bold"), bg=CARD, fg=TXT).pack(side="right")
        tk.Frame(stats_box, bg=CARD, height=10).pack()
        stats_box.pack(fill="x", padx=16, pady=6)

    def do_map():
        try:
            d = get_json(f"{BASE}/api/track-trip/{urllib.parse.quote(trip_id)}")
        except Exception as e:
            return toast(f"Mappa non disponibile: {e}", bad=True)
        dd = (d.get("data") if isinstance(d, dict) else None) or d or {}
        pos = dd.get("trainPosition") if isinstance(dd, dict) else None
        msg = f"Fermate tracciate: {len(dd.get('stops', []) if isinstance(dd, dict) else [])}"
        if isinstance(pos, dict):
            msg += f"\nPosizione: {pos.get('lat')}, {pos.get('lng')}"
        toast(msg)

    def do_share():
        try:
            url = sheet_share_link(trip_id, country, state["trip"])
        except Exception as e:
            return toast(f"Condivisione fallita: {e}", bad=True)
        if not url:
            return toast("Condivisione fallita", bad=True)
        root.clipboard_clear()
        root.clipboard_append(url)
        toast(f"Link copiato negli appunti:\n{url}")

    def do_social():
        nick = simpledialog.askstring("Social", "Nickname:", parent=root)
        if not nick:
            return
        try:
            res = post_json(f"{BASE}/api/social/publish",
                            {"train_key": train_key,
                             "train": {"category": cat, "trainNumber": num,
                                       "origin": stop_name(state["trip"].get("origin")),
                                       "destination": stop_name(state["trip"].get("destination")),
                                       "country": country}, "nick": nick})
        except Exception as e:
            return toast(f"Social: {e}", bad=True)
        toast(f"Pubblicato: {res}")

    def do_save():
        os.makedirs(CACHE_DIR, exist_ok=True)
        out = cache_path("train", trip_id)
        okw = save_json_file(out, state["trip"])
        toast(f"Salvato offline:\n{out}" if okw else "Salvataggio fallito", bad=not okw)

    def do_fav():
        fav_add("train", {"number": num,
                          "origin": stop_name(state["trip"].get("origin")),
                          "destination": stop_name(state["trip"].get("destination")),
                          "name": f"Treno {num}"})
        toast("Aggiunto ai preferiti ⭐")

    def do_alerts():
        msgs = collect_messages(state["trip"])
        if not msgs:
            return toast("Nessun avviso per questo treno.")
        win = tk.Toplevel(root)
        win.title(f"Avvisi ({len(msgs)})")
        win.configure(bg=BG)
        txt = tk.Text(win, wrap="word", bg=CARD, fg=TXT, font=("Segoe UI", 10),
                      width=60, height=min(20, len(msgs) + 2))
        txt.pack(fill="both", expand=True, padx=12, pady=12)
        for m in msgs:
            txt.insert("end", f"• {m.get('text') or m}\n\n")
        txt.configure(state="disabled")

    def do_match():
        sts = [s for s in (state["trip"].get("stops") or []) if isinstance(s, dict)]
        payload = [{"stationName": s.get("station") or s.get("stop") or s.get("name"),
                    "arrival": str(s.get("arrival") or ""),
                    "departure": str(s.get("departure") or ""),
                    "platform": s.get("platform"), "country": country,
                    "cancelled": bool(s.get("cancelled"))} for s in sts]
        try:
            res = post_json(f"{BASE}/api/trains/match",
                            {"tripId": trip_id, "country": country, "stops": payload},
                            timeout=50)
        except Exception as e:
            return toast(f"Match: {e}", bad=True)
        d = res.get("data") if isinstance(res, dict) else None
        ms = d.get("matches", []) if isinstance(d, dict) else []
        okm = bool(isinstance(d, dict) and d.get("isMatched") and any(
            isinstance(x, dict) and x.get("matched") for x in ms))
        det = ", ".join(str((x if isinstance(x, dict) else {}).get("country", "?"))
                        for x in ms[:5])
        match_var.set(("✓ match: " + det) if okm else "nessun match")
        toast(("Match trovato: " + det) if okm else "Nessun match multi-paese.")

    for i, (label, fn) in enumerate([("📊 Statistiche", do_stats), ("🗺 Mappa", do_map),
                                     ("🔗 Condividi", do_share), ("👥 Social", do_social),
                                     ("💾 Salva", do_save), ("⚠ Avvisi", do_alerts),
                                     ("☆ Preferito", do_fav), ("🔔 Match", do_match)]):
        mkbtn(grid, label, CARD, cmd=fn).grid(row=i // 4, column=i % 4,
                                              padx=4, pady=4, sticky="ew")
    for c in range(4):
        grid.columnconfigure(c, weight=1)
    tk.Label(grid, textvariable=match_var, font=("Segoe UI", 9, "bold"),
             bg=BG, fg=WARN).grid(row=2, column=0, columnspan=4, sticky="w", pady=(4, 0))

    # -- Timeline Grafica --
    tk.Label(body, text="TIMELINE FERMATE", font=("Segoe UI", 9, "bold"),
             bg=BG, fg=hexcol).pack(anchor="w", padx=16, pady=(12, 4))
    canvas = tk.Canvas(body, bg=BG, highlightthickness=0, height=220)
    canvas.pack(fill="x", padx=16)

    def draw(data):
        sts = [s for s in (data.get("stops") or data.get("stopovers") or [])
               if isinstance(s, dict)]
        canvas.delete("all")
        if not sts:
            return 0, 0
        at, now, eff = position(sts)
        row_h, x0, y0 = 70, 50, 35
        h = y0 * 2 + row_h * max(len(sts) - 1, 0)
        canvas.configure(height=h)
        
        canvas.create_line(x0, y0, x0, y0 + row_h * max(len(sts) - 1, 0),
                           fill="#3A3A3A", width=3)
        cur_y = y0 + max(at, 0) * row_h if at >= 0 else y0
        if cur_y > y0:
            canvas.create_line(x0, y0, x0, cur_y, fill=hexcol, width=4)
            
        for i, s in enumerate(sts):
            y = y0 + i * row_h
            name = str(s.get("station") or s.get("stop") or s.get("stationName")
                       or s.get("name") or "?")
            arr = fmt_time(s.get("scheduledArrival") or s.get("arrival"))
            dep = fmt_time(s.get("scheduledDeparture") or s.get("departure") or s.get("time"))
            plat = str(s.get("platform") or s.get("actualPlatform") or "")
            try:
                dl = int(s.get("delay") or s.get("arrivalDelay") or s.get("departureDelay") or 0)
            except (TypeError, ValueError):
                dl = 0
            cancelled = s.get("cancelled") or s.get("canceled") or s.get("isCancelled")
            passed = at >= i and not (at == -1)
            is_cur = at == i and eff[at] is not None and (now - eff[at]).total_seconds() <= 180
            
            if cancelled:
                canvas.create_text(x0, y, text="✖", font=("Segoe UI", 14, "bold"), fill=ERR)
                fg, fnt = (ERR, ("Segoe UI", 10, "italic"))
            elif is_cur or (at == i and not cancelled):
                canvas.create_oval(x0 - 16, y - 16, x0 + 16, y + 16,
                                   outline=shade(hexcol, 1.4), width=2)
                canvas.create_oval(x0 - 10, y - 10, x0 + 10, y + 10,
                                   fill=hexcol, outline=hexcol)
                fg, fnt = (TXT, ("Segoe UI", 11, "bold"))
            elif passed:
                canvas.create_oval(x0 - 6, y - 6, x0 + 6, y + 6,
                                   fill="#7F8C8D", outline="#7F8C8D")
                fg, fnt = (SUB, ("Segoe UI", 10))
            else:
                canvas.create_oval(x0 - 6, y - 6, x0 + 6, y + 6,
                                   fill=BG, outline="#7F8C8D", width=2)
                fg, fnt = (TXT, ("Segoe UI", 10))
                
            canvas.create_text(x0 + 24, y - 9, text=name, anchor="w", font=fnt, fill=fg)
            sub = f"{arr}/{dep}" if arr != dep else arr
            if plat:
                sub += f"   •   bin {plat}"
            canvas.create_text(x0 + 24, y + 10, text=sub, anchor="w",
                               font=("Segoe UI", 8), fill=SUB)
            if dl:
                canvas.create_text(x0 + 440, y, text=f"+{dl}'",
                                   font=("Segoe UI", 9, "bold"),
                                   fill=delay_hex(dl), anchor="e")
            if at == -1 and i == 0:
                canvas.create_text(x0 + 440, y, text="🚂 non partito",
                                   font=("Segoe UI", 8, "bold"), fill=OK, anchor="e")
            elif at == len(sts) - 1 and i == len(sts) - 1:
                canvas.create_text(x0 + 440, y, text="🚂 arrivato",
                                   font=("Segoe UI", 8, "bold"), fill=OK, anchor="e")
            elif at == i and eff[at] is not None and (now - eff[at]).total_seconds() > 180:
                canvas.create_text(x0, y, text="🚂", font=("Segoe UI Emoji", 12))
        return at, len(sts)

    def refresh():
        try:
            data = train_trip_data(trip_id, country)
        except Exception:
            return
        state["trip"] = data
        at, n = draw(data)
        try:
            d = int(data.get("delay", 0) or 0)
        except (TypeError, ValueError):
            d = 0
        title_var.set(f"{data.get('line') or data.get('category') or line} "
                      f"{data.get('tripNumber') or data.get('trainNumber') or num}".strip())
        route_var.set(f"{stop_name(data.get('origin'))} → {stop_name(data.get('destination'))}")
        delay_var.set("IN ORARIO" if d <= 0 else f"+{d} MIN")
        delay_lbl.configure(bg=delay_hex(d))
        plat_var.set(f"BIN {data.get('platform')}" if data.get("platform") else "")
        done = max(at + 1, 0)
        prog_lbl_var.set(f"Fermate completate: {done} di {n}")
        bar.delete("all")
        bar_width = bar.winfo_width() or 500
        bar.create_rectangle(0, 0, bar_width * (done / max(n, 1)), 6,
                             fill=hexcol, outline="")
        if 0 <= at + 1 < n:
            sts = [s for s in (data.get("stops") or []) if isinstance(s, dict)]
            nx = sts[at + 1]
            nm = str(nx.get("station") or nx.get("stop") or nx.get("stationName")
                     or nx.get("name") or "?")
            pl = nx.get("platform") or ""
            next_var.set(f"{nm}" + (f"  •  binario {pl}" if pl else ""))
        elif at == n - 1:
            next_var.set("Treno arrivato a destinazione ✓")
        else:
            next_var.set("In attesa di partenza…")
        upLbl_var.set(f"Aggiornato {datetime.now().strftime('%H:%M:%S')}")

    def tick_viewers():
        if not alive["on"]:
            return
        try:
            if root.winfo_exists():
                res = post_json(f"{BASE}/api/train-presence/heartbeat",
                                {"clientId": client_id, "trainKey": train_key,
                                 "screen": "national",
                                 "train": {"category": cat, "trainNumber": num,
                                           "origin": stop_name(state["trip"].get("origin")),
                                           "destination": stop_name(state["trip"].get("destination")),
                                           "country": country, "tripId": trip_id}})
                v = res.get("viewers") if isinstance(res, dict) else None
                viewers_var.set(f"👁 {v} online" if isinstance(v, int) and v > 0 else "")
        except Exception:
            pass
        if alive["on"]:
            root.after(15000, tick_viewers)

    def auto():
        if not alive["on"]:
            return
        try:
            if root.winfo_exists() and alive["live"]:
                refresh()
        except Exception:
            pass
        if alive["on"]:
            root.after(30000, auto)

    refresh()
    tick_viewers()
    root.after(30000, auto)
    p_ok("Finestra timeline aperta con grafica moderna.")
    root.mainloop()

def train_trip(trip_id, country):
    p_title(f"🚂 Trip {trip_id} [{country}]")
    url = f"{TRAINBOARD}/{country}/trip?tripId={urllib.parse.quote(trip_id)}"
    p_dim(f"GET {url}")
    try:
        data = get_json(url)
    except Exception as e:
        return p_err(f"Errore trip: {e}")
    e = (data.get("data") if isinstance(data, dict) else None) or data or {}
    print(f"  {bold('Linea:')} {e.get('line') or e.get('category') or '—'}")
    print(f"  {bold('Destinazione:')} {stop_name(e.get('destination')) or '—'}")
    print_timeline(e.get("stops") or e.get("stopovers") or [])

def train_number(q):
    p_title(f'🔎 Treni live · filtro "{q}"')
    url = ("https://data.cuzimmartin.dev/train-map?north=85&south=-5&east=91"
           "&west=-64&duration=300&results=1000&polylines=false")
    p_dim(f"GET {url}")
    try:
        data = get_json(url)
    except Exception as e:
        return p_err(f"Errore mappa live: {e}")
    mov = data.get("movements", []) if isinstance(data, dict) else []
    term = q.lower()
    found = [m for m in mov if isinstance(m, dict)
             and term in f"{((m.get('line') or {}) if isinstance(m.get('line'), dict) else {}).get('name', '')} "
                        f"{((m.get('line') or {}) if isinstance(m.get('line'), dict) else {}).get('id', '')}".lower()]
    if not found:
        return p_warn("Nessun treno live corrisponde.")
    for m in found[:20]:
        line = m.get("line") if isinstance(m.get("line"), dict) else {}
        name = str(line.get("name") or line.get("id") or "?")
        cat = train_category(name, line.get("productName"))
        print(f"  {cat_paint(cat, name)}  "
              f"{short(m.get('destination') or m.get('tripId') or '', 30)}")
    p_dim(f"Trovati: {len(found)} (mostrati max 20)")

def fal(station_id):
    p_title(f"🟣 FAL · stazione {station_id}")
    url = f"{BASE}/api/fal/stop-updates?stationId={urllib.parse.quote(station_id)}"
    p_dim(f"GET {url}")
    try:
        data = get_json(url)
    except Exception as e:
        return p_err(f"Errore FAL: {e}")
    grouped = data.get("grouped") if isinstance(data, dict) else None
    if not isinstance(grouped, dict) or not grouped:
        return p_warn("Nessuna partenza FAL.")
    for dest, lst in grouped.items():
        print(f"\n  {c_fal('→ ' + dest)}")
        for item in (lst if isinstance(lst, list) else [])[:8]:
            if not isinstance(item, dict):
                continue
            trip = item.get("trip") if isinstance(item.get("trip"), dict) else {}
            stop = item.get("stopInfo") if isinstance(item.get("stopInfo"), dict) else {}
            t = fmt_time(stop.get("expected_passing_date"))
            rit = stop.get("ritardo") if isinstance(stop.get("ritardo"), int) else 0
            print(f"    {bold(t)}  {trip.get('LineCode') or trip.get('id_documento') or ''}  {delay_badge(rit)}")

# -- BUS ----------------------------------------------------------------------
def fetch_providers():
    data = get_json(f"{BASE}/config/bus_providers.json")
    provs = data.get("providers", []) if isinstance(data, dict) else []
    return [p for p in provs if isinstance(p, dict)]

def provider_country(p):
    if p.get("country"):
        return p["country"]
    prefix = str(p.get("apiPrefix") or "")
    return prefix.split("/")[0] if "/" in prefix else "it"

def resolve_country(provider, fallback="it"):
    try:
        for p in fetch_providers():
            if str(p.get("name", "")).lower() == provider.lower():
                return provider_country(p)
    except Exception:
        pass
    return fallback

def bus_providers():
    p_title("🚌 Provider bus disponibili")
    try:
        provs = fetch_providers()
    except Exception as e:
        return p_err(f"Errore providers: {e}")
    for p in provs:
        print(f"  {c_bus(str(p.get('name', '?')).ljust(18))} "
              f"{dim(provider_country(p))}  {short(p.get('provider') or p.get('city') or '', 30)}")
    p_dim(f"Totale: {len(provs)}")

def bus_lines(provider, paese):
    country = paese or resolve_country(provider)
    p_title(f"🚌 Linee · {provider} [{country}]")
    try:
        for page in (1, 2):
            url = f"{BASE}/api/{country}/bus/{provider}/lines?page={page}&chunkSize=100"
            data = get_json(url)
            if not isinstance(data, dict):
                break
            for line in (data.get("lines") or [])[:60]:
                if not isinstance(line, dict):
                    continue
                code = str(line.get("code") or line.get("line") or line.get("id") or "?")
                name = str(line.get("name") or line.get("description") or "")
                print(f"  {c_bus(code.ljust(10))} {short(name, 50)}")
            pag = data.get("pagination") if isinstance(data.get("pagination"), dict) else None
            if not pag or page >= int(pag.get("totalPages", 1)):
                break
    except Exception as e:
        return p_err(f"Errore linee: {e}")
    p_dim("Mostrate prime righe. Usa --fermate/--partenze per il live.")

def _fnum(v):
    try:
        return float(str(v))
    except (TypeError, ValueError):
        return 0.0

def norm_stop(s):
    return {"stopId": str(s.get("stop_id") or s.get("stopId") or s.get("id") or ""),
            "stopName": str(s.get("stop_name") or s.get("stopName") or s.get("name") or ""),
            "latitude": _fnum(s.get("stop_lat") or s.get("stopLat") or s.get("latitude") or s.get("lat") or 0),
            "longitude": _fnum(s.get("stop_lon") or s.get("stopLon") or s.get("longitude") or s.get("lng") or s.get("lon") or 0)}

def fetch_bus_stops(provider, paese):
    country = paese or resolve_country(provider)
    url = f"{BASE}/api/{country}/bus/{provider}/stops"
    data = get_json(url)
    lst = data if isinstance(data, list) else (data.get("stops", []) if isinstance(data, dict) else [])
    return country, url, [norm_stop(s) for s in lst if isinstance(s, dict)]

def bus_stops(provider, paese):
    country = paese or resolve_country(provider)
    p_title(f"🚌 Fermate · {provider} [{country}]")
    url = f"{BASE}/api/{country}/bus/{provider}/stops"
    p_dim(f"GET {url}")
    try:
        _, _, lst = fetch_bus_stops(provider, paese)
    except Exception as e:
        return p_err(f"Errore fermate: {e}")
    if not lst:
        return p_warn("Nessuna fermata.")
    for s in lst[:30]:
        sid = s.get("stopId") or "?"
        name = s.get("stopName") or "?"
        print(f"  {c_bus(sid.ljust(12))} {short(name, 48)}")
    p_dim(f"Totale: {len(lst)} (mostrate 30)")

def bus_departures(provider, stop_id, paese):
    country = paese or resolve_country(provider)
    p_title(f"🚌 Partenze fermata {stop_id} · {provider} [{country}]")
    url = (f"{BASE}/api/{country}/bus/{provider}/stops-updates"
           f"?stopId={urllib.parse.quote(stop_id)}")
    p_dim(f"GET {url}")
    try:
        data = get_json(url)
    except Exception as e:
        return p_err(f"Errore partenze bus: {e}")
    deps = data.get("departures", []) if isinstance(data, dict) else []
    if not deps:
        return p_warn("Nessuna partenza.")
    for d in deps[:25]:
        if not isinstance(d, dict):
            continue
        line = str(d.get("line") or d.get("route") or d.get("code") or "?")
        dest = str(d.get("destination") or d.get("headsign") or "—")
        t = fmt_time(d.get("expectedTime") or d.get("scheduledTime") or d.get("time"))
        print(f"  {bold(t.ljust(7))} {c_bus(line.ljust(10))} "
              f"{short(dest, 40)}  {delay_badge(d.get('delay', 0))}")
    p_dim(f"Totale: {len(deps)}")

def bus_vehicles(provider, paese):
    country = paese or resolve_country(provider)
    p_title(f"🚌 Veicoli live · {provider} [{country}]")
    url = f"{BASE}/api/{country}/bus/{provider}/vehicles"
    p_dim(f"GET {url}")
    try:
        data = get_json(url)
    except Exception as e:
        return p_err(f"Errore veicoli: {e}")
    lst = (data.get("entities", []) if isinstance(data, dict)
           else data if isinstance(data, list) else [])
    if not lst:
        return p_warn("Nessun veicolo live al momento.")
    for v in lst[:20]:
        if not isinstance(v, dict):
            continue
        print(f"  {c_bus(str(v.get('routeId') or v.get('line') or '?').ljust(10))} "
              f"veicolo {v.get('vehicleId') or v.get('id') or '?'}")
    p_dim(f"Totale: {len(lst)}")

# -- VOLI ---------------------------------------------------------------------
def flights_area():
    p_title("✈️ Radar voli · Italia")
    url = f"{BASE}/api/flightradar?bounds=47.5,35.0,6.0,19.0"
    p_dim(f"GET {url}")
    try:
        data = get_json(url)
    except Exception as e:
        return p_err(f"Errore radar: {e}")
    flights = data.get("flights", []) if isinstance(data, dict) else []
    if not flights:
        return p_warn("Nessun volo rilevato.")
    print(f"  {dim('VOLO'.ljust(10))} {dim('DA'.ljust(6))}→{dim('A'.ljust(6))} "
          f"{dim('ALT'.ljust(8))} {dim('VEL'.ljust(7))}")
    for f in flights[:25]:
        if not isinstance(f, dict):
            continue
        num = str(f.get("flightNumber") or f.get("callsign") or f.get("id") or "?")
        print(f"  {c_plane(num.ljust(10))} {str(f.get('origin') or '???').ljust(6)}→"
              f"{str(f.get('destination') or '???').ljust(6)} "
              f"{str(f.get('altitude', 0)).ljust(8)} {str(f.get('speed', 0)).ljust(7)}")
    p_dim(f"Totale: {len(flights)}")

def airport(iata, arrivi):
    typ = "arrivals" if arrivi else "departures"
    p_title(f"✈️ Aeroporto {iata} · {typ}")
    url = f"{BASE}/proxy/skyscanner/airport/{urllib.parse.quote(iata)}/{typ}"
    p_dim(f"GET {url}")
    try:
        data = get_json(url)
    except Exception as e:
        return p_err(f"Errore aeroporto: {e}")
    lst = data.get(typ, []) if isinstance(data, dict) else []
    if not lst:
        return p_warn("Nessun volo trovato.")
    for f in lst[:25]:
        if not isinstance(f, dict):
            continue
        num = str(f.get("flightNumber") or f.get("flight") or "?")
        other = str(f.get("origin") or f.get("destination") or f.get("airport") or "—")
        print(f"  {bold(fmt_time(f.get('scheduledTime') or f.get('time')).ljust(7))} "
              f"{c_plane(num.ljust(12))} {other}")
    p_dim(f"Totale: {len(lst)}")

# -- FLIXBUS ------------------------------------------------------------------
def fetch_flix_stations(q):
    return as_list(get_json(f"{FLIX}/stations?query={urllib.parse.quote(q)}"))

def flix_stations(q):
    p_title(f'🟢 Flixbus · stazioni "{q}"')
    try:
        lst = fetch_flix_stations(q)
    except Exception as e:
        return p_err(f"Errore Flixbus: {e}")
    if not lst:
        return p_warn("Nessuna stazione Flixbus.")
    for s in lst[:15]:
        if isinstance(s, dict):
            print(f"  {ok(str(s.get('name', '?')))}  {dim('id=' + str(s.get('id', '?')))}")
    return lst

def flix_departures(station_id):
    p_title(f"🟢 Flixbus · partenze {station_id}")
    try:
        lst = as_list(get_json(f"{FLIX}/departures?stationId={urllib.parse.quote(station_id)}"))
    except Exception as e:
        return p_err(f"Errore Flixbus: {e}")
    if not lst:
        return p_warn("Nessuna partenza.")
    for d in lst[:20]:
        if not isinstance(d, dict):
            continue
        print(f"  {bold(fmt_time(d.get('scheduledTime') or d.get('time')).ljust(7))} "
              f"{ok(str(d.get('line', '?')).ljust(10))} {short(d.get('destination', '—'), 40)}")

def flix_trip(trip_id):
    p_title(f"🟢 Flixbus · trip {trip_id}")
    try:
        data = get_json(f"{FLIX}/trip?tripId={urllib.parse.quote(trip_id)}")
    except Exception as e:
        return p_err(f"Errore Flixbus trip: {e}")
    e = (data.get("data") if isinstance(data, dict) else None) or data or {}
    stops = e.get("stops", []) if isinstance(e, dict) else []
    if not stops:
        return p_warn("Trip non trovato.")
    for s in stops:
        if isinstance(s, dict):
            print(f"  {dim(fmt_time(s.get('scheduledTime') or s.get('time')))}  "
                  f"{s.get('name') or s.get('station') or '?'}")

# -- CONFIG / STATS / LOGHI ---------------------------------------------------
def config_show():
    p_title("⚙️ Config trasporti (+ fallback come ApiService)")
    try:
        data = fetch_config()
    except Exception as e:
        return p_err(f"Errore config: {e}")
    if data.get("_fallback"):
        p_warn(f"Server non raggiungibile, uso default ({data.get('_error')})")
    for t in (data.get("transports") or []):
        print(f"  {ok(str(t.get('name', '?')).ljust(18))} {dim(str(t.get('type', '')))}  id={t.get('id', '?')}")
    if not (data.get("transports") or []):
        p_dim(f"Risposta grezza: {short(data, 200)}")
        sys_data = data.get("systemEndpoints") or data.get("system_endpoints") or {}
        if isinstance(sys_data, dict) and sys_data:
            for k, v in sys_data.items():
                print(f"  {ok(k)}: {short(v, 80)}")
    p_dim(f"Totale: {len(data.get('transports') or [])}")

def stats_general():
    p_title("📊 Statistiche generali treni")
    try:
        data = get_json(f"{BASE}/api/stats/trains/general")
    except Exception as e:
        return p_err(f"Errore stats: {e}")
    d = (data.get("data") if isinstance(data, dict) else None) or data
    print(json.dumps(d, ensure_ascii=False, indent=2)[:2000])

def stats_lines():
    p_title("📊 Statistiche per linea")
    try:
        data = get_json(f"{BASE}/api/stats/trains/lines")
    except Exception as e:
        return p_err(f"Errore stats linee: {e}")
    for s in as_list(data)[:20]:
        print(f"  {short(s if isinstance(s, dict) else str(s), 80)}")

def train_logos():
    p_title("🎨 Loghi vettori treni")
    try:
        data = get_json(f"{BASE}/api/train-logos")
    except Exception as e:
        return p_err(f"Errore loghi: {e}")
    src = (data.get("official") if isinstance(data, dict) else None) or {}
    for k in list(src)[:20]:
        print(f"  {ok(k)}")
    p_dim(f"Totale official: {len(src)}")

# -- TRENI extra --------------------------------------------------------------
def train_search_direct(q):
    p_title(f'🚂 Ricerca diretta RFI · "{q}"')
    url = f"{BASE}/proxy/viaggiatreno?q={urllib.parse.quote(q)}"
    p_dim(f"GET {url}")
    try:
        data = get_json(url)
    except Exception as e:
        return p_err(f"Errore: {e}")
    for e in (data if isinstance(data, list) else [])[:10]:
        print(f"  {c_train(str(e.get('nomestazione', '?')))}  {dim('cod=' + str(e.get('codStazione', '?')))}")

def train_board_rfi(station_id, arrivi):
    ep = "rfi-arrivals" if arrivi else "rfi-departures"
    p_title(f"🚂 RFI {'arrivi' if arrivi else 'partenze'} · {station_id}")
    url = f"{BASE}/api/{ep}?placeId={urllib.parse.quote(station_id)}"
    p_dim(f"GET {url}")
    try:
        lst = as_list(get_json(url))
    except Exception as e:
        return p_err(f"Errore RFI: {e}")
    for raw in lst[:20]:
        e = raw if isinstance(raw, dict) else {}
        print(f"  {bold(fmt_time(e.get('scheduledTime') or e.get('time')).ljust(7))} "
              f"{c_train(str(e.get('tripNumber') or e.get('trainNumber') or '?').ljust(10))} "
              f"{short((e.get('origin') if arrivi else e.get('destination')) or e.get('stationName'), 34)}")

def train_details_rfi(numero):
    p_title(f"🚂 Dettaglio RFI treno {numero}")
    try:
        data = get_json(f"{BASE}/api/rfi-train/{urllib.parse.quote(numero)}")
    except Exception as e:
        return p_err(f"Errore: {e}")
    e = (data.get("data") if isinstance(data, dict) else None) or data or {}
    print(f"  {bold('Destinazione:')} {e.get('destination') or '—'}")
    for s in ((e.get("stops") or e.get("stopovers") or []) if isinstance(e, dict) else [])[:30]:
        if isinstance(s, dict):
            print(f"    {dim(fmt_time(s.get('time') or s.get('departure')))}  "
                  f"{s.get('station') or s.get('stop') or s.get('name') or '?'}")

def train_share(trip_id, country):
    p_title(f"🔗 Condividi trip {trip_id} [{country}]")
    try:
        data = get_json(f"{TRAINBOARD}/{country}/trip?tripId={urllib.parse.quote(trip_id)}")
    except Exception as e:
        return p_err(f"Fetch trip: {e}")
    e = (data.get("data") if isinstance(data, dict) else None) or data or {}
    payload = {"tripId": trip_id, "country": country,
               "tripNumber": e.get("tripNumber") or e.get("trainNumber"),
               "origin": e.get("origin"), "destination": e.get("destination"),
               "platform": e.get("platform"), "delay": e.get("delay", 0),
               "scheduledTime": str(e.get("scheduledTime") or ""),
               "estimatedTime": str(e.get("estimatedTime") or ""),
               "stops": e.get("stops") or e.get("stopovers") or []}
    try:
        res = post_json(f"{BASE}/api/share-trip", payload)
    except Exception as e:
        return p_err(f"Share: {e}")
    sid = res.get("shareId") if isinstance(res, dict) else None
    if sid:
        p_ok(f"URL: {BASE}/share/?id={sid}")
    else:
        p_warn("Condivisione fallita.")

def train_open_share(share_id):
    p_title(f"🔗 Apri share {share_id}")
    try:
        data = get_json(f"{BASE}/api/share-trip/{urllib.parse.quote(share_id)}", timeout=12)
    except Exception as e:
        return p_err(f"Errore: {e}")
    print(f"  {bold('Tratta:')} {data.get('origin', '?')} → {data.get('destination', '?')}")
    for s in (data.get("stops") or [])[:30]:
        if isinstance(s, dict):
            print(f"    {s.get('stationName') or s.get('name') or '?'}")

def train_match(trip_id, country):
    p_title(f"🧩 Match trip {trip_id} [{country}]")
    try:
        data = get_json(f"{TRAINBOARD}/{country}/trip?tripId={urllib.parse.quote(trip_id)}")
    except Exception as e:
        return p_err(f"Fetch trip: {e}")
    e = (data.get("data") if isinstance(data, dict) else None) or data or {}
    stops = []
    for s in (e.get("stops") or e.get("stopovers") or []):
        if isinstance(s, dict):
            stops.append({"stationName": s.get("station") or s.get("stop") or s.get("name"),
                          "arrival": str(s.get("arrival") or ""), "departure": str(s.get("departure") or ""),
                          "platform": s.get("platform"), "country": country})
    try:
        res = post_json(f"{BASE}/api/trains/match",
                        {"tripId": trip_id, "country": country, "stops": stops}, timeout=50)
    except Exception as e:
        return p_err(f"Match: {e}")
    print(json.dumps(res, ensure_ascii=False, indent=2)[:2000])

def train_live():
    p_title("📡 Treni live (snapshot /api/trains/live)")
    try:
        data = get_json(f"{BASE}/api/trains/live", timeout=10)
    except Exception as e:
        return p_err(f"Errore live: {e}")
    lst = as_list(data) if not isinstance(data, list) else data
    if isinstance(data, dict) and isinstance(data.get("trains"), list):
        lst = data["trains"]
    for t in lst[:20]:
        if isinstance(t, dict):
            print(f"  {c_train(str(t.get('trip_number') or t.get('tripNumber') or '?').ljust(10))} "
                  f"{short(t.get('destination') or t.get('trip_id') or '', 36)}")
    p_dim(f"Totale: {len(lst)}")

def train_track(trip_id):
    p_title(f"🗺️ Traccia trip {trip_id}")
    try:
        data = get_json(f"{BASE}/api/track-trip/{urllib.parse.quote(trip_id)}")
    except Exception as e:
        return p_err(f"Errore track: {e}")
    d = (data.get("data") if isinstance(data, dict) else None) or data or {}
    pos = d.get("trainPosition") if isinstance(d, dict) else None
    if isinstance(pos, dict):
        print(f"  {bold('Posizione:')} {pos.get('lat')}, {pos.get('lng')}")
    stops = d.get("stops", []) if isinstance(d, dict) else []
    for s in stops[:25]:
        if isinstance(s, dict):
            print(f"    {s.get('stationName') or s.get('name') or '?'}")

def train_routing(frm, to, date, time_, provider="eurail"):
    from datetime import datetime, timezone
    p_title(f"🧭 Itinerario {frm} → {to} il {date} ore {time_}")
    body = {"provider": provider, "from": frm, "to": to, "date": date, "time": time_,
            "tripsNumber": 5, "travellers": 1, "currency": "EUR",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "arrival": False, "minChangeTime": 1, "order": "DEPARTURE_DATE",
            "limit": 10, "offset": 0}
    try:
        res = post_json(f"{BASE}/api/trains/routing", body, timeout=40)
    except Exception as e:
        return p_err(f"Routing: {e}")
    routes = res.get("routes") or res.get("data") or res.get("results") or []
    if isinstance(routes, list):
        for r in routes[:5]:
            print(f"  {short(r if isinstance(r, dict) else str(r), 100)}")
    else:
        print(json.dumps(res, ensure_ascii=False, indent=2)[:2000])

def stats_train(category, number):
    p_title(f"📊 Comportamento treno {category} {number}")
    try:
        data = get_json(f"{BASE}/api/stats/train/{urllib.parse.quote(category)}/{urllib.parse.quote(number)}")
    except Exception as e:
        return p_err(f"Errore (404 = nessun dato): {e}")
    print(json.dumps((data.get("data") if isinstance(data, dict) else data), ensure_ascii=False, indent=2)[:2000])

def stats_station(station_id, period="today"):
    p_title(f"📊 Stazione {station_id} [{period}]")
    q = "" if period == "today" else f"?period={urllib.parse.quote(period)}"
    try:
        data = get_json(f"{BASE}/api/stats/station/{urllib.parse.quote(station_id)}{q}", timeout=30)
    except Exception as e:
        return p_err(f"Errore: {e}")
    d = (data.get("data") if isinstance(data, dict) else None) or data or {}
    for k in ("general", "stationRating", "categoryDistribution"):
        if isinstance(d, dict) and k in d:
            print(f"  {bold(k + ':')} {short(d[k], 100)}")

def monitor_check(station_id):
    try:
        data = get_json(f"{BASE}/api/stats/monitor/check/{urllib.parse.quote(station_id)}", timeout=5)
        p_ok(f"Monitorata: {data}") if (data.get("isMonitored") if isinstance(data, dict) else False) else p_warn("Non monitorata.")
    except Exception as e:
        p_err(f"Errore: {e}")

def monitor_add(station_id, name, country):
    try:
        post_json(f"{BASE}/api/stats/monitor/add",
                  {"stationId": station_id, "name": name, "country": country}, timeout=10)
        p_ok("Monitoraggio aggiunto.")
    except Exception as e:
        p_err(f"Errore: {e}")

def search_train_stats(q):
    p_title(f'🔎 Statistiche treno · "{q}"')
    try:
        data = get_json(f"{BASE}/api/stats/search/train?q={urllib.parse.quote(q)}", timeout=10)
    except Exception as e:
        return p_err(f"Errore: {e}")
    for t in as_list(data)[:15]:
        print(f"  {short(t if isinstance(t, dict) else str(t), 90)}")

def train_countries():
    p_title("🌍 Paesi treni (scegli col numero)")
    try:
        data = get_json("https://prod.cuzimmartin.dev/api/providers", timeout=10)
    except Exception as e:
        return p_err(f"Errore: {e}")
    grouped = []
    if isinstance(data, dict):
        d = data.get("data") if isinstance(data.get("data"), dict) else data
        if isinstance(d, dict) and isinstance(d.get("grouped"), list):
            grouped = d["grouped"]
        elif isinstance(d, list):
            grouped = d
    entries = []
    for g in grouped:
        if not isinstance(g, dict):
            continue
        code = str(g.get("regionCode") or g.get("countryCode") or "?")
        provs = g.get("providers") if isinstance(g.get("providers"), list) else []
        name = ""
        if provs and isinstance(provs[0], dict):
            name = str(provs[0].get("displayName") or provs[0].get("name") or "")
        entries.append({"n": len(entries) + 1, "code": code, "name": name})
    for code, name in (("GLOBAL", "ricerca globale"),
                       ("UK_LONDON", "Londra"),
                       ("FAL", "Ferrovie Appulo Lucane")):
        if not any(e["code"] == code for e in entries):
            entries.append({"n": len(entries) + 1, "code": code, "name": name})
    for e in entries:
        print(f"  {c_train('[' + str(e['n']) + ']')} {bold(e['code'].ljust(18))} {dim(e['name'])}")
    save_json_file(os.path.join(HOME, ".bc_cli_countries.json"),
                   {"entries": entries})
    p_dim("Esempio: treni --cerca \"bari\" --paese IT   ·   nel menu interattivo basta il numero.")
    return entries

def country_from_number(n):
    try:
        num = int(str(n).strip())
    except (TypeError, ValueError):
        return None
    data = load_json_file(os.path.join(HOME, ".bc_cli_countries.json"), {})
    for e in data.get("entries", []):
        if e.get("n") == num:
            return e.get("code")
    return None

def presence(cmd, key="", limit=20):
    if cmd == "live":
        p_title("👁️ Treni seguiti live (presence)")
        try:
            data = get_json(f"{BASE}/api/train-presence/live")
            print(json.dumps(data, ensure_ascii=False, indent=2)[:2000])
        except Exception as e:
            p_err(f"Errore: {e}")
    elif cmd == "recent":
        p_title("👁️ Treni recenti")
        try:
            data = get_json(f"{BASE}/api/train-presence/recent?limit={limit}")
            print(json.dumps(data, ensure_ascii=False, indent=2)[:2000])
        except Exception as e:
            p_err(f"Errore: {e}")
    elif cmd == "viewers":
        try:
            data = get_json(f"{BASE}/api/train-presence/viewers?trainKey={urllib.parse.quote(key)}", timeout=8)
            p_info(f"Spettatori {key}: {data}")
        except Exception as e:
            p_err(f"Errore: {e}")
    elif cmd == "heartbeat":
        import time
        p_title(f"💓 Heartbeat {key} (3 battiti ogni 5s, come i sheet)")
        for i in range(3):
            try:
                res = post_json(f"{BASE}/api/train-presence/heartbeat",
                                {"clientId": f"cli-{os.getpid()}", "trainKey": key, "screen": "cli"})
                p_ok(f"battito {i + 1}: {res}")
            except Exception as e:
                p_err(f"battito {i + 1}: {e}")
            time.sleep(5)
        try:
            post_json(f"{BASE}/api/train-presence/leave",
                      {"clientId": f"cli-{os.getpid()}", "trainKey": key})
            p_dim("leave inviato.")
        except Exception:
            pass

# -- REGIONALI ----------------------------------------------------------------
def reg_providers(country):
    p_title(f"🏳️ Provider regionali · {country}")
    try:
        data = get_json(f"{BASE}/api/train/regional_providers/{urllib.parse.quote(country)}")
    except Exception as e:
        return p_err(f"Errore: {e}")
    provs = (data.get("providers") if isinstance(data, dict) else None) or as_list(data)
    for p in provs:
        if isinstance(p, dict):
            print(f"  {ok(str(p.get('name') or p.get('key') or '?'))}  {dim(str(p.get('apiPrefix') or ''))}")
    p_dim(f"Totale: {len(provs)}")

def reg_base(country, prefix):
    return f"{BASE}/api/{prefix.strip('/')}"

def reg_stations(country, prefix, q=""):
    base = reg_base(country, prefix)
    url = f"{base}/stations?limit=100" if not q else f"{base}/stations?query={urllib.parse.quote(q)}&limit=50"
    p_title(f"🏳️ Stazioni regionali {prefix} · '{q}'")
    p_dim(f"GET {url}")
    try:
        data = get_json(url)
    except Exception as e:
        return p_err(f"Errore: {e}")
    for s in as_list(data)[:20]:
        if isinstance(s, dict):
            print(f"  {ok(str(s.get('name') or s.get('stationName') or '?'))}  "
                  f"{dim('id=' + str(s.get('id') or s.get('stationId') or '?'))}")

def reg_board(country, prefix, station_id, arrivi):
    base = reg_base(country, prefix)
    ep = "arrivals" if arrivi else "departures"
    p_title(f"🏳️ {ep} regionali · {station_id}")
    try:
        lst = as_list(get_json(f"{base}/{ep}?stationId={urllib.parse.quote(station_id)}"))
    except Exception as e:
        return p_err(f"Errore: {e}")
    for raw in lst[:20]:
        e = raw if isinstance(raw, dict) else {}
        print(f"  {bold(fmt_time(e.get('scheduledTime') or e.get('time')).ljust(7))} "
              f"{ok(str(e.get('tripNumber') or e.get('trainNumber') or '?').ljust(10))} "
              f"{short((e.get('origin') if arrivi else e.get('destination')) or e.get('stationName'), 34)}")

def reg_news(country, prefix):
    p_title(f"📰 News {prefix}")
    try:
        data = get_json(f"{reg_base(country, prefix)}/news")
    except Exception as e:
        return p_err(f"Errore: {e}")
    for n in as_list(data)[:15]:
        if isinstance(n, dict):
            print(f"  [{warn(str(n.get('severity', 'info')))}] {n.get('title') or n.get('shortTitle')}")

def reg_trip(country, prefix, trip_id):
    base = reg_base(country, prefix)
    p_title(f"🏳️ Trip regionale {trip_id}")
    for url in (f"{base}/trip/{urllib.parse.quote(trip_id)}",
                f"{base}/trip?tripId={urllib.parse.quote(trip_id)}"):
        try:
            data = get_json(url, timeout=12)
            d = (data.get("data") if isinstance(data, dict) else None) or data or {}
            stops = (d.get("stops") or []) if isinstance(d, dict) else []
            if stops:
                for s in stops[:30]:
                    if isinstance(s, dict):
                        print(f"    {dim(fmt_time(s.get('time') or s.get('departure')))}  "
                              f"{s.get('station') or s.get('name') or '?'}")
                return
        except Exception as e:
            p_dim(f"skip {url}: {e}")
    p_warn("Trip non trovato.")

# -- BUS extra ----------------------------------------------------------------
def bus_solutions(from_stop, to_stop, provider="bari", paese="it"):
    p_title(f"🧭 Soluzioni bus {from_stop} → {to_stop} [{provider}]")
    try:
        stops = get_json(f"{BASE}/api/{paese}/bus/{provider}/stops")
        raw = stops if isinstance(stops, list) else stops.get("stops", [])
        lst = [norm_stop(s) for s in raw if isinstance(s, dict)]
        f = next((s for s in lst if s["stopId"] == from_stop), None)
        t = next((s for s in lst if s["stopId"] == to_stop), None)
        if not f or not t:
            return p_err("Fermate non trovate.")
        from datetime import datetime
        ms = int(datetime.now().timestamp() * 1000)
        body = {"action": "FindTPSolutions",
                "PuntoOrigine": {"Formato": 0, "Lat": f["latitude"], "Lng": f["longitude"]},
                "PuntoDestinazione": {"Formato": 0, "Lat": t["latitude"], "Lng": t["longitude"]},
                "DataPartenza": f"/Date({ms}+0100)/", "OraDa": f"/Date({ms}+0100)/",
                "NumMaxSoluzioni": 8, "NumeroAdulti": 1, "NumeroRagazzi": 0,
                "FiltroModalita": [0, 2, 1, 3, 15], "Ambiente": {"Ambiti": [0, 1, 2]},
                "TipoPercorso": 0, "Intermodale": False, "ActivateRunsOnNextDay": True}
        res = post_json(f"{BASE}/api/{paese}/bus/{provider}/solutions", body)
        for s in (res.get("Oggetti") or [])[:8]:
            print(f"  {short(s, 110)}")
    except Exception as e:
        p_err(f"Errore soluzioni: {e}")

def bus_solution_detail(solution_id, provider="bari", paese="it"):
    try:
        res = post_json(f"{BASE}/api/{paese}/bus/{provider}/solutions",
                        {"action": "GetTPSolutionDetail", "IdSoluzione": solution_id})
        print(json.dumps(res, ensure_ascii=False, indent=2)[:2000])
    except Exception as e:
        p_err(f"Errore: {e}")

def bus_realtime(provider, vehicle_id, trip_id, paese=""):
    country = paese or resolve_country(provider)
    p_title(f"🛰️ Realtime {provider} veicolo {vehicle_id} trip {trip_id}")
    urls = [f"{BASE}/api/{country}/bus/{provider}/realtime?vehicleId={urllib.parse.quote(vehicle_id)}"
            f"&tripId={urllib.parse.quote(trip_id)}&vehicles=true",
            f"{BASE}/api/{country}/bus/{provider}/realtime?routeId={urllib.parse.quote(vehicle_id)}"
            f"&tripId={urllib.parse.quote(trip_id)}"]
    for url in urls:
        try:
            data = get_json(url)
            vehs = (data.get("vehicles") or []) if isinstance(data, dict) else []
            if vehs:
                v = vehs[0]
                print(f"  {bold('Destinazione:')} {v.get('destination') or '—'}")
                for s in (v.get("stops") or [])[:25]:
                    if isinstance(s, dict):
                        print(f"    {s.get('stopName') or s.get('stopId')}  "
                              f"{s.get('expectedTime') or ''}  ritardo={s.get('delay', 0)}")
                return
        except Exception as e:
            p_dim(f"skip: {e}")
    p_warn("Nessun dato realtime.")

def bus_trip_stops(provider, trip_id, paese=""):
    country = paese or resolve_country(provider)
    p_title(f"🚌 Fermate corsa {trip_id} [{provider}]")
    try:
        data = get_json(f"{BASE}/api/{country}/bus/{provider}/trip-stops?tripId={urllib.parse.quote(trip_id)}")
    except Exception as e:
        return p_err(f"Errore: {e}")
    for s in ((data.get("stops") or []) if isinstance(data, dict) else [])[:30]:
        if isinstance(s, dict):
            print(f"  {s.get('stopName') or s.get('stopId') or '?'}")

def bus_route_path(provider, trip_id, paese=""):
    country = paese or resolve_country(provider)
    try:
        data = get_json(f"{BASE}/api/{country}/bus/{provider}/route-path?tripId={urllib.parse.quote(trip_id)}")
        pts = (data.get("points") or data.get("path") or []) if isinstance(data, dict) else []
        p_ok(f"Percorso {trip_id}: {len(pts)} punti.")
    except Exception as e:
        p_err(f"Errore: {e}")

def bus_static(provider, paese=""):
    import urllib.request as ur
    country = paese or resolve_country(provider)
    url = f"{BASE}/api/{country}/bus/{provider}/stops-updates?static=true"
    p_title(f"💾 Pacchetto offline {provider} [{country}]")
    p_dim(f"GET {url}")
    try:
        req = ur.Request(url, headers=HEADERS)
        with ur.urlopen(req, timeout=60) as res:
            total = int(res.headers.get("Content-Length") or 0)
            buf, got = bytearray(), 0
            while True:
                chunk = res.read(65536)
                if not chunk:
                    break
                buf += chunk
                got += len(chunk)
                pct = (got / total * 100) if total else min(98.0, got / 200000 * 100)
                print(f"\r  {pct:5.1f}%  {got // 1024} KB", end="", flush=True)
            print()
        data = json.loads(bytes(buf).decode("utf-8"))
        out = cache_path("bus", f"{provider}_static")
        os.makedirs(CACHE_DIR, exist_ok=True)
        save_json_file(out, data)
        p_ok(f"Salvato in {out}")
    except Exception as e:
        p_err(f"Errore: {e}")

# -- VOLI extra ---------------------------------------------------------------
def fetch_airports(q):
    url = ("https://www.skyscanner.it/g/autosuggest-search/api/v1/search-flight/IT/it-IT/"
           f"{urllib.parse.quote(q)}?isDestination=true&autosuggestExp=")
    data = get_json(url)
    return url, [it for it in (data if isinstance(data, list) else [])
                 if isinstance(it, dict) and it.get("PlaceId") and len(str(it["PlaceId"])) == 3]

def search_airports(q):
    p_title(f'✈️ Aeroporti · "{q}"')
    if len(q) < 2:
        return p_warn("Scrivi almeno 2 caratteri.")
    try:
        url, lst = fetch_airports(q)
    except Exception as e:
        return p_err(f"Errore autosuggest: {e}")
    p_dim(f"GET {url}")
    n = 0
    for it in lst[:15]:
        print(f"  {c_plane(str(it['PlaceId']))}  {it.get('PlaceName') or it.get('name')} "
              f"{dim(str(it.get('CityName') or ''))}")
        n += 1
    if not n:
        p_warn("Nessun aeroporto (codice IATA di 3 lettere).")
    return lst

# -- STRADE -------------------------------------------------------------------
def road_news(paese="it", highways=""):
    p_title(f"🛣️ News strade [{paese}]")
    q = f"?highways={urllib.parse.quote(highways)}" if highways else ""
    try:
        data = get_json(f"{BASE}/api/roadways/{paese}/news{q}")
    except Exception as e:
        return p_err(f"Errore: {e}")
    for n in ((data.get("data") or []) if isinstance(data, dict) else [])[:15]:
        if isinstance(n, dict):
            print(f"  [{warn(str(n.get('severity', n.get('type', 'news'))))}] "
                  f"{n.get('title') or n.get('event')} {dim(str(n.get('motorwayName') or n.get('location') or ''))}")

def road_tolls(paese="it"):
    p_title(f"🛣️ Caselli [{paese}]")
    try:
        data = get_json(f"{BASE}/api/roadways/{paese}/tolls")
    except Exception as e:
        return p_err(f"Errore: {e}")
    d = (data.get("data") if isinstance(data, dict) else None) or data
    if isinstance(data, dict) and data.get("note"):
        p_info(str(data["note"]))
    tolls = (d.get("tolls") if isinstance(d, dict) else d) or []
    for t in tolls[:15]:
        print(f"  {short(t if isinstance(t, dict) else str(t), 90)}")

def road_services(paese="it", highway=""):
    p_title(f"⛽ Aree di servizio [{paese}] {highway}")
    path = f"/api/roadways/{paese}/services/{urllib.parse.quote(highway.upper())}" if highway \
        else f"/api/roadways/{paese}/services"
    try:
        data = get_json(f"{BASE}{path}")
    except Exception as e:
        return p_err(f"Errore: {e}")
    for s in ((data.get("data") or []) if isinstance(data, dict) else [])[:15]:
        print(f"  {short(s if isinstance(s, dict) else str(s), 100)}")

# -- METEO --------------------------------------------------------------------
def meteo_search(q):
    p_title(f'🏙️ Città · "{q}"')
    try:
        data = get_json(f"https://geocoding-api.open-meteo.com/v1/search?name={urllib.parse.quote(q)}"
                        f"&count=10&language=it&format=json", timeout=8)
    except Exception as e:
        return p_err(f"Errore geocoding: {e}")
    for r in (data.get("results") or [])[:10]:
        print(f"  {ok(r.get('name', '?'))}  {dim(str(r.get('country') or ''))}  "
              f"lat={r.get('latitude')} lon={r.get('longitude')}")

def meteo_now(city="Roma", lat=41.9028, lon=12.4964):
    p_title(f"🌤️ Meteo {city} ({lat},{lon})")
    try:
        data = get_json(f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}"
                        f"&current_weather=true&hourly=precipitation_probability&forecast_days=1&timezone=auto",
                        timeout=8)
    except Exception as e:
        return p_err(f"Errore meteo: {e}")
    cw = data.get("current_weather") or {}
    print(f"  {bold(str(cw.get('temperature', '?')) + '°C')}  vento {cw.get('windspeed', '?')} km/h  "
          f"codice {cw.get('weathercode', '?')}")

# -- SOCIAL -------------------------------------------------------------------
def social_feed(limit=30):
    p_title("💬 Social feed")
    try:
        data = get_json(f"{BASE}/api/social/feed?limit={limit}", timeout=10)
    except Exception as e:
        return p_err(f"Errore feed: {e}")
    for t in ((data.get("topics") or []) if isinstance(data, dict) else [])[:15]:
        if isinstance(t, dict):
            print(f"  [{ok(str(t.get('id', '?')))}] {t.get('title') or t.get('train_key') or ''}  "
                  f"{dim(str(t.get('nick') or ''))}")

def social_publish(train_key, nick, number="", origin="", dest=""):
    try:
        res = post_json(f"{BASE}/api/social/publish",
                        {"train_key": train_key, "train": {"category": "SOCIAL", "trainNumber": number,
                         "origin": origin, "destination": dest, "country": "IT"}, "nick": nick})
        print(json.dumps(res, ensure_ascii=False, indent=2)[:1000])
    except Exception as e:
        p_err(f"Publish: {e}")

def social_topic(topic_id, limit=50):
    try:
        data = get_json(f"{BASE}/api/social/topics/{topic_id}/messages?limit={limit}")
    except Exception as e:
        return p_err(f"Errore: {e}")
    for m in ((data.get("messages") or []) if isinstance(data, dict) else [])[:30]:
        if isinstance(m, dict):
            print(f"  {bold(str(m.get('nick', '?')) + ':')} {m.get('text', '')}")

def social_send(topic_id, nick, text):
    try:
        res = post_json(f"{BASE}/api/social/topics/{topic_id}/message",
                        {"nick": nick, "text": text[:500]})
        p_ok(f"Inviato: {res}")
    except Exception as e:
        p_err(f"Send: {e}")

def social_like(topic_id, nick):
    try:
        res = post_json(f"{BASE}/api/social/topics/{topic_id}/message".replace("/message", "/like"),
                        {"nick": nick})
        p_ok(f"Like: {res}")
    except Exception as e:
        p_err(f"Like: {e}")

def social_delete(topic_id, nick):
    try:
        status, res = api_delete(f"{BASE}/api/social/topics/{topic_id}", {"nick": nick})
        p_ok("Topic eliminato.") if status == 200 else p_warn(f"Non eliminato: {res}")
    except Exception as e:
        p_err(f"Delete: {e}")

def social_user(nick):
    try:
        data = get_json(f"{BASE}/api/social/users/{urllib.parse.quote(nick)}/stats")
        print(json.dumps(data, ensure_ascii=False, indent=2)[:1000])
    except Exception as e:
        p_err(f"Errore: {e}")

def social_leaderboard(period="week"):
    try:
        data = get_json(f"{BASE}/api/social/leaderboard?period={period}&limit=50")
        for e in ((data.get("entries") or []) if isinstance(data, dict) else [])[:15]:
            print(f"  {short(e if isinstance(e, dict) else str(e), 80)}")
    except Exception as e:
        p_err(f"Errore: {e}")

def social_online():
    try:
        data = get_json(f"{BASE}/api/active-connections")
        p_info(f"Connessioni attive: {data.get('activeConnections', 0) if isinstance(data, dict) else data}")
    except Exception as e:
        p_err(f"Errore: {e}")

# -- AUTH ---------------------------------------------------------------------
def auth_login(email, password):
    try:
        res = post_json(f"{BASE}/api/auth/login", {"email": email.strip(), "password": password})
    except Exception as e:
        return p_err(f"Login: {e}")
    user = (res.get("user") or res.get("data") or {}) if isinstance(res, dict) else {}
    if user:
        save_json_file(SESS_FILE, {"user": user, "token": res.get("token")})
        p_ok(f"Login ok: {user.get('email') or user.get('nickname')}")
    else:
        p_warn("Credenziali non valide.")

def auth_register(email, password, nick):
    try:
        res = post_json(f"{BASE}/api/auth/register",
                        {"email": email.strip(), "password": password, "nickname": nick})
    except Exception as e:
        return p_err(f"Register: {e}")
    user = (res.get("user") or {}) if isinstance(res, dict) else {}
    if user:
        save_json_file(SESS_FILE, {"user": user, "token": res.get("token")})
        p_ok(f"Registrato: {user.get('email')}")
    else:
        p_warn(f"Risposta: {res}")

def auth_available(nick, except_id=""):
    q = f"?nickname={urllib.parse.quote(nick)}" + (f"&exceptId={except_id}" if except_id else "")
    try:
        data = get_json(f"{BASE}/api/users/nickname-available{q}", timeout=8)
        p_ok("Nickname disponibile.") if (data.get("available") if isinstance(data, dict) else False) \
            else p_warn("Nickname occupato.")
    except Exception as e:
        p_err(f"Errore: {e}")

def auth_profile(nick):
    s = session()
    if not s.get("token"):
        return p_warn("Devi fare login prima.")
    try:
        res = api_patch(f"{BASE}/api/auth/profile", {"nickname": nick}, token=s["token"])
        s["user"] = res.get("user", s.get("user"))
        save_json_file(SESS_FILE, s)
        p_ok(f"Profilo aggiornato: {nick}")
    except Exception as e:
        p_err(f"Profilo: {e}")

def auth_delete(password):
    s = session()
    if not s.get("token"):
        return p_warn("Devi fare login prima.")
    try:
        status, _ = api_delete(f"{BASE}/api/auth/account", {"password": password}, token=s["token"])
        if status == 200:
            save_json_file(SESS_FILE, {})
            p_ok("Account eliminato, sessione pulita.")
        else:
            p_warn("Eliminazione fallita.")
    except Exception as e:
        p_err(f"Delete: {e}")

def auth_status():
    s = session()
    u = s.get("user") or {}
    if u:
        p_ok(f"Loggato come {u.get('email') or u.get('nickname')} (nickname: {u.get('nickname')})")
    else:
        p_info("Nessuna sessione. Usa: auth --login <email> <pw>")

def auth_logout():
    save_json_file(SESS_FILE, {})
    p_ok("Logout, sessione pulita.")

# -- PREFERITI ----------------------------------------------------------------
def fav_list():
    p_title("⭐ Preferiti")
    favs = fav_all()
    if not favs:
        return p_info("Nessun preferito. Aggiungi con preferiti --aggiungi-... .")
    for f in favs:
        print(f"  [{warn(str(f.get('id', '?')))}] {ok(str(f.get('type', '')))}  "
              f"{short(f.get('data', {}).get('name') or f.get('data', {}).get('destination') or f.get('data'), 60)}")

def fav_add(ftype, data):
    favs = fav_all()
    uid = (session().get("user") or {}).get("id", "guest")
    key = {"stop": f"{uid}_busStop_{data.get('code', '?')}",
           "train": f"{uid}_train_{data.get('number', '?')}",
           "busLine": f"{uid}_bus_{data.get('line', '?')}"}[ftype]
    if any(f.get("id") == key for f in favs):
        return p_warn("Già nei preferiti.")
    from datetime import datetime, timezone
    favs.append({"id": key, "userId": uid, "type": ftype, "data": data,
                 "addedAt": datetime.now(timezone.utc).isoformat()})
    save_json_file(FAV_FILE, favs)
    p_ok(f"Aggiunto {key}")

def fav_remove(fid):
    favs = [f for f in fav_all() if f.get("id") != fid]
    save_json_file(FAV_FILE, favs)
    p_ok(f"Rimosso {fid}")

# -- OFFLINE CACHE ------------------------------------------------------------
def offline_save(ttype, ident, infile):
    os.makedirs(CACHE_DIR, exist_ok=True)
    try:
        with open(infile, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        return p_err(f"Lettura {infile}: {e}")
    out = cache_path(ttype, ident)
    from datetime import datetime, timezone
    save_json_file(out, data)
    meta = load_json_file(os.path.join(CACHE_DIR, "_meta.json"), {})
    meta[f"{ttype}_{ident}"] = datetime.now(timezone.utc).isoformat()
    save_json_file(os.path.join(CACHE_DIR, "_meta.json"), meta)
    p_ok(f"Cache salvata: {out}")

def offline_get(ttype, ident):
    p = cache_path(ttype, ident)
    if not os.path.exists(p):
        return p_warn("Non in cache.")
    print(json.dumps(load_json_file(p, {}), ensure_ascii=False, indent=2)[:2000])

def offline_list():
    if not os.path.isdir(CACHE_DIR):
        return p_info("Cache vuota.")
    names = [n for n in os.listdir(CACHE_DIR) if n != "_meta.json"]
    for n in names:
        sz = os.path.getsize(os.path.join(CACHE_DIR, n)) // 1024
        print(f"  {n}  {dim(str(sz) + ' KB')}")
    p_dim(f"Totale: {len(names)} voci")

def offline_clear():
    import shutil
    shutil.rmtree(CACHE_DIR, ignore_errors=True)
    p_ok("Cache pulita.")

def offline_size():
    total = 0
    for root, _, files in os.walk(CACHE_DIR):
        for n in files:
            total += os.path.getsize(os.path.join(root, n))
    p_info(f"Dimensione cache: {total // 1024} KB")

# -- MENU INTERATTIVI ---------------------------------------------------------
def banner():
    if USE_COLOR:
        bar = f"{BOLD}{B}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{RESET}"
        print(bar)
        print(f"   {BOLD}{C_}BC.Transporter{RESET}  {dim('· terminale')}")
        print(bar)
    else:
        print("=== BC.Transporter · terminale ===")
    print(f"  {dim('Bus · Treni · Aerei nel terminale — stessi endpoint dell’app Flutter')}")

def pick_country():
    data = load_json_file(os.path.join(HOME, ".bc_cli_countries.json"), {})
    entries = data.get("entries", [])
    if not entries:
        entries = train_countries() or []
    if not entries:
        return (ask("Paese [IT]: ") or "IT").upper()
    print(f"\n  {dim('Paesi (numero → codice):')}")
    for e in entries:
        mark = " ←" if e["code"].upper() == "IT" or e["code"] == "it" else ""
        print(f"  {c_train('[' + str(e['n']) + ']')} {e['code'].ljust(18)} {dim(e['name'])}{mark}")
    sel = ask("Numero paese [invio = IT]: ")
    if not sel:
        return "IT"
    code = country_from_number(sel)
    if code:
        p_ok(f"Paese: {code}")
        return code
    return sel.upper()

COMMANDS = ("treni", "bus", "voli", "flixbus", "regionali", "strade",
            "meteo", "social", "auth", "preferiti", "config", "offline")

def run_direct(line):
    import shlex
    try:
        main(shlex.split(line))
    except SystemExit:
        pass

TRANSPORTS = (("treni", "🚂 Treni"), ("bus", "🚌 Bus"),
              ("voli", "✈️  Voli"), ("flixbus", "🟢 Flixbus"))

def pick_transport(default="1"):
    print(f"\n  {dim('Tipo di trasporto:')}")
    painters = {"treni": c_train, "bus": c_bus, "voli": c_plane, "flixbus": ok}
    for i, (key, label) in enumerate(TRANSPORTS, 1):
        print(f"  {painters[key](f'[{i}]')} {label}")
    print(f"  {dim('[0] Indietro')}")
    s = ask(f"Numero trasporto [{default}]: ").strip() or default
    if s == "0":
        return None
    try:
        return TRANSPORTS[int(s) - 1][0]
    except (ValueError, IndexError):
        return TRANSPORTS[int(default) - 1][0]

def simple_mode():
    p_title("🟢 Modalità semplice (0 = menu)")
    transport = pick_transport()
    if transport is None:
        return
    if transport == "treni":
        simple_train()
    elif transport == "bus":
        simple_bus()
    elif transport == "voli":
        simple_fly()
    elif transport == "flixbus":
        simple_flix()

def pick_board_row(board):
    if not board:
        p_warn("Nessuna riga: mostra prima il tabellone (tasto 1).")
        return None
    r = ask(f"Numero riga del treno [1-{len(board)}]: ").strip()
    try:
        row = board[int(r) - 1] if 1 <= int(r) <= len(board) else None
    except ValueError:
        row = None
    if not isinstance(row, dict):
        p_warn("Numero non valido.")
        return None
    return row

def simple_train():
    country = pick_country()
    while True:
        q = ask("\nNome stazione (0 = menu): ")
        if not q or q.strip() == "0":
            return
        try:
            _, lst = fetch_stations(q, country)
        except Exception as e:
            p_err(f"Errore ricerca: {e}")
            continue
        if not lst:
            p_warn("Nessuna stazione trovata, riprova.")
            continue
        p_title(f'🚂 Stazioni · "{q}" [{country}]')
        for i, e in enumerate(lst, 1):
            e = e if isinstance(e, dict) else {}
            name = e.get("name") or e.get("stationName") or "?"
            print(f"  {c_train(f'[{i}]')} {bold(name)}")
        s = ask("Numero stazione (0 = nuova ricerca): ").strip()
        if s == "0" or not s:
            continue
        try:
            choice = lst[int(s) - 1] if 1 <= int(s) <= len(lst) else None
        except ValueError:
            choice = None
        if not choice:
            p_warn("Numero non valido.")
            continue
        sid = str(choice.get("id") or choice.get("stationId") or "")
        m = ask("Tasto 1) Partenze  2) Arrivi  [1]: ").strip() or "1"
        arrivi = (m == "2")
        board = []
        while True:
            board = train_board(sid, country, arrivi) or []
            nxt = ask("\nTasto 1) Altra stazione  2) Cambia nazione  "
                      f"3) Passa a {'Partenze' if arrivi else 'Arrivi'}  "
                      f"4) Timeline treno  5) Timeline grafica (finestra)  0) Menu  [1]: ").strip() or "1"
            if nxt == "3":
                arrivi = not arrivi
            elif nxt in ("4", "5"):
                row = pick_board_row(board)
                if row is None:
                    continue
                trip_id = str(row.get("tripId") or "")
                if nxt == "5":
                    if not trip_id:
                        p_warn("Trip non disponibile per questa riga.")
                        continue
                    open_timeline_gui(trip_id, country)
                    continue
                if trip_id:
                    train_trip(trip_id, country)
                else:
                    num = str(row.get("tripNumber") or row.get("trainNumber") or "")
                    if not num:
                        p_warn("Trip non disponibile per questa riga.")
                        continue
                    train_details(num, sid, country)
            elif nxt == "2":
                country = pick_country()
                break
            elif nxt == "0":
                return
            else:
                break

def simple_bus():
    try:
        provs = fetch_providers()
    except Exception as e:
        return p_err(f"Errore providers: {e}")
    if not provs:
        return p_warn("Nessun provider.")
    for i, p in enumerate(provs, 1):
        print(f"  {c_bus(f'[{i}]')} {p.get('name', '?')}  {dim(provider_country(p))}")
    s = ask("Numero provider [1]: ").strip() or "1"
    try:
        sel = provs[int(s) - 1]
    except (ValueError, IndexError):
        sel = provs[0]
    provider = str(sel.get("name"))
    country = provider_country(sel)
    p_info(f"Provider: {provider} [{country}] — scarico fermate…")
    try:
        _, _, stops = fetch_bus_stops(provider, country)
    except Exception as e:
        return p_err(f"Errore fermate: {e}")
    p_ok(f"{len(stops)} fermate caricate.")
    while True:
        q = ask("\nNome fermata (0 = menu): ")
        if not q or q.strip() == "0":
            return
        q = q.strip()
        found = [x for x in stops
                 if q.lower() in str(x.get("stopName") or "").lower()
                 or q in str(x.get("stopId") or "")][:10]
        if not found:
            p_warn("Nessuna fermata trovata, riprova.")
            continue
        by_id = {x.get("stopId"): x for x in found}
        if q in by_id:
            bus_departures(provider, q, country)
        else:
            for i, x in enumerate(found, 1):
                print(f"  {c_bus(f'[{i}]')} {x.get('stopName')}  {dim(x.get('stopId'))}")
            s = ask("Numero fermata o ID diretto (0 = nuova ricerca): ").strip()
            if s == "0" or not s:
                continue
            choice = None
            if s in by_id:
                choice = by_id[s]
            else:
                try:
                    choice = found[int(s) - 1] if 1 <= int(s) <= len(found) else None
                except ValueError:
                    choice = None
            if not choice:
                p_warn("Numero non valido.")
                continue
            bus_departures(provider, str(choice.get("stopId")), country)
        nxt = ask("\nTasto 1) Altra fermata  0) Menu  [1]: ").strip() or "1"
        if nxt == "0":
            return

def simple_fly():
    while True:
        q = ask("\nAeroporto, città o codice (0 = menu): ")
        if not q or q.strip() == "0":
            return
        if len(q.strip()) < 2:
            p_warn("Scrivi almeno 2 caratteri.")
            continue
        if len(q.strip()) == 3 and q.strip().isalpha():
            iata = q.strip().upper()
            m = ask("Tasto 1) Partenze  2) Arrivi  [1]: ").strip() or "1"
            arrivi = (m == "2")
            while True:
                airport(iata, arrivi)
                nxt = ask("\nTasto 1) Altro aeroporto  "
                          f"2) Passa a {'Partenze' if arrivi else 'Arrivi'}  0) Menu  [1]: ").strip() or "1"
                if nxt == "2":
                    arrivi = not arrivi
                elif nxt == "0":
                    return
                else:
                    break
            continue
        try:
            _, lst = fetch_airports(q)
        except Exception as e:
            p_err(f"Errore ricerca: {e}")
            continue
        if not lst:
            p_warn("Nessun aeroporto trovato, riprova.")
            continue
        for i, it in enumerate(lst[:10], 1):
            print(f"  {c_plane(f'[{i}]')} {it.get('PlaceId')}  "
                  f"{it.get('PlaceName') or it.get('name')} {dim(str(it.get('CityName') or ''))}")
        s = ask("Numero aeroporto (0 = nuova ricerca): ").strip()
        if s == "0" or not s:
            continue
        try:
            choice = lst[int(s) - 1] if 1 <= int(s) <= min(len(lst), 10) else None
        except ValueError:
            choice = None
        if not choice:
            p_warn("Numero non valido.")
            continue
        iata = str(choice["PlaceId"])
        m = ask("Tasto 1) Partenze  2) Arrivi  [1]: ").strip() or "1"
        arrivi = (m == "2")
        while True:
            airport(iata, arrivi)
            nxt = ask("\nTasto 1) Altro aeroporto  "
                      f"2) Passa a {'Partenze' if arrivi else 'Arrivi'}  0) Menu  [1]: ").strip() or "1"
            if nxt == "2":
                arrivi = not arrivi
            elif nxt == "0":
                return
            else:
                break

def simple_flix():
    while True:
        q = ask("\nStazione Flixbus (0 = menu): ")
        if not q or q.strip() == "0":
            return
        try:
            lst = fetch_flix_stations(q) or []
        except Exception as e:
            p_err(f"Errore ricerca: {e}")
            continue
        if not lst:
            p_warn("Nessuna stazione trovata, riprova.")
            continue
        for i, s in enumerate(lst[:10], 1):
            if isinstance(s, dict):
                print(f"  {ok(f'[{i}]')} {s.get('name', '?')}")
        s = ask("Numero stazione (0 = nuova ricerca): ").strip()
        if s == "0" or not s:
            continue
        try:
            choice = lst[int(s) - 1] if 1 <= int(s) <= min(len(lst), 10) else None
        except (ValueError, IndexError, TypeError):
            choice = None
        if not isinstance(choice, dict):
            p_warn("Numero non valido.")
            continue
        flix_departures(str(choice.get("id")))
        nxt = ask("\nTasto 1) Altra stazione  0) Menu  [1]: ").strip() or "1"
        if nxt == "0":
            return

def commands_guide():
    p_title("📖 Guida comandi")
    print(f"  {bold('TRENI')}  nazione → stazione → tabellone")
    print(f"    {c_train('treni --cerca <nome>')} [--paese IT] | {c_train('--partenze <id>')} [--arrivi]")
    print(f"    {c_train('treni --treno <num> --stazione <id>')} | {c_train('--trip <tripId>')} | {c_train('--numero <testo>')}")
    print(f"    {c_train('treni --fal <id>')} | {c_train('--diretta <q>')} | {c_train('--rfi <id>')} | {c_train('--live')} | {c_train('--track <tripId>')}")
    print(f"    {c_train('treni --condividi <tripId>')} | {c_train('--apri-share <id>')} | {c_train('--match <tripId>')}")
    print(f"    {c_train('treni --routing DA A --date YYYY-MM-DD --time HH:MM')}")
    print(f"    {c_train('treni --stats-treno CAT NUM')} | {c_train('--stats-stazione <id> [--period week]')}")
    print(f"    {c_train('treni --monitor-check <id>')} | {c_train('--cerca-treno <q>')} | {c_train('--paesi')} | {c_train('--categorie')}")
    print(f"    {c_train('treni --presence live|recent|viewers|heartbeat [--key K]')}")
    print(f"    {c_train('treni --mappa <tripId>')} = timeline grafica in finestra (logo categoria)")
    print(f"  {bold('BUS')}  provider → fermata → partenze")
    print(f"    {c_bus('bus --providers')} | {c_bus('--linee <prov>')} | {c_bus('--fermate <prov>')} | {c_bus('--veicoli <prov>')}")
    print(f"    {c_bus('bus --partenze <prov> <stopId>')} | {c_bus('--realtime <veicolo> <trip> --provider <prov>')}")
    print(f"    {c_bus('bus --soluzioni <da> <a> --provider <prov>')} | {c_bus('--trip-stops <trip>')} | {c_bus('--route-path <trip>')} | {c_bus('--static <prov>')}")
    print(f"  {bold('VOLI')}  radar + aeroporti")
    print(f"    {c_plane('voli --area')} | {c_plane('voli --aeroporto <IATA> [--arrivi]')} | {c_plane('voli --cerca <nome>')}")
    print(f"  {bold('FLIXBUS / REGIONALI / STRADE / METEO')}")
    print(f"    {ok('flixbus --stazioni <q>')} | {ok('--partenze <id>')} | {ok('--trip <id>')}")
    print(f"    {c_train('regionali --lista IT')} | {c_train('--stazioni IT <prefix> [--cerca q]')} | {c_train('--partenze IT <prefix> <id> [--arrivi]')}")
    print(f"    {warn('strade --news|--pedaggi|--servizi [--paese it]')}   {info('meteo --cerca <città> | --ora <nome> <lat> <lon>')}")
    print(f"  {bold('SOCIAL / AUTH / SISTEMA')}")
    print(f"    {paint('social --feed|--topic <id>|--online|--leaderboard|--user <nick>', M)}")
    print(f"    {paint('social --publish <key> <nick> | --send <id> <nick> <testo> | --like|--delete <id> <nick>', M)}")
    print(f"    {paint('auth --login <email> <pw> | --register <e> <p> <nick> | --stato | --logout', B)}")
    print(f"    {warn('preferiti --lista | --treno <n> <o> <d> | --fermata <cod> <nome> | --rimuovi <id>')}")
    print(f"    {info('config --show | offline --lista | flixbus --help')}   {dim('<comando> --help = aiuto dettagliato')}")
    p_dim("Con prefisso automatico (bc:treni>) basta la parte dopo il nome: --partenze S11119 --paese IT")

def commands_mode():
    p_title("⌨️ Modalità comandi (0 = menu)")
    print(f"  {dim('0) Nessun prefisso (comando libero)')}")
    t = ask("Numero trasporto per prefisso automatico [0]: ").strip() or "0"
    prefix = {"1": "treni", "2": "bus", "3": "voli", "4": "flixbus"}.get(t)
    p_dim("Esempi: treni --partenze S11119 --paese IT · voli --area · bus --providers" +
          (f"  (oppure solo gli argomenti: il prefisso '{prefix}' è automatico)" if prefix else "") +
          "  ·  help = guida di tutti i comandi")
    while True:
        line = ask(f"bc:{prefix}> " if prefix else "bc> ").strip()
        if not line or line.lower() in ("0", "indietro", "menu", "q", "exit"):
            return
        if line.lower() in ("help", "aiuto", "guida", "?"):
            commands_guide()
            continue
        first = line.split(" ", 1)[0].lower()
        if first in COMMANDS:
            run_direct(line)
        elif prefix:
            run_direct(f"{prefix} {line}")
        else:
            p_warn("Comando sconosciuto. Prova: " + ", ".join(COMMANDS))

def menu():
    banner()
    while True:
        print(f"\n{title('MENU PRINCIPALE')}")
        print(f"  {c_train('1)')} 🟢 Modalità semplice  (nazione → stazione → tabellone)")
        print(f"  {c_bus('2)')} ⌨️  Modalità comandi   (scrivi il comando diretto)")
        print(f"  {paint('3)', M)} 🧰 Menu avanzato      (tutte le funzioni)")
        print(f"  {dim('0) Esci')}")
        c = ask("\nScelta [0-3]: ").strip()
        if c == "1":
            simple_mode()
        elif c == "2":
            commands_mode()
        elif c == "3":
            advanced_menu()
        elif c.split(" ", 1)[0].lower() in COMMANDS:
            run_direct(c)
        elif c in ("0", "q", "exit"):
            p_ok("Ciao! 👋")
            return
        else:
            p_warn("Scelta non valida: premi 1, 2, 3 oppure scrivi un comando.")

def advanced_menu():
    while True:
        print(f"\n{title('MENU AVANZATO (0 = indietro)')}")
        print(f"  {c_train('1)')} 🚂 Treni  (stazioni, partenze, dettagli, FAL, live, routing, stats)")
        print(f"  {c_bus('2)')} 🚌 Bus    (provider, linee, fermate, live, soluzioni)")
        print(f"  {c_plane('3)')} ✈️  Voli   (radar + aeroporti + ricerca)")
        print(f"  {ok('4)')} 🟢 Flixbus")
        print(f"  {c_train('5)')} 🏳️ Regionali (trenord & co.)")
        print(f"  {warn('6)')} 🛣️ Strade + 🌤️ Meteo")
        print(f"  {paint('7)', M)} 💬 Social + 👁️ Presence")
        print(f"  {paint('8)', B)} ⚙️ Config/Stats + 👤 Auth + ⭐ Preferiti + 💾 Offline")
        print(f"  {dim('0) Indietro')}")
        print(f"  {dim('oppure scrivi un comando diretto, es. treni --partenze S11119 --paese it')}")
        c = ask("\nScelta [0-8]: ")
        if c.split(" ", 1)[0].lower() in COMMANDS:
            run_direct(c)
            continue
        if c == "1":
            print(f"\n{title('━━ 🚂 Treni ━━')}")
            print("  1) Cerca stazione\n  2) Partenze/Arrivi (serve id)\n"
                  "  3) Dettaglio treno (numero + id)\n  4) Treno live per numero\n  5) FAL\n"
                  "  6) Lista paesi numerata")
            s = ask("Scelta: ")
            if s == "6":
                train_countries()
                continue
            p = pick_country()
            if s == "1":
                q = ask("Nome stazione: ")
                if q: train_search(q, p)
            elif s == "2":
                sid = ask("ID stazione: ")
                a = ask("Arrivi? [s/N]: ").lower().startswith("s")
                if sid: train_board(sid, p, a)
            elif s == "3":
                n, sid = ask("Numero treno: "), ask("ID stazione: ")
                if n and sid: train_details(n, sid, p)
            elif s == "4":
                q = ask("Numero/linea (es. 5440, FR, S4): ")
                if q: train_number(q)
            elif s == "5":
                sid = ask("ID stazione FAL: ")
                if sid: fal(sid)
        elif c == "2":
            print(f"\n{title('━━ 🚌 Bus ━━')}")
            print("  1) Provider\n  2) Linee\n  3) Fermate\n  4) Partenze fermata\n  5) Veicoli live")
            s = ask("Scelta: ")
            if s == "1":
                bus_providers()
            elif s in ("2", "3", "5"):
                pr = ask("Provider (es. bari): ")
                if pr:
                    {"2": bus_lines, "3": bus_stops, "5": bus_vehicles}[s](pr, "")
            elif s == "4":
                pr, st = ask("Provider (es. bari): "), ask("ID fermata: ")
                if pr and st: bus_departures(pr, st, "")
        elif c == "3":
            print(f"\n{title('━━ ✈️ Voli ━━')}")
            print("  1) Radar Italia\n  2) Aeroporto (IATA)")
            s = ask("Scelta: ")
            if s == "1":
                flights_area()
            elif s == "2":
                iata = ask("Codice IATA (es. BRI): ").upper()
                a = ask("Arrivi? [s/N]: ").lower().startswith("s")
                if iata: airport(iata, a)
        elif c == "4":
            q = ask("Cerca stazione Flixbus (nome): ")
            if q:
                flix_stations(q)
                sid = ask("ID stazione per partenze (invio = salta): ")
                if sid: flix_departures(sid)
        elif c == "5":
            print(f"\n{title('━━ 🏳️ Regionali ━━')}")
            pa = (ask("Paese [IT]: ") or "IT").upper()
            reg_providers(pa)
            px = ask("apiPrefix (es. it/trains/trenord, invio = salta): ")
            if px:
                q = ask("Cerca stazione (invio = tutte): ")
                reg_stations(pa, px, q)
        elif c == "6":
            print(f"\n{title('━━ 🛣️ Strade / 🌤️ Meteo ━━')}")
            print("  1) News strade  2) Caselli  3) Servizi  4) Cerca città  5) Meteo Roma")
            s = ask("Scelta: ")
            if s == "1": road_news()
            elif s == "2": road_tolls()
            elif s == "3": road_services()
            elif s == "4":
                q = ask("Città: ")
                if q: meteo_search(q)
            elif s == "5": meteo_now()
        elif c == "7":
            print(f"\n{title('━━ 💬 Social ━━')}")
            print("  1) Feed  2) Online  3) Leaderboard  4) Presence live")
            s = ask("Scelta: ")
            if s == "1": social_feed()
            elif s == "2": social_online()
            elif s == "3": social_leaderboard()
            elif s == "4": presence("live")
        elif c == "8":
            print(f"\n{title('━━ ⚙️ Sistema ━━')}")
            print("  1) Config  2) Stato auth  3) Preferiti  4) Cache offline (size)")
            s = ask("Scelta: ")
            if s == "1": config_show()
            elif s == "2": auth_status()
            elif s == "3": fav_list()
            elif s == "4": offline_size()
        elif c in ("0", "q", "exit", "menu", "indietro"):
            return
        else:
            p_warn("Scelta non valida.")

# -- CLI PARSER ---------------------------------------------------------------
def build_parser():
    p = argparse.ArgumentParser(
        prog="bc_cli.py",
        description="BC.Transporter nel terminale — stessi endpoint dell'app Flutter, output colorato.")
    p.add_argument("--no-color", action="store_true", help="disattiva i colori ANSI")
    sub = p.add_subparsers(dest="cmd")

    t = sub.add_parser("treni", help="orari treni")
    t.add_argument("--cerca", help="cerca stazione per nome")
    t.add_argument("--partenze", metavar="STATION_ID", help="tabellone stazione")
    t.add_argument("--treno", help="numero treno (richiede --stazione)")
    t.add_argument("--stazione", help="id stazione per --treno")
    t.add_argument("--trip", help="tripId")
    t.add_argument("--numero", help="cerca treno live per numero/linea")
    t.add_argument("--fal", metavar="STATION_ID", help="partenze FAL")
    t.add_argument("--paese", default="IT")
    t.add_argument("--arrivi", nargs="?", const=True, default=False, metavar="STATION_ID",
                   help="solo arrivi; accetta anche l'id diretto: --arrivi <stationId>")
    t.add_argument("--diretta", metavar="QUERY", help="ricerca diretta RFI (service=direct IT)")
    t.add_argument("--rfi", metavar="STATION_ID", help="tabellone RFI via proxy")
    t.add_argument("--dettaglio-rfi", metavar="NUMERO", help="dettaglio treno RFI")
    t.add_argument("--condividi", metavar="TRIP_ID", help="crea link di condivisione trip")
    t.add_argument("--apri-share", metavar="SHARE_ID")
    t.add_argument("--match", metavar="TRIP_ID", help="POST /api/trains/match")
    t.add_argument("--live", action="store_true", help="snapshot /api/trains/live")
    t.add_argument("--track", metavar="TRIP_ID", help="traccia GPS + fermate")
    t.add_argument("--routing", nargs=2, metavar=("DA", "A"), help="itinerario (richiede --date/--time)")
    t.add_argument("--date", help="data YYYY-MM-DD per routing")
    t.add_argument("--time", help="ora HH:MM per routing")
    t.add_argument("--stats-treno", nargs=2, metavar=("CATEGORIA", "NUMERO"))
    t.add_argument("--stats-stazione", metavar="STATION_ID")
    t.add_argument("--period", default="today", help="today/week/month/year")
    t.add_argument("--monitor-check", metavar="STATION_ID")
    t.add_argument("--monitor-add", nargs=3, metavar=("ID", "NOME", "PAESE"))
    t.add_argument("--cerca-treno", metavar="QUERY", help="ricerca statistica treno")
    t.add_argument("--categorie", action="store_true",
                   help="tutte le categorie dalla mappa live mondiale, colorate")
    t.add_argument("--mappa", metavar="TRIP_ID",
                   help="timeline grafica in finestra separata (logo categoria)")
    t.add_argument("--paesi", action="store_true", help="lista paesi/operatori")
    t.add_argument("--presence", choices=["live", "recent", "viewers", "heartbeat"])
    t.add_argument("--key", help="trainKey per presence")
    t.add_argument("--limit", type=int, default=20)

    b = sub.add_parser("bus", help="bus urbani")
    b.add_argument("--providers", action="store_true")
    b.add_argument("--linee", metavar="PROVIDER")
    b.add_argument("--fermate", metavar="PROVIDER")
    b.add_argument("--partenze", nargs=2, metavar=("PROVIDER", "STOP_ID"))
    b.add_argument("--veicoli", metavar="PROVIDER")
    b.add_argument("--paese", default="")
    b.add_argument("--soluzioni", nargs=2, metavar=("FROM_STOP", "TO_STOP"))
    b.add_argument("--provider", default="bari")
    b.add_argument("--soluzione-dettaglio", metavar="SOLUTION_ID")
    b.add_argument("--realtime", nargs=2, metavar=("VEHICLE_ID", "TRIP_ID"))
    b.add_argument("--trip-stops", metavar="TRIP_ID")
    b.add_argument("--route-path", metavar="TRIP_ID")
    b.add_argument("--static", metavar="PROVIDER", help="scarica pacchetto offline con progress")

    v = sub.add_parser("voli", help="voli e aeroporti")
    v.add_argument("--area", action="store_true", help="radar sull'Italia")
    v.add_argument("--aeroporto", metavar="IATA")
    v.add_argument("--arrivi", action="store_true")
    v.add_argument("--cerca", metavar="QUERY", help="autosuggest aeroporti Skyscanner")

    f = sub.add_parser("flixbus", help="rete Flixbus")
    f.add_argument("--stazioni")
    f.add_argument("--partenze", metavar="STATION_ID")
    f.add_argument("--trip", metavar="TRIP_ID")

    r = sub.add_parser("regionali", help="provider regionali (trenord & co.)")
    r.add_argument("--lista", metavar="PAESE", help="provider regionali per paese")
    r.add_argument("--stazioni", nargs=2, metavar=("PAESE", "PREFIX"))
    r.add_argument("--cerca", default="", help="filtro stazioni regionali")
    r.add_argument("--partenze", nargs=3, metavar=("PAESE", "PREFIX", "STATION_ID"))
    r.add_argument("--arrivi", action="store_true")
    r.add_argument("--news", nargs=2, metavar=("PAESE", "PREFIX"))
    r.add_argument("--trip", nargs=3, metavar=("PAESE", "PREFIX", "TRIP_ID"))

    s = sub.add_parser("strade", help="autostrade: news, caselli, servizi")
    s.add_argument("--news", action="store_true")
    s.add_argument("--pedaggi", action="store_true")
    s.add_argument("--servizi", action="store_true")
    s.add_argument("--paese", default="it")
    s.add_argument("--highways", default="")
    s.add_argument("--highway", default="")

    m = sub.add_parser("meteo", help="meteo open-meteo (stessa logica app)")
    m.add_argument("--cerca", metavar="CITTA")
    m.add_argument("--ora", nargs=3, metavar=("CITTA", "LAT", "LON"))

    sc = sub.add_parser("social", help="bacheca viaggiatori")
    sc.add_argument("--feed", action="store_true")
    sc.add_argument("--limit", type=int, default=30)
    sc.add_argument("--publish", nargs=2, metavar=("TRAIN_KEY", "NICK"))
    sc.add_argument("--topic", metavar="ID")
    sc.add_argument("--send", nargs=3, metavar=("ID", "NICK", "TESTO"))
    sc.add_argument("--like", nargs=2, metavar=("ID", "NICK"))
    sc.add_argument("--delete", nargs=2, metavar=("ID", "NICK"))
    sc.add_argument("--user", metavar="NICK")
    sc.add_argument("--leaderboard", action="store_true")
    sc.add_argument("--online", action="store_true")

    au = sub.add_parser("auth", help="login/registrazione/profilo (API web)")
    au.add_argument("--login", nargs=2, metavar=("EMAIL", "PW"))
    au.add_argument("--register", nargs=3, metavar=("EMAIL", "PW", "NICK"))
    au.add_argument("--disponibile", metavar="NICK")
    au.add_argument("--profilo", metavar="NICK")
    au.add_argument("--elimina", metavar="PW")
    au.add_argument("--stato", action="store_true")
    au.add_argument("--logout", action="store_true")

    fv = sub.add_parser("preferiti", help="preferiti locali (stessi id dell'app)")
    fv.add_argument("--lista", action="store_true")
    fv.add_argument("--treno", nargs=3, metavar=("NUMERO", "ORIGINE", "DEST"))
    fv.add_argument("--fermata", nargs=2, metavar=("CODICE", "NOME"))
    fv.add_argument("--bus", nargs=2, metavar=("LINEA", "NOME"))
    fv.add_argument("--rimuovi", metavar="ID")
    fv.add_argument("--check", metavar="ID")

    cf = sub.add_parser("config", help="config + stats globali + loghi")
    cf.add_argument("--show", action="store_true")
    cf.add_argument("--stats-general", action="store_true")
    cf.add_argument("--stats-linee", action="store_true")
    cf.add_argument("--loghi", action="store_true")

    of = sub.add_parser("offline", help="cache file (stessa logica OfflineSyncService)")
    of.add_argument("--save", nargs=3, metavar=("TIPO", "ID", "FILE_JSON"))
    of.add_argument("--get", nargs=2, metavar=("TIPO", "ID"))
    of.add_argument("--lista", action="store_true")
    of.add_argument("--clear", action="store_true")
    of.add_argument("--size", action="store_true")
    return p

def main(argv=None):
    global USE_COLOR
    parser = build_parser()
    if not argv:
        try:
            menu()
        except BrokenPipeError:
            pass
        return
    a = parser.parse_args(argv)
    if a.no_color:
        USE_COLOR = False
    try:
        if a.cmd == "treni":
            paese = (a.paese or "IT").upper()
            arrivi_id = a.arrivi if isinstance(a.arrivi, str) else None
            arrivi = bool(a.arrivi)
            station = a.partenze or arrivi_id
            if a.cerca: train_search(a.cerca, paese)
            elif station: train_board(station, paese, arrivi)
            elif a.treno:
                if not a.stazione:
                    p_err("Serve --stazione <id>. Esempio: --treno 5440 --stazione <id>")
                else:
                    train_details(a.treno, a.stazione, paese)
            elif a.trip: train_trip(a.trip, paese)
            elif a.numero: train_number(a.numero)
            elif a.fal: fal(a.fal)
            elif a.diretta: train_search_direct(a.diretta)
            elif a.rfi: train_board_rfi(a.rfi, a.arrivi)
            elif a.dettaglio_rfi: train_details_rfi(a.dettaglio_rfi)
            elif a.condividi: train_share(a.condividi, paese)
            elif a.apri_share: train_open_share(a.apri_share)
            elif a.match: train_match(a.match, paese)
            elif a.live: train_live()
            elif a.track: train_track(a.track)
            elif a.routing:
                if not (a.date and a.time):
                    p_err("Routing richiede --date YYYY-MM-DD e --time HH:MM")
                else:
                    train_routing(a.routing[0], a.routing[1], a.date, a.time)
            elif a.stats_treno: stats_train(a.stats_treno[0], a.stats_treno[1])
            elif a.stats_stazione: stats_station(a.stats_stazione, a.period)
            elif a.monitor_check: monitor_check(a.monitor_check)
            elif a.monitor_add: monitor_add(*a.monitor_add)
            elif a.cerca_treno: search_train_stats(a.cerca_treno)
            elif a.categorie: train_categories()
            elif a.mappa: open_timeline_gui(a.mappa, paese)
            elif a.paesi: train_countries()
            elif a.presence: presence(a.presence, a.key or "", a.limit)
            else: parser.parse_args(["treni", "--help"])
        elif a.cmd == "bus":
            if a.providers: bus_providers()
            elif a.linee: bus_lines(a.linee, a.paese or "")
            elif a.fermate: bus_stops(a.fermate, a.paese or "")
            elif a.partenze: bus_departures(a.partenze[0], a.partenze[1], a.paese or "")
            elif a.veicoli: bus_vehicles(a.veicoli, a.paese or "")
            elif a.soluzioni: bus_solutions(a.soluzioni[0], a.soluzioni[1], a.provider, a.paese or "it")
            elif a.soluzione_dettaglio: bus_solution_detail(a.soluzione_dettaglio, a.provider, a.paese or "it")
            elif a.realtime: bus_realtime(a.provider, a.realtime[0], a.realtime[1], a.paese or "")
            elif a.trip_stops: bus_trip_stops(a.provider, a.trip_stops, a.paese or "")
            elif a.route_path: bus_route_path(a.provider, a.route_path, a.paese or "")
            elif a.static: bus_static(a.static, a.paese or "")
            else: parser.parse_args(["bus", "--help"])
        elif a.cmd == "voli":
            if a.area: flights_area()
            elif a.aeroporto: airport(a.aeroporto.upper(), a.arrivi)
            elif a.cerca: search_airports(a.cerca)
            else: parser.parse_args(["voli", "--help"])
        elif a.cmd == "flixbus":
            if a.stazioni: flix_stations(a.stazioni)
            elif a.partenze: flix_departures(a.partenze)
            elif a.trip: flix_trip(a.trip)
            else: parser.parse_args(["flixbus", "--help"])
        elif a.cmd == "regionali":
            if a.lista: reg_providers(a.lista.upper())
            elif a.stazioni: reg_stations(a.stazioni[0].upper(), a.stazioni[1], a.cerca)
            elif a.partenze: reg_board(a.partenze[0].upper(), a.partenze[1], a.partenze[2], a.arrivi)
            elif a.news: reg_news(a.news[0].upper(), a.news[1])
            elif a.trip: reg_trip(a.trip[0].upper(), a.trip[1], a.trip[2])
            else: parser.parse_args(["regionali", "--help"])
        elif a.cmd == "strade":
            if a.news: road_news(a.paese, a.highways)
            elif a.pedaggi: road_tolls(a.paese)
            elif a.servizi: road_services(a.paese, a.highway)
            else: parser.parse_args(["strade", "--help"])
        elif a.cmd == "meteo":
            if a.cerca: meteo_search(a.cerca)
            elif a.ora: meteo_now(a.ora[0], float(a.ora[1]), float(a.ora[2]))
            else: parser.parse_args(["meteo", "--help"])
        elif a.cmd == "social":
            if a.feed: social_feed(a.limit)
            elif a.publish: social_publish(a.publish[0], a.publish[1])
            elif a.topic: social_topic(a.topic, a.limit)
            elif a.send: social_send(*a.send)
            elif a.like: social_like(*a.like)
            elif a.delete: social_delete(*a.delete)
            elif a.user: social_user(a.user)
            elif a.leaderboard: social_leaderboard()
            elif a.online: social_online()
            else: parser.parse_args(["social", "--help"])
        elif a.cmd == "auth":
            if a.login: auth_login(*a.login)
            elif a.register: auth_register(*a.register)
            elif a.disponibile: auth_available(a.disponibile)
            elif a.profilo: auth_profile(a.profilo)
            elif a.elimina: auth_delete(a.elimina)
            elif a.stato or (not any([a.login, a.register, a.disponibile, a.profilo, a.elimina, a.logout])): auth_status()
            elif a.logout: auth_logout()
            else: parser.parse_args(["auth", "--help"])
        elif a.cmd == "preferiti":
            if a.lista or not any([a.treno, a.fermata, a.bus, a.rimuovi, a.check]): fav_list()
            elif a.treno: fav_add("train", {"number": a.treno[0], "origin": a.treno[1], "destination": a.treno[2], "name": f"Treno {a.treno[0]}"})
            elif a.fermata: fav_add("stop", {"code": a.fermata[0], "name": a.fermata[1]})
            elif a.bus: fav_add("busLine", {"line": a.bus[0], "name": a.bus[1]})
            elif a.rimuovi: fav_remove(a.rimuovi)
            elif a.check:
                p_ok("Nei preferiti.") if any(f.get("id") == a.check for f in fav_all()) else p_warn("Non nei preferiti.")
            else: parser.parse_args(["preferiti", "--help"])
        elif a.cmd == "config":
            if a.stats_general: stats_general()
            elif a.stats_linee: stats_lines()
            elif a.loghi: train_logos()
            else: config_show()
        elif a.cmd == "offline":
            if a.save: offline_save(*a.save)
            elif a.get: offline_get(*a.get)
            elif a.clear: offline_clear()
            elif a.size: offline_size()
            else: offline_list()
        else:
            parser.print_help()
    except BrokenPipeError:
        pass
    except Exception as e:
        p_err(f"Errore: {e}")
        sys.exit(1)

if __name__ == "__main__":
    try:
        main(sys.argv[1:])
    except BrokenPipeError:
        pass