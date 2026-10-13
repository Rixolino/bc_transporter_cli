# BC.Transporter · Terminal-CLI

*Read in: [Italiano](README.md) · [English](README.en.md) · [Français](README.fr.md)*

Terminal-Version der Flutter-App **BCTransporterMobileApp** — **dieselben Logiken und Endpunkte**, nutzbar in der Konsole mit **farbiger Ausgabe** und einem **Grafikfenster** für Zug-Timelines.

- 🟢 Züge = grün · 🟡 Busse = gelb · 🔵 Flüge = cyan · 🟣 FAL/Social = magenta
- Verspätungen: 🟢 pünktlich/zu früh · 🟡 <5 Min. · 🔴 ≥5 Min.
- 🌍 Oberfläche in 4 Sprachen (it/en/de/fr + automatisch vom System)
- ⭐ Favoriten bei Login mit der Datenbank synchronisiert (dieselben IDs wie die App)
- 📡 Verspätung von Bahnhofstafeln, wenn der Trip sie nicht liefert (wie das Sheet der App, mit Hysterese)
- 📍 Fraktionale Zugposition auf der Strecke, mit fahrendem Marker
- `bc_cli.py`: Basis nur Python-Stdlib · erweitertes Fenster mit CustomTkinter (+ Pillow), automatischer Tkinter-Fallback
- `bin/bc_cli.dart`: derselbe Port in purem Dart (`dart:io`+`dart:convert`)
- 🖥️ Kompilierbar zu einer einzigen `BC-Transporter.exe` (siehe unten)

## Voraussetzungen

- **Python 3** → `python bc_cli.py` (empfohlen, getestet mit 3.13)
- Erweiterte Grafik (empfohlen): `pip install customtkinter pillow` — sonst öffnet sich das Basisfenster
- *Alternative:* [Dart SDK](https://dart.dev/get-started) → `dart bin/bc_cli.dart` (dieselben Befehle)
- *Oder:* `dist/BC-Transporter.exe`, keine Runtime nötig

> Unter Windows **Windows Terminal** für Farben nutzen. Fallback: `--no-color`.

## Start

```bash
cd bc_transporter_cli
python bc_cli.py                        # interaktives Menü
python bc_cli.py --lang de              # deutsches Menü (gespeichert)
python bc_cli.py --lang auto            # Systemsprache (Standard)
python bc_cli.py --help
```

Hauptmenü:

| Taste | Was es tut |
|---|---|
| `1` | Einfacher Modus: Züge (erst **National / Regional**), Busse, Flüge, Flixbus — nur Tasten |
| `2` | Befehlsmodus (`bc:treni>` mit automatischem Präfix, `help` = Übersicht) |
| `3` | Erweitertes Menü (alle 12 Bereiche) |
| `4` / `help` | Übersicht aller Befehle |
| `5` | Favoriten: öffnet nach Typ (Zug→Timeline, Bahnhof→Tafel, Bus, Flughafen) |
| `6` | Konto (Status, Login, Registrierung, Nick, Logout, Löschen) |
| `7` | Konfig (bevorzugte Sprache: it/en/de/fr/auto) |
| *freier Text* | Bahnhofsname → Sofortsuche im aktuellen Land |
| `ultimo` | Öffnet die letzte Tafel erneut |
| `lingua` | Sprache unterwegs wechseln |

Eingebauter Komfort: merkt sich Land, Busanbieter, letzte Bahnhöfe/Haltestellen (`R1`, `R2`…), letzte Tafel; **Enter = aktualisieren** auf den Tafeln; Land per Enter = zuletzt verwendet (`?` = Liste).

## Sprachen

Dieselben 4 Sprachen wie die App (`l10n`: it/en/de/fr), italienischer Fallback bei fehlenden Schlüsseln:

```bash
python bc_cli.py --lang de              # speichert Deutsch
python bc_cli.py config --lang auto     # zurück zum System
```

Beim ersten Start automatisch vom System erkannt; `lingua` im Menü oder Eintrag `7` zum Wechseln.

## Beispiele (alle App-Logiken)

```bash
# ZÜGE (train_repository + Provider + Sheet: Suche, Tafel, Details, Trip,
#        Live-Karte, FAL, RFI direkt, Share, Match, Live, Track, Routing, Stats, Presence)
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
python bc_cli.py treni --categorie   # alle Live-Kategorien (Welt), farbig
python bc_cli.py treni --mappa <tripId> --paese IT   # grafische Timeline im Fenster

# Kategoriefarben (stabil, wertbasiert): Hochgeschwindigkeit = rot
# (FR, ICE, TGV…), Fernverkehr = gelb (IC, EC…), Regional = grün
# (REG, REX, RE…), S-Bahn = cyan (S), Bus = gelb, Tram/FAL = magenta.

# REGIONALE (gleiches Format wie national, Basis .../api/{country}/trains/{provider})
python bc_cli.py regionali --lista IT
python bc_cli.py regionali --stazioni IT trenord [--cerca milano]
python bc_cli.py regionali --partenze IT trenord <stationId> [--arrivi]
python bc_cli.py regionali --news IT trenord
python bc_cli.py regionali --trip IT trenord <tripId>

# BUSSE (bus_repository: Anbieter, paginierte Linien, Halte, Abfahrten, Fahrzeuge,
#      AMTAB-Routen, Realtime+Fallback, Trip-Stops, Route-Path, Offline-Paket)
python bc_cli.py bus --providers
python bc_cli.py bus --linee bari | --fermate bari | --veicoli bari
python bc_cli.py bus --partenze bari <stopId>
python bc_cli.py bus --soluzioni <fromStop> <toStop> --provider bari
python bc_cli.py bus --realtime <vehicleId> <tripId> --provider bari
python bc_cli.py bus --trip-stops <tripId> | --route-path <tripId> --provider bari
python bc_cli.py bus --static bari

# FLÜGE (plane_repository + Provider: Radar, Flughäfen, IATA-Autosuggest)
python bc_cli.py voli --area
python bc_cli.py voli --aeroporto BRI [--arrivi]
python bc_cli.py voli --cerca bari

# FLIXBUS
python bc_cli.py flixbus --stazioni "bari" | --partenze <id> | --trip <id>

# STRASSEN (roadway_service) + WETTER (weather_service: Geocoding, Open-Meteo)
python bc_cli.py strade --news [--paese it] [--highways A1]
python bc_cli.py strade --pedaggi | --servizi [--highway A1]
python bc_cli.py meteo --cerca roma | --ora Roma 41.9 12.5

# SOCIAL (social_repository + Presence Heartbeat/Leave)
python bc_cli.py social --feed | --topic <id> | --online | --leaderboard
python bc_cli.py social --publish <trainKey> <nick> | --send <id> <nick> <text>
python bc_cli.py social --like <id> <nick> | --delete <id> <nick> | --user <nick>

# AUTH (Web-auth_repository + Sitzung wie SessionService)
python bc_cli.py auth --login <email> <pw> | --register <e> <p> <nick>
python bc_cli.py auth --disponibile <nick> | --profilo <nick> | --stato | --logout

# FAVORITEN (dieselben IDs/Modelle wie die App; mit Login per API aus der DB)
python bc_cli.py preferiti --lista [--cloud] | --sync
python bc_cli.py preferiti --treno 5440 Bari Roma
python bc_cli.py preferiti --fermata S11119 "Bari Centrale" --tipo trainStation --paese IT
python bc_cli.py preferiti --bus 11 "Linea 11" --provider bari
python bc_cli.py preferiti --rimuovi <id> | --check <id>

# CONFIG (ApiService: 3x Retry + Fallback) + STATS + LOGOS + SPRACHE
python bc_cli.py config --show | --stats-general | --stats-linee | --loghi
python bc_cli.py config --lang <it|en|de|fr|auto>

# OFFLINE (dateibasierter OfflineSyncService)
python bc_cli.py offline --lista | --size | --save train <id> dati.json | --get train <id> | --clear
```

Zugländer: `IT FR DE CH AT ES GLOBAL`, `UK_LONDON` für London.

## Zug-Timeline-Fenster

Gleich für nationale und regionale Züge (nur die Basis-URL ändert sich), mit der Logik des Flutter-`train_details_sheet`:

- Kopf in Kategoriefarbe mit Betreiberlogo (mit Pillow/LANCZOS skaliert), weißes Status-Pill (`PÜNKTLICH` / `VERSPÄTUNG +n` / `FRÜHER -n`), Gleis, `● LIVE`, Zuschauer online
- Verspätung aus dem Trip, sonst **von den Tafeln kommender Stationen** (TripId-Match → Nummer+Ziel, 2-Bestätigungen-Hysterese) mit Quellenangabe (`VERSPÄTUNG VON …-TAFEL`)
- **Fraktionale Position**: HD-Zugmarker fährt entlang des Segments (Halt im Bahnhof = `HIER`), echte Prozent auf Balken und Karte (`Unterwegs · A → B · 48 %`)
- Timeline pro Halt: Ortszeiten, Gleis, `+n`/`-n` Verspätung, Zustände `NICHT ABGEFAHREN/HIER/UNTERWEGS/ANGEKOMMEN/ENTFALLEN`
- Aktionen: Statistik, Karte/Track, Link teilen (kopiert), Social, Offline speichern, Meldungen, Favorit (speichert TripId zum direkten Wiederöffnen), Länder-Match
- Chirurgischer Refresh (kein Flackern, Scroll bleibt), 30-s-Auto-Refresh, 15-s-Presence-Heartbeat, `LIVE AN/AUS`-Umschalter

## Favoriten: Erkennung

Dieselben IDs wie die App (`favorites_provider.dart`), App und CLI sehen also dieselben Favoriten:

| Typ | ID-Format |
|---|---|
| Halt | `{userId}_{busStop\|trainStation\|airport}_{code}[_{country}][_{provider}]` |
| Zug | `{userId}_train_{Nummer}_{Abfahrt}_{Ankunft}` |
| Buslinie | `{userId}_bus_{Anbieter}_{Linie}` |

Angemeldet → Datenbank via `GET/POST/DELETE /api/favorites` (Bearer); abgemeldet → lokale Datei `~/.bc_cli_favorites.json`. `--sync` lädt die DB erneut lokal.

## Exe bauen

```bash
pip install pyinstaller customtkinter pillow
python -m PyInstaller --clean --noconfirm --onefile --console --name BC-Transporter --collect-all customtkinter --collect-all darkdetect bc_cli.py
# → dist/BC-Transporter.exe (mit Konsole: die Ausgabe lebt dort)
```

Sitzung/Favoriten/Cache werden mit der Python-Version geteilt (dieselben Home-Dateien).

## Datenherkunft (Flutter-App-Dateien)

| CLI | Original-App-Datei |
|---|---|
| Basis `treni` | `features/train/data/repositories/train_repository.dart`, `presentation/providers/train_provider.dart` |
| `treni --match/--live/--track/--routing` | `presentation/widgets/train_details_sheet.dart`, `train_panel_content.dart`, `routing_search_screen.dart`, `pages/train_map_page.dart` |
| Timeline-Fenster (Tafel-Verspätung, fraktionaler Fortschritt, Marker) | `presentation/widgets/train_details_sheet.dart` (`refreshDelayFromUpcomingStations`, `_calcRouteProgress`, Marker-Timeline) |
| `treni --stats-* / --monitor / --cerca-treno` | `widgets/train_stats_screen.dart`, `railway_station_stats_screen.dart`, `train_panel_content.dart` |
| `treni --presence` + Fenster-LIVE | `core/services/train_presence_service.dart` |
| `regionali` (gleiches nationales Format) | `data/repositories/regional_providers_repository.dart`, `screens/regional_*`, `widgets/regional_train_details_sheet.dart` |
| `bus` | `features/bus/data/repositories/bus_repository.dart` (+ legacy `data/repositories/bus_repository.dart`) |
| `voli` | `features/plane/data/repositories/plane_repository.dart`, `presentation/providers/plane_provider.dart` |
| `strade` | `features/roadways/data/services/roadway_service.dart` |
| `meteo` | `core/services/weather_service.dart` |
| `social` | `features/social/data/repositories/social_repository.dart` |
| `auth` | `features/auth/repositories/auth_repository.dart`, `core/services/session_service.dart` |
| `preferiti` (IDs + DB-Sync) | `features/favorites/{repositories/favorites_repository.dart, models/favorite_*.dart, providers/favorites_provider.dart}`, `server.js` `/api/favorites` |
| `config --lang` / Sprachen | `core/services/runtime_localizations.dart`, `l10n/app_{it,en,de,fr}.arb` |
| `config` | `data/services/api_service.dart`, `core/api_constants.dart` |
| `offline` | `core/services/offline_sync_service.dart` |

Dieselben App-Regeln: `User-Agent: BC.Transporter`-Header, Retry+Backoff+Fallback für die Config, tolerantes Parsing (stürzt nie bei unerwarteten Payloads ab), Dual-Try für regionale Trips, Hysterese-Trip-Match, Haversine-Busankunftsschätzung, 5-s-Presence-Heartbeat (Fenster: 15 s).
