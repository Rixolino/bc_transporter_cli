# BC.Transporter · Terminal CLI

*Read in: [Italiano](README.md) · [Deutsch](README.de.md) · [Français](README.fr.md)*

Terminal version of the Flutter app **BCTransporterMobileApp** — **the same logic and endpoints**, usable from the console with **colored output** and a **graphical window** for train timelines.

- 🟢 Trains = green · 🟡 Buses = yellow · 🔵 Flights = cyan · 🟣 FAL/Social = magenta
- Delays: 🟢 on time/early · 🟡 <5 min · 🔴 ≥5 min
- 🌍 4-language UI (it/en/de/fr + automatic from the system)
- ⭐ Favorites synced with the database when logged in (same ids as the app)
- 📡 Delay taken from station boards when the trip doesn't provide it (like the app sheet, with hysteresis)
- 📍 Fractional train position along the route, with moving marker
- `bc_cli.py`: stdlib-only base · advanced window with CustomTkinter (+ Pillow), automatic tkinter fallback
- `bin/bc_cli.dart`: same port in pure Dart (`dart:io`+`dart:convert`)
- 🖥️ Builds to a single `BC-Transporter.exe` (see below)

## Requirements

- **Python 3** → `python bc_cli.py` (recommended, tested on 3.13)
- Advanced graphics (recommended): `pip install customtkinter pillow` — otherwise the base window opens
- *Alternative:* [Dart SDK](https://dart.dev/get-started) → `dart bin/bc_cli.dart` (same commands)
- *Or:* `dist/BC-Transporter.exe`, no runtime needed

> On Windows use **Windows Terminal** for colors. Fallback: `--no-color`.

## Start

```bash
cd bc_transporter_cli
python bc_cli.py                        # interactive menu
python bc_cli.py --lang en              # English menu (saved)
python bc_cli.py --lang auto            # system language (default)
python bc_cli.py --help
```

Main menu:

| Key | What it does |
|---|---|
| `1` | Simple mode: trains (ask **National / Regional**), buses, flights, flixbus — keys only |
| `2` | Command mode (`bc:treni>` with auto prefix, `help` = guide) |
| `3` | Advanced menu (all 12 areas) |
| `4` / `help` | Guide to all commands |
| `5` | Favorites: opens by type (train→timeline, station→board, bus, airport) |
| `6` | Account (status, login, register, nick, logout, delete) |
| `7` | Config (preferred language: it/en/de/fr/auto) |
| *free text* | Station name → instant search in the current country |
| `ultimo` | Reopens the last board |
| `lingua` | Switch language on the fly |

Built-in comfort: remembers country, bus provider, recent stations/stops (`R1`, `R2`…), last board; **enter = refresh** on boards; country defaults to last used (`?` = list).

## Languages

Same 4 languages as the app (`l10n`: it/en/de/fr), Italian fallback for missing keys:

```bash
python bc_cli.py --lang de              # saves German
python bc_cli.py config --lang auto     # back to system
```

Auto-detected from the system on first start; `lingua` in the menu or entry `7` to change.

## Examples (all app logic)

```bash
# TRAINS (train_repository + provider + sheet: search, board, details, trip,
#        live map, FAL, RFI direct, share, match, live, track, routing, stats, presence)
python bc_cli.py treni --cerca "bari"
python bc_cli.py treni --partenze S11119 --paese IT [--arrivi]
python bc_cli.py treni --treno 5440 --stazione S11119
python bc_cli.py treni --trip <tripId> --paese IT
python bc_cli.py treni --numero "FR" | --fal <id> | --diretta "bari"
python bc_cli.py treni --rfi <placeId> | --dettaglio-rfi 5440
python bc_cli.py treni --condividi <tripId> --paese IT | --apri-share <id>
python bc_cli.py treni --match <tripId> | --live | --track <tripId>
python bc_cli.py treni --routing Milano Roma --date 2026-10-20 --time 08:00
python bc_cli.py treni --stats-treno FR 9600 | --stats-stazione S11119 --period week
python bc_cli.py treni --monitor-check S11119 | --cerca-treno 9600 | --paesi
python bc_cli.py treni --presence live|recent|viewers|heartbeat --key <trainKey>
python bc_cli.py treni --categorie   # all live categories (world), colored
python bc_cli.py treni --mappa <tripId> --paese IT   # graphical timeline window

# Category colors (stable, value-based): high speed = red
# (FR, ICE, TGV…), long distance = yellow (IC, EC…), regionals = green
# (REG, REX, RE…), suburban = cyan (S), bus = yellow, tram/FAL = magenta.

# REGIONALS (same format as national, base .../api/{country}/trains/{provider})
python bc_cli.py regionali --lista IT
python bc_cli.py regionali --stazioni IT trenord [--cerca milano]
python bc_cli.py regionali --partenze IT trenord <stationId> [--arrivi]
python bc_cli.py regionali --news IT trenord
python bc_cli.py regionali --trip IT trenord <tripId>

# BUSES (bus_repository: providers, paged lines, stops, departures, vehicles,
#      AMTAB solutions, realtime+fallback, trip-stops, route-path, offline pack)
python bc_cli.py bus --providers
python bc_cli.py bus --linee bari | --fermate bari | --veicoli bari
python bc_cli.py bus --partenze bari <stopId>
python bc_cli.py bus --soluzioni <fromStop> <toStop> --provider bari
python bc_cli.py bus --realtime <vehicleId> <tripId> --provider bari
python bc_cli.py bus --trip-stops <tripId> | --route-path <tripId> --provider bari
python bc_cli.py bus --static bari

# FLIGHTS (plane_repository + provider: radar, airports, IATA autosuggest)
python bc_cli.py voli --area
python bc_cli.py voli --aeroporto BRI [--arrivi]
python bc_cli.py voli --cerca bari

# FLIXBUS
python bc_cli.py flixbus --stazioni "bari" | --partenze <id> | --trip <id>

# ROADS (roadway_service) + WEATHER (weather_service: geocoding, open-meteo)
python bc_cli.py strade --news [--paese it] [--highways A1]
python bc_cli.py strade --pedaggi | --servizi [--highway A1]
python bc_cli.py meteo --cerca roma | --ora Roma 41.9 12.5

# SOCIAL (social_repository + presence heartbeat/leave)
python bc_cli.py social --feed | --topic <id> | --online | --leaderboard
python bc_cli.py social --publish <trainKey> <nick> | --send <id> <nick> <text>
python bc_cli.py social --like <id> <nick> | --delete <id> <nick> | --user <nick>

# AUTH (web auth_repository + session like SessionService)
python bc_cli.py auth --login <email> <pw> | --register <e> <p> <nick>
python bc_cli.py auth --disponibile <nick> | --profilo <nick> | --stato | --logout

# FAVORITES (same ids/models as the app; with login uses the DB via API)
python bc_cli.py preferiti --lista [--cloud] | --sync
python bc_cli.py preferiti --treno 5440 Bari Roma
python bc_cli.py preferiti --fermata S11119 "Bari Centrale" --tipo trainStation --paese IT
python bc_cli.py preferiti --bus 11 "Linea 11" --provider bari
python bc_cli.py preferiti --rimuovi <id> | --check <id>

# CONFIG (ApiService: 3x retry + fallback) + STATS + LOGOS + LANGUAGE
python bc_cli.py config --show | --stats-general | --stats-linee | --loghi
python bc_cli.py config --lang <it|en|de|fr|auto>

# OFFLINE (file-based OfflineSyncService)
python bc_cli.py offline --lista | --size | --save train <id> dati.json | --get train <id> | --clear
```

Train countries: `IT FR DE CH AT ES GLOBAL`, `UK_LONDON` for London.

## Train timeline window

Same for national and regional trains (only the base URL changes), with the Flutter `train_details_sheet` logic:

- Category-colored header with operator logo (resized with Pillow/LANCZOS), white status pill (`ON TIME` / `DELAY +n` / `EARLY -n`), platform, `● LIVE`, online viewers
- Delay from the trip, otherwise **from upcoming stations' boards** (tripId match → number+destination, 2-confirmation hysteresis) with source shown (`DELAY FROM … BOARD`)
- **Fractional position**: HD train marker sliding along the segment (station dwell = `HERE`), real percentage on bar and card (`Traveling · A → B · 48%`)
- Per-stop timeline: local times, platform, `+n`/`-n` delay, `NOT DEPARTED/HERE/TRAVELING/ARRIVED/CANCELLED` states
- Actions: stats, map/track, link share (copied), social, offline save, alerts, favorite (saves tripId for direct reopen), cross-country match
- Surgical refresh (no flicker, scroll kept), 30s auto-refresh, 15s presence heartbeat, `LIVE ON/OFF` toggle

## Favorites: recognition

Same ids as the app (`favorites_provider.dart`), so app and CLI see the same favorites:

| Type | Id format |
|---|---|
| Stop | `{userId}_{busStop\|trainStation\|airport}_{code}[_{country}][_{provider}]` |
| Train | `{userId}_train_{number}_{departure}_{arrival}` |
| Bus line | `{userId}_bus_{provider}_{line}` |

Logged in → database via `GET/POST/DELETE /api/favorites` (Bearer); logged out → local file `~/.bc_cli_favorites.json`. `--sync` re-downloads the DB locally.

## Building the exe

```bash
pip install pyinstaller customtkinter pillow
python -m PyInstaller --clean --noconfirm --onefile --console --name BC-Transporter --collect-all customtkinter --collect-all darkdetect bc_cli.py
# → dist/BC-Transporter.exe (with console: output lives there)
```

Session/favorites/cache shared with the Python version (same home files).

## SmartScreen warning ("Unknown publisher")

The setup is not digitally signed: Windows blocks it until you click
**More info → Run anyway** (it's our own build, no risk).
Quick alternative:

```powershell
Unblock-File installer\out\BC-Transporter-Setup-1.0.0.exe   # removes the web block
```

Definitive fix for distribution: a paid **OV/EV code signing certificate**,
then `installer\sign.bat cert.pfx [password]` (needs Windows SDK `signtool`) —
signs exe + setup with timestamp. EV removes the warning immediately, OV after
the file builds reputation.

## Data origin (Flutter app files)

| CLI | Original app file |
|---|---|
| base `treni` | `features/train/data/repositories/train_repository.dart`, `presentation/providers/train_provider.dart` |
| `treni --match/--live/--track/--routing` | `presentation/widgets/train_details_sheet.dart`, `train_panel_content.dart`, `routing_search_screen.dart`, `pages/train_map_page.dart` |
| timeline window (board delay, fractional progress, marker) | `presentation/widgets/train_details_sheet.dart` (`refreshDelayFromUpcomingStations`, `_calcRouteProgress`, marker timeline) |
| `treni --stats-* / --monitor / --cerca-treno` | `widgets/train_stats_screen.dart`, `railway_station_stats_screen.dart`, `train_panel_content.dart` |
| `treni --presence` + window LIVE | `core/services/train_presence_service.dart` |
| `regionali` (same national format) | `data/repositories/regional_providers_repository.dart`, `screens/regional_*`, `widgets/regional_train_details_sheet.dart` |
| `bus` | `features/bus/data/repositories/bus_repository.dart` (+ legacy `data/repositories/bus_repository.dart`) |
| `voli` | `features/plane/data/repositories/plane_repository.dart`, `presentation/providers/plane_provider.dart` |
| `strade` | `features/roadways/data/services/roadway_service.dart` |
| `meteo` | `core/services/weather_service.dart` |
| `social` | `features/social/data/repositories/social_repository.dart` |
| `auth` | `features/auth/repositories/auth_repository.dart`, `core/services/session_service.dart` |
| `preferiti` (ids + DB sync) | `features/favorites/{repositories/favorites_repository.dart, models/favorite_*.dart, providers/favorites_provider.dart}`, `server.js` `/api/favorites` |
| `config --lang` / languages | `core/services/runtime_localizations.dart`, `l10n/app_{it,en,de,fr}.arb` |
| `config` | `data/services/api_service.dart`, `core/api_constants.dart` |
| `offline` | `core/services/offline_sync_service.dart` |

Same app rules: `User-Agent: BC.Transporter` header, retry+backoff+fallback for config, tolerant parsing (never crashes on unexpected payloads), dual-try for regional trips, hysteresis trip match, Haversine bus arrival estimates, 5s presence heartbeat (window: 15s).
