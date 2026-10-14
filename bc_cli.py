#!/usr/bin/env python3
"""BC.Transporter - versione Terminale (solo stdlib, output colorato).

Stessi endpoint dell'app Flutter BCTransporterMobileApp, usabili da console.

Uso:
    python bc_cli.py                       -> menu interattivo (ricorda paese/recenti,
                                                invio=aggiorna, testo=cerca stazione)
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
    python bc_cli.py preferiti --lista [--cloud] | --treno <num> <org> <dest>
                                     [--fermata <cod> <nome> --tipo trainStation --paese IT]
                                     [--bus <linea> <nome> --provider bari] | --sync | --check <id>
    python bc_cli.py config --show | --stats-general | --loghi
    python bc_cli.py offline --lista | --size | --save <tipo> <id> <file>
    python bc_cli.py treni --live | --match <tripId> | --routing DA A --date X --time Y

Globale: --no-color
"""

import argparse
import getpass
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
        if dt.tzinfo is not None:
            # L'API manda orari UTC con "Z": convertiamo in ora locale
            # (sulla macchina in Italia = Europe/Rome, es. 15:07Z -> 17:07).
            try:
                dt = dt.astimezone()
            except Exception:
                pass
        return dt.strftime("%H:%M")
    except Exception:
        return str(t)

def delay_badge(d):
    try:
        n = int(d or 0)
    except (TypeError, ValueError):
        n = 0
    if n <= 0:
        return ok(t("in_time"))
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

def ask_password(prompt):
    try:
        return getpass.getpass(paint(prompt, C_)).strip()
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
        return p_warn(t("tl_none"))
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    times = [stop_eff_time(s) for s in items]
    passed = [i for i, t in enumerate(times) if t is not None and t <= now]
    at = passed[-1] if passed else -1
    print(f"\n  {bold(t('tl_title', n=len(items)))}")
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
            here = f"  {ok(t('tl_not_left'))}"
        elif at == len(items) - 1 and i == len(items) - 1:
            here = f"  {ok(t('tl_arrived'))}"
        elif at == i and times[at] is not None:
            if (now - times[at]).total_seconds() <= 180:
                here = f"  {ok(t('tl_here'))}"
            else:
                moving = True
        print(f"  {mark} {dim(times_.ljust(11))} {name}{tail}{here}")
        if i < len(items) - 1:
            if moving and at == i:
                print(f"  {dim('│')} {ok(t('tl_travel'))}")
            else:
                print(f"  {dim('│')}")

def print_board_table(lst, arrivi, page=0, page_size=20):
    """Tabella tabellone identica per nazionale e regionali (stesso formato)."""
    if not lst:
        p_warn(t("board_empty"))
        return []
    head_place = t("col_from") if arrivi else t("col_dest")
    rows = []
    data_rows = []
    
    start = page * page_size
    end = start + page_size
    subset = lst[start:end]
    
    for raw in subset:
        if not isinstance(raw, dict):
            continue
        e = raw.get("data") if isinstance(raw.get("data"), dict) else raw
        line = str(e.get("line") or e.get("category") or "")
        num = str(e.get("tripNumber") or e.get("trainNumber") or "")
        label = train_label(line, num)
        cat = train_category(line, e.get("category"))
        place = short(str((e.get("origin") if arrivi else e.get("destination"))
                          or e.get("stationName") or "—"), 32)
        ora = fmt_time(e.get("scheduledTime") or e.get("time"))
        plat = str(e.get("platform") or e.get("plannedPlatform") or "—")
        rows.append((ora, cat_paint(cat, label), place, paint(plat, Y),
                     delay_badge(e.get("delay", 0))))
        data_rows.append(e)
    _h = [t("col_n"), t("col_time"), t("col_train"), head_place, t("col_plat")]
    w = [len(x) for x in _h]
    for i, r in enumerate(rows, 1):
        w = [max(w[0], len(str(i))), max(w[1], vlen(r[0])), max(w[2], vlen(r[1])),
             max(w[3], vlen(r[2])), max(w[4], vlen(r[3]))]
    print(f"  {dim(pad_v(_h[0], w[0]))} {dim(pad_v(_h[1], w[1]))} {dim(pad_v(_h[2], w[2]))} "
          f"{dim(pad_v(head_place, w[3]))} {dim(pad_v(_h[4], w[4]))} {dim(t('col_state'))}")
    for i, r in enumerate(rows, 1):
        print(f"  {c_train(pad_v(str(i), w[0]))} {bold(pad_v(r[0], w[1]))} {pad_v(r[1], w[2])} "
              f"{pad_v(r[2], w[3])} {pad_v(r[3], w[4])} {r[4]}")
    
    total = len(lst)
    p_dim(f"Pagina {page+1} ({start+1}-{min(end, total)} di {total})")
    return data_rows

def train_board(station_id, country, arrivi, page=0):
    ep = "arrivals" if arrivi else "departures"
    p_title(t("board_title_dep" if not arrivi else "board_title_arr",
              sid=station_id, c=country))
    url = f"{TRAINBOARD}/{country}/{ep}?stationId={urllib.parse.quote(station_id)}"
    p_dim(f"GET {url}")
    try:
        lst = as_list(get_json(url))
    except Exception as e:
        return p_err(f"Errore tabellone: {e}")
    return print_board_table(lst, arrivi, page=page) or []

def train_details(numero, stazione, country):
    p_title(t("det_title", n=numero, s=stazione, c=country))
    url = (f"{TRAINBOARD}/{country}/details?trainNumber={urllib.parse.quote(numero)}"
           f"&stationId={urllib.parse.quote(stazione)}")
    p_dim(f"GET {url}")
    try:
        data = get_json(url)
    except Exception as e:
        return p_err(f"Errore dettaglio treno: {e}")
    e = (data.get("data") if isinstance(data, dict) else None) or data or {}
    print(f"  {bold(t('det_cat'))} {e.get('category') or e.get('line') or '—'}")
    print(f"  {bold(t('det_org'))} {stop_name(e.get('origin') or e.get('stationName')) or '—'}")
    print(f"  {bold(t('det_dest'))} {stop_name(e.get('destination')) or '—'}")
    print(f"  {bold(t('det_time'))} {fmt_time(e.get('scheduledTime') or e.get('time'))}  "
          f"{t('det_est')} {fmt_time(e.get('estimatedTime'))}  {delay_badge(e.get('delay', 0))}")
    print(f"  {bold(t('det_plat'))} {e.get('platform') or '—'}")
    print_timeline(e.get("stops") or e.get("stopovers") or [])

def train_trip_data(trip_id, country, base=None):
    # base = None -> nazionale (TRAINBOARD); altrimenti base regionale
    # (es. .../api/it/trains/trenord). Dual-try come reg_trip, mai vuoto.
    q = urllib.parse.quote(trip_id)
    bases = [base] if base else [f"{TRAINBOARD}/{country}"]
    last = {}
    for b in bases:
        for url in (f"{b}/trip?tripId={q}", f"{b}/trip/{q}"):
            try:
                data = get_json(url, timeout=12)
            except Exception:
                continue
            e = (data.get("data") if isinstance(data, dict) else None) or data or {}
            if isinstance(e, dict) and (e.get("stops") or e.get("stopovers")):
                return e
            if isinstance(e, dict) and e:
                last = e
    return last

# -- Fallback ritardo dai tabelloni (port di
# TrainProvider.refreshDelayFromUpcomingStations in
# mobile_app/lib/features/train/presentation/providers/train_provider.dart,
# usato dalla train_details_sheet quando il trip non fornisce il delay) -----
_delayCandidates = {}
_delayCandidateHits = {}

def _board_delay_value(e):
    # Mirror di TrainDeparture.fromJson: 'delay' int, altrimenti 'delayMinutes'.
    # (bool esclusi: in Python bool e' sottoclasse di int.)
    # None = voce senza info ritardo -> si passa alla stazione successiva
    # (l'app Flutter con ?? 0 non distingue, qui evitiamo falsi "in orario").
    for k in ("delay", "delayMinutes"):
        v = e.get(k)
        if isinstance(v, bool):
            continue
        if isinstance(v, int):
            return v
        try:
            if v is not None and str(v).strip() != "":
                return int(str(v).strip())
        except (TypeError, ValueError):
            pass
    return None

def _unwrap_board(raw):
    e = raw.get("data") if isinstance(raw.get("data"), dict) else raw
    return e if isinstance(e, dict) else {}

def refresh_delay_from_upcoming_stations(stops, trip_id="", train_number="",
                                         destination="", country="IT",
                                         current_delay=None, max_stations=3,
                                         board_base=None):
    """Cerca il ritardo nei tabelloni delle prossime fermate.

    Il trip endpoint spesso risponde delay=null mentre le bacheche di
    stazione hanno il realtime (es. FR 8326: trip null, Bari dice +7).
    Match per tripId, fallback numero+destinazione (il tripId cambia da
    stazione a stazione). Isteresi come nell'app: se il trip non fornisce
    alcun delay (None) adotta subito, altrimenti servono 2 conferme
    consecutive dello stesso valore. Ritorna (delay:int|None, stazione:str|None).
    board_base = base tabelloni regionali (es. .../api/it/trains/trenord),
    altrimenti tabelloni nazionali TRAINBOARD.
    """
    from datetime import datetime, timezone, timedelta
    items = [s for s in (stops or []) if isinstance(s, dict)]
    if not items:
        return None, None
    now = datetime.now(timezone.utc)

    def eff_dep(s):
        return (parse_utc(s.get("estimatedDeparture")) or parse_utc(s.get("departure"))
                or parse_utc(s.get("scheduledDeparture")) or parse_utc(s.get("time")))

    indices = []
    for i, s in enumerate(items):
        if s.get("cancelled") or s.get("canceled") or s.get("isCancelled"):
            continue
        t = eff_dep(s)
        if t is not None and t < now - timedelta(minutes=2):
            continue  # gia' passata
        indices.append(i)
        if len(indices) >= max_stations:
            break
    if not indices:
        # tutte passate (treno in arrivo): prova comunque le ultime
        for i in range(len(items) - 1, -1, -1):
            s = items[i]
            if not (s.get("cancelled") or s.get("canceled") or s.get("isCancelled")):
                indices.insert(0, i)
                if len(indices) >= max_stations:
                    break
    if not indices:
        return None, None

    dest_norm = (destination or "").strip().lower()
    num_norm = "".join(c for c in str(train_number or "") if c.isdigit())
    key = f"id:{trip_id}" if trip_id else f"n:{num_norm}|{dest_norm}"

    for i in indices:
        stop = items[i]
        station_id = str(stop.get("stationId") or stop.get("id") or stop.get("stopId") or "")
        if not station_id:
            continue
        st_country = (stop.get("country") or country or "IT")
        is_last = (i == len(items) - 1)
        modes = ("arrivals",) if is_last else ("departures", "arrivals")
        for ep in modes:
            is_arr = (ep == "arrivals")
            try:
                if board_base:
                    url = f"{board_base}/{ep}?stationId={urllib.parse.quote(station_id)}"
                else:
                    url = (f"{TRAINBOARD}/{st_country}/{ep}"
                           f"?stationId={urllib.parse.quote(station_id)}")
                board = as_list(get_json(url, timeout=8))
            except Exception:
                continue
            match = None
            if trip_id:
                for raw in board:
                    e = _unwrap_board(raw if isinstance(raw, dict) else {})
                    if str(e.get("tripId") or "") == trip_id:
                        match = e
                        break
            if match is None and num_norm:
                for raw in board:
                    e = _unwrap_board(raw if isinstance(raw, dict) else {})
                    enum = "".join(c for c in str(e.get("tripNumber") or e.get("trainNumber") or "") if c.isdigit())
                    if not enum or enum != num_norm:
                        continue
                    edest = (str(e.get("destination") or e.get("stationName") or "").strip().lower()
                             if not is_arr else
                             str(e.get("stationName") or e.get("destination") or "").strip().lower())
                    if dest_norm and edest and edest != dest_norm:
                        continue
                    match = e
                    break
            if match is None:
                continue
            delay = _board_delay_value(match)
            if delay is None:
                continue
            if current_delay is not None and delay == current_delay:
                _delayCandidates.pop(key, None)
                _delayCandidateHits.pop(key, None)
                return delay, stop.get("station") or stop.get("stationName") or stop.get("name")
            if current_delay is None:
                return delay, stop.get("station") or stop.get("stationName") or stop.get("name")
            if _delayCandidates.get(key) == delay:
                hits = _delayCandidateHits.get(key, 1) + 1
                _delayCandidateHits[key] = hits
                if hits >= 2:
                    _delayCandidates.pop(key, None)
                    _delayCandidateHits.pop(key, None)
                    return delay, stop.get("station") or stop.get("stationName") or stop.get("name")
            else:
                _delayCandidates[key] = delay
                _delayCandidateHits[key] = 1
    return None, None

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

def train_label(line, num):
    # "FR 8807" contiene gia' il numero -> non ripeterlo ("FR 8807 8807")
    line, num = str(line or "").strip(), str(num or "").strip()
    if num and num in line:
        return line
    return (line + " " + num).strip()

def draw_train_marker(cv, x, y, color, r=11):
    # Marker posizione HD: disco colorato + pittogramma treno geometrico
    # (primitive canvas, niente font/emoji: nitido su qualsiasi schermo).
    # Confinato dentro il canvas: a fine tratta non viene mai tagliato.
    try:
        h = cv.winfo_height()
    except Exception:
        h = 0
    if h and h > 2 * (r + 2):
        y = min(max(y, r + 2), h - r - 2)
    cv.create_oval(x - r, y - r, x + r, y + r,
                   fill=color, outline="white", width=2)
    ir = r * 0.68
    cv.create_oval(x - ir, y - ir, x + ir, y + ir, fill="white", outline="")
    bw, bh = ir * 1.02, ir * 1.12
    cv.create_rectangle(x - bw / 2, y - bh / 2, x + bw / 2, y + bh * 0.32,
                        fill=color, outline="")
    cv.create_rectangle(x - bw * 0.30, y - bh * 0.30, x + bw * 0.30, y + bh * 0.04,
                        fill="white", outline="")
    wr = max(1.2, ir * 0.15)
    for sx in (-1, 1):
        cv.create_oval(x + sx * bw * 0.27 - wr, y + bh * 0.30,
                       x + sx * bw * 0.27 + wr, y + bh * 0.30 + wr * 2,
                       fill=color, outline="")
    cv.create_line(x, y - bh / 2, x, y - bh / 2 - ir * 0.32,
                   fill=color, width=max(1, int(ir * 0.14)))

def open_timeline_gui(trip_id, country, trip_base=None, board_base=None):
    """Dispatcher grafica: CustomTkinter se disponibile, tkinter altrimenti."""
    try:
        import customtkinter  # noqa: F401
    except ImportError:
        p_dim("CustomTkinter assente: uso finestra base (pip install customtkinter).")
        return open_timeline_tk(trip_id, country, trip_base, board_base)
    return open_timeline_ctk(trip_id, country, trip_base, board_base)

def open_timeline_tk(trip_id, country, trip_base=None, board_base=None):
    # Stessa finestra per nazionale e regionali: cambia solo la base URL
    # (trip_base/board_base = es. .../api/it/trains/trenord, su
    # betacloud-transporter.is-cool.dev). Resto identico.
    import tkinter as tk
    from tkinter import ttk, messagebox, simpledialog
    from datetime import datetime, timezone
    try:
        trip = train_trip_data(trip_id, country, base=trip_base)
    except Exception as e:
        return p_err(f"Trip: {e}")
    stops = [s for s in (trip.get("stops") or trip.get("stopovers") or [])
             if isinstance(s, dict)]
    if not stops:
        return p_warn(t("gui_no_stops"))

    # Palette dark raffinata (slate + accento categoria)
    BG, SURFACE, CARD, CARD_HL = "#0A0C10", "#11151C", "#171D27", "#1F2733"
    TXT, SUB, TERT = "#F2F5F9", "#8A94A6", "#4A5468"
    BORDER, TRACK = "#232B38", "#1B2230"
    PRIMARY = "#3B82F6"
    OK, WARN, ERR = "#22C55E", "#F59E0B", "#EF4444"
    GUI_CAT = {"FR": "#E30613", "AV": "#E30613", "ICE": "#E30613", "TGV": "#E30613",
               "IC": "#F59E0B", "EC": "#F59E0B", "EN": "#F59E0B",
               "REG": "#22C55E", "R": "#22C55E", "RE": "#22C55E", "RB": "#22C55E",
               "S": "#06B6D4", "BUS": "#EAB308", "TRAM": "#EC4899", "FAL": "#EC4899"}

    def cat_hex(c):
        c = (c or "").upper()
        return GUI_CAT.get(c, "#3498DB")

    def delay_hex(d):
        try:
            n = int(d or 0)
        except (TypeError, ValueError):
            n = 0
        return OK if n <= 0 else (WARN if n <= 5 else ERR)  # stesse soglie della sheet

    def badge(parent, textvariable=None, text=None, color=PRIMARY):
        # Badge stile sheet Flutter: sfondo tinta 10%, bordo tinta 20%, testo pieno
        b = tk.Label(parent, textvariable=textvariable, text=text,
                     font=("Segoe UI", 9, "bold"),
                     bg=shade(color, 0.15), fg=color,
                     highlightbackground=shade(color, 0.40),
                     highlightthickness=1, padx=10, pady=4)
        return b

    def shade(hexcol, f):
        hexcol = hexcol.lstrip("#")
        r, g, b = (int(hexcol[i:i + 2], 16) for i in (0, 2, 4))
        r, g, b = (max(0, min(255, int(c * f))) for c in (r, g, b))
        return f"#{r:02x}{g:02x}{b:02x}"

    def mkbtn(parent, text, bg, fg="white", cmd=None, var=None):
        b = tk.Button(parent, text=text, textvariable=var,
                      font=("Segoe UI", 10, "bold"), bg=bg, fg=fg,
                      activebackground=shade(bg, 1.25), activeforeground=fg,
                      relief="flat", padx=14, pady=9, cursor="hand2",
                      bd=0, highlightthickness=0, command=cmd)
        b.bind("<Enter>", lambda e: b.configure(bg=shade(bg, 1.25)))
        b.bind("<Leave>", lambda e: b.configure(bg=bg))
        return b

    def ghostbtn(parent, text, cmd=None, var=None):
        b = tk.Button(parent, text=text, textvariable=var,
                      font=("Segoe UI", 10, "bold"), bg=CARD, fg=TXT,
                      activebackground=CARD_HL, activeforeground=TXT,
                      relief="flat", padx=14, pady=9, cursor="hand2",
                      highlightbackground=BORDER, highlightthickness=1,
                      bd=0, command=cmd)
        b.bind("<Enter>", lambda e: b.configure(bg=CARD_HL))
        b.bind("<Leave>", lambda e: b.configure(bg=CARD))
        return b

    def pill(parent, text=None, textvariable=None, bg="#000000", fg="white",
             font=("Segoe UI", 9, "bold")):
        """Pill scura semitrasparente per header colorati."""
        f = tk.Frame(parent, bg=bg)
        tk.Label(f, text=text, textvariable=textvariable, font=font,
                 bg=bg, fg=fg, padx=12, pady=5).pack()
        return f

    def section(parent, text):
        tk.Label(parent, text=text, font=("Segoe UI", 9, "bold"),
                 bg=BG, fg=SUB).pack(anchor="w", pady=(18, 8))

    def shift(dt, delay):
        if dt is None or not delay:
            return dt
        from datetime import timedelta
        try:
            return dt + timedelta(minutes=int(delay))
        except (TypeError, ValueError):
            return dt

    def position(sts, train_delay=0):
        # Mirror di _calcRouteProgress della sheet: stimati prima, poi
        # programmati + ritardo treno (il ritardo sposta gli orari).
        now = datetime.now(timezone.utc)
        eff = []
        for s in sts:
            eff.append(parse_utc(s.get("estimatedDeparture"))
                       or shift(parse_utc(s.get("departure"))
                                or parse_utc(s.get("scheduledDeparture"))
                                or parse_utc(s.get("time")), train_delay)
                       or parse_utc(s.get("estimatedArrival"))
                       or shift(parse_utc(s.get("scheduledArrival"))
                                or parse_utc(s.get("arrival")), train_delay))
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
    root.title(f"BC.Transporter – {train_label(line, num)}".strip())
    restore_window_geom(root, "480x860")
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
        save_window_geom(root)
        try:
            cancel_timers()
        except Exception:
            pass
        try:
            post_json(f"{BASE}/api/train-presence/leave",
                      {"clientId": client_id, "trainKey": train_key})
        except Exception:
            pass
        root.destroy()
    root.protocol("WM_DELETE_WINDOW", on_close)

    # -- Header --
    head = tk.Frame(root, bg=hexcol)
    head.pack(fill="x")

    hwrap = tk.Frame(head, bg=hexcol)
    hwrap.pack(fill="x", padx=22, pady=(22, 18))

    hrow = tk.Frame(hwrap, bg=hexcol)
    hrow.pack(fill="x")

    logo_tile = tk.Frame(hrow, bg="white", padx=12, pady=10)
    logo_tile.pack(side="left")
    logo_box = tk.Label(logo_tile, bg="white", fg=hexcol,
                        font=("Segoe UI", 17, "bold"), text=cat or "—")
    logo_box.pack()
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
            # fattore UNIFORME su x e y dentro un box 104x44: con fattori
            # diversi (es. subsample(nx, 1)) il logo si stira in verticale
            n = 1
            while img.width() // n > 104 or img.height() // n > 44:
                n += 1
            if n > 1:
                img = img.subsample(n, n)
            logo_box.configure(image=img)
            logo_box.image = img
        except Exception:
            pass

    hinfo = tk.Frame(hrow, bg=hexcol)
    hinfo.pack(side="left", padx=(14, 0), fill="x", expand=True)
    over_var = tk.StringVar(value=t("gui_train", c=country))
    tk.Label(hinfo, textvariable=over_var, font=("Segoe UI", 9, "bold"),
             bg=hexcol, fg="#FFFFFF").pack(anchor="w")
    title_var = tk.StringVar(value=train_label(line, num))
    tk.Label(hinfo, textvariable=title_var, font=("Segoe UI", 26, "bold"),
             bg=hexcol, fg="white").pack(anchor="w", pady=(1, 0))
    route_var = tk.StringVar()
    tk.Label(hinfo, textvariable=route_var, font=("Segoe UI", 12),
             bg=hexcol, fg="#FFE9E9").pack(anchor="w", pady=(3, 0))

    # Pills di stato: una bianca per lo stato, le altre scure
    chips = tk.Frame(hwrap, bg=hexcol)
    chips.pack(fill="x", pady=(14, 0))

    delay_var = tk.StringVar(value="")
    status_pill = tk.Frame(chips, bg="white", padx=12, pady=6)
    status_pill.pack(side="left")
    delay_lbl = tk.Label(status_pill, textvariable=delay_var,
                         font=("Segoe UI", 9, "bold"), bg="white", fg="#15803D")
    delay_lbl.pack()

    plat_var = tk.StringVar(value="")
    plat_pill = pill(chips, textvariable=plat_var, bg="#000000", fg="white")
    # visibile solo se c'e' un binario

    live_pill = tk.Frame(chips, bg="#000000", padx=12, pady=6)
    live_pill.pack(side="left", padx=(8, 0))
    tk.Label(live_pill, text="● LIVE", font=("Segoe UI", 9, "bold"),
             bg="#000000", fg="#4ADE80").pack()

    viewers_var = tk.StringVar(value="")
    tk.Label(chips, textvariable=viewers_var, font=("Segoe UI", 9, "bold"),
             bg=hexcol, fg="white").pack(side="left", padx=(10, 0))

    # -- Barra inferiore fissa --
    tk.Frame(root, bg=BORDER, height=1).pack(side="bottom", fill="x")
    upLbl_var = tk.StringVar(value="")
    live_var = tk.StringVar(value=t("gui_live_on"))
    bottom = tk.Frame(root, bg=SURFACE)
    bottom.pack(side="bottom", fill="x")
    brow = tk.Frame(bottom, bg=SURFACE)
    brow.pack(fill="x", padx=14, pady=12)

    mkbtn(brow, t("gui_update"), hexcol, cmd=lambda: refresh()).pack(side="left")
    ghostbtn(brow, "", var=live_var,
             cmd=lambda: (alive.update(live=not alive["live"]),
                          live_var.set(t("gui_live_on") if alive["live"] else t("gui_live_off")))
             ).pack(side="left", padx=(8, 0))
    ghostbtn(brow, t("gui_close"), cmd=on_close).pack(side="right")
    tk.Label(brow, textvariable=upLbl_var, font=("Segoe UI", 9), bg=SURFACE,
             fg=SUB).pack(side="right", padx=(0, 12))

    # -- Area scrollabile con colonna centrata (max 640px) --
    scroll_host = tk.Frame(root, bg=BG)
    scroll_host.pack(side="top", fill="both", expand=True)

    outer = tk.Canvas(scroll_host, bg=BG, highlightthickness=0)
    vsb = ttk.Scrollbar(scroll_host, orient="vertical", command=outer.yview)
    outer.configure(yscrollcommand=vsb.set)

    vsb.pack(side="right", fill="y")
    outer.pack(side="left", fill="both", expand=True)

    body = tk.Frame(outer, bg=BG)
    outer.create_window((0, 0), window=body, anchor="nw", tags="bodywin")
    content = tk.Frame(body, bg=BG)
    content.pack(fill="x")

    def _sync_scroll(_e=None):
        try:
            outer.configure(scrollregion=outer.bbox("all"))
            w = outer.winfo_width()
            outer.itemconfigure("bodywin", width=w)
            # colonna centrata: su schermi larghi non si allarga a dismisura
            side = max(18, (w - 640) // 2)
            content.pack_configure(padx=(side, side))
        except Exception:
            pass
    body.bind("<Configure>", lambda e: _sync_scroll())
    outer.bind("<Configure>", lambda e: _sync_scroll())

    def _wheel(e):
        try:
            d = int(-e.delta / 120) if getattr(e, "delta", 0) else 0
            if d:
                outer.yview_scroll(d, "units")
            else:
                outer.yview_scroll(1 if e.num == 5 else -1, "units")
        except Exception:
            pass
    outer.bind_all("<MouseWheel>", _wheel)
    outer.bind_all("<Button-4>", _wheel)
    outer.bind_all("<Button-5>", _wheel)

    # -- Stato corsa --
    prog = tk.Frame(content, bg=CARD, padx=16, pady=14)
    prog.pack(fill="x", pady=(18, 0))
    prog_top = tk.Frame(prog, bg=CARD)
    prog_top.pack(fill="x")
    prog_lbl_var = tk.StringVar()
    tk.Label(prog_top, textvariable=prog_lbl_var, font=("Segoe UI", 9, "bold"),
             bg=CARD, fg=SUB).pack(side="left")
    pct_var = tk.StringVar()
    tk.Label(prog_top, textvariable=pct_var, font=("Segoe UI", 13, "bold"),
             bg=CARD, fg=TXT).pack(side="right")
    bar = tk.Canvas(prog, height=8, bg=TRACK, highlightthickness=0)
    bar.pack(fill="x", pady=(10, 0))
    state_var = tk.StringVar()
    tk.Label(prog, textvariable=state_var, font=("Segoe UI", 11, "bold"),
             bg=CARD, fg=TXT, justify="left").pack(anchor="w", pady=(10, 0))

    # -- Prossima fermata (hero con banda accento) --
    nxt = tk.Frame(content, bg=CARD)
    nxt.pack(fill="x", pady=(12, 0))
    tk.Frame(nxt, bg=hexcol, width=4).pack(side="left", fill="y")
    nxt_in = tk.Frame(nxt, bg=CARD, padx=14, pady=12)
    nxt_in.pack(side="left", fill="both", expand=True)
    tk.Label(nxt_in, text=t("gui_next"), font=("Segoe UI", 9, "bold"),
             bg=CARD, fg=hexcol).pack(anchor="w")
    next_var = tk.StringVar()
    tk.Label(nxt_in, textvariable=next_var, font=("Segoe UI", 15, "bold"),
             bg=CARD, fg=TXT, justify="left").pack(anchor="w", pady=(3, 0))
    next_sub_var = tk.StringVar()
    tk.Label(nxt_in, textvariable=next_sub_var, font=("Segoe UI", 11),
             bg=CARD, fg=SUB, justify="left").pack(anchor="w", pady=(2, 0))

    section(content, t("gui_actions"))

    grid = tk.Frame(content, bg=BG)
    grid.pack(fill="x")
    match_var = tk.StringVar(value="")
    stats_box = tk.Frame(content, bg=CARD)

    def toast(msg, bad=False):
        (messagebox.showwarning if bad else messagebox.showinfo)("BC.Transporter", msg)

    def do_stats():
        try:
            d = get_json(f"{BASE}/api/stats/train/{urllib.parse.quote(cat)}/"
                         f"{urllib.parse.quote(num)}")
        except Exception as e:
            return toast(t("gui_e_stats", e=e), bad=True)
        rep = (d.get("data") if isinstance(d, dict) else None) or d or {}
        m = rep.get("metrics") if isinstance(rep, dict) else None or {}
        ins = rep.get("insights") if isinstance(rep, dict) else None or {}
        for w in stats_box.winfo_children():
            w.destroy()
        tk.Label(stats_box, text=t("gui_stats_title"), font=("Segoe UI", 9, "bold"),
                 bg=CARD, fg=SUB).pack(anchor="w", padx=12, pady=(10, 4))
        for k, v in [(t("gui_s_rel"), str(m.get("reliabilityScore", "—"))),
                     (t("gui_s_trend"), str(m.get("behaviorTrend", "—"))),
                     (t("gui_s_avg"), f"{m.get('averageNetDelayChangeMinutes', '—')} min"),
                     (t("gui_s_canc"), f"{m.get('cancellationRatePercentage', '—')}%"),
                     (t("gui_s_trips"), str(m.get("totalTripsAnalyzed", "—"))),
                     (t("gui_s_day"), str(ins.get("worstDayOfWeek", "—"))),
                     (t("gui_s_station"), str(ins.get("criticalBottleneckStation", "—")))]:
            r = tk.Frame(stats_box, bg=CARD)
            r.pack(fill="x", padx=12, pady=2)
            tk.Label(r, text=k, font=("Segoe UI", 9), bg=CARD, fg=SUB).pack(side="left")
            tk.Label(r, text=v, font=("Segoe UI", 9, "bold"), bg=CARD, fg=TXT).pack(side="right")
        tk.Frame(stats_box, bg=CARD, height=10).pack()
        stats_box.pack(fill="x", pady=(12, 0))

    def do_map():
        try:
            d = get_json(f"{BASE}/api/track-trip/{urllib.parse.quote(trip_id)}")
        except Exception as e:
            return toast(t("gui_e_map", e=e), bad=True)
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
            return toast(t("gui_e_share", e=e), bad=True)
        if not url:
            return toast(t("gui_share_ko"), bad=True)
        root.clipboard_clear()
        root.clipboard_append(url)
        toast(t("gui_share_ok", url=url))

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
            return toast(t("gui_e_social", e=e), bad=True)
        toast(t("gui_published", res=res))

    def do_save():
        os.makedirs(CACHE_DIR, exist_ok=True)
        out = cache_path("train", trip_id)
        okw = save_json_file(out, state["trip"])
        toast(t("gui_save_ok", out=out) if okw else t("gui_save_ko"), bad=not okw)

    def do_fav():
        # routeId=tripId e provider=country: così la sezione Preferiti
        # riapre diretto la timeline (come FavoriteTrain dell'app)
        fav_add("train", {"number": num,
                          "origin": stop_name(state["trip"].get("origin")),
                          "destination": stop_name(state["trip"].get("destination")),
                          "name": f"Treno {num}",
                          "routeId": trip_id, "provider": country})
        toast(t("gui_fav_added"))

    def do_alerts():
        msgs = collect_messages(state["trip"])
        if not msgs:
            return toast(t("gui_no_alerts"))
        win = tk.Toplevel(root)
        win.title(t("gui_alerts_t", n=len(msgs)))
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
            return toast(t("gui_e_match", e=e), bad=True)
        d = res.get("data") if isinstance(res, dict) else None
        ms = d.get("matches", []) if isinstance(d, dict) else []
        okm = bool(isinstance(d, dict) and d.get("isMatched") and any(
            isinstance(x, dict) and x.get("matched") for x in ms))
        det = ", ".join(str((x if isinstance(x, dict) else {}).get("country", "?"))
                        for x in ms[:5])
        match_var.set(t("gui_match_ok", d=det) if okm else t("gui_match_ko"))
        toast(t("gui_match_found", d=det) if okm else t("gui_match_none"))

    _btns = t("gui_btns")
    for i, (label, fn) in enumerate([(b, f) for b, f in zip(
            _btns, [do_stats, do_map, do_share, do_social,
                    do_save, do_alerts, do_fav, do_match])]):
        ghostbtn(grid, label, cmd=fn).grid(row=i // 2, column=i % 2,
                                           padx=4, pady=4, sticky="ew")
    for c in range(2):
        grid.columnconfigure(c, weight=1)
    tk.Label(grid, textvariable=match_var, font=("Segoe UI", 9, "bold"),
             bg=BG, fg=WARN).grid(row=4, column=0, columnspan=2, sticky="w", pady=(4, 0))

    # -- Timeline fermate (widget veri: ora | binario | fermata) --
    tl_head = tk.Frame(content, bg=BG)
    tl_head.pack(fill="x", pady=(18, 8))
    tk.Label(tl_head, text=t("gui_stops"), font=("Segoe UI", 9, "bold"),
             bg=BG, fg=SUB).pack(side="left")
    tl_count_var = tk.StringVar(value="")
    tk.Label(tl_head, textvariable=tl_count_var, font=("Segoe UI", 9),
             bg=BG, fg=TERT).pack(side="left", padx=(8, 0))

    tl = tk.Frame(content, bg=CARD, padx=6, pady=6)
    tl.pack(fill="x")

    ROW_H = 64

    def stop_eff(s, delay):
        # Mirror di _estimateStopTimesGlobal della sheet: stimati, altrimenti
        # programmati + ritardo treno (con backfill ±1 min se manca un lato)
        a = parse_utc(s.get("estimatedArrival"))
        if a is None:
            a = shift(parse_utc(s.get("scheduledArrival")) or parse_utc(s.get("arrival")),
                      delay)
        d = parse_utc(s.get("estimatedDeparture"))
        if d is None:
            d = shift(parse_utc(s.get("departure")) or parse_utc(s.get("scheduledDeparture"))
                      or parse_utc(s.get("time")), delay)
        from datetime import timedelta
        if a is None and d is not None:
            a = d - timedelta(minutes=1)
        if d is None and a is not None:
            d = a + timedelta(minutes=1)
        return a, d

    def stop_key(s):
        return str(s.get("stationId") or s.get("id") or s.get("stopId")
                   or s.get("station") or s.get("name") or "?")

    def build_row(i, is_last):
        # Struttura fissa creata una sola volta; testi e binario si
        # aggiornano a ogni refresh senza ricostruire (niente flicker,
        # lo scroll resta dov'e').
        vis = {"at": -1, "passed": False, "is_cur": False, "in_travel": False,
               "cancelled": False, "mp": None}
        row = tk.Frame(tl, bg=CARD)
        row.pack(fill="x")
        tcol = tk.Frame(row, bg=CARD, width=76)
        tcol.pack(side="left", fill="y")
        tcol.pack_propagate(False)
        if i == 0:
            t1 = tk.Label(tcol, font=("Segoe UI", 12, "bold"), bg=CARD, fg=TXT)
            t1.pack(anchor="e", pady=(14, 0))
            tk.Label(tcol, text=t("gui_dep"), font=("Segoe UI", 8),
                     bg=CARD, fg=TERT).pack(anchor="e")
            t2 = None
        elif is_last:
            t1 = tk.Label(tcol, font=("Segoe UI", 12, "bold"), bg=CARD, fg=TXT)
            t1.pack(anchor="e", pady=(14, 0))
            tk.Label(tcol, text=t("gui_arr"), font=("Segoe UI", 8),
                     bg=CARD, fg=TERT).pack(anchor="e")
            t2 = None
        else:
            t1 = tk.Label(tcol, font=("Segoe UI", 11, "bold"), bg=CARD, fg=TXT)
            t1.pack(anchor="e", pady=(10, 0))
            t2 = tk.Label(tcol, font=("Segoe UI", 10), bg=CARD, fg=SUB)
            t2.pack(anchor="e")

        rail = tk.Canvas(row, width=26, height=ROW_H, bg=CARD,
                         highlightthickness=0)
        rail.pack(side="left", fill="y", padx=(10, 6))

        def _paint_rail(_e=None):
            try:
                h = rail.winfo_height()
            except Exception:
                h = ROW_H
            if h < 24:
                h = ROW_H
            rail.delete("all")
            mid = h // 2
            _at, _mp = vis["at"], vis["mp"]
            # tratto sopra: percorso se siamo arrivati almeno a questa fermata
            if i != 0:
                rail.create_line(13, 0, 13, mid,
                                 fill=hexcol if _at != -1 and _at >= i else TRACK,
                                 width=3)
            # tratto sotto: pieno se superata, parziale col marker se in tratta
            if not is_last:
                if _mp is not None:
                    my = mid + (h - mid) * min(1.0, max(0.0, _mp))
                    rail.create_line(13, mid, 13, my, fill=hexcol, width=3)
                    rail.create_line(13, my, 13, h, fill=TRACK, width=3)
                else:
                    rail.create_line(13, mid, 13, h,
                                     fill=hexcol if _at > i else TRACK, width=3)
            if vis["cancelled"]:
                rail.create_text(13, mid, text="×",
                                 font=("Segoe UI", 14, "bold"), fill=ERR)
            elif vis["is_cur"] or vis["in_travel"] or (_at == i and not vis["cancelled"]):
                rail.create_oval(13 - 11, mid - 11, 13 + 11, mid + 11,
                                 outline=hexcol, width=2)
                rail.create_oval(13 - 6, mid - 6, 13 + 6, mid + 6,
                                 fill=hexcol, outline=hexcol)
            elif vis["passed"]:
                rail.create_oval(13 - 6, mid - 6, 13 + 6, mid + 6,
                                 fill=hexcol, outline=hexcol)
            else:
                rail.create_oval(13 - 6, mid - 6, 13 + 6, mid + 6,
                                 fill=CARD, outline="#5B6675", width=2)
            # marker treno in movimento lungo il segmento (come la Flutter)
            if _mp is not None and not is_last and not vis["cancelled"]:
                draw_train_marker(
                    rail, 13, mid + (h - mid) * min(1.0, max(0.0, _mp)), hexcol)

        rail.bind("<Configure>", _paint_rail)
        info = tk.Frame(row, bg=CARD)
        info.pack(side="left", fill="both", expand=True, pady=10)
        top = tk.Frame(info, bg=CARD)
        top.pack(fill="x")
        name_lbl = tk.Label(top, font=("Segoe UI", 12, "bold"), bg=CARD, fg=TXT)
        name_lbl.pack(side="left")
        state_lbl = tk.Label(top, font=("Segoe UI", 8, "bold"), bg=CARD, fg=SUB)
        state_lbl.pack(side="right")
        sub = tk.Frame(info, bg=CARD)
        sub.pack(fill="x", pady=(3, 0))
        detail_lbl = tk.Label(sub, font=("Segoe UI", 10), bg=CARD, fg=SUB)
        detail_lbl.pack(side="left")
        delay_lbl = tk.Label(sub, font=("Segoe UI", 10, "bold"), bg=CARD, fg=SUB)
        delay_lbl.pack(side="right")
        return {"vis": vis, "paint": _paint_rail, "t1": t1, "t2": t2,
                "name": name_lbl, "state": state_lbl,
                "detail": detail_lbl, "delay": delay_lbl}

    def paint_row(rec, i, s, n, is_last, at, now, eff, arrs, deps,
                  seg, seg_p, dwell, no_clock, train_delay):
        name = str(s.get("station") or s.get("stop") or s.get("stationName")
                   or s.get("name") or "?")
        arr = fmt_time(s.get("scheduledArrival") or s.get("arrival"))
        dep = fmt_time(s.get("scheduledDeparture") or s.get("departure") or s.get("time"))
        plat = str(s.get("platform") or s.get("actualPlatform") or "")
        _own = next((s[k] for k in ("delay", "arrivalDelay", "departureDelay")
                     if s.get(k) is not None), None)
        if _own is None:
            dl = train_delay
        else:
            try:
                dl = int(_own)
            except (TypeError, ValueError):
                dl = train_delay
        cancelled = bool(s.get("cancelled") or s.get("canceled") or s.get("isCancelled"))
        passed = at >= i and at != -1
        if no_clock:
            is_cur = (at == i and not cancelled and eff[at] is not None
                      and (now - eff[at]).total_seconds() <= 180)
            in_travel = (at == i and not cancelled and eff[at] is not None
                         and (now - eff[at]).total_seconds() > 180)
        else:
            is_cur = dwell and at == i and not cancelled
            in_travel = seg == i and not cancelled
        marker_p = seg_p if (seg == i and not is_last) else None
        if cancelled:
            st, st_fg = t("gui_cancelled"), ERR
        elif at == -1 and i == 0:
            st, st_fg = t("gui_not_left"), OK
        elif at == n - 1 and is_last:
            st, st_fg = t("gui_arrived"), OK
        elif is_cur:
            st, st_fg = t("gui_here"), OK
        elif in_travel:
            st, st_fg = t("gui_travel"), OK
        else:
            st, st_fg = "", SUB
        rec["vis"].update(at=at, passed=passed, is_cur=is_cur,
                           in_travel=in_travel, cancelled=cancelled,
                           mp=marker_p)
        if i == 0:
            rec["t1"].configure(text=dep)
        elif is_last:
            rec["t1"].configure(text=arr)
        else:
            rec["t1"].configure(text=arr)
            rec["t2"].configure(text=dep)
        rec["name"].configure(
            text=name,
            fg=ERR if cancelled else (SUB if (passed and not is_cur and not in_travel) else TXT))
        rec["state"].configure(text=st, fg=st_fg)
        bits = []
        if arr != dep and i != 0 and not is_last:
            bits.append(f"{arr} → {dep}")
        elif is_last:
            bits.append(t("gui_arr_full", t=arr))
        elif i == 0:
            bits.append(t("gui_dep_full", t=dep))
        if plat:
            bits.append(t("gui_bin", p=plat))
        rec["detail"].configure(text="  •  ".join(bits))
        rec["delay"].configure(text=f"{dl:+d} min" if (dl and not cancelled) else "",
                                fg=delay_hex(dl))
        rec["paint"]()

    def draw(data, train_delay=0):
        sts = [s for s in (data.get("stops") or data.get("stopovers") or [])
               if isinstance(s, dict)]
        n = len(sts)
        if not sts:
            state["tl_key"] = None
            state["tl_rows"] = []
            for w in tl.winfo_children():
                w.destroy()
            tk.Label(tl, text=t("gui_no_stops"), font=("Segoe UI", 10),
                     bg=CARD, fg=SUB, pady=12).pack()
            return 0, 0, {"frac": 0.0, "seg": -1, "seg_p": 0.0, "dwell": False}
        at, now, eff = position(sts, train_delay)
        tl_count_var.set(t("gui_n_stops", n=n))
        # posizione frazionaria sul segmento (come la timeline Flutter):
        # fermo in stazione (dwell) oppure in tratta con % del segmento
        arrs, deps = [], []
        for s in sts:
            a, dpt = stop_eff(s, train_delay)
            arrs.append(a)
            deps.append(dpt)
        seg, seg_p, dwell = -1, 0.0, False
        if 0 <= at < n - 1:
            a0, d0, a1 = arrs[at], deps[at], arrs[at + 1]
            if a0 is not None and d0 is not None and a0 <= now <= d0:
                dwell = True
            elif (d0 is not None and a1 is not None and a1 > d0
                    and d0 <= now < a1):
                total = (a1 - d0).total_seconds()
                seg = at
                seg_p = min(1.0, max(0.0, (now - d0).total_seconds() / total)) if total > 0 else 1.0
        if n <= 1:
            frac = 1.0 if at >= 0 else 0.0
        elif at == -1:
            frac = 0.0
        elif at >= n - 1:
            frac = 1.0
        elif dwell:
            frac = at / (n - 1)
        elif seg >= 0:
            frac = (seg + seg_p) / (n - 1)
        else:
            frac = at / (n - 1)
        pos = {"frac": frac, "seg": seg, "seg_p": seg_p, "dwell": dwell}
        no_clock = 0 <= at < n and (arrs[at] is None or deps[at] is None)
        # ricostruisci le righe solo se cambia la tratta, altrimenti aggiorna
        key = tuple(stop_key(s) for s in sts)
        if key != state.get("tl_key") or len(state.get("tl_rows") or []) != n:
            for w in tl.winfo_children():
                w.destroy()
            state["tl_rows"] = [build_row(i, i == n - 1) for i in range(n)]
            state["tl_key"] = key
        rows = state["tl_rows"]
        for i, s in enumerate(sts):
            paint_row(rows[i], i, s, n, i == n - 1, at, now, eff,
                      arrs, deps, seg, seg_p, dwell, no_clock, train_delay)
        return at, n, pos

    tk.Frame(content, bg=BG, height=24).pack()

    def refresh():
        try:
            data = train_trip_data(trip_id, country, base=trip_base)
        except Exception:
            return
        state["trip"] = data
        # Ritardo: prima il trip endpoint, poi le bacheche delle prossime
        # fermate (stessa logica della train_details_sheet Flutter: il trip
        # spesso risponde delay=null mentre i tabelloni hanno il realtime).
        try:
            _td = data.get("delay", data.get("delayMinutes"))
            trip_delay = None if _td is None else int(_td)
        except (TypeError, ValueError):
            trip_delay = None
        _stops = [s for s in (data.get("stops") or data.get("stopovers") or [])
                  if isinstance(s, dict)]
        _dest = stop_name(data.get("destination"))
        fb_delay, fb_station = refresh_delay_from_upcoming_stations(
            _stops, trip_id=trip_id, train_number=num, destination=_dest,
            country=country, current_delay=trip_delay,
            board_base=board_base)
        if fb_delay is not None:
            d = fb_delay
            state["delay_src"] = f"bacheca {fb_station}" if fb_station else "bacheca"
        elif trip_delay is not None:
            d = trip_delay
            state["delay_src"] = "trip"
        else:
            d = 0
            state["delay_src"] = ""
        at, n, pos = draw(data, d)
        frac = max(0.0, min(1.0, pos.get("frac", 0.0)))
        seg, seg_p = pos.get("seg", -1), pos.get("seg_p", 0.0)
        title_var.set(train_label(data.get('line') or data.get('category') or line,
                                  data.get('tripNumber') or data.get('trainNumber') or num))
        route_var.set(f"{stop_name(data.get('origin'))}  →  {stop_name(data.get('destination'))}")
        # pill di stato bianca con testo colorato (segno sempre corretto)
        delay_var.set(t("gui_on_time") if d == 0
                      else (t("gui_delay", d=d) if d > 0 else t("gui_early", d=d)))
        delay_lbl.configure(fg="#15803D" if d <= 0 else ("#B45309" if d <= 5 else "#DC2626"))
        _plat = str(data.get("platform") or "").strip()
        plat_var.set(f"BIN {_plat}" if _plat else "")
        try:
            if _plat:
                plat_pill.pack(side="left", padx=(8, 0))
            else:
                plat_pill.pack_forget()
        except Exception:
            pass
        # progresso + frase di stato (frazionario come la sheet Flutter)
        sts_all = [s for s in (data.get("stops") or data.get("stopovers") or [])
                   if isinstance(s, dict)]
        done = (at + 1) if at >= 0 else 0
        _src = state.get("delay_src", "")
        _suffix = f"  ·  {t('gui_delay_from', src=_src.upper())}" if _src.startswith("bacheca") else ""
        prog_lbl_var.set(t("gui_route_done", done=done, n=n) + _suffix)
        pct_var.set(f"{int(frac * 100)}%")
        try:
            bar.delete("all")
            bw = bar.winfo_width() or 400
            if frac > 0:
                bar.create_rectangle(0, 0, bw * frac, 8, fill=hexcol, outline="")
        except Exception:
            pass
        if n and at == -1:
            t0 = fmt_time(sts_all[0].get("scheduledDeparture") or sts_all[0].get("departure")
                          or sts_all[0].get("time")) if sts_all else "—"
            state_var.set(t("gui_stop_wait", t=t0))
        elif n and at == n - 1:
            state_var.set(t("gui_stop_done"))
        elif n and 0 <= at < n:
            cur = sts_all[at]
            cn = str(cur.get("station") or cur.get("stop") or cur.get("stationName")
                     or cur.get("name") or "?")
            if 0 <= seg < n - 1:
                nx = sts_all[seg + 1]
                nn = str(nx.get("station") or nx.get("stop") or nx.get("stationName")
                         or nx.get("name") or "?")
                state_var.set(t("gui_stop_travel", a=cn, b=nn, p=int(seg_p * 100)))
            elif pos.get("dwell"):
                state_var.set(t("gui_stop_dwell", s=cn))
            else:
                state_var.set(t("gui_stop_last", s=cn))
        else:
            state_var.set("")
        # prossima fermata
        if n and 0 <= at + 1 < n:
            nx = sts_all[at + 1]
            nm = str(nx.get("station") or nx.get("stop") or nx.get("stationName")
                     or nx.get("name") or "?")
            nt = fmt_time(nx.get("scheduledArrival") or nx.get("arrival")
                          or nx.get("scheduledDeparture") or nx.get("departure"))
            pl = str(nx.get("platform") or "")
            next_var.set(nm)
            bits = []
            if nt and nt != "—":
                bits.append(t("gui_at", t=nt))
            if pl:
                bits.append(t("gui_plat", p=pl))
            next_sub_var.set("  •  ".join(bits))
        elif n and at == n - 1:
            next_var.set(t("gui_dest_done"))
            next_sub_var.set("")
        else:
            next_var.set("—")
            next_sub_var.set("")
        upLbl_var.set(t("gui_updated", t=datetime.now().strftime('%H:%M:%S')))
        try:
            _sync_scroll()
        except Exception:
            pass

    timers = {"tick": None, "auto": None}

    def cancel_timers():
        for k in ("tick", "auto"):
            try:
                if timers[k]:
                    root.after_cancel(timers[k])
            except Exception:
                pass
            timers[k] = None

    def tick_viewers():
        try:
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
                    viewers_var.set(t("gui_online", v=v) if isinstance(v, int) and v > 0 else "")
            except Exception:
                pass
            if alive["on"]:
                timers["tick"] = root.after(15000, tick_viewers)
        except Exception:
            pass

    def auto():
        try:
            if not alive["on"]:
                return
            try:
                if root.winfo_exists() and alive["live"]:
                    refresh()
            except Exception:
                pass
            if alive["on"]:
                timers["auto"] = root.after(30000, auto)
        except Exception:
            pass

    root.minsize(440, 640)

    refresh()
    root.after_idle(_sync_scroll)
    tick_viewers()
    try:
        timers["auto"] = root.after(30000, auto)
    except Exception:
        pass
    p_ok("Finestra timeline aperta con grafica moderna.")
    root.mainloop()

def open_timeline_ctk(trip_id, country, trip_base=None, board_base=None):
    # Finestra avanzata in CustomTkinter (+Pillow per i loghi): stesse logiche
    # dati della versione tkinter (trip, ritardo da bacheche, posizione
    # frazionaria), widget moderni con scroll nativo e angoli arrotondati.
    import io
    import tkinter as tk
    import customtkinter as ctk
    from tkinter import messagebox, simpledialog
    from datetime import datetime, timezone, timedelta
    from PIL import Image

    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")

    try:
        trip = train_trip_data(trip_id, country, base=trip_base)
    except Exception as e:
        return p_err(f"Trip: {e}")
    stops = [s for s in (trip.get("stops") or trip.get("stopovers") or [])
             if isinstance(s, dict)]
    if not stops:
        return p_warn(t("gui_no_stops"))

    BG, SURFACE, CARD, CARD_HL = "#0A0C10", "#11151C", "#171D27", "#232C3B"
    TXT, SUB, TERT = "#F2F5F9", "#8A94A6", "#4A5468"
    TRACK = "#1B2230"
    OK, WARN, ERR = "#22C55E", "#F59E0B", "#EF4444"
    GUI_CAT = {"FR": "#E30613", "AV": "#E30613", "ICE": "#E30613", "TGV": "#E30613",
               "IC": "#F59E0B", "EC": "#F59E0B", "EN": "#F59E0B",
               "REG": "#22C55E", "R": "#22C55E", "RE": "#22C55E", "RB": "#22C55E",
               "S": "#06B6D4", "BUS": "#EAB308", "TRAM": "#EC4899", "FAL": "#EC4899"}

    def cat_hex(c):
        return GUI_CAT.get((c or "").upper(), "#3498DB")

    def delay_hex(d):
        try:
            n = int(d or 0)
        except (TypeError, ValueError):
            n = 0
        return OK if n <= 0 else (WARN if n <= 5 else ERR)

    def shade(hexcol, f):
        hexcol = hexcol.lstrip("#")
        r, g, b = (int(hexcol[i:i + 2], 16) for i in (0, 2, 4))
        r, g, b = (max(0, min(255, int(c * f))) for c in (r, g, b))
        return f"#{r:02x}{g:02x}{b:02x}"

    def shift(dt, delay):
        if dt is None or not delay:
            return dt
        try:
            return dt + timedelta(minutes=int(delay))
        except (TypeError, ValueError):
            return dt

    def stop_eff(s, delay):
        a = parse_utc(s.get("estimatedArrival"))
        if a is None:
            a = shift(parse_utc(s.get("scheduledArrival")) or parse_utc(s.get("arrival")),
                      delay)
        d = parse_utc(s.get("estimatedDeparture"))
        if d is None:
            d = shift(parse_utc(s.get("departure")) or parse_utc(s.get("scheduledDeparture"))
                      or parse_utc(s.get("time")), delay)
        if a is None and d is not None:
            a = d - timedelta(minutes=1)
        if d is None and a is not None:
            d = a + timedelta(minutes=1)
        return a, d

    def position(sts, train_delay=0):
        now = datetime.now(timezone.utc)
        eff = []
        for s in sts:
            eff.append(parse_utc(s.get("estimatedDeparture"))
                       or shift(parse_utc(s.get("departure"))
                                or parse_utc(s.get("scheduledDeparture"))
                                or parse_utc(s.get("time")), train_delay)
                       or parse_utc(s.get("estimatedArrival"))
                       or shift(parse_utc(s.get("scheduledArrival"))
                                or parse_utc(s.get("arrival")), train_delay))
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

    root = ctk.CTk()
    root.title(f"BC.Transporter – {train_label(line, num)}")
    restore_window_geom(root, "520x920")
    root.minsize(460, 680)
    root.configure(fg_color=BG)

    FT_OVER = ctk.CTkFont(family="Segoe UI", size=11, weight="bold")
    FT_TITLE = ctk.CTkFont(family="Segoe UI", size=28, weight="bold")
    FT_ROUTE = ctk.CTkFont(family="Segoe UI", size=13)
    FT_PILL = ctk.CTkFont(family="Segoe UI", size=11, weight="bold")
    FT_SEC = ctk.CTkFont(family="Segoe UI", size=11, weight="bold")
    FT_NAME = ctk.CTkFont(family="Segoe UI", size=13, weight="bold")
    FT_SUB = ctk.CTkFont(family="Segoe UI", size=11)
    FT_TIME = ctk.CTkFont(family="Segoe UI", size=13, weight="bold")
    FT_BTN = ctk.CTkFont(family="Segoe UI", size=12, weight="bold")

    alive = {"on": True, "live": True}
    state = {"trip": trip, "delay_src": ""}

    def on_close():
        alive["on"] = False
        save_window_geom(root)
        try:
            cancel_timers()
        except Exception:
            pass
        try:
            post_json(f"{BASE}/api/train-presence/leave",
                      {"clientId": client_id, "trainKey": train_key})
        except Exception:
            pass
        root.destroy()
    root.protocol("WM_DELETE_WINDOW", on_close)

    # -- Header --
    head = ctk.CTkFrame(root, fg_color=hexcol, corner_radius=0)
    head.pack(fill="x")
    hwrap = ctk.CTkFrame(head, fg_color="transparent")
    hwrap.pack(fill="x", padx=22, pady=(22, 18))
    hrow = ctk.CTkFrame(hwrap, fg_color="transparent")
    hrow.pack(fill="x")

    logo_tile = ctk.CTkFrame(hrow, fg_color="white", corner_radius=10)
    logo_tile.pack(side="left")
    logo_lbl = ctk.CTkLabel(logo_tile, text=cat or "—", font=ctk.CTkFont(
        family="Segoe UI", size=17, weight="bold"),
        text_color=hexcol, fg_color="transparent")
    logo_lbl.pack(padx=12, pady=10)
    if png_url:
        try:
            req = urllib.request.Request(png_url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=15) as res:
                raw = res.read()
            pil = Image.open(io.BytesIO(raw)).convert("RGBA")
            w, h = pil.size
            sc = min(120 / w, 48 / h, 1.0)
            nw, nh = max(1, int(w * sc)), max(1, int(h * sc))
            img = ctk.CTkImage(pil.resize((nw, nh), Image.LANCZOS), size=(nw, nh))
            logo_lbl.configure(image=img, text="")
            logo_lbl.image = img
        except Exception:
            pass

    hinfo = ctk.CTkFrame(hrow, fg_color="transparent")
    hinfo.pack(side="left", padx=(14, 0), fill="x", expand=True)
    over_var = ctk.StringVar(value=t("gui_train", c=country))
    ctk.CTkLabel(hinfo, textvariable=over_var, font=FT_OVER,
                 text_color="white", fg_color="transparent").pack(anchor="w")
    title_var = ctk.StringVar(value=train_label(line, num))
    ctk.CTkLabel(hinfo, textvariable=title_var, font=FT_TITLE,
                 text_color="white", fg_color="transparent").pack(anchor="w")
    route_var = ctk.StringVar(value="")
    ctk.CTkLabel(hinfo, textvariable=route_var, font=FT_ROUTE,
                 text_color="#FFE9E9", fg_color="transparent").pack(anchor="w", pady=(3, 0))

    chips = ctk.CTkFrame(hwrap, fg_color="transparent")
    chips.pack(fill="x", pady=(14, 0))

    def pill(parent, text="", textvariable=None, fg="#000000", tc="white"):
        f = ctk.CTkFrame(parent, fg_color=fg, corner_radius=12)
        ctk.CTkLabel(f, text=text, textvariable=textvariable, font=FT_PILL,
                     text_color=tc, fg_color="transparent").pack(padx=12, pady=6)
        return f

    delay_var = ctk.StringVar(value="")
    status_pill = ctk.CTkFrame(chips, fg_color="white", corner_radius=12)
    status_pill.pack(side="left")
    delay_lbl = ctk.CTkLabel(status_pill, textvariable=delay_var, font=FT_PILL,
                             text_color="#15803D", fg_color="transparent")
    delay_lbl.pack(padx=12, pady=6)

    plat_var = ctk.StringVar(value="")
    plat_pill = pill(chips, textvariable=plat_var, fg="#000000", tc="white")
    plat_shown = {"on": False}

    live_pill = pill(chips, text="● LIVE", fg="#000000", tc="#4ADE80")
    live_pill.pack(side="left", padx=(8, 0))

    viewers_var = ctk.StringVar(value="")
    ctk.CTkLabel(chips, textvariable=viewers_var, font=FT_PILL,
                 text_color="white", fg_color="transparent").pack(side="left", padx=(10, 0))

    # -- Barra inferiore --
    ctk.CTkFrame(root, fg_color="#232B38", height=1, corner_radius=0).pack(
        side="bottom", fill="x")
    upLbl_var = ctk.StringVar(value="")
    live_var = ctk.StringVar(value=t("gui_live_on"))
    bottom = ctk.CTkFrame(root, fg_color=SURFACE, corner_radius=0)
    bottom.pack(side="bottom", fill="x")
    brow = ctk.CTkFrame(bottom, fg_color="transparent")
    brow.pack(fill="x", padx=14, pady=12)
    ctk.CTkButton(brow, text=t("gui_update"), font=FT_BTN, fg_color=hexcol,
                  hover_color=shade(hexcol, 0.85), text_color="white",
                  corner_radius=10, height=38,
                  command=lambda: refresh()).pack(side="left")

    def toggle_live():
        alive["live"] = not alive["live"]
        live_var.set(t("gui_live_on") if alive["live"] else t("gui_live_off"))
    ctk.CTkButton(brow, textvariable=live_var, font=FT_BTN, fg_color=CARD,
                  hover_color=CARD_HL, text_color=TXT, corner_radius=10,
                  height=38, command=toggle_live).pack(side="left", padx=(8, 0))
    ctk.CTkButton(brow, text=t("gui_close"), font=FT_BTN, fg_color=CARD,
                  hover_color=CARD_HL, text_color=TXT, corner_radius=10,
                  height=38, command=on_close).pack(side="right")
    ctk.CTkLabel(brow, textvariable=upLbl_var, font=FT_SUB,
                 text_color=SUB, fg_color="transparent").pack(side="right", padx=(0, 12))

    # -- Area scrollabile --
    body = ctk.CTkScrollableFrame(root, fg_color=BG, corner_radius=0)
    body.pack(fill="both", expand=True)
    content = ctk.CTkFrame(body, fg_color="transparent")
    content.pack(fill="x")

    def _fix_scroll():
        # la scrollregion a volte non si aggiorna da sola: forziamola
        try:
            body._parent_canvas.configure(
                scrollregion=body._parent_canvas.bbox("all"))
        except Exception:
            pass

    def _sync_pad(_e=None):
        try:
            w = body.winfo_width()
            side = max(18, (w - 660) // 2)
            content.pack_configure(padx=(side, side))
        except Exception:
            pass
        root.after_idle(_fix_scroll)
    body.bind("<Configure>", _sync_pad)

    # -- Stato corsa --
    prog = ctk.CTkFrame(content, fg_color=CARD, corner_radius=14)
    prog.pack(fill="x", pady=(18, 0))
    prog_in = ctk.CTkFrame(prog, fg_color="transparent")
    prog_in.pack(fill="x", padx=16, pady=14)
    prog_top = ctk.CTkFrame(prog_in, fg_color="transparent")
    prog_top.pack(fill="x")
    prog_lbl_var = ctk.StringVar(value="")
    ctk.CTkLabel(prog_top, textvariable=prog_lbl_var, font=FT_SEC,
                 text_color=SUB, fg_color="transparent").pack(side="left")
    pct_var = ctk.StringVar(value="")
    ctk.CTkLabel(prog_top, textvariable=pct_var,
                 font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
                 text_color=TXT, fg_color="transparent").pack(side="right")
    bar = ctk.CTkProgressBar(prog_in, progress_color=hexcol, fg_color=TRACK,
                             height=8, corner_radius=4)
    bar.pack(fill="x", pady=(10, 0))
    bar.set(0)
    state_var = ctk.StringVar(value="")
    ctk.CTkLabel(prog_in, textvariable=state_var,
                 font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
                 text_color=TXT, fg_color="transparent",
                 justify="left").pack(anchor="w", pady=(10, 0))

    # -- Prossima fermata --
    nxt = ctk.CTkFrame(content, fg_color=CARD, corner_radius=14)
    nxt.pack(fill="x", pady=(12, 0))
    ctk.CTkFrame(nxt, fg_color=hexcol, width=4, corner_radius=0).pack(
        side="left", fill="y")
    nxt_in = ctk.CTkFrame(nxt, fg_color="transparent")
    nxt_in.pack(side="left", fill="both", expand=True, padx=14, pady=12)
    ctk.CTkLabel(nxt_in, text=t("gui_next"), font=FT_SEC,
                 text_color=hexcol, fg_color="transparent").pack(anchor="w")
    next_var = ctk.StringVar(value="")
    ctk.CTkLabel(nxt_in, textvariable=next_var,
                 font=ctk.CTkFont(family="Segoe UI", size=16, weight="bold"),
                 text_color=TXT, fg_color="transparent",
                 justify="left").pack(anchor="w", pady=(3, 0))
    next_sub_var = ctk.StringVar(value="")
    ctk.CTkLabel(nxt_in, textvariable=next_sub_var, font=FT_SUB,
                 text_color=SUB, fg_color="transparent",
                 justify="left").pack(anchor="w", pady=(2, 0))

    # -- Azioni --
    ctk.CTkLabel(content, text=t("gui_actions"), font=FT_SEC, text_color=SUB,
                 fg_color="transparent").pack(anchor="w", pady=(18, 8))
    grid = ctk.CTkFrame(content, fg_color="transparent")
    grid.pack(fill="x")
    grid.columnconfigure(0, weight=1)
    grid.columnconfigure(1, weight=1)
    match_var = ctk.StringVar(value="")
    stats_box = ctk.CTkFrame(content, fg_color=CARD, corner_radius=14)

    def toast(msg, bad=False):
        (messagebox.showwarning if bad else messagebox.showinfo)("BC.Transporter", msg)

    def do_stats():
        try:
            d = get_json(f"{BASE}/api/stats/train/{urllib.parse.quote(cat)}/"
                         f"{urllib.parse.quote(num)}")
        except Exception as e:
            return toast(t("gui_e_stats", e=e), bad=True)
        rep = (d.get("data") if isinstance(d, dict) else None) or d or {}
        m = rep.get("metrics") if isinstance(rep, dict) else None or {}
        ins = rep.get("insights") if isinstance(rep, dict) else None or {}
        for w in stats_box.winfo_children():
            w.destroy()
        box = ctk.CTkFrame(stats_box, fg_color="transparent")
        box.pack(fill="x", padx=14, pady=12)
        ctk.CTkLabel(box, text=t("gui_stats_title"), font=FT_SEC,
                     text_color=SUB, fg_color="transparent").pack(anchor="w", pady=(0, 6))
        for k, v in [(t("gui_s_rel"), str(m.get("reliabilityScore", "—"))),
                     (t("gui_s_trend"), str(m.get("behaviorTrend", "—"))),
                     (t("gui_s_avg"), f"{m.get('averageNetDelayChangeMinutes', '—')} min"),
                     (t("gui_s_canc"), f"{m.get('cancellationRatePercentage', '—')}%"),
                     (t("gui_s_trips"), str(m.get("totalTripsAnalyzed", "—"))),
                     (t("gui_s_day"), str(ins.get("worstDayOfWeek", "—"))),
                     (t("gui_s_station"), str(ins.get("criticalBottleneckStation", "—")))]:
            r = ctk.CTkFrame(box, fg_color="transparent")
            r.pack(fill="x", pady=2)
            ctk.CTkLabel(r, text=k, font=FT_SUB, text_color=SUB,
                         fg_color="transparent").pack(side="left")
            ctk.CTkLabel(r, text=v, font=FT_PILL, text_color=TXT,
                         fg_color="transparent").pack(side="right")
        stats_box.pack(fill="x", pady=(12, 0))
        _sync_pad()

    def do_map():
        try:
            d = get_json(f"{BASE}/api/track-trip/{urllib.parse.quote(trip_id)}")
        except Exception as e:
            return toast(t("gui_e_map", e=e), bad=True)
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
            return toast(t("gui_e_share", e=e), bad=True)
        if not url:
            return toast(t("gui_share_ko"), bad=True)
        root.clipboard_clear()
        root.clipboard_append(url)
        toast(t("gui_share_ok", url=url))

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
            return toast(t("gui_e_social", e=e), bad=True)
        toast(t("gui_published", res=res))

    def do_save():
        os.makedirs(CACHE_DIR, exist_ok=True)
        out = cache_path("train", trip_id)
        okw = save_json_file(out, state["trip"])
        toast(t("gui_save_ok", out=out) if okw else t("gui_save_ko"), bad=not okw)

    def do_fav():
        fav_add("train", {"number": num,
                          "origin": stop_name(state["trip"].get("origin")),
                          "destination": stop_name(state["trip"].get("destination")),
                          "name": f"Treno {num}",
                          "routeId": trip_id, "provider": country})
        toast(t("gui_fav_added"))

    def do_alerts():
        msgs = collect_messages(state["trip"])
        if not msgs:
            return toast(t("gui_no_alerts"))
        win = ctk.CTkToplevel(root)
        win.title(t("gui_alerts_t", n=len(msgs)))
        win.geometry("480x400")
        txt = ctk.CTkTextbox(win, font=FT_SUB, fg_color=CARD, text_color=TXT,
                             corner_radius=10)
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
            return toast(t("gui_e_match", e=e), bad=True)
        d = res.get("data") if isinstance(res, dict) else None
        ms = d.get("matches", []) if isinstance(d, dict) else []
        okm = bool(isinstance(d, dict) and d.get("isMatched") and any(
            isinstance(x, dict) and x.get("matched") for x in ms))
        det = ", ".join(str((x if isinstance(x, dict) else {}).get("country", "?"))
                        for x in ms[:5])
        match_var.set(t("gui_match_ok", d=det) if okm else t("gui_match_ko"))
        toast(t("gui_match_found", d=det) if okm else t("gui_match_none"))

    _btns = t("gui_btns")
    for i, (label, fn) in enumerate([(b, f) for b, f in zip(
            _btns, [do_stats, do_map, do_share, do_social,
                    do_save, do_alerts, do_fav, do_match])]):
        ctk.CTkButton(grid, text=label, font=FT_BTN, fg_color=CARD,
                      hover_color=CARD_HL, text_color=TXT, corner_radius=10,
                      height=42, command=fn).grid(row=i // 2, column=i % 2,
                                                 padx=4, pady=4, sticky="ew")
    ctk.CTkLabel(grid, textvariable=match_var, font=FT_PILL, text_color=WARN,
                 fg_color="transparent").grid(row=4, column=0, columnspan=2,
                                             sticky="w", pady=(4, 0))

    # -- Timeline --
    tl_head = ctk.CTkFrame(content, fg_color="transparent")
    tl_head.pack(fill="x", pady=(18, 8))
    ctk.CTkLabel(tl_head, text=t("gui_stops"), font=FT_SEC, text_color=SUB,
                 fg_color="transparent").pack(side="left")
    tl_count_var = ctk.StringVar(value="")
    ctk.CTkLabel(tl_head, textvariable=tl_count_var, font=FT_SUB,
                 text_color=TERT, fg_color="transparent").pack(side="left", padx=(8, 0))

    tl = ctk.CTkFrame(content, fg_color=CARD, corner_radius=14)
    tl.pack(fill="x")

    ROW_H = 64

    def stop_key(s):
        return str(s.get("stationId") or s.get("id") or s.get("stopId")
                   or s.get("station") or s.get("name") or "?")

    def build_row(i, is_last):
        # Struttura fissa creata una sola volta; testi e binario si
        # aggiornano a ogni refresh senza ricostruire (niente flicker,
        # lo scroll resta dov'e').
        vis = {"at": -1, "passed": False, "is_cur": False, "in_travel": False,
               "cancelled": False, "mp": None}
        row = ctk.CTkFrame(tl, fg_color="transparent")
        row.pack(fill="x")
        # height esplicita: CTkFrame di default chiede 200px e con
        # propagate off la riga diventerebbe altissima
        tcol = ctk.CTkFrame(row, fg_color="transparent", width=76, height=10)
        tcol.pack(side="left", fill="y")
        tcol.pack_propagate(False)
        if i == 0:
            t1 = ctk.CTkLabel(tcol, font=FT_TIME, text_color=TXT,
                              fg_color="transparent")
            t1.pack(anchor="e", pady=(14, 0))
            ctk.CTkLabel(tcol, text=t("gui_dep"), font=FT_SUB, text_color=TERT,
                         fg_color="transparent").pack(anchor="e")
            t2 = None
        elif is_last:
            t1 = ctk.CTkLabel(tcol, font=FT_TIME, text_color=TXT,
                              fg_color="transparent")
            t1.pack(anchor="e", pady=(14, 0))
            ctk.CTkLabel(tcol, text=t("gui_arr"), font=FT_SUB, text_color=TERT,
                         fg_color="transparent").pack(anchor="e")
            t2 = None
        else:
            t1 = ctk.CTkLabel(tcol, font=FT_TIME, text_color=TXT,
                              fg_color="transparent")
            t1.pack(anchor="e", pady=(10, 0))
            t2 = ctk.CTkLabel(tcol, font=FT_SUB, text_color=SUB,
                              fg_color="transparent")
            t2.pack(anchor="e")

        rail = tk.Canvas(row, width=26, height=ROW_H, bg=CARD,
                         highlightthickness=0)
        rail.pack(side="left", fill="y", padx=(10, 6))

        def _paint_rail(_e=None):
            try:
                h = rail.winfo_height()
            except Exception:
                h = ROW_H
            if h < 24:
                h = ROW_H
            rail.delete("all")
            mid = h // 2
            _at, _mp = vis["at"], vis["mp"]
            if i != 0:
                rail.create_line(13, 0, 13, mid,
                                 fill=hexcol if _at != -1 and _at >= i else TRACK,
                                 width=3)
            if not is_last:
                if _mp is not None:
                    my = mid + (h - mid) * min(1.0, max(0.0, _mp))
                    rail.create_line(13, mid, 13, my, fill=hexcol, width=3)
                    rail.create_line(13, my, 13, h, fill=TRACK, width=3)
                else:
                    rail.create_line(13, mid, 13, h,
                                     fill=hexcol if _at > i else TRACK, width=3)
            if vis["cancelled"]:
                rail.create_text(13, mid, text="×",
                                 font=("Segoe UI", 14, "bold"), fill=ERR)
            elif vis["is_cur"] or vis["in_travel"] or (_at == i and not vis["cancelled"]):
                rail.create_oval(13 - 11, mid - 11, 13 + 11, mid + 11,
                                 outline=hexcol, width=2)
                rail.create_oval(13 - 6, mid - 6, 13 + 6, mid + 6,
                                 fill=hexcol, outline=hexcol)
            elif vis["passed"]:
                rail.create_oval(13 - 6, mid - 6, 13 + 6, mid + 6,
                                 fill=hexcol, outline=hexcol)
            else:
                rail.create_oval(13 - 6, mid - 6, 13 + 6, mid + 6,
                                 fill=CARD, outline="#5B6675", width=2)
            if _mp is not None and not is_last and not vis["cancelled"]:
                draw_train_marker(
                    rail, 13, mid + (h - mid) * min(1.0, max(0.0, _mp)), hexcol)

        rail.bind("<Configure>", _paint_rail)
        info = ctk.CTkFrame(row, fg_color="transparent")
        info.pack(side="left", fill="both", expand=True, pady=10)
        top = ctk.CTkFrame(info, fg_color="transparent")
        top.pack(fill="x")
        name_lbl = ctk.CTkLabel(top, font=FT_NAME, text_color=TXT,
                                fg_color="transparent")
        name_lbl.pack(side="left")
        state_lbl = ctk.CTkLabel(top, font=FT_SEC, text_color=SUB,
                                 fg_color="transparent")
        state_lbl.pack(side="right")
        sub = ctk.CTkFrame(info, fg_color="transparent")
        sub.pack(fill="x", pady=(3, 0))
        detail_lbl = ctk.CTkLabel(sub, font=FT_SUB, text_color=SUB,
                                  fg_color="transparent")
        detail_lbl.pack(side="left")
        delay_lbl = ctk.CTkLabel(sub, font=FT_PILL, text_color=SUB,
                                 fg_color="transparent")
        delay_lbl.pack(side="right")
        return {"vis": vis, "paint": _paint_rail, "t1": t1, "t2": t2,
                "name": name_lbl, "state": state_lbl,
                "detail": detail_lbl, "delay": delay_lbl}

    def paint_row(rec, i, s, n, is_last, at, now, eff, arrs, deps,
                  seg, seg_p, dwell, no_clock, train_delay):
        name = str(s.get("station") or s.get("stop") or s.get("stationName")
                   or s.get("name") or "?")
        arr = fmt_time(s.get("scheduledArrival") or s.get("arrival"))
        dep = fmt_time(s.get("scheduledDeparture") or s.get("departure") or s.get("time"))
        plat = str(s.get("platform") or s.get("actualPlatform") or "")
        _own = next((s[k] for k in ("delay", "arrivalDelay", "departureDelay")
                     if s.get(k) is not None), None)
        if _own is None:
            dl = train_delay
        else:
            try:
                dl = int(_own)
            except (TypeError, ValueError):
                dl = train_delay
        cancelled = bool(s.get("cancelled") or s.get("canceled") or s.get("isCancelled"))
        passed = at >= i and at != -1
        if no_clock:
            is_cur = (at == i and not cancelled and eff[at] is not None
                      and (now - eff[at]).total_seconds() <= 180)
            in_travel = (at == i and not cancelled and eff[at] is not None
                         and (now - eff[at]).total_seconds() > 180)
        else:
            is_cur = dwell and at == i and not cancelled
            in_travel = seg == i and not cancelled
        marker_p = seg_p if (seg == i and not is_last) else None
        if cancelled:
            st, st_fg = t("gui_cancelled"), ERR
        elif at == -1 and i == 0:
            st, st_fg = t("gui_not_left"), OK
        elif at == n - 1 and is_last:
            st, st_fg = t("gui_arrived"), OK
        elif is_cur:
            st, st_fg = t("gui_here"), OK
        elif in_travel:
            st, st_fg = t("gui_travel"), OK
        else:
            st, st_fg = "", SUB
        rec["vis"].update(at=at, passed=passed, is_cur=is_cur,
                           in_travel=in_travel, cancelled=cancelled,
                           mp=marker_p)
        if i == 0:
            rec["t1"].configure(text=dep)
        elif is_last:
            rec["t1"].configure(text=arr)
        else:
            rec["t1"].configure(text=arr)
            rec["t2"].configure(text=dep)
        rec["name"].configure(
            text=name,
            text_color=ERR if cancelled else (SUB if (passed and not is_cur and not in_travel) else TXT))
        rec["state"].configure(text=st, text_color=st_fg)
        bits = []
        if arr != dep and i != 0 and not is_last:
            bits.append(f"{arr} → {dep}")
        elif is_last:
            bits.append(t("gui_arr_full", t=arr))
        elif i == 0:
            bits.append(t("gui_dep_full", t=dep))
        if plat:
            bits.append(t("gui_bin", p=plat))
        rec["detail"].configure(text="  •  ".join(bits))
        rec["delay"].configure(text=f"{dl:+d} min" if (dl and not cancelled) else "",
                                text_color=delay_hex(dl))
        rec["paint"]()

    def draw(data, train_delay=0):
        sts = [s for s in (data.get("stops") or data.get("stopovers") or [])
               if isinstance(s, dict)]
        n = len(sts)
        if not sts:
            state["tl_key"] = None
            state["tl_rows"] = []
            for w in tl.winfo_children():
                w.destroy()
            ctk.CTkLabel(tl, text=t("gui_no_stops"), font=FT_SUB,
                         text_color=SUB, fg_color="transparent").pack(pady=12)
            return 0, 0, {"frac": 0.0, "seg": -1, "seg_p": 0.0, "dwell": False}
        at, now, eff = position(sts, train_delay)
        tl_count_var.set(t("gui_n_stops", n=n))
        arrs, deps = [], []
        for s in sts:
            a, dpt = stop_eff(s, train_delay)
            arrs.append(a)
            deps.append(dpt)
        seg, seg_p, dwell = -1, 0.0, False
        if 0 <= at < n - 1:
            a0, d0, a1 = arrs[at], deps[at], arrs[at + 1]
            if a0 is not None and d0 is not None and a0 <= now <= d0:
                dwell = True
            elif (d0 is not None and a1 is not None and a1 > d0
                    and d0 <= now < a1):
                total = (a1 - d0).total_seconds()
                seg = at
                seg_p = min(1.0, max(0.0, (now - d0).total_seconds() / total)) if total > 0 else 1.0
        if n <= 1:
            frac = 1.0 if at >= 0 else 0.0
        elif at == -1:
            frac = 0.0
        elif at >= n - 1:
            frac = 1.0
        elif dwell:
            frac = at / (n - 1)
        elif seg >= 0:
            frac = (seg + seg_p) / (n - 1)
        else:
            frac = at / (n - 1)
        pos = {"frac": frac, "seg": seg, "seg_p": seg_p, "dwell": dwell}
        no_clock = 0 <= at < n and (arrs[at] is None or deps[at] is None)
        # ricostruisci le righe solo se cambia la tratta, altrimenti aggiorna
        key = tuple(stop_key(s) for s in sts)
        if key != state.get("tl_key") or len(state.get("tl_rows") or []) != n:
            for w in tl.winfo_children():
                w.destroy()
            state["tl_rows"] = [build_row(i, i == n - 1) for i in range(n)]
            state["tl_key"] = key
        rows = state["tl_rows"]
        for i, s in enumerate(sts):
            paint_row(rows[i], i, s, n, i == n - 1, at, now, eff,
                      arrs, deps, seg, seg_p, dwell, no_clock, train_delay)
        return at, n, pos

    ctk.CTkFrame(content, fg_color=BG, height=24).pack()

    def refresh():
        try:
            data = train_trip_data(trip_id, country, base=trip_base)
        except Exception:
            return
        state["trip"] = data
        try:
            _td = data.get("delay", data.get("delayMinutes"))
            trip_delay = None if _td is None else int(_td)
        except (TypeError, ValueError):
            trip_delay = None
        _stops = [s for s in (data.get("stops") or data.get("stopovers") or [])
                  if isinstance(s, dict)]
        _dest = stop_name(data.get("destination"))
        fb_delay, fb_station = refresh_delay_from_upcoming_stations(
            _stops, trip_id=trip_id, train_number=num, destination=_dest,
            country=country, current_delay=trip_delay,
            board_base=board_base)
        if fb_delay is not None:
            d = fb_delay
            state["delay_src"] = f"bacheca {fb_station}" if fb_station else "bacheca"
        elif trip_delay is not None:
            d = trip_delay
            state["delay_src"] = "trip"
        else:
            d = 0
            state["delay_src"] = ""
        at, n, pos = draw(data, d)
        frac = max(0.0, min(1.0, pos.get("frac", 0.0)))
        seg, seg_p = pos.get("seg", -1), pos.get("seg_p", 0.0)
        title_var.set(train_label(data.get('line') or data.get('category') or line,
                                  data.get('tripNumber') or data.get('trainNumber') or num))
        route_var.set(f"{stop_name(data.get('origin'))}  →  {stop_name(data.get('destination'))}")
        delay_var.set(t("gui_on_time") if d == 0
                      else (t("gui_delay", d=d) if d > 0 else t("gui_early", d=d)))
        delay_lbl.configure(text_color="#15803D" if d <= 0 else ("#B45309" if d <= 5 else "#DC2626"))
        _plat = str(data.get("platform") or "").strip()
        plat_var.set(f"BIN {_plat}" if _plat else "")
        try:
            if _plat and not plat_shown["on"]:
                plat_pill.pack(side="left", padx=(8, 0))
                plat_shown["on"] = True
            elif not _plat and plat_shown["on"]:
                plat_pill.pack_forget()
                plat_shown["on"] = False
        except Exception:
            pass
        sts_all = [s for s in (data.get("stops") or data.get("stopovers") or [])
                   if isinstance(s, dict)]
        done = (at + 1) if at >= 0 else 0
        _src = state.get("delay_src", "")
        _suffix = f"  ·  {t('gui_delay_from', src=_src.upper())}" if _src.startswith("bacheca") else ""
        prog_lbl_var.set(t("gui_route_done", done=done, n=n) + _suffix)
        pct_var.set(f"{int(frac * 100)}%")
        try:
            bar.set(max(0.0, min(1.0, frac)))
        except Exception:
            pass
        if n and at == -1:
            t0 = fmt_time(sts_all[0].get("scheduledDeparture") or sts_all[0].get("departure")
                          or sts_all[0].get("time")) if sts_all else "—"
            state_var.set(t("gui_stop_wait", t=t0))
        elif n and at == n - 1:
            state_var.set(t("gui_stop_done"))
        elif n and 0 <= at < n:
            cur = sts_all[at]
            cn = str(cur.get("station") or cur.get("stop") or cur.get("stationName")
                     or cur.get("name") or "?")
            if 0 <= seg < n - 1:
                nx = sts_all[seg + 1]
                nn = str(nx.get("station") or nx.get("stop") or nx.get("stationName")
                         or nx.get("name") or "?")
                state_var.set(t("gui_stop_travel", a=cn, b=nn, p=int(seg_p * 100)))
            elif pos.get("dwell"):
                state_var.set(t("gui_stop_dwell", s=cn))
            else:
                state_var.set(t("gui_stop_last", s=cn))
        else:
            state_var.set("")
        if n and 0 <= at + 1 < n:
            nx = sts_all[at + 1]
            nm = str(nx.get("station") or nx.get("stop") or nx.get("stationName")
                     or nx.get("name") or "?")
            nt = fmt_time(nx.get("scheduledArrival") or nx.get("arrival")
                          or nx.get("scheduledDeparture") or nx.get("departure"))
            pl = str(nx.get("platform") or "")
            next_var.set(nm)
            bits = []
            if nt and nt != "—":
                bits.append(t("gui_at", t=nt))
            if pl:
                bits.append(t("gui_plat", p=pl))
            next_sub_var.set("  •  ".join(bits))
        elif n and at == n - 1:
            next_var.set(t("gui_dest_done"))
            next_sub_var.set("")
        else:
            next_var.set("—")
            next_sub_var.set("")
        upLbl_var.set(t("gui_updated", t=datetime.now().strftime('%H:%M:%S')))
        _sync_pad()
        root.after_idle(_fix_scroll)

    timers = {"tick": None, "auto": None}

    def cancel_timers():
        # i callback pendenti non devono sopravvivere alla chiusura,
        # altrimenti scattano nella finestra successiva
        for k in ("tick", "auto"):
            try:
                if timers[k]:
                    root.after_cancel(timers[k])
            except Exception:
                pass
            timers[k] = None

    def tick_viewers():
        try:
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
                    viewers_var.set(t("gui_online", v=v) if isinstance(v, int) and v > 0 else "")
            except Exception:
                pass
            if alive["on"]:
                timers["tick"] = root.after(15000, tick_viewers)
        except Exception:
            pass

    def auto():
        try:
            if not alive["on"]:
                return
            try:
                if root.winfo_exists() and alive["live"]:
                    refresh()
            except Exception:
                pass
            if alive["on"]:
                timers["auto"] = root.after(30000, auto)
        except Exception:
            pass

    root.minsize(460, 680)

    refresh()
    root.after_idle(_sync_pad)
    tick_viewers()
    try:
        timers["auto"] = root.after(30000, auto)
    except Exception:
        pass
    p_ok("Finestra timeline aperta (CustomTkinter).")
    root.mainloop()

def train_trip(trip_id, country):
    p_title(t("trip_title", t=trip_id, c=country))
    url = f"{TRAINBOARD}/{country}/trip?tripId={urllib.parse.quote(trip_id)}"
    p_dim(f"GET {url}")
    try:
        data = get_json(url)
    except Exception as e:
        return p_err(f"Errore trip: {e}")
    e = (data.get("data") if isinstance(data, dict) else None) or data or {}
    print(f"  {bold(t('trip_line'))} {e.get('line') or e.get('category') or '—'}")
    print(f"  {bold(t('det_dest'))} {stop_name(e.get('destination')) or '—'}")
    print_timeline(e.get("stops") or e.get("stopovers") or [])

def train_number(q):
    p_title(t("live_title", q=q))
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
    p_title(t("fal_title", s=station_id))
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
        return p_warn(t("bus_no_stops"))
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
    p_title(t("reg_providers", c=country))
    try:
        data = get_json(f"{BASE}/api/train/regional_providers/{urllib.parse.quote(country)}")
    except Exception as e:
        return p_err(f"Errore: {e}")
    provs = (data.get("providers") if isinstance(data, dict) else None) or as_list(data)
    for p in provs:
        if isinstance(p, dict):
            print(f"  {ok(str(p.get('name') or p.get('key') or '?')).ljust(20)}  "
                  f"{dim(str(p.get('api_prefix') or p.get('apiPrefix') or ''))}")
    p_dim(f"Totale: {len(provs)} — usa il nome (es. trenord) con --stazioni/--partenze")
    return provs

def reg_base(country, prefix):
    # Accetta nome provider (trenord) o prefisso completo (it/trains/trenord):
    # GET /api/{country}/trains/{provider}/... (come regional_provider_screen)
    p = (prefix or "").strip().strip("/")
    parts = [x for x in p.split("/") if x]
    if len(parts) >= 3 and parts[-2] == "trains":
        return f"{BASE}/api/{'/'.join(parts)}"
    provider = parts[-1] if parts else ""
    return f"{BASE}/api/{str(country or 'it').lower()}/trains/{provider}"

def fetch_reg_stations(country, prefix, q=""):
    base = reg_base(country, prefix)
    url = f"{base}/stations?limit=100" if not q else f"{base}/stations?query={urllib.parse.quote(q)}&limit=50"
    return url, base, as_list(get_json(url))

def fetch_reg_board(country, prefix, station_id, arrivi):
    base = reg_base(country, prefix)
    ep = "arrivals" if arrivi else "departures"
    url = f"{base}/{ep}?stationId={urllib.parse.quote(station_id)}"
    rows = []
    for raw in as_list(get_json(url)):
        e = _unwrap_board(raw if isinstance(raw, dict) else {})
        if e:
            rows.append(e)
    return url, base, rows

def reg_stations(country, prefix, q=""):
    p_title(t("reg_stations", p=prefix, q=q))
    try:
        url, _, lst = fetch_reg_stations(country, prefix, q)
    except Exception as e:
        return p_err(f"Errore: {e}")
    p_dim(f"GET {url}")
    for s in lst[:20]:
        if isinstance(s, dict):
            print(f"  {ok(str(s.get('name') or s.get('stationName') or '?'))}  "
                  f"{dim('id=' + str(s.get('id') or s.get('stationId') or '?'))}")
    return lst

def reg_board(country, prefix, station_id, arrivi):
    ep = "arrivals" if arrivi else "departures"
    p_title(t("reg_board_arr" if arrivi else "reg_board_dep", sid=station_id))
    try:
        url, _, lst = fetch_reg_board(country, prefix, station_id, arrivi)
    except Exception as e:
        return p_err(f"Errore: {e}")
    p_dim(f"GET {url}")
    return print_board_table(lst, arrivi) or []

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
    p_title(t("reg_trip", t=trip_id))
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
        p_ok(t("login_ok", u=user.get('email') or user.get('nickname')))
    else:
        p_warn(t("login_ko"))

def auth_register(email, password, nick):
    try:
        res = post_json(f"{BASE}/api/auth/register",
                        {"email": email.strip(), "password": password, "nickname": nick})
    except Exception as e:
        return p_err(f"Register: {e}")
    user = (res.get("user") or {}) if isinstance(res, dict) else {}
    if user:
        save_json_file(SESS_FILE, {"user": user, "token": res.get("token")})
        p_ok(t("reg_ok", e=user.get('email')))
    else:
        p_warn(f"Risposta: {res}")

def auth_available(nick, except_id=""):
    q = f"?nickname={urllib.parse.quote(nick)}" + (f"&exceptId={except_id}" if except_id else "")
    try:
        data = get_json(f"{BASE}/api/users/nickname-available{q}", timeout=8)
        p_ok(t("nick_ok")) if (data.get("available") if isinstance(data, dict) else False) \
            else p_warn(t("nick_ko"))
    except Exception as e:
        p_err(f"Errore: {e}")

def auth_profile(nick):
    s = session()
    if not s.get("token"):
        return p_warn(t("need_login"))
    try:
        res = api_patch(f"{BASE}/api/auth/profile", {"nickname": nick}, token=s["token"])
        s["user"] = res.get("user", s.get("user"))
        save_json_file(SESS_FILE, s)
        p_ok(t("prof_ok", n=nick))
    except Exception as e:
        p_err(f"Profilo: {e}")

def auth_delete(password):
    s = session()
    if not s.get("token"):
        return p_warn(t("need_login"))
    try:
        status, _ = api_delete(f"{BASE}/api/auth/account", {"password": password}, token=s["token"])
        if status == 200:
            save_json_file(SESS_FILE, {})
            p_ok(t("del_ok"))
        else:
            p_warn(t("del_ko"))
    except Exception as e:
        p_err(f"Delete: {e}")

def auth_status():
    s = session()
    u = s.get("user") or {}
    if u:
        p_ok(t("logged_as", e=u.get('email') or u.get('nickname'), n=u.get('nickname')))
    else:
        p_info(t("no_session"))

def auth_logout():
    save_json_file(SESS_FILE, {})
    p_ok(t("logout_ok"))

# -- PREFERITI (stessi id/modelli dell'app + sync database via API) ------------
# Riconoscimento identico all'app (favorites_provider.dart):
#   stop:    {userId}_{stopType}_{code}[_{country}][_{provider}]
#            stopType = busStop | trainStation | airport
#   train:   {userId}_train_{trainNumber}_{departureStation}_{arrivalStation}
#   busLine: {userId}_bus_{provider}_{lineCode}
# Sul database (server.js /api/favorites, auth Bearer): GET lista,
# POST {id,type,data} salvo con il nostro id, DELETE {id}.
FAV_API = f"{BASE}/api/favorites"
STOP_TYPES = ("busStop", "trainStation", "airport")

def _fav_auth():
    s = session()
    tok = s.get("token")
    if not tok:
        return None, "guest"
    uid = (s.get("user") or {}).get("id", "guest")
    return tok, str(uid)

def _fav_get(url, token, timeout=12):
    req = urllib.request.Request(url, headers={
        **HEADERS, "Authorization": f"Bearer {token}"})
    with urllib.request.urlopen(req, timeout=timeout) as res:
        return json.loads(res.read().decode("utf-8") or "{}")

def fav_id_stop(uid, stop_type, code, country=None, provider=None):
    st = stop_type if stop_type in STOP_TYPES else "busStop"
    key = f"{uid}_{st}_{code}"
    if country:
        key += f"_{country}"
    if (provider or "").strip():
        key += f"_{provider.strip()}"
    return key

def fav_id_train(uid, number, dep, arr):
    return f"{uid}_train_{number}_{dep}_{arr}"

def fav_id_bus(uid, provider, line):
    return f"{uid}_bus_{provider}_{line}"

def fav_build(ftype, data, uid):
    """(id, type, payload) negli stessi campi dei modelli Favorite*.dart."""
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc).isoformat()
    if ftype == "train":
        num, dep, arr = (str(data.get("number") or "?"), str(data.get("origin") or "?"),
                         str(data.get("destination") or "?"))
        return (fav_id_train(uid, num, dep, arr), "train",
                {"trainNumber": num, "departureStation": dep, "arrivalStation": arr,
                 "departureTime": str(data.get("departureTime") or ""),
                 "arrivalTime": str(data.get("arrivalTime") or ""),
                 "operator": data.get("operator"), "category": data.get("category"),
                 "routeId": data.get("routeId"), "provider": data.get("provider")}, now)
    if ftype == "busLine":
        prov, line = str(data.get("provider") or "bari"), str(data.get("line") or "?")
        return (fav_id_bus(uid, prov, line), "busLine",
                {"lineCode": line, "lineName": str(data.get("name") or line),
                 "provider": prov, "routeId": data.get("routeId"),
                 "agencyId": data.get("agencyId"), "color": data.get("color"),
                 "textColor": data.get("textColor"),
                 "description": data.get("description"), "url": data.get("url"),
                 "stops": data.get("stops")}, now)
    st = data.get("stopType") if data.get("stopType") in STOP_TYPES else "busStop"
    code = str(data.get("code") or "?")
    return (fav_id_stop(uid, st, code, data.get("country"), data.get("provider")), "stop",
            {"name": str(data.get("name") or code), "code": code, "stopType": st,
             "latitude": data.get("latitude"), "longitude": data.get("longitude"),
             "city": data.get("city"), "region": data.get("region"),
             "provider": data.get("provider"), "country": data.get("country")}, now)

def fav_remote_list():
    """Preferiti dal database (richiede login). Ritorna lista flat come l'app."""
    tok, _ = _fav_auth()
    if not tok:
        return None
    try:
        res = _fav_get(FAV_API, tok)
    except Exception as e:
        p_err(f"{t('fav_cloud')}: {e}")
        return None
    out = []
    for item in (res.get("favorites") or []):
        if not isinstance(item, dict):
            continue
        data = item.get("data") if isinstance(item.get("data"), dict) else {}
        out.append({"id": item.get("id"), "userId": item.get("userId"),
                    "type": item.get("type"), "addedAt": item.get("addedAt"),
                    "data": {**data}})
    return out

def _fav_norm(f):
    """Normalizza voci vecchie (chiavi number/origin/line/...) al formato app."""
    d = dict(f.get("data") or {})
    t = f.get("type")
    if t == "train":
        d.setdefault("trainNumber", d.get("number", "?"))
        d.setdefault("departureStation", d.get("origin", "?"))
        d.setdefault("arrivalStation", d.get("destination", "?"))
    elif t == "busLine":
        d.setdefault("lineCode", d.get("line", "?"))
        d.setdefault("lineName", d.get("name") or d.get("line", "?"))
        d.setdefault("provider", d.get("provider") or "bari")
    elif t == "stop":
        d.setdefault("code", d.get("code", "?"))
        d.setdefault("name", d.get("name") or d.get("code", "?"))
        d.setdefault("stopType", d.get("stopType") or "busStop")
    return t, d

def _fav_describe(f):
    t, d = _fav_norm(f)
    if t == "train":
        return (f"{d.get('trainNumber', '?')}: {d.get('departureStation', '?')} "
                f"→ {d.get('arrivalStation', '?')}")
    if t == "busLine":
        return f"{d.get('lineCode', '?')} - {d.get('lineName', '')} ({d.get('provider', '')})"
    return f"{d.get('name', '?')} ({d.get('code', '?')})"

def fav_open(fav):
    """Apre un preferito con la vista giusta in base al tipo (come l'app)."""
    ft, d = _fav_norm(fav)
    if ft == "train":
        num = str(d.get("trainNumber") or "")
        trip_id = str(d.get("routeId") or "")
        country = str(d.get("provider") or "IT").upper() or "IT"
        if trip_id:
            return open_timeline_gui(trip_id, country)
        # senza tripId: risolvi dalla mappa live per numero
        digits = "".join(c for c in num if c.isdigit())
        try:
            data = get_json("https://data.cuzimmartin.dev/train-map?north=85&south=-5&east=91"
                            "&west=-64&duration=300&results=1000&polylines=false")
        except Exception as e:
            return p_err(f"Mappa live: {e}")
        best = None
        for m in (data.get("movements", []) if isinstance(data, dict) else []):
            if not isinstance(m, dict):
                continue
            line = m.get("line") if isinstance(m.get("line"), dict) else {}
            nm = f"{line.get('name', '')} {line.get('id', '')}"
            if digits and digits in "".join(c for c in nm if c.isdigit()):
                if m.get("tripId"):
                    best = m
                    break
        if best:
            c = pick_country()
            return open_timeline_gui(str(best["tripId"]), c)
        sid = ask(t("fav_train_fallback"))
        if sid:
            c = pick_country()
            return train_details(num, sid, c)
        return p_warn(t("fav_no_trip"))
    if ft == "stop":
        st, code = d.get("stopType"), str(d.get("code") or "")
        if st == "trainStation":
            c = (d.get("country") or "IT").upper()
            m = ask(t("dep_arr")).strip() or "1"
            return train_board(code, c, m == "2")
        if st == "airport":
            m = ask(t("dep_arr")).strip() or "1"
            return airport(code.upper(), m == "2")
        prov = str(d.get("provider") or "").strip() or ask(t("fav_bus_prov")).strip()
        if not prov:
            return p_warn(t("fav_need_prov"))
        return bus_departures(prov, code, "")
    if ft == "busLine":
        prov, line = str(d.get("provider") or "bari"), str(d.get("lineCode") or "")
        p_title(f"🚌 Linea {line} · {prov}")
        try:
            country = resolve_country(prov)
            found = None
            for page in (1, 2):
                url = f"{BASE}/api/{country}/bus/{prov}/lines?page={page}&chunkSize=100"
                data = get_json(url)
                if not isinstance(data, dict):
                    break
                for ln in (data.get("lines") or []):
                    if not isinstance(ln, dict):
                        continue
                    if str(ln.get("code") or ln.get("line") or ln.get("id") or "") == line:
                        found = ln
                        break
                if found:
                    break
                pag = data.get("pagination") if isinstance(data.get("pagination"), dict) else None
                if not pag or page >= int(pag.get("totalPages", 1)):
                    break
        except Exception as e:
            return p_err(f"Linee: {e}")
        if found:
            print(f"  {c_bus(line)} {found.get('name') or found.get('description') or ''}")
        else:
            p_warn(t("fav_no_line"))
        return bus_vehicles(prov, "")
    return p_warn(t("fav_unknown", t=ft))

def account_section():
    p_title(t("acc_title"))
    while True:
        s = session()
        u = s.get("user") or {}
        if u:
            p_ok(t("acc_in", e=u.get('email') or u.get('nickname'),
                   n=u.get('nickname'), i=u.get('id')))
        else:
            p_info(t("acc_out"))
        print(f"  {t('acc_menu')}")
        c = (ask(t("acc_choice")) or "0").strip()
        if c == "0":
            return
        elif c == "1":
            auth_status()
        elif c == "2":
            e, p = ask(t("ask_email")), ask_password(t("ask_pw"))
            if e and p:
                auth_login(e, p)
        elif c == "3":
            e, p, n = ask(t("ask_email")), ask_password(t("ask_pw")), ask(t("ask_nick"))
            if e and p and n:
                auth_register(e, p, n)
        elif c == "4":
            n = ask(t("ask_new_nick"))
            if n:
                auth_profile(n)
        elif c == "5":
            n = ask(t("ask_check_nick"))
            if n:
                auth_available(n)
        elif c == "6":
            auth_logout()
        elif c == "7":
            p = ask_password(t("ask_del_pw"))
            if p:
                auth_delete(p)
        else:
            p_warn(t("invalid_num"))

def config_section():
    p_title(t("cfg_title"))
    while True:
        pinned = str(app_state().get("lang") or "").lower()
        if pinned in LANGS:
            p_info(t("cfg_cur", lang=LANG_NAMES.get(pinned, pinned)))
        else:
            eff = system_lang()
            p_info(t("cfg_auto_is", lang=LANG_NAMES.get(eff, eff)))
        print(f"  {ok('[1]')} {t('cfg_change')}  {dim('[0] ' + t('t_back'))}")
        c = (ask(t("cfg_choice")) or "0").strip()
        if c == "0":
            return
        elif c == "1":
            pick_language()
        else:
            p_warn(t("invalid_num"))

def favorites_section():
    p_title(t("fav_title"))
    while True:
        tok, _ = _fav_auth()
        favs = fav_remote_list() if tok else fav_all()
        if favs is None:
            return
        p_dim(t("fav_db") if tok else t("fav_local"))
        if not favs:
            p_info(t("fav_empty"))
            return
        for i, f in enumerate(favs, 1):
            ft, _ = _fav_norm(f)
            print(f"  {ok(f'[{i}]')} {_fav_describe(f)}  {dim(str(ft))}")
        print(f"  {dim('[0] ' + t('t_back'))}")
        s = (ask(t("fav_num", n=len(favs))) or "0").strip()
        if s == "0":
            return
        try:
            fav = favs[int(s) - 1] if 1 <= int(s) <= len(favs) else None
        except ValueError:
            fav = None
        if not isinstance(fav, dict):
            p_warn(t("invalid_num"))
            continue
        fav_open(fav)

def fav_list(cloud=False):
    tok, _ = _fav_auth()
    if cloud or tok:
        if not tok:
            return p_warn(t("need_login") + " (auth --login <email> <pw>).")
        p_title(t("fav_title"))
        favs = fav_remote_list()
        if favs is None:
            return
    else:
        p_title(t("fav_title"))
        favs = fav_all()
        if tok is None:
            p_dim(t("fav_local"))
    if not favs:
        return p_info(t("fav_empty"))
    for f in favs:
        print(f"  [{warn(str(f.get('id', '?')))}] {ok(str(f.get('type', '')))}  "
              f"{short(_fav_describe(f), 60)}")
    p_dim(t("fav_total", n=len(favs)))

def fav_add(ftype, data):
    tok, uid = _fav_auth()
    key, ftype_name, payload, now = fav_build(ftype, data, uid)
    if tok:
        # salvabile nel database con il nostro id (riconoscimento uguale all'app)
        try:
            res = post_json(FAV_API, {"id": key, "type": ftype_name, "data": payload},
                            token=tok)
        except Exception as e:
            return p_err(f"{t('fav_cloud_save')}: {e}")
        fav = (res.get("favorite") if isinstance(res, dict) else None) or {}
        rid = fav.get("id") or key
        favs = [f for f in fav_all() if f.get("id") != rid]
        favs.append({"id": rid, "userId": uid, "type": ftype_name,
                     "addedAt": fav.get("addedAt") or now, "data": payload})
        save_json_file(FAV_FILE, favs)
        return p_ok(t("fav_saved_db", rid=rid))
    favs = fav_all()
    if any(f.get("id") == key for f in favs):
        return p_warn(t("fav_dup"))
    favs.append({"id": key, "userId": uid, "type": ftype_name,
                 "addedAt": now, "data": payload})
    save_json_file(FAV_FILE, favs)
    p_ok(t("fav_added_local", key=key))

def fav_remove(fid):
    tok, _ = _fav_auth()
    if tok:
        try:
            status, _ = api_delete(f"{FAV_API}/{urllib.parse.quote(fid)}", token=tok)
        except Exception as e:
            return p_err(f"{t('fav_cloud_del')}: {e}")
        if status != 200:
            return p_warn("Non rimosso dal database.")
    favs = [f for f in fav_all() if f.get("id") != fid]
    save_json_file(FAV_FILE, favs)
    p_ok(t("fav_removed", fid=fid))

def fav_check(fid):
    tok, _ = _fav_auth()
    if tok:
        favs = fav_remote_list()
        if favs is None:
            return
        found = any(f.get("id") == fid for f in favs)
    else:
        found = any(f.get("id") == fid for f in fav_all())
    p_ok(t("fav_is")) if found else p_warn(t("fav_is_not"))

def fav_sync():
    """Scarica i preferiti dal database e li salva nel file locale."""
    tok, _ = _fav_auth()
    if not tok:
        return p_warn(t("need_login") + " (auth --login <email> <pw>).")
    favs = fav_remote_list()
    if favs is None:
        return
    save_json_file(FAV_FILE, favs)
    p_ok(t("fav_synced", n=len(favs)))
    p_dim(t("fav_mirror", f=FAV_FILE))

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

# -- STATO LOCALE (comfort: ricorda paese, recenti, ultimo tabellone) --------
STATE_FILE = os.path.join(HOME, ".bc_cli_state.json")

def app_state():
    return load_json_file(STATE_FILE, {})

def save_state(patch):
    st = app_state()
    if isinstance(patch, dict):
        st.update(patch)
    save_json_file(STATE_FILE, st)
    return st

def remember_country(c):
    if c:
        save_state({"country": str(c).upper()})

def last_country():
    return str(app_state().get("country") or "IT").upper()

def push_recent(kind, entry, limit=8):
    st = app_state()
    lst = [e for e in (st.get(kind) or []) if isinstance(e, dict)]
    key = entry.get("sid") or entry.get("stop_id") or entry.get("name")
    lst = [e for e in lst
           if (e.get("sid") or e.get("stop_id") or e.get("name")) != key]
    lst.insert(0, entry)
    st[kind] = lst[:limit]
    save_json_file(STATE_FILE, st)

def get_recent(kind):
    return [e for e in (app_state().get(kind) or []) if isinstance(e, dict)]

def save_window_geom(root):
    # Salva posizione/dimensione/zoom finestra treni (ripristinati all'apertura)
    try:
        import re
        zoomed = root.state() == "zoomed"
        m = re.match(r"(\d+)x(\d+)\+(-?\d+)\+(-?\d+)", root.geometry() or "")
        if not m:
            save_state({"train_win": {"zoomed": zoomed}})
            return
        w, h, x, y = map(int, m.groups())
        sw, sh = root.winfo_screenwidth(), root.winfo_screenheight()
        x = max(0, min(x, max(0, sw - 200)))
        y = max(0, min(y, max(0, sh - 200)))
        save_state({"train_win": {"w": w, "h": h, "x": x, "y": y,
                                  "zoomed": zoomed}})
    except Exception:
        pass

def restore_window_geom(root, default):
    try:
        d = app_state().get("train_win") or {}
        if d.get("zoomed"):
            root.geometry(default)
            root.after_idle(lambda: root.state("zoomed"))
            return
        w, h, x, y = int(d["w"]), int(d["h"]), int(d["x"]), int(d["y"])
        sw, sh = root.winfo_screenwidth(), root.winfo_screenheight()
        w = max(400, min(w, sw))
        h = max(500, min(h, sh))
        x = max(0, min(x, max(0, sw - 200)))
        y = max(0, min(y, max(0, sh - 200)))
        root.geometry(f"{w}x{h}+{x}+{y}")
    except Exception:
        root.geometry(default)

# -- I18N (stesse 4 lingue dell'app: it/en/de/fr) ---------------------------
LANGS = ("it", "en", "de", "fr")
LANG_NAMES = {"it": "Italiano", "en": "English", "de": "Deutsch", "fr": "Français"}

def system_lang():
    try:
        import locale
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            loc = (locale.getdefaultlocale()[0] or "it").lower()
        for code in LANGS:
            if loc.startswith(code):
                return code
    except Exception:
        pass
    return "it"

def get_lang():
    lang = str(app_state().get("lang") or "").lower()
    if lang in LANGS:
        return lang
    return system_lang()

def set_lang(code):
    code = str(code or "").lower()
    if code == "auto":
        st = app_state()
        st.pop("lang", None)
        save_json_file(STATE_FILE, st)
        return True
    if code in LANGS:
        save_state({"lang": code})
        return True
    return False

def t(key, **params):
    """Testo localizzato con fallback it → chiave. Vedi STRINGS."""
    lang = get_lang()
    s = STRINGS.get(lang, {}).get(key)
    if s is None:
        s = STRINGS.get("it", {}).get(key, key)
    try:
        return s.format(**params) if params else s
    except Exception:
        return s

def pick_language():
    print(f"\n  {t('lang_title')}")
    pinned = str(app_state().get("lang") or "").lower()
    opts = list(LANGS) + ["auto"]
    for i, code in enumerate(opts, 1):
        name = LANG_NAMES.get(code, code) if code != "auto" else t("lang_auto")
        if code == "auto":
            name += f" ({LANG_NAMES.get(system_lang(), system_lang())})"
        mark = " ←" if (code == pinned or (code == "auto" and not pinned)) else ""
        print(f"  [{i}] {name}{mark}")
    s = (ask(t("lang_prompt")) or "").strip().lower()
    if not s:
        return get_lang()
    try:
        code = opts[int(s) - 1] if s.isdigit() else s
    except (ValueError, IndexError):
        code = s
    if set_lang(code):
        eff = get_lang()
        p_ok(f"{LANG_NAMES.get(eff, eff)} ✓" if code != "auto"
              else f"{t('lang_auto')} ({LANG_NAMES.get(eff, eff)}) ✓")
        return eff
    p_warn(t("lang_invalid"))
    return get_lang()

STRINGS = {
"it": {
"tagline": "Bus · Treni · Aerei nel terminale — stessi endpoint dell’app Flutter",
"menu_title": "MENU PRINCIPALE",
"m_simple": "Modalità semplice  (nazione → stazione → tabellone)",
"m_commands": "Modalità comandi   (scrivi il comando diretto)",
"m_advanced": "Menu avanzato      (tutte le funzioni)",
"m_guide": "Guida comandi      (tutti i comandi)",
"m_fav": "Preferiti           (apre per tipo: treno/stazione/bus/voli)",
"m_account": "Account             (login, profilo, logout)",
"m_exit": "Esci",
"m_choice": "Scelta [0-7, help]: ",
"m_ctx_country": "Paese {c}",
"m_ctx_last": "ultimo: {name} [{sid}]",
"m_ctx_hint": "— scrivi una stazione per cercarla subito",
"m_invalid": "Scelta non valida: premi 1-7 oppure scrivi un comando.",
"m_bye": "Ciao! 👋",
"m_last_none": "Nessun tabellone recente.",
"transport_title": "Tipo di trasporto:",
"tr_treni": "🚂 Treni", "tr_bus": "🚌 Bus", "tr_voli": "✈️  Voli", "tr_flix": "🟢 Flixbus",
"t_back": "Indietro",
"num_transport": "Numero trasporto [{d}]: ",
"simple_title": "🟢 Modalità semplice (0 = menu)",
"train_part": "Tasto 1) Nazionale  2) Regionale  [1]: ",
"countries_title": "Paesi (numero → codice):",
"country_prompt": "Paese [{last}] (? = lista): ",
"country_list_prompt": "Numero paese [invio = {last}]: ",
"stitle": "🚂 Stazioni · \"{q}\" [{c}]",
"num_station": "Numero stazione [1-{n}, 0 = annulla]: ",
"cancelled": "Annullato.",
"invalid_num": "Numero non valido.",
"dep_arr": "Tasto 1) Partenze  2) Arrivi  [1]: ",
"board_menu": "Tasto R) Aggiorna [invio]  1) Altra stazione  2) {opt2}  3) Passa a {other}  4) Timeline treno  5) Grafica  0) Menu  [R]: ",
"opt_country": "Cambia nazione", "opt_provider": "Cambia provider",
"to_arr": "Arrivi", "to_dep": "Partenze",
"row_pick": "Numero riga del treno [1-{n}]: ",
"no_rows": "Nessuna riga: mostra prima il tabellone.",
"no_trip_row": "Trip non disponibile per questa riga.",
"recents": "Recenti:",
"train_search_prompt": "Nome stazione, R-numero (0 = menu): ",
"recent_invalid": "Recente non valido.",
"board_title_dep": "🚂 Partenze · {sid} [{c}]",
"board_title_arr": "🚂 Arrivi · {sid} [{c}]",
"col_n": "N", "col_time": "ORA", "col_train": "TRENO", "col_dest": "DESTINAZIONE",
"col_from": "PROVENIENZA", "col_plat": "BIN", "col_state": "STATO",
"board_total": "Totale: {n} (mostrati max 30) · tasto 4 = timeline del treno",
"board_empty": "Nessun treno trovato.",
"in_time": "in orario",
"tl_title": "Timeline ({n} fermate):",
"tl_none": "Nessuna fermata nella timeline.",
"tl_not_left": "🚂 non partito", "tl_here": "🚂 qui", "tl_travel": "🚂 ↓ in viaggio",
"tl_arrived": "🚂 arrivato",
"reg_title": "🏳️ Regionali (0 = menu)",
"reg_providers": "🏳️ Provider regionali · {c}",
"reg_none": "Nessun provider regionale.",
"reg_num": "Numero provider [1-{n}, 0 = annulla]: ",
"reg_with": "Provider: {p}",
"reg_station_prompt": "Nome stazione, R-numero (0 = menu): ",
"reg_board_dep": "🏳️ Partenze regionali · {sid}",
"reg_board_arr": "🏳️ Arrivi regionali · {sid}",
"fav_title": "⭐ Preferiti",
"fav_db": "Dal database (login attivo).",
"fav_local": "File locale (fai login per il database).",
"fav_empty": "Nessun preferito.",
"fav_num": "Numero [0-{n}]: ",
"acc_title": "👤 Account",
"acc_in": "Loggato come {e} (nick: {n}, id: {i})",
"acc_out": "Non loggato (i preferiti restano locali).",
"acc_menu": "[1] Stato  [2] Login  [3] Registra  [4] Cambia nick  [5] Verifica nick  [6] Logout  [7] Elimina account  [0] Indietro",
"acc_choice": "Scelta [0-7]: ",
"ask_email": "Email: ", "ask_pw": "Password: ", "ask_nick": "Nickname: ",
"ask_new_nick": "Nuovo nickname: ", "ask_check_nick": "Nickname da verificare: ",
"ask_del_pw": "Password per confermare l'eliminazione (invio = annulla): ",
"login_ok": "Login ok: {u}", "login_ko": "Credenziali non valide.",
"reg_ok": "Registrato: {e}",
"nick_ok": "Nickname disponibile.", "nick_ko": "Nickname occupato.",
"prof_ok": "Profilo aggiornato: {n}",
"del_ok": "Account eliminato, sessione pulita.", "del_ko": "Eliminazione fallita.",
"need_login": "Devi fare login prima.",
"logout_ok": "Logout, sessione pulita.",
"logged_as": "Loggato come {e} (nickname: {n})",
"no_session": "Nessuna sessione. Usa: auth --login <email> <pw>",
"lang_title": "Lingua / Language / Sprache / Langue:",
"lang_prompt": "Numero o codice [invio = attuale]: ",
"lang_invalid": "Lingua non valida.",
"gui_train": "TRENO · {c}",
"gui_on_time": "IN ORARIO", "gui_delay": "RITARDO +{d} MIN", "gui_early": "ANTICIPO {d} MIN",
"gui_online": "● {v} online",
"gui_live_on": "LIVE ON", "gui_live_off": "LIVE OFF",
"gui_update": "Aggiorna", "gui_close": "Chiudi",
"gui_updated": "Aggiornato {t}",
"gui_route_done": "PERCORSO · {done} DI {n} FERMATE",
"gui_delay_from": "RITARDO DA {src}",
"gui_next": "PROSSIMA FERMATA",
"gui_at": "ore {t}", "gui_plat": "binario {p}",
"gui_dest_done": "Destinazione raggiunta",
"gui_wait": "In attesa di partenza...",
"gui_actions": "AZIONI RAPIDE",
"gui_btns": ["Statistiche", "Mappa", "Condividi", "Social", "Salva", "Avvisi", "Preferito", "Match"],
"gui_match_ok": "✓ match: {d}", "gui_match_ko": "nessun match",
"gui_stops": "FERMATE", "gui_n_stops": "{n} fermate", "gui_no_stops": "Nessuna fermata.",
"gui_not_left": "NON PARTITO", "gui_here": "QUI", "gui_travel": "IN VIAGGIO",
"gui_arrived": "ARRIVATO", "gui_cancelled": "SOPPRESSA",
"gui_dep": "partenza", "gui_arr": "arrivo", "gui_bin": "bin {p}",
"gui_dep_full": "partenza {t}", "gui_arr_full": "arrivo {t}",
"gui_stop_wait": "Treno fermo in stazione · partenza {t}",
"gui_stop_done": "Corsa terminata · treno arrivato a destinazione",
"gui_stop_travel": "In viaggio · {a} → {b} · {p}%",
"gui_stop_dwell": "Fermo in stazione · {s}",
"gui_stop_last": "In viaggio · ultima fermata {s}",
"gui_stats_title": "STATISTICHE TRENO",
"bus_prov_title": "Provider bus (invio = ultimo): ",
"bus_stop_prompt": "Nome fermata, ID o R-numero (0 = menu): ",
"bus_stop_pick": "Numero fermata o ID diretto (0 = nuova ricerca): ",
"bus_board_menu": "Tasto R) Aggiorna [invio]  1) Altra fermata  0) Menu  [R]: ",
"fly_prompt": "Aeroporto, città o codice (0 = menu): ",
"fly_short": "Scrivi almeno 2 caratteri.",
"fly_menu": "Tasto R) Aggiorna [invio]  1) Altro aeroporto  2) Passa a {o}  0) Menu  [R]: ",
"reg_stations": "🏳️ Stazioni regionali {p} · '{q}'",
"reg_trip": "🏳️ Trip regionale {t}",
"fav_saved_db": "Salvato nel database: {rid}",
"fav_dup": "Già nei preferiti.",
"fav_added_local": "Aggiunto (locale, fai login per il cloud): {key}",
"fav_removed": "Rimosso {fid}",
"fav_is": "Nei preferiti.",
"fav_is_not": "Non nei preferiti.",
"fav_synced": "Sincronizzati {n} preferiti dal database.",
"fav_mirror": "Mirror locale: {f}",
"fav_cloud": "Preferiti cloud",
"fav_cloud_save": "Salvataggio cloud",
"fav_cloud_del": "Rimozione cloud",
"fav_train_fallback": "Treno non live, ID stazione per il dettaglio (invio = annulla): ",
"fav_no_trip": "Nessun trip disponibile per questo preferito.",
"fav_bus_prov": "Provider bus (es. bari): ",
"fav_need_prov": "Serve il provider per la fermata bus.",
"fav_no_line": "Linea non trovata tra le prime righe del provider.",
"fav_unknown": "Tipo preferito sconosciuto: {t}",
"gui_e_stats": "Statistiche non disponibili: {e}",
"gui_e_map": "Mappa non disponibile: {e}",
"gui_e_share": "Condivisione fallita: {e}",
"gui_share_ko": "Condivisione fallita",
"gui_share_ok": "Link copiato negli appunti:\n{url}",
"gui_e_social": "Social: {e}",
"gui_published": "Pubblicato: {res}",
"gui_save_ok": "Salvato offline:\n{out}",
"gui_save_ko": "Salvataggio fallito",
"gui_fav_added": "Aggiunto ai preferiti",
"gui_no_alerts": "Nessun avviso per questo treno.",
"gui_e_match": "Match: {e}",
"gui_match_found": "Match trovato: {d}",
"gui_match_none": "Nessun match multi-paese.",
"gui_alerts_t": "Avvisi ({n})",
"gui_s_rel": "Affidabilità",
"gui_s_trend": "Trend",
"gui_s_avg": "Ritardo medio",
"gui_s_canc": "Cancellazioni",
"gui_s_trips": "Viaggi analizzati",
"gui_s_day": "Giorno peggiore",
"gui_s_station": "Stazione critica",
"fav_total": "Totale: {n}",
"bus_no_stops": "Nessuna fermata trovata.",
"det_title": "🚂 Dettaglio treno {n} @ {s} [{c}]",
"det_cat": "Categoria:",
"det_org": "Origine:",
"det_dest": "Destinazione:",
"det_time": "Orario:",
"det_est": "stimato",
"det_plat": "Binario:",
"lang_auto": "Automatica (sistema)",
"m_config": "⚙️ Config             (lingua e opzioni)",
"cfg_title": "⚙️ Config",
"cfg_cur": "Lingua: {lang} (scelta manuale)",
"cfg_auto_is": "Lingua automatica: {lang} (dal sistema)",
"cfg_change": "Cambia lingua",
"cfg_choice": "Scelta: ",
"trip_title": "🚂 Trip {t} [{c}]",
"trip_line": "Linea:",
"live_title": "🔎 Treni live · filtro \"{q}\"",
"fal_title": "🟣 FAL · stazione {s}",
},
"en": {
"tagline": "Bus · Trains · Planes in the terminal — same endpoints as the Flutter app",
"menu_title": "MAIN MENU",
"m_simple": "Simple mode  (country → station → board)",
"m_commands": "Command mode   (type the command directly)",
"m_advanced": "Advanced menu      (all features)",
"m_guide": "Command guide      (all commands)",
"m_fav": "Favorites           (opens by type: train/station/bus/flights)",
"m_account": "Account             (login, profile, logout)",
"m_exit": "Exit",
"m_choice": "Choice [0-7, help]: ",
"m_ctx_country": "Country {c}",
"m_ctx_last": "last: {name} [{sid}]",
"m_ctx_hint": "— type a station to search it right away",
"m_invalid": "Invalid choice: press 1-7 or type a command.",
"m_bye": "Bye! 👋",
"m_last_none": "No recent board.",
"transport_title": "Transport type:",
"tr_treni": "🚂 Trains", "tr_bus": "🚌 Buses", "tr_voli": "✈️  Flights", "tr_flix": "🟢 Flixbus",
"t_back": "Back",
"num_transport": "Transport number [{d}]: ",
"simple_title": "🟢 Simple mode (0 = menu)",
"train_part": "Key 1) National  2) Regional  [1]: ",
"countries_title": "Countries (number → code):",
"country_prompt": "Country [{last}] (? = list): ",
"country_list_prompt": "Country number [enter = {last}]: ",
"stitle": "🚂 Stations · \"{q}\" [{c}]",
"num_station": "Station number [1-{n}, 0 = cancel]: ",
"cancelled": "Cancelled.",
"invalid_num": "Invalid number.",
"dep_arr": "Key 1) Departures  2) Arrivals  [1]: ",
"board_menu": "Key R) Refresh [enter]  1) Other station  2) {opt2}  3) Switch to {other}  4) Train timeline  5) Graphics  0) Menu  [R]: ",
"opt_country": "Change country", "opt_provider": "Change provider",
"to_arr": "Arrivals", "to_dep": "Departures",
"row_pick": "Train row number [1-{n}]: ",
"no_rows": "No rows: show the board first.",
"no_trip_row": "Trip not available for this row.",
"recents": "Recent:",
"train_search_prompt": "Station name, R-number (0 = menu): ",
"recent_invalid": "Invalid recent.",
"board_title_dep": "🚂 Departures · {sid} [{c}]",
"board_title_arr": "🚂 Arrivals · {sid} [{c}]",
"col_n": "N", "col_time": "TIME", "col_train": "TRAIN", "col_dest": "DESTINATION",
"col_from": "ORIGIN", "col_plat": "PLAT", "col_state": "STATUS",
"board_total": "Total: {n} (showing max 30) · key 4 = train timeline",
"board_empty": "No trains found.",
"in_time": "on time",
"tl_title": "Timeline ({n} stops):",
"tl_none": "No stops in timeline.",
"tl_not_left": "🚂 not departed", "tl_here": "🚂 here", "tl_travel": "🚂 ↓ traveling",
"tl_arrived": "🚂 arrived",
"reg_title": "🏳️ Regional (0 = menu)",
"reg_providers": "🏳️ Regional providers · {c}",
"reg_none": "No regional provider.",
"reg_num": "Provider number [1-{n}, 0 = cancel]: ",
"reg_with": "Provider: {p}",
"reg_station_prompt": "Station name, R-number (0 = menu): ",
"reg_board_dep": "🏳️ Regional departures · {sid}",
"reg_board_arr": "🏳️ Regional arrivals · {sid}",
"fav_title": "⭐ Favorites",
"fav_db": "From database (logged in).",
"fav_local": "Local file (log in for the database).",
"fav_empty": "No favorites.",
"fav_num": "Number [0-{n}]: ",
"acc_title": "👤 Account",
"acc_in": "Logged in as {e} (nick: {n}, id: {i})",
"acc_out": "Not logged in (favorites stay local).",
"acc_menu": "[1] Status  [2] Login  [3] Register  [4] Change nick  [5] Check nick  [6] Logout  [7] Delete account  [0] Back",
"acc_choice": "Choice [0-7]: ",
"ask_email": "Email: ", "ask_pw": "Password: ", "ask_nick": "Nickname: ",
"ask_new_nick": "New nickname: ", "ask_check_nick": "Nickname to check: ",
"ask_del_pw": "Password to confirm deletion (enter = cancel): ",
"login_ok": "Login ok: {u}", "login_ko": "Invalid credentials.",
"reg_ok": "Registered: {e}",
"nick_ok": "Nickname available.", "nick_ko": "Nickname taken.",
"prof_ok": "Profile updated: {n}",
"del_ok": "Account deleted, session cleared.", "del_ko": "Deletion failed.",
"need_login": "You must log in first.",
"logout_ok": "Logout, session cleared.",
"logged_as": "Logged in as {e} (nickname: {n})",
"no_session": "No session. Use: auth --login <email> <pw>",
"lang_title": "Language / Lingua / Sprache / Langue:",
"lang_prompt": "Number or code [enter = current]: ",
"lang_invalid": "Invalid language.",
"gui_train": "TRAIN · {c}",
"gui_on_time": "ON TIME", "gui_delay": "DELAY +{d} MIN", "gui_early": "EARLY {d} MIN",
"gui_online": "● {v} online",
"gui_live_on": "LIVE ON", "gui_live_off": "LIVE OFF",
"gui_update": "Refresh", "gui_close": "Close",
"gui_updated": "Updated {t}",
"gui_route_done": "ROUTE · {done} OF {n} STOPS",
"gui_delay_from": "DELAY FROM {src}",
"gui_next": "NEXT STOP",
"gui_at": "at {t}", "gui_plat": "platform {p}",
"gui_dest_done": "Destination reached",
"gui_wait": "Waiting for departure...",
"gui_actions": "QUICK ACTIONS",
"gui_btns": ["Stats", "Map", "Share", "Social", "Save", "Alerts", "Favorite", "Match"],
"gui_match_ok": "✓ match: {d}", "gui_match_ko": "no match",
"gui_stops": "STOPS", "gui_n_stops": "{n} stops", "gui_no_stops": "No stops.",
"gui_not_left": "NOT DEPARTED", "gui_here": "HERE", "gui_travel": "TRAVELING",
"gui_arrived": "ARRIVED", "gui_cancelled": "CANCELLED",
"gui_dep": "departure", "gui_arr": "arrival", "gui_bin": "plat {p}",
"gui_dep_full": "departure {t}", "gui_arr_full": "arrival {t}",
"gui_stop_wait": "Train at station · departure {t}",
"gui_stop_done": "Run finished · train arrived",
"gui_stop_travel": "Traveling · {a} → {b} · {p}%",
"gui_stop_dwell": "Stopped at station · {s}",
"gui_stop_last": "Traveling · last stop {s}",
"gui_stats_title": "TRAIN STATS",
"bus_prov_title": "Bus provider (enter = last): ",
"bus_stop_prompt": "Stop name, ID or R-number (0 = menu): ",
"bus_stop_pick": "Stop number or direct ID (0 = new search): ",
"bus_board_menu": "Key R) Refresh [enter]  1) Other stop  0) Menu  [R]: ",
"fly_prompt": "Airport, city or code (0 = menu): ",
"fly_short": "Type at least 2 characters.",
"fly_menu": "Key R) Refresh [enter]  1) Other airport  2) Switch to {o}  0) Menu  [R]: ",
"reg_stations": "🏳️ Regional stations {p} · '{q}'",
"reg_trip": "🏳️ Regional trip {t}",
"fav_saved_db": "Saved to database: {rid}",
"fav_dup": "Already in favorites.",
"fav_added_local": "Added (local, log in for cloud): {key}",
"fav_removed": "Removed {fid}",
"fav_is": "In favorites.",
"fav_is_not": "Not in favorites.",
"fav_synced": "Synced {n} favorites from database.",
"fav_mirror": "Local mirror: {f}",
"fav_cloud": "Cloud favorites",
"fav_cloud_save": "Cloud save",
"fav_cloud_del": "Cloud removal",
"fav_train_fallback": "Train not live, station ID for details (enter = cancel): ",
"fav_no_trip": "No trip available for this favorite.",
"fav_bus_prov": "Bus provider (e.g. bari): ",
"fav_need_prov": "Provider needed for bus stop.",
"fav_no_line": "Line not found in provider top rows.",
"fav_unknown": "Unknown favorite type: {t}",
"gui_e_stats": "Stats unavailable: {e}",
"gui_e_map": "Map unavailable: {e}",
"gui_e_share": "Share failed: {e}",
"gui_share_ko": "Share failed",
"gui_share_ok": "Link copied to clipboard:\n{url}",
"gui_e_social": "Social: {e}",
"gui_published": "Published: {res}",
"gui_save_ok": "Saved offline:\n{out}",
"gui_save_ko": "Save failed",
"gui_fav_added": "Added to favorites",
"gui_no_alerts": "No alerts for this train.",
"gui_e_match": "Match: {e}",
"gui_match_found": "Match found: {d}",
"gui_match_none": "No cross-country match.",
"gui_alerts_t": "Alerts ({n})",
"gui_s_rel": "Reliability",
"gui_s_trend": "Trend",
"gui_s_avg": "Avg delay",
"gui_s_canc": "Cancellations",
"gui_s_trips": "Trips analyzed",
"gui_s_day": "Worst day",
"gui_s_station": "Critical station",
"fav_total": "Total: {n}",
"bus_no_stops": "No stops found.",
"det_title": "🚂 Train details {n} @ {s} [{c}]",
"det_cat": "Category:",
"det_org": "Origin:",
"det_dest": "Destination:",
"det_time": "Time:",
"det_est": "estimated",
"det_plat": "Platform:",
"lang_auto": "Automatic (system)",
"m_config": "⚙️ Config             (language & options)",
"cfg_title": "⚙️ Config",
"cfg_cur": "Language: {lang} (manual)",
"cfg_auto_is": "Automatic language: {lang} (from system)",
"cfg_change": "Change language",
"cfg_choice": "Choice: ",
"trip_title": "🚂 Trip {t} [{c}]",
"trip_line": "Line:",
"live_title": "🔎 Live trains · filter \"{q}\"",
"fal_title": "🟣 FAL · station {s}",
},
"de": {
"tagline": "Bus · Züge · Flugzeuge im Terminal — gleiche Endpunkte wie die Flutter-App",
"menu_title": "HAUPTMENÜ",
"m_simple": "Einfacher Modus  (Land → Bahnhof → Abfahrtstafel)",
"m_commands": "Befehlsmodus   (Befehl direkt eingeben)",
"m_advanced": "Erweitertes Menü      (alle Funktionen)",
"m_guide": "Befehlsübersicht      (alle Befehle)",
"m_fav": "Favoriten           (öffnet nach Typ: Zug/Bahnhof/Bus/Flüge)",
"m_account": "Konto             (Login, Profil, Logout)",
"m_exit": "Beenden",
"m_choice": "Auswahl [0-7, help]: ",
"m_ctx_country": "Land {c}",
"m_ctx_last": "zuletzt: {name} [{sid}]",
"m_ctx_hint": "— Bahnhof eingeben, um sofort zu suchen",
"m_invalid": "Ungültige Auswahl: 1-7 drücken oder Befehl eingeben.",
"m_bye": "Tschüss! 👋",
"m_last_none": "Keine aktuelle Tafel.",
"transport_title": "Verkehrsmittel:",
"tr_treni": "🚂 Züge", "tr_bus": "🚌 Busse", "tr_voli": "✈️  Flüge", "tr_flix": "🟢 Flixbus",
"t_back": "Zurück",
"num_transport": "Verkehrsmittelnummer [{d}]: ",
"simple_title": "🟢 Einfacher Modus (0 = Menü)",
"train_part": "Taste 1) National  2) Regional  [1]: ",
"countries_title": "Länder (Nummer → Code):",
"country_prompt": "Land [{last}] (? = Liste): ",
"country_list_prompt": "Ländernummmer [Enter = {last}]: ",
"stitle": "🚂 Bahnhöfe · \"{q}\" [{c}]",
"num_station": "Bahnhofsnummer [1-{n}, 0 = Abbrechen]: ",
"cancelled": "Abgebrochen.",
"invalid_num": "Ungültige Nummer.",
"dep_arr": "Taste 1) Abfahrten  2) Ankünfte  [1]: ",
"board_menu": "Taste R) Aktualisieren [Enter]  1) Anderer Bahnhof  2) {opt2}  3) Wechseln zu {other}  4) Zug-Timeline  5) Grafik  0) Menü  [R]: ",
"opt_country": "Land wechseln", "opt_provider": "Anbieter wechseln",
"to_arr": "Ankünfte", "to_dep": "Abfahrten",
"row_pick": "Zugzeilennummer [1-{n}]: ",
"no_rows": "Keine Zeilen: zuerst die Tafel anzeigen.",
"no_trip_row": "Trip für diese Zeile nicht verfügbar.",
"recents": "Zuletzt:",
"train_search_prompt": "Bahnhofsname, R-Nummer (0 = Menü): ",
"recent_invalid": "Ungültiger Verlauf.",
"board_title_dep": "🚂 Abfahrten · {sid} [{c}]",
"board_title_arr": "🚂 Ankünfte · {sid} [{c}]",
"col_n": "N", "col_time": "ZEIT", "col_train": "ZUG", "col_dest": "ZIEL",
"col_from": "HERKUNFT", "col_plat": "GLS", "col_state": "STATUS",
"board_total": "Gesamt: {n} (max. 30 gezeigt) · Taste 4 = Zug-Timeline",
"board_empty": "Keine Züge gefunden.",
"in_time": "pünktlich",
"tl_title": "Timeline ({n} Halte):",
"tl_none": "Keine Halte in der Timeline.",
"tl_not_left": "🚂 nicht abgefahren", "tl_here": "🚂 hier", "tl_travel": "🚂 ↓ unterwegs",
"tl_arrived": "🚂 angekommen",
"reg_title": "🏳️ Regional (0 = Menü)",
"reg_providers": "🏳️ Regionale Anbieter · {c}",
"reg_none": "Kein regionaler Anbieter.",
"reg_num": "Anbieternummer [1-{n}, 0 = Abbrechen]: ",
"reg_with": "Anbieter: {p}",
"reg_station_prompt": "Bahnhofsname, R-Nummer (0 = Menü): ",
"reg_board_dep": "🏳️ Regionale Abfahrten · {sid}",
"reg_board_arr": "🏳️ Regionale Ankünfte · {sid}",
"fav_title": "⭐ Favoriten",
"fav_db": "Aus Datenbank (angemeldet).",
"fav_local": "Lokale Datei (für Datenbank anmelden).",
"fav_empty": "Keine Favoriten.",
"fav_num": "Nummer [0-{n}]: ",
"acc_title": "👤 Konto",
"acc_in": "Angemeldet als {e} (Nick: {n}, ID: {i})",
"acc_out": "Nicht angemeldet (Favoriten bleiben lokal).",
"acc_menu": "[1] Status  [2] Login  [3] Registrieren  [4] Nick ändern  [5] Nick prüfen  [6] Logout  [7] Konto löschen  [0] Zurück",
"acc_choice": "Auswahl [0-7]: ",
"ask_email": "E-Mail: ", "ask_pw": "Passwort: ", "ask_nick": "Nickname: ",
"ask_new_nick": "Neuer Nickname: ", "ask_check_nick": "Zu prüfender Nickname: ",
"ask_del_pw": "Passwort zum Bestätigen (Enter = Abbrechen): ",
"login_ok": "Login ok: {u}", "login_ko": "Ungültige Anmeldedaten.",
"reg_ok": "Registriert: {e}",
"nick_ok": "Nickname verfügbar.", "nick_ko": "Nickname vergeben.",
"prof_ok": "Profil aktualisiert: {n}",
"del_ok": "Konto gelöscht, Sitzung beendet.", "del_ko": "Löschen fehlgeschlagen.",
"need_login": "Bitte zuerst anmelden.",
"logout_ok": "Logout, Sitzung beendet.",
"logged_as": "Angemeldet als {e} (Nickname: {n})",
"no_session": "Keine Sitzung. Nutze: auth --login <email> <pw>",
"lang_title": "Sprache / Lingua / Language / Langue:",
"lang_prompt": "Nummer oder Code [Enter = aktuell]: ",
"lang_invalid": "Ungültige Sprache.",
"gui_train": "ZUG · {c}",
"gui_on_time": "PÜNKTLICH", "gui_delay": "VERSPÄTUNG +{d} MIN", "gui_early": "FRÜHER {d} MIN",
"gui_online": "● {v} online",
"gui_live_on": "LIVE AN", "gui_live_off": "LIVE AUS",
"gui_update": "Aktualisieren", "gui_close": "Schließen",
"gui_updated": "Aktualisiert {t}",
"gui_route_done": "STRECKE · {done} VON {n} HALTEN",
"gui_delay_from": "VERSPÄTUNG VON {src}",
"gui_next": "NÄCHSTER HALT",
"gui_at": "um {t}", "gui_plat": "Gleis {p}",
"gui_dest_done": "Ziel erreicht",
"gui_wait": "Warte auf Abfahrt...",
"gui_actions": "SCHNELLAKTIONEN",
"gui_btns": ["Statistik", "Karte", "Teilen", "Social", "Speichern", "Meldungen", "Favorit", "Match"],
"gui_match_ok": "✓ Match: {d}", "gui_match_ko": "kein Match",
"gui_stops": "HALTE", "gui_n_stops": "{n} Halte", "gui_no_stops": "Keine Halte.",
"gui_not_left": "NICHT ABGEFAHREN", "gui_here": "HIER", "gui_travel": "UNTERWEGS",
"gui_arrived": "ANGEKOMMEN", "gui_cancelled": "ENTFALLEN",
"gui_dep": "Abfahrt", "gui_arr": "Ankunft", "gui_bin": "Gl {p}",
"gui_dep_full": "Abfahrt {t}", "gui_arr_full": "Ankunft {t}",
"gui_stop_wait": "Zug im Bahnhof · Abfahrt {t}",
"gui_stop_done": "Fahrt beendet · Zug angekommen",
"gui_stop_travel": "Unterwegs · {a} → {b} · {p}%",
"gui_stop_dwell": "Halt im Bahnhof · {s}",
"gui_stop_last": "Unterwegs · letzter Halt {s}",
"gui_stats_title": "ZUGSTATISTIK",
"bus_prov_title": "Busanbieter (Enter = letzter): ",
"bus_stop_prompt": "Haltestellenname, ID oder R-Nummer (0 = Menü): ",
"bus_stop_pick": "Haltestellennummer oder direkte ID (0 = neue Suche): ",
"bus_board_menu": "Taste R) Aktualisieren [Enter]  1) Andere Haltestelle  0) Menü  [R]: ",
"fly_prompt": "Flughafen, Stadt oder Code (0 = Menü): ",
"fly_short": "Mindestens 2 Zeichen eingeben.",
"fly_menu": "Taste R) Aktualisieren [Enter]  1) Anderer Flughafen  2) Wechseln zu {o}  0) Menü  [R]: ",
"reg_stations": "🏳️ Regionale Bahnhöfe {p} · '{q}'",
"reg_trip": "🏳️ Regionaler Trip {t}",
"fav_saved_db": "In Datenbank gespeichert: {rid}",
"fav_dup": "Bereits in Favoriten.",
"fav_added_local": "Hinzugefügt (lokal, für Cloud anmelden): {key}",
"fav_removed": "Entfernt {fid}",
"fav_is": "In Favoriten.",
"fav_is_not": "Nicht in Favoriten.",
"fav_synced": "{n} Favoriten aus Datenbank synchronisiert.",
"fav_mirror": "Lokale Kopie: {f}",
"fav_cloud": "Cloud-Favoriten",
"fav_cloud_save": "Cloud-Speichern",
"fav_cloud_del": "Cloud-Löschen",
"fav_train_fallback": "Zug nicht live, Bahnhofs-ID für Details (Enter = Abbrechen): ",
"fav_no_trip": "Kein Trip für diesen Favoriten verfügbar.",
"fav_bus_prov": "Busanbieter (z. B. bari): ",
"fav_need_prov": "Anbieter für Bushaltestelle nötig.",
"fav_no_line": "Linie in den Top-Zeilen des Anbieters nicht gefunden.",
"fav_unknown": "Unbekannter Favoritentyp: {t}",
"gui_e_stats": "Statistik nicht verfügbar: {e}",
"gui_e_map": "Karte nicht verfügbar: {e}",
"gui_e_share": "Teilen fehlgeschlagen: {e}",
"gui_share_ko": "Teilen fehlgeschlagen",
"gui_share_ok": "Link in Zwischenablage kopiert:\n{url}",
"gui_e_social": "Social: {e}",
"gui_published": "Veröffentlicht: {res}",
"gui_save_ok": "Offline gespeichert:\n{out}",
"gui_save_ko": "Speichern fehlgeschlagen",
"gui_fav_added": "Zu Favoriten hinzugefügt",
"gui_no_alerts": "Keine Meldungen für diesen Zug.",
"gui_e_match": "Match: {e}",
"gui_match_found": "Match gefunden: {d}",
"gui_match_none": "Kein länderübergreifender Match.",
"gui_alerts_t": "Meldungen ({n})",
"gui_s_rel": "Zuverlässigkeit",
"gui_s_trend": "Trend",
"gui_s_avg": "Ø Verspätung",
"gui_s_canc": "Ausfälle",
"gui_s_trips": "Analysierte Fahrten",
"gui_s_day": "Schlechtester Tag",
"gui_s_station": "Kritischer Bahnhof",
"fav_total": "Gesamt: {n}",
"bus_no_stops": "Keine Haltestelle gefunden.",
"det_title": "🚂 Zugdetails {n} @ {s} [{c}]",
"det_cat": "Kategorie:",
"det_org": "Herkunft:",
"det_dest": "Ziel:",
"det_time": "Zeit:",
"det_est": "voraussichtlich",
"det_plat": "Gleis:",
"lang_auto": "Automatisch (System)",
"m_config": "⚙️ Konfig             (Sprache & Optionen)",
"cfg_title": "⚙️ Konfig",
"cfg_cur": "Sprache: {lang} (manuell)",
"cfg_auto_is": "Automatische Sprache: {lang} (vom System)",
"cfg_change": "Sprache ändern",
"cfg_choice": "Auswahl: ",
"trip_title": "🚂 Trip {t} [{c}]",
"trip_line": "Linie:",
"live_title": "🔎 Live-Züge · Filter \"{q}\"",
"fal_title": "🟣 FAL · Bahnhof {s}",
},
"fr": {
"tagline": "Bus · Trains · Avions dans le terminal — mêmes endpoints que l’app Flutter",
"menu_title": "MENU PRINCIPAL",
"m_simple": "Mode simple  (pays → gare → tableau)",
"m_commands": "Mode commandes   (tapez la commande)",
"m_advanced": "Menu avancé      (toutes les fonctions)",
"m_guide": "Guide commandes      (toutes les commandes)",
"m_fav": "Favoris           (ouvre par type : train/gare/bus/vols)",
"m_account": "Compte             (login, profil, logout)",
"m_exit": "Quitter",
"m_choice": "Choix [0-7, help]: ",
"m_ctx_country": "Pays {c}",
"m_ctx_last": "dernier : {name} [{sid}]",
"m_ctx_hint": "— tapez une gare pour la chercher aussitôt",
"m_invalid": "Choix invalide : 1-7 ou tapez une commande.",
"m_bye": "Salut ! 👋",
"m_last_none": "Aucun tableau récent.",
"transport_title": "Type de transport :",
"tr_treni": "🚂 Trains", "tr_bus": "🚌 Bus", "tr_voli": "✈️  Vols", "tr_flix": "🟢 Flixbus",
"t_back": "Retour",
"num_transport": "Numéro transport [{d}]: ",
"simple_title": "🟢 Mode simple (0 = menu)",
"train_part": "Touche 1) National  2) Régional  [1] : ",
"countries_title": "Pays (numéro → code) :",
"country_prompt": "Pays [{last}] (? = liste) : ",
"country_list_prompt": "Numéro pays [entrée = {last}] : ",
"stitle": "🚂 Gares · « {q} » [{c}]",
"num_station": "Numéro gare [1-{n}, 0 = annuler] : ",
"cancelled": "Annulé.",
"invalid_num": "Numéro invalide.",
"dep_arr": "Touche 1) Départs  2) Arrivées  [1] : ",
"board_menu": "Touche R) Actualiser [entrée]  1) Autre gare  2) {opt2}  3) Passer à {other}  4) Timeline train  5) Graphique  0) Menu  [R] : ",
"opt_country": "Changer de pays", "opt_provider": "Changer d’opérateur",
"to_arr": "Arrivées", "to_dep": "Départs",
"row_pick": "Numéro ligne du train [1-{n}] : ",
"no_rows": "Aucune ligne : affichez d’abord le tableau.",
"no_trip_row": "Trip indisponible pour cette ligne.",
"recents": "Récents :",
"train_search_prompt": "Nom gare, n° R (0 = menu) : ",
"recent_invalid": "Récent invalide.",
"board_title_dep": "🚂 Départs · {sid} [{c}]",
"board_title_arr": "🚂 Arrivées · {sid} [{c}]",
"col_n": "N", "col_time": "HEURE", "col_train": "TRAIN", "col_dest": "DESTINATION",
"col_from": "PROVENANCE", "col_plat": "VOIE", "col_state": "ÉTAT",
"board_total": "Total : {n} (max 30 affichés) · touche 4 = timeline du train",
"board_empty": "Aucun train trouvé.",
"in_time": "à l’heure",
"tl_title": "Timeline ({n} arrêts) :",
"tl_none": "Aucun arrêt dans la timeline.",
"tl_not_left": "🚂 non parti", "tl_here": "🚂 ici", "tl_travel": "🚂 ↓ en route",
"tl_arrived": "🚂 arrivé",
"reg_title": "🏳️ Régional (0 = menu)",
"reg_providers": "🏳️ Opérateurs régionaux · {c}",
"reg_none": "Aucun opérateur régional.",
"reg_num": "Numéro opérateur [1-{n}, 0 = annuler] : ",
"reg_with": "Opérateur : {p}",
"reg_station_prompt": "Nom gare, n° R (0 = menu) : ",
"reg_board_dep": "🏳️ Départs régionaux · {sid}",
"reg_board_arr": "🏳️ Arrivées régionales · {sid}",
"fav_title": "⭐ Favoris",
"fav_db": "Depuis la base (connecté).",
"fav_local": "Fichier local (connectez-vous pour la base).",
"fav_empty": "Aucun favori.",
"fav_num": "Numéro [0-{n}] : ",
"acc_title": "👤 Compte",
"acc_in": "Connecté : {e} (pseudo : {n}, id : {i})",
"acc_out": "Non connecté (les favoris restent locaux).",
"acc_menu": "[1] État  [2] Login  [3] Inscription  [4] Changer pseudo  [5] Vérifier pseudo  [6] Logout  [7] Supprimer compte  [0] Retour",
"acc_choice": "Choix [0-7] : ",
"ask_email": "Email : ", "ask_pw": "Mot de passe : ", "ask_nick": "Pseudo : ",
"ask_new_nick": "Nouveau pseudo : ", "ask_check_nick": "Pseudo à vérifier : ",
"ask_del_pw": "Mot de passe pour confirmer (entrée = annuler) : ",
"login_ok": "Login ok : {u}", "login_ko": "Identifiants invalides.",
"reg_ok": "Inscrit : {e}",
"nick_ok": "Pseudo disponible.", "nick_ko": "Pseudo occupé.",
"prof_ok": "Profil mis à jour : {n}",
"del_ok": "Compte supprimé, session nettoyée.", "del_ko": "Suppression échouée.",
"need_login": "Connectez-vous d’abord.",
"logout_ok": "Logout, session nettoyée.",
"logged_as": "Connecté : {e} (pseudo : {n})",
"no_session": "Aucune session. Utilisez : auth --login <email> <pw>",
"lang_title": "Langue / Lingua / Language / Sprache :",
"lang_prompt": "Numéro ou code [entrée = actuelle] : ",
"lang_invalid": "Langue invalide.",
"gui_train": "TRAIN · {c}",
"gui_on_time": "À L’HEURE", "gui_delay": "RETARD +{d} MIN", "gui_early": "EN AVANCE {d} MIN",
"gui_online": "● {v} en ligne",
"gui_live_on": "LIVE ON", "gui_live_off": "LIVE OFF",
"gui_update": "Actualiser", "gui_close": "Fermer",
"gui_updated": "Mis à jour {t}",
"gui_route_done": "PARCOURS · {done} SUR {n} ARRÊTS",
"gui_delay_from": "RETARD VIA {src}",
"gui_next": "PROCHAIN ARRÊT",
"gui_at": "{t}", "gui_plat": "voie {p}",
"gui_dest_done": "Destination atteinte",
"gui_wait": "En attente de départ...",
"gui_actions": "ACTIONS RAPIDES",
"gui_btns": ["Stats", "Carte", "Partager", "Social", "Sauver", "Alertes", "Favori", "Match"],
"gui_match_ok": "✓ match : {d}", "gui_match_ko": "aucun match",
"gui_stops": "ARRÊTS", "gui_n_stops": "{n} arrêts", "gui_no_stops": "Aucun arrêt.",
"gui_not_left": "NON PARTI", "gui_here": "ICI", "gui_travel": "EN ROUTE",
"gui_arrived": "ARRIVÉ", "gui_cancelled": "SUPPRIMÉ",
"gui_dep": "départ", "gui_arr": "arrivée", "gui_bin": "voie {p}",
"gui_dep_full": "départ {t}", "gui_arr_full": "arrivée {t}",
"gui_stop_wait": "Train en gare · départ {t}",
"gui_stop_done": "Course terminée · train arrivé",
"gui_stop_travel": "En route · {a} → {b} · {p}%",
"gui_stop_dwell": "Arrêt en gare · {s}",
"gui_stop_last": "En route · dernier arrêt {s}",
"gui_stats_title": "STATS TRAIN",
"bus_prov_title": "Opérateur bus (entrée = dernier) : ",
"bus_stop_prompt": "Nom arrêt, ID ou n° R (0 = menu) : ",
"bus_stop_pick": "Numéro arrêt ou ID direct (0 = nouvelle recherche) : ",
"bus_board_menu": "Touche R) Actualiser [entrée]  1) Autre arrêt  0) Menu  [R] : ",
"fly_prompt": "Aéroport, ville ou code (0 = menu) : ",
"fly_short": "Au moins 2 caractères.",
"fly_menu": "Touche R) Actualiser [entrée]  1) Autre aéroport  2) Passer à {o}  0) Menu  [R] : ",
"reg_stations": "🏳️ Gares régionales {p} · « {q} »",
"reg_trip": "🏳️ Trip régional {t}",
"fav_saved_db": "Enregistré en base : {rid}",
"fav_dup": "Déjà dans les favoris.",
"fav_added_local": "Ajouté (local, connectez-vous pour le cloud) : {key}",
"fav_removed": "Supprimé {fid}",
"fav_is": "Dans les favoris.",
"fav_is_not": "Pas dans les favoris.",
"fav_synced": "{n} favoris synchronisés depuis la base.",
"fav_mirror": "Miroir local : {f}",
"fav_cloud": "Favoris cloud",
"fav_cloud_save": "Sauvegarde cloud",
"fav_cloud_del": "Suppression cloud",
"fav_train_fallback": "Train non live, ID gare pour le détail (entrée = annuler) : ",
"fav_no_trip": "Aucun trip pour ce favori.",
"fav_bus_prov": "Opérateur bus (ex. bari) : ",
"fav_need_prov": "Opérateur requis pour l’arrêt de bus.",
"fav_no_line": "Ligne introuvable dans les premières lignes de l’opérateur.",
"fav_unknown": "Type de favori inconnu : {t}",
"gui_e_stats": "Stats indisponibles : {e}",
"gui_e_map": "Carte indisponible : {e}",
"gui_e_share": "Partage échoué : {e}",
"gui_share_ko": "Partage échoué",
"gui_share_ok": "Lien copié :\n{url}",
"gui_e_social": "Social : {e}",
"gui_published": "Publié : {res}",
"gui_save_ok": "Sauvé hors-ligne :\n{out}",
"gui_save_ko": "Sauvegarde échouée",
"gui_fav_added": "Ajouté aux favoris",
"gui_no_alerts": "Aucune alerte pour ce train.",
"gui_e_match": "Match : {e}",
"gui_match_found": "Match trouvé : {d}",
"gui_match_none": "Aucun match multi-pays.",
"gui_alerts_t": "Alertes ({n})",
"gui_s_rel": "Fiabilité",
"gui_s_trend": "Tendance",
"gui_s_avg": "Retard moyen",
"gui_s_canc": "Annulations",
"gui_s_trips": "Trajets analysés",
"gui_s_day": "Pire jour",
"gui_s_station": "Gare critique",
"fav_total": "Total : {n}",
"bus_no_stops": "Aucun arrêt trouvé.",
"det_title": "🚂 Détail train {n} @ {s} [{c}]",
"det_cat": "Catégorie :",
"det_org": "Origine :",
"det_dest": "Destination :",
"det_time": "Horaire :",
"det_est": "estimé",
"det_plat": "Voie :",
"lang_auto": "Automatique (système)",
"m_config": "⚙️ Config             (langue et options)",
"cfg_title": "⚙️ Config",
"cfg_cur": "Langue : {lang} (manuelle)",
"cfg_auto_is": "Langue automatique : {lang} (du système)",
"cfg_change": "Changer de langue",
"cfg_choice": "Choix : ",
"trip_title": "🚂 Trip {t} [{c}]",
"trip_line": "Ligne :",
"live_title": "🔎 Trains live · filtre « {q} »",
"fal_title": "🟣 FAL · gare {s}",
},
}

# -- MENU INTERATTIVI ---------------------------------------------------------
def banner():
    if USE_COLOR:
        bar = f"{BOLD}{B}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{RESET}"
        print(bar)
        print(f"   {BOLD}{C_}BC.Transporter{RESET}  {dim('· terminale')}")
        print(bar)
    else:
        print("=== BC.Transporter · terminale ===")
    print(f"  {dim(t('tagline'))}")

def pick_country():
    # Veloce: invio = ultimo usato, codice diretto, ? = lista completa
    last = last_country()
    data = load_json_file(os.path.join(HOME, ".bc_cli_countries.json"), {})
    entries = data.get("entries", [])
    if not entries:
        entries = train_countries() or []
    if not entries:
        c = (ask(t("country_prompt", last=last)) or last).upper()
        remember_country(c)
        return c

    def show_list():
        print(f"\n  {dim(t('countries_title'))}")
        for e in entries:
            mark = " ←" if str(e["code"]).upper() == last else ""
            print(f"  {c_train('[' + str(e['n']) + ']')} {e['code'].ljust(18)} {dim(e['name'])}{mark}")

    sel = (ask(t("country_prompt", last=last)).strip() or last)
    if sel == "?":
        show_list()
        sel = (ask(t("country_list_prompt", last=last)).strip() or last)
    code = country_from_number(sel)
    if code:
        remember_country(code)
        return code
    c = sel.upper()
    remember_country(c)
    return c

COMMANDS = ("treni", "bus", "voli", "flixbus", "regionali", "strade",
            "meteo", "social", "auth", "preferiti", "config", "offline")

def run_direct(line):
    import shlex
    try:
        main(shlex.split(line))
    except SystemExit:
        pass

TRANSPORTS = (("treni", "tr_treni"), ("bus", "tr_bus"),
              ("voli", "tr_voli"), ("flixbus", "tr_flix"))

def pick_transport(default="1"):
    print(f"\n  {dim(t('transport_title'))}")
    painters = {"treni": c_train, "bus": c_bus, "voli": c_plane, "flixbus": ok}
    for i, (key, tkey) in enumerate(TRANSPORTS, 1):
        print(f"  {painters[key](f'[{i}]')} {t(tkey)}")
    print(f"  {dim('[0] ' + t('t_back'))}")
    s = ask(t("num_transport", d=default)).strip() or default
    if s == "0":
        return None
    try:
        return TRANSPORTS[int(s) - 1][0]
    except (ValueError, IndexError):
        return TRANSPORTS[int(default) - 1][0]

def simple_mode():
    p_title(t("simple_title"))
    transport = pick_transport()
    if transport is None:
        return
    if transport == "treni":
        parte = ask(t("train_part")).strip() or "1"
        if parte == "2":
            simple_regional()
        else:
            simple_train()
    elif transport == "bus":
        simple_bus()
    elif transport == "voli":
        simple_fly()
    elif transport == "flixbus":
        simple_flix()

def simple_regional():
    p_title(t("reg_title"))
    country = pick_country()
    provider = pick_regional_provider(country)
    if not provider:
        return
    p_ok(t("reg_with", p=provider))
    while True:
        rec = [e for e in get_recent("recent_regstations")
               if e.get("provider") == provider][:5]
        if rec:
            print(f"\n  {dim(t('recents'))}")
            for i, e in enumerate(rec, 1):
                print(f"  {ok(f'[R{i}]')} {e.get('name')}  {dim(str(e.get('sid')))}")
        q = ask("\n" + t("reg_station_prompt"))
        if not q or q.strip() == "0":
            return
        q = q.strip()
        if q.lower().startswith("r") and q[1:].isdigit():
            idx = int(q[1:]) - 1
            if 0 <= idx < len(rec):
                e = rec[idx]
                m = ask(t("dep_arr")).strip() or "1"
                r = train_board_loop(str(e.get("sid")), country, m == "2",
                                     str(e.get("name") or "?"), provider=provider)
                if r is None:
                    return
                if r.get("provider") and r["provider"] != provider:
                    provider = r["provider"]
                    p_ok(t("reg_with", p=provider))
                continue
            p_warn(t("recent_invalid"))
            continue
        try:
            _, _, lst = fetch_reg_stations(country, provider, q)
        except Exception as e:
            p_err(f"Errore ricerca: {e}")
            continue
        if not lst:
            p_warn("Nessuna stazione trovata, riprova.")
            continue
        for i, e in enumerate(lst[:10], 1):
            print(f"  {ok(f'[{i}]')} {e.get('name') or e.get('stationName') or '?'}")
        s = (ask("Numero stazione (0 = nuova ricerca): ").strip() or "0")
        if s == "0":
            continue
        try:
            choice = lst[int(s) - 1] if 1 <= int(s) <= min(len(lst), 10) else None
        except ValueError:
            choice = None
        if not isinstance(choice, dict):
            p_warn("Numero non valido.")
            continue
        sid = str(choice.get("id") or choice.get("stationId") or "")
        name = str(choice.get("name") or choice.get("stationName") or "?")
        m = ask(t("dep_arr")).strip() or "1"
        r = train_board_loop(sid, country, m == "2", name, provider=provider)
        if r is None:
            return
        if r.get("provider") and r["provider"] != provider:
            provider = r["provider"]
            p_ok(t("reg_with", p=provider))

def pick_board_row(board):
    if not board:
        p_warn(t("no_rows"))
        return None
    r = ask(t("row_pick", n=len(board))).strip()
    try:
        row = board[int(r) - 1] if 1 <= int(r) <= len(board) else None
    except ValueError:
        row = None
    if not isinstance(row, dict):
        p_warn("Numero non valido.")
        return None
    return row

def station_search_pick(q, country):
    """Cerca stazioni e fa scegliere: ritorna (sid, nome) o None."""
    try:
        _, lst = fetch_stations(q, country)
    except Exception as e:
        p_err(f"Errore ricerca: {e}")
        return None
    if not lst:
        p_warn("Nessuna stazione trovata, riprova.")
        return None
    p_title(t("stitle", q=q, c=country))
    for i, e in enumerate(lst, 1):
        e = e if isinstance(e, dict) else {}
        name = e.get("name") or e.get("stationName") or "?"
        print(f"  {c_train(f'[{i}]')} {bold(name)}")
    s = (ask(t("num_station", n=len(lst))).strip() or "1")
    if s == "0":
        return None
    try:
        choice = lst[int(s) - 1] if 1 <= int(s) <= len(lst) else None
    except ValueError:
        choice = None
    if not isinstance(choice, dict):
        p_warn(t("invalid_num"))
        return None
    sid = str(choice.get("id") or choice.get("stationId") or "")
    name = str(choice.get("name") or choice.get("stationName") or "?")
    return sid, name

def pick_regional_provider(country):
    """Sceglie il provider regionale numerato: ritorna il nome o None."""
    try:
        provs = reg_providers(country) or []
    except Exception:
        provs = []
    provs = [p for p in provs if isinstance(p, dict)]
    if not provs:
        p_warn(t("reg_none"))
        return None
    for i, p in enumerate(provs, 1):
        print(f"  {ok(f'[{i}]')} {p.get('name', '?')}  {dim(str(p.get('description') or ''))}")
    s = (ask(t("reg_num", n=len(provs))).strip() or "0")
    try:
        sel = provs[int(s) - 1] if 1 <= int(s) <= len(provs) else None
    except ValueError:
        sel = None
    if not isinstance(sel, dict):
        return None
    return str(sel.get("name") or "")

def train_board_loop(sid, country, arrivi, station_name="?", provider=None):
    """Stesso loop per nazionale (provider=None) e regionali (provider=nome).

    Stesso formato tabella, stesse azioni; cambiano solo gli endpoint
    (TRAINBOARD vs .../api/{country}/trains/{provider} su betacloud).
    Ritorna None (= menu) o {"country":..., "provider":...}.
    """
    regional = bool(provider)
    base = reg_base(country, provider) if regional else None
    push_recent("recent_regstations" if regional else "recent_stations",
                {"name": station_name, "sid": sid, "country": country,
                 **({"provider": provider} if regional else {})})
    if not regional:
        save_state({"last_board": {"sid": sid, "country": country,
                                   "arrivi": bool(arrivi), "name": station_name}})
    opt2 = t("opt_provider") if regional else t("opt_country")
    page = 0
    while True:
        if regional:
            board = reg_board(country, provider, sid, arrivi) or []
        else:
            board = train_board(sid, country, arrivi, page=page) or []
        other = t("to_arr") if not arrivi else t("to_dep")
        nxt = (ask("\n" + t("board_menu", opt2=opt2, other=other) + " [N=Next, P=Prev]") .strip() or "R")
        if nxt.lower() == "r":
            continue
        if nxt.lower() == "n":
            page += 1
            continue
        if nxt.lower() == "p":
            page = max(0, page - 1)
            continue
        if nxt == "3":
            arrivi = not arrivi
            if not regional:
                save_state({"last_board": {"sid": sid, "country": country,
                                           "arrivi": bool(arrivi),
                                           "name": station_name}})
        elif nxt in ("4", "5"):
            row = pick_board_row(board)
            if row is None:
                continue
            trip_id = str(row.get("tripId") or "")
            if nxt == "5":
                if not trip_id:
                    p_warn(t("no_trip_row"))
                    continue
                open_timeline_gui(trip_id, country,
                                  trip_base=base, board_base=base)
                continue
            if regional:
                stops = [x for x in (row.get("stops") or []) if isinstance(x, dict)]
                if stops:
                    p_title(f"🏳️ {train_label(row.get('line'), row.get('tripNumber'))} → "
                            f"{row.get('destination') or ''}")
                    print_timeline(stops)
                elif trip_id:
                    reg_trip(country, provider, trip_id)
                else:
                    p_warn(t("no_trip_row"))
            elif trip_id:
                train_trip(trip_id, country)
            else:
                num = str(row.get("tripNumber") or row.get("trainNumber") or "")
                if not num:
                    p_warn(t("no_trip_row"))
                    continue
                train_details(num, sid, country)
        elif nxt == "2":
            if regional:
                new_prov = pick_regional_provider(country)
                if new_prov:
                    return {"country": country, "provider": new_prov}
            else:
                return {"country": pick_country(), "provider": None}
        elif nxt == "0":
            return None
        else:
            return {"country": country, "provider": provider if regional else None}

def simple_train():
    country = pick_country()
    while True:
        rec = get_recent("recent_stations")
        if rec:
            print(f"\n  {dim(t('recents'))}")
            for i, e in enumerate(rec, 1):
                print(f"  {c_train(f'[R{i}]')} {e.get('name')}  "
                      f"{dim(str(e.get('sid')) + ' · ' + str(e.get('country')))}")
        q = ask("\n" + t("train_search_prompt"))
        if not q or q.strip() == "0":
            return
        q = q.strip()
        if q.lower().startswith("r") and q[1:].isdigit():
            idx = int(q[1:]) - 1
            if 0 <= idx < len(rec):
                e = rec[idx]
                m = ask(t("dep_arr")).strip() or "1"
                r = train_board_loop(str(e.get("sid")), str(e.get("country") or country),
                                     m == "2", str(e.get("name") or "?"))
                if r is None:
                    return
                country = r.get("country", country)
                continue
            p_warn(t("recent_invalid"))
            continue
        pick = station_search_pick(q, country)
        if pick is None:
            continue
        sid, name = pick
        m = ask(t("dep_arr")).strip() or "1"
        r = train_board_loop(sid, country, m == "2", name)
        if r is None:
            return
        country = r.get("country", country)

def simple_bus():
    try:
        provs = fetch_providers()
    except Exception as e:
        return p_err(f"Errore providers: {e}")
    if not provs:
        return p_warn("Nessun provider.")
    last_prov = str(app_state().get("bus_provider") or "")
    for i, p in enumerate(provs, 1):
        mark = " ←" if str(p.get("name", "")) == last_prov else ""
        print(f"  {c_bus(f'[{i}]')} {p.get('name', '?')}  {dim(provider_country(p))}{mark}")
    dflt = next((str(i) for i, p in enumerate(provs, 1)
                 if str(p.get("name", "")) == last_prov), "1")
    s = ask(t("bus_prov_title") + f"[{dflt}]: ").strip() or dflt
    try:
        sel = provs[int(s) - 1]
    except (ValueError, IndexError):
        sel = provs[0]
    provider = str(sel.get("name"))
    country = provider_country(sel)
    save_state({"bus_provider": provider})
    p_info(f"Provider: {provider} [{country}] — scarico fermate…")
    try:
        _, _, stops = fetch_bus_stops(provider, country)
    except Exception as e:
        return p_err(f"Errore fermate: {e}")
    p_ok(f"{len(stops)} fermate caricate.")
    stop_index = {x.get("stopId"): x for x in stops if x.get("stopId")}
    while True:
        rec = get_recent("recent_busstops")
        rec = [e for e in rec if e.get("provider") == provider][:5]
        if rec:
            print(f"\n  {dim(t('recents'))}")
            for i, e in enumerate(rec, 1):
                print(f"  {c_bus(f'[R{i}]')} {e.get('name')}  {dim(str(e.get('stop_id')))}")
        q = ask("\n" + t("bus_stop_prompt"))
        if not q or q.strip() == "0":
            return
        q = q.strip()
        stop_id, stop_name = None, None
        if q.lower().startswith("r") and q[1:].isdigit():
            idx = int(q[1:]) - 1
            if 0 <= idx < len(rec):
                stop_id = str(rec[idx].get("stop_id"))
                stop_name = str(rec[idx].get("name") or stop_id)
            else:
                p_warn(t("recent_invalid"))
                continue
        elif q in stop_index:
            stop_id = q
            stop_name = str(stop_index[q].get("stopName") or q)
        else:
            found = [x for x in stops
                     if q.lower() in str(x.get("stopName") or "").lower()
                     or q in str(x.get("stopId") or "")][:10]
            if not found:
                p_warn("Nessuna fermata trovata, riprova.")
                continue
            by_id = {x.get("stopId"): x for x in found}
            if q in by_id:
                stop_id = q
                stop_name = str(by_id[q].get("stopName") or q)
            else:
                for i, x in enumerate(found, 1):
                    print(f"  {c_bus(f'[{i}]')} {x.get('stopName')}  {dim(x.get('stopId'))}")
            s = ask(t("bus_stop_pick")).strip()
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
                p_warn(t("invalid_num"))
                continue
            stop_id = str(choice.get("stopId"))
            stop_name = str(choice.get("stopName") or stop_id)
        push_recent("recent_busstops",
                    {"name": stop_name, "stop_id": stop_id, "provider": provider})
        while True:
            bus_departures(provider, stop_id, country)
            nxt = (ask("\n" + t("bus_board_menu")).strip() or "R")
            if nxt.lower() == "r":
                continue
            elif nxt == "0":
                return
            else:
                break

def simple_fly():
    while True:
        q = ask("\n" + t("fly_prompt"))
        if not q or q.strip() == "0":
            return
        if len(q.strip()) < 2:
            p_warn(t("fly_short"))
            continue
        if len(q.strip()) == 3 and q.strip().isalpha():
            iata = q.strip().upper()
            m = ask(t("dep_arr")).strip() or "1"
            arrivi = (m == "2")
            while True:
                airport(iata, arrivi)
                other = t("to_arr") if not arrivi else t("to_dep")
                nxt = (ask("\n" + t("fly_menu", o=other)).strip() or "R")
                if nxt.lower() == "r":
                    continue
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
        m = ask(t("dep_arr")).strip() or "1"
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
        print(f"\n{title(t('menu_title'))}")
        print(f"  {c_train('1)')} {t('m_simple')}")
        print(f"  {c_bus('2)')} {t('m_commands')}")
        print(f"  {paint('3)', M)} {t('m_advanced')}")
        print(f"  {info('4)')} {t('m_guide')}")
        print(f"  {ok('5)')} {t('m_fav')}")
        print(f"  {paint('6)', B)} {t('m_account')}")
        print(f"  {paint('7)', C_)} {t('m_config')}")
        print(f"  {dim('0) ' + t('m_exit'))}")
        nick = (session().get("user") or {}).get("nickname")
        lb = app_state().get("last_board") or {}
        ctx = t("m_ctx_country", c=last_country())
        if nick:
            ctx += f" · {nick}"
        if lb.get("sid"):
            ctx += " · " + t("m_ctx_last", name=lb.get("name"), sid=lb.get("sid"))
        print(f"  {dim(ctx + ' ' + t('m_ctx_hint'))}")
        print(f"  {dim('lingua = ' + '/'.join(LANGS))}")
        c = ask("\n" + t("m_choice")).strip()
        if c == "1":
            simple_mode()
        elif c == "2":
            commands_mode()
        elif c == "3":
            advanced_menu()
        elif c == "4" or c.lower() in ("help", "aiuto", "guida", "?", "aide", "hilfe"):
            commands_guide()
        elif c == "5":
            favorites_section()
        elif c == "6":
            account_section()
        elif c == "7":
            config_section()
        elif c.lower() in ("lingua", "lang", "language", "sprache", "config"):
            pick_language()
        elif c.lower() == "ultimo" and lb.get("sid"):
            train_board_loop(str(lb["sid"]), str(lb.get("country") or last_country()),
                             bool(lb.get("arrivi")), str(lb.get("name") or "?"))
        elif c.lower() == "ultimo":
            p_warn(t("m_last_none"))
        elif c.split(" ", 1)[0].lower() in COMMANDS:
            run_direct(c)
        elif c in ("0", "q", "exit"):
            p_ok(t("m_bye"))
            return
        else:
            p_warn(t("m_invalid"))

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
    p.add_argument("--lang", choices=["it", "en", "de", "fr", "auto"],
                   help="lingua interfaccia (salvata, auto = sistema)")
    sub = p.add_subparsers(dest="cmd")

    t = sub.add_parser("treni", aliases=["trains"], help="orari treni / train schedules")
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

    b = sub.add_parser("bus", aliases=["buses"], help="bus urbani / urban buses")
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

    v = sub.add_parser("voli", aliases=["flights"], help="voli e aeroporti / flights and airports")
    v.add_argument("--area", action="store_true", help="radar sull'Italia")
    v.add_argument("--aeroporto", metavar="IATA")
    v.add_argument("--arrivi", action="store_true")
    v.add_argument("--cerca", metavar="QUERY", help="autosuggest aeroporti Skyscanner")

    f = sub.add_parser("flixbus", aliases=["flixbuses"], help="rete Flixbus / Flixbus network")
    f.add_argument("--stazioni")
    f.add_argument("--partenze", metavar="STATION_ID")
    f.add_argument("--trip", metavar="TRIP_ID")

    r = sub.add_parser("regionali", aliases=["regional"], help="provider regionali / regional providers")
    r.add_argument("--lista", metavar="PAESE", help="provider regionali per paese")
    r.add_argument("--stazioni", nargs=2, metavar=("PAESE", "PREFIX"))
    r.add_argument("--cerca", default="", help="filtro stazioni regionali")
    r.add_argument("--partenze", nargs=3, metavar=("PAESE", "PREFIX", "STATION_ID"))
    r.add_argument("--arrivi", action="store_true")
    r.add_argument("--news", nargs=2, metavar=("PAESE", "PREFIX"))
    r.add_argument("--trip", nargs=3, metavar=("PAESE", "PREFIX", "TRIP_ID"))

    s = sub.add_parser("strade", aliases=["roads"], help="autostrade / highways")
    s.add_argument("--news", action="store_true")
    s.add_argument("--pedaggi", action="store_true")
    s.add_argument("--servizi", action="store_true")
    s.add_argument("--paese", default="it")
    s.add_argument("--highways", default="")
    s.add_argument("--highway", default="")
    m = sub.add_parser("meteo", aliases=["weather"], help="meteo / weather")
    m.add_argument("--cerca", metavar="CITTA")
    m.add_argument("--ora", nargs=3, metavar=("CITTA", "LAT", "LON"))
    sc = sub.add_parser("social", aliases=["socials"], help="bacheca viaggiatori / travelers board")
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
    au = sub.add_parser("auth", aliases=["authenticate"], help="login e profilo / login and profile")
    au.add_argument("--register", nargs=3, metavar=("EMAIL", "PW", "NICK"))
    au.add_argument("--disponibile", metavar="NICK")
    au.add_argument("--profilo", metavar="NICK")
    au.add_argument("--elimina", metavar="PW")
    au.add_argument("--stato", action="store_true")
    au.add_argument("--logout", action="store_true")
    fv = sub.add_parser("preferiti", aliases=["favorites"], help="preferiti / favorites")
    fv.add_argument("--sync", action="store_true")
    fv.add_argument("--treno", nargs=3, metavar=("NUMERO", "ORIGINE", "DEST"))
    fv.add_argument("--fermata", nargs=2, metavar=("CODICE", "NOME"))
    fv.add_argument("--bus", nargs=2, metavar=("LINEA", "NOME"))
    fv.add_argument("--tipo", choices=["busStop", "trainStation", "airport"],
                    default="trainStation")
    fv.add_argument("--paese", metavar="PAESE")
    fv.add_argument("--provider", metavar="PROVIDER")
    fv.add_argument("--rimuovi", metavar="ID")
    fv.add_argument("--check", metavar="ID")

    cf = sub.add_parser("config", aliases=["configuration"], help="configurazione / configuration")
    cf.add_argument("--loghi", action="store_true")
    cf.add_argument("--lang", choices=["it", "en", "de", "fr", "auto"],
                    help="lingua preferita (auto = sistema)")

    of = sub.add_parser("offline", aliases=["offline_cache"], help="cache offline / offline cache")
    of.add_argument("--save", nargs=3, metavar=("TIPO", "ID", "FILE_JSON"))

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

    # Normalizzazione comandi (English -> Italian)
    cmd_map = {
        "trains": "treni", "buses": "bus", "flights": "voli",
        "flixbuses": "flixbus", "regional": "regionali", "roads": "strade",
        "weather": "meteo", "socials": "social", "authenticate": "auth",
        "favorites": "preferiti", "configuration": "config", "offline_cache": "offline"
    }
    if a.cmd in cmd_map:
        a.cmd = cmd_map[a.cmd]
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
            if a.sync: fav_sync()
            elif (a.cloud or a.lista or not any([a.treno, a.fermata, a.bus, a.rimuovi,
                                                 a.check, a.cloud, a.sync])): fav_list(cloud=a.cloud)
            elif a.treno: fav_add("train", {"number": a.treno[0], "origin": a.treno[1], "destination": a.treno[2], "name": f"Treno {a.treno[0]}"})
            elif a.fermata: fav_add("stop", {"code": a.fermata[0], "name": a.fermata[1],
                                             "stopType": a.tipo, "country": a.paese,
                                             "provider": a.provider})
            elif a.bus: fav_add("busLine", {"line": a.bus[0], "name": a.bus[1],
                                            "provider": a.provider or "bari"})
            elif a.rimuovi: fav_remove(a.rimuovi)
            elif a.check: fav_check(a.check)
            else: parser.parse_args(["preferiti", "--help"])
        elif a.cmd == "config":
            if a.stats_general: stats_general()
            elif a.stats_linee: stats_lines()
            elif a.loghi: train_logos()
            elif a.lang:
                if a.lang == "auto":
                    p_ok(t("cfg_auto_is", lang=LANG_NAMES.get(system_lang(), system_lang())))
                else:
                    p_ok(t("cfg_cur", lang=LANG_NAMES.get(a.lang, a.lang)))
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