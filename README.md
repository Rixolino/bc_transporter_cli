# BC.Transporter · CLI Terminale

Versione da terminale dell'app Flutter **BCTransporterMobileApp** — **tutte le stesse logiche e gli stessi endpoint**, ma usabile in console con **output colorato**.

- 🟢 Treni = verde · 🟡 Bus = giallo · 🔵 Voli = ciano · 🟣 FAL/Social = magenta
- Ritardi: 🟢 in orario · 🟡 <5 min · 🔴 ≥5 min
- `bc_cli.py`: solo stdlib Python, zero dipendenze, già verificato live
- Finestra timeline: grafica avanzata con **CustomTkinter** (+ Pillow per i loghi)
  se installati (`pip install customtkinter pillow`), altrimenti fallback
  automatico alla finestra tkinter base — il resto resta stdlib
- `bin/bc_cli.dart`: stesso porting in Dart puro (stesse funzioni, `dart:io`+`dart:convert`)

## Requisiti

- **Python 3** → `python bc_cli.py` (consigliato, testato)
- *Alternativa:* [Dart SDK](https://dart.dev/get-started) → `dart bin/bc_cli.dart` (stessi comandi)

## Avvio

```bash
cd bc_transporter_cli
python bc_cli.py            # menu: ricorda paese/recenti, invio=aggiorna,
                            # scrivi una stazione per cercarla subito, "ultimo" riapre
python bc_cli.py --help
```

- **Tasto 1 · Modalità semplice**: prima scegli il trasporto coi tasti (1 treni, 2 bus, 3 voli, 4 flixbus), poi cerca col numero e vedi il tabellone con tasto 1 partenze / 2 arrivi. Solo tasti, niente sintassi.
- **Tasto 2 · Modalità comandi**: scegli il trasporto per il prefisso automatico (`bc:treni>`), poi scrivi solo gli argomenti (`--partenze S11119 --paese IT`) oppure il comando completo.
- **Tasto 3 · Menu avanzato**: tutte le 12 aree (bus, voli, regionali, strade, meteo, social, auth, preferiti, config, offline).

> Su Windows usa **Windows Terminal** per i colori. Fallback: `--no-color`.

## Esempi (tutte le logiche dell'app)

```bash
# TRENI (train_repository + provider + sheet: cerca, tabellone, dettagli, trip,
#        mappa live, FAL, diretta RFI, share, match, live, track, routing, stats, presence)
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
python bc_cli.py treni --categorie   # tutte le categorie live (mondo), colorate
python bc_cli.py treni --mappa <tripId> --paese IT   # timeline grafica in finestra (logo categoria)

# Colori categoria (stabili, basati sul valore): alta velocità = rosso
# (FR, ICE, TGV…), lunga percorrenza = giallo (IC, EC…), regionali = verde
# (REG, REX, RE…), suburbane = ciano (S), bus = giallo, tram/FAL = magenta.

# REGIONALI (regional_providers_repository + screens: lista, stazioni, tabellone, news, trip dual-try)
python bc_cli.py regionali --lista IT
python bc_cli.py regionali --stazioni IT it/trains/trenord [--cerca milano]
python bc_cli.py regionali --partenze IT it/trains/trenord <stationId> [--arrivi]
python bc_cli.py regionali --news IT it/trains/trenord
python bc_cli.py regionali --trip IT it/trains/trenord <tripId>

# BUS (bus_repository: providers, linee paginate, fermate, partenze, veicoli,
#      soluzioni AMTAB, realtime+fallback, trip-stops, route-path, pacchetto offline con progress)
python bc_cli.py bus --providers
python bc_cli.py bus --linee bari | --fermate bari | --veicoli bari
python bc_cli.py bus --partenze bari <stopId>
python bc_cli.py bus --soluzioni <fromStop> <toStop> --provider bari
python bc_cli.py bus --realtime <vehicleId> <tripId> --provider bari
python bc_cli.py bus --trip-stops <tripId> | --route-path <tripId> --provider bari
python bc_cli.py bus --static bari

# VOLI (plane_repository + provider: radar, aeroporti, autosuggest IATA)
python bc_cli.py voli --area
python bc_cli.py voli --aeroporto BRI [--arrivi]
python bc_cli.py voli --cerca bari

# FLIXBUS
python bc_cli.py flixbus --stazioni "bari" | --partenze <id> | --trip <id>

# STRADE (roadway_service) + METEO (weather_service: geocoding, open-meteo, fallback Roma)
python bc_cli.py strade --news [--paese it] [--highways A1]
python bc_cli.py strade --pedaggi | --servizi [--highway A1]
python bc_cli.py meteo --cerca roma | --ora Roma 41.9 12.5

# SOCIAL (social_repository + presence heartbeat/leave)
python bc_cli.py social --feed | --topic <id> | --online | --leaderboard
python bc_cli.py social --publish <trainKey> <nick> | --send <id> <nick> <testo>
python bc_cli.py social --like <id> <nick> | --delete <id> <nick> | --user <nick>

# AUTH (auth_repository web + sessione come SessionService)
python bc_cli.py auth --login <email> <pw> | --register <e> <p> <nick>
python bc_cli.py auth --disponibile <nick> | --profilo <nick> | --stato | --logout

# PREFERITI (stessi id/tipi dei modelli FavoriteItem/Stop/Train/BusLine;
# se loggato usa il database via API come l'app, altrimenti file locale)
python bc_cli.py preferiti --lista [--cloud] | --sync
python bc_cli.py preferiti --treno 5440 Bari Roma
python bc_cli.py preferiti --fermata S11119 "Bari Centrale" --tipo trainStation --paese IT
python bc_cli.py preferiti --bus 11 "Linea 11" --provider bari
python bc_cli.py preferiti --rimuovi <id> | --check <id>

# CONFIG (ApiService: retry 3x + fallback) + STATS + LOGHI + OFFLINE (OfflineSyncService su file)
python bc_cli.py config --show | --stats-general | --stats-linee | --loghi
python bc_cli.py offline --lista | --size | --save train <id> dati.json | --get train <id> | --clear
```

Paesi treni: `IT FR DE CH AT ES GLOBAL`, `UK_LONDON` per Londra.

## Origine dati (file dell'app Flutter)

| CLI | File app originale |
|---|---|
| `treni` base | `features/train/data/repositories/train_repository.dart`, `presentation/providers/train_provider.dart` |
| `treni --match/--live/--track/--routing` | `presentation/widgets/train_details_sheet.dart`, `train_panel_content.dart`, `routing_search_screen.dart`, `pages/train_map_page.dart` |
| `treni --stats-* / --monitor / --cerca-treno` | `widgets/train_stats_screen.dart`, `railway_station_stats_screen.dart`, `train_panel_content.dart` |
| `treni --presence` | `core/services/train_presence_service.dart` |
| `regionali` | `data/repositories/regional_providers_repository.dart`, `screens/regional_*`, `widgets/regional_train_details_sheet.dart` |
| `bus` | `features/bus/data/repositories/bus_repository.dart` (+ legacy `data/repositories/bus_repository.dart`) |
| `voli` | `features/plane/data/repositories/plane_repository.dart`, `presentation/providers/plane_provider.dart` |
| `strade` | `features/roadways/data/services/roadway_service.dart` |
| `meteo` | `core/services/weather_service.dart` |
| `social` | `features/social/data/repositories/social_repository.dart` |
| `auth` | `features/auth/repositories/auth_repository.dart`, `core/services/session_service.dart` |
| `preferiti` | `features/favorites/repositories/favorites_repository.dart`, `models/favorite_*.dart` |
| `config` | `data/services/api_service.dart`, `core/api_constants.dart` |
| `offline` | `core/services/offline_sync_service.dart` |

Stesse regole dell'app: header `User-Agent: BC.Transporter`, retry+backoff+fallback per la config, parsing tollerante (mai crash su payload inattesi), dual-try per i trip regionali, match trip con isteresi, stima arrivi bus con Haversine, id preferiti `{userId}_{tipo}_{codice}`, heartbeat presence ogni 5s.
