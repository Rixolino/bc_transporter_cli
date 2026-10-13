# BC.Transporter · CLI Terminale

*Leggimi in: [English](README.en.md) · [Deutsch](README.de.md) · [Français](README.fr.md)*

Versione da terminale dell'app Flutter **BCTransporterMobileApp** — **tutte le stesse logiche e gli stessi endpoint**, ma usabile in console con **output colorato** e una **finestra grafica** per la timeline dei treni.

- 🟢 Treni = verde · 🟡 Bus = giallo · 🔵 Voli = ciano · 🟣 FAL/Social = magenta
- Ritardi: 🟢 in orario/anticipi · 🟡 <5 min · 🔴 ≥5 min
- 🌍 Interfaccia in 4 lingue (it/en/de/fr + automatica dal sistema)
- ⭐ Preferiti sincronizzati col database quando fai login (stessi id dell'app)
- 📡 Ritardo pescato dalle bacheche di stazione quando il trip non lo dà (come la sheet dell'app, con isteresi)
- 📍 Posizione frazionaria del treno lungo la tratta, con marker in movimento
- `bc_cli.py`: base solo stdlib Python · finestra avanzata con CustomTkinter (+ Pillow), fallback tkinter automatico
- `bin/bc_cli.dart`: stesso porting in Dart puro (`dart:io`+`dart:convert`)
- 🖥️ Compilabile in `BC-Transporter.exe` singolo (vedi sotto)

## Requisiti

- **Python 3** → `python bc_cli.py` (consigliato, testato su 3.13)
- Grafica avanzata (consigliata): `pip install customtkinter pillow` — senza, si apre la finestra base
- *Alternativa:* [Dart SDK](https://dart.dev/get-started) → `dart bin/bc_cli.dart` (stessi comandi)
- *Oppure:* `dist/BC-Transporter.exe`, nessun runtime richiesto

> Su Windows usa **Windows Terminal** per i colori. Fallback: `--no-color`.

## Avvio

```bash
cd bc_transporter_cli
python bc_cli.py                        # menu interattivo
python bc_cli.py --lang en              # menu in inglese (salvata)
python bc_cli.py --lang auto            # lingua di sistema (default)
python bc_cli.py --help
```

Menu principale:

| Tasto | Cosa fa |
|---|---|
| `1` | Modalità semplice: treni ( rivolgiti a **Nazionale / Regionale**), bus, voli, flixbus — solo tasti |
| `2` | Modalità comandi (`bc:treni>` con prefisso automatico, `help` = guida) |
| `3` | Menu avanzato (tutte le 12 aree) |
| `4` / `help` | Guida di tutti i comandi |
| `5` | Preferiti: apre per tipo (treno→timeline, stazione→tabellone, bus, aeroporto) |
| `6` | Account (stato, login, registrazione, nick, logout, eliminazione) |
| `7` | Config (lingua preferita: it/en/de/fr/auto) |
| *testo libero* | Nome stazione → ricerca immediata nel paese attuale |
| `ultimo` | Riapre l'ultimo tabellone |
| `lingua` | Cambio lingua al volo |

Comodità integrate: ricorda paese, provider bus, stazioni/fermate recenti (`R1`, `R2`…), ultimo tabellone; **invio = aggiorna** nei tabelloni; paese con invio = ultimo usato (`?` = lista).

## Lingue

Stesse 4 lingue dell'app (`l10n`: it/en/de/fr), fallback italiano per le chiavi mancanti:

```bash
python bc_cli.py --lang de              # salva il tedesco
python bc_cli.py config --lang auto     # torna al sistema
```

Rilevamento automatico dal sistema al primo avvio; `lingua` nel menu o voce `7` per cambiare.

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
python bc_cli.py treni --mappa <tripId> --paese IT   # timeline grafica in finestra

# Colori categoria (stabili, basati sul valore): alta velocità = rosso
# (FR, ICE, TGV…), lunga percorrenza = giallo (IC, EC…), regionali = verde
# (REG, REX, RE…), suburbane = ciano (S), bus = giallo, tram/FAL = magenta.

# REGIONALI (stesso formato del nazionale, base .../api/{country}/trains/{provider})
python bc_cli.py regionali --lista IT
python bc_cli.py regionali --stazioni IT trenord [--cerca milano]
python bc_cli.py regionali --partenze IT trenord <stationId> [--arrivi]
python bc_cli.py regionali --news IT trenord
python bc_cli.py regionali --trip IT trenord <tripId>

# BUS (bus_repository: providers, linee paginate, fermate, partenze, veicoli,
#      soluzioni AMTAB, realtime+fallback, trip-stops, route-path, pacchetto offline)
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

# STRADE (roadway_service) + METEO (weather_service: geocoding, open-meteo)
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

# PREFERITI (stessi id/modelli dell'app; col login usa il database via API)
python bc_cli.py preferiti --lista [--cloud] | --sync
python bc_cli.py preferiti --treno 5440 Bari Roma
python bc_cli.py preferiti --fermata S11119 "Bari Centrale" --tipo trainStation --paese IT
python bc_cli.py preferiti --bus 11 "Linea 11" --provider bari
python bc_cli.py preferiti --rimuovi <id> | --check <id>

# CONFIG (ApiService: retry 3x + fallback) + STATS + LOGHI + LINGUA
python bc_cli.py config --show | --stats-general | --stats-linee | --loghi
python bc_cli.py config --lang <it|en|de|fr|auto>

# OFFLINE (OfflineSyncService su file)
python bc_cli.py offline --lista | --size | --save train <id> dati.json | --get train <id> | --clear
```

Paesi treni: `IT FR DE CH AT ES GLOBAL`, `UK_LONDON` per Londra.

## Finestra timeline treni

Stessa per nazionali e regionali (cambia solo la base URL), con le logiche della `train_details_sheet` Flutter:

- Header in tinta categoria con logo vettore (ridimensionato con Pillow/LANCZOS), pill di stato bianca (`IN ORARIO` / `RITARDO +n` / `ANTICIPO -n`), binario, `● LIVE`, spettatori online
- Ritardo dal trip, altrimenti **dalle bacheche delle prossime fermate** (match tripId → numero+destinazione, isteresi a 2 conferme) con fonte indicata (`RITARDO DA BACHECA …`)
- **Posizione frazionaria**: marker-treno HD che scorre lungo il segmento (fermo in stazione = `QUI`), percentuale reale su barra e card (`In viaggio · A → B · 48%`)
- Timeline per fermata: orari locali, binario, ritardo `+n`/`-n`, stati `NON PARTITO/QUI/IN VIAGGIO/ARRIVATO/SOPPRESSA`
- Azioni: statistiche, mappa/track, condivisione link (copiato), social, salvataggio offline, avvisi, preferito (salva tripId per riapertura diretta), match multi-paese
- Refresh chirurgico (niente flicker, scroll preservato), auto-refresh 30s, heartbeat presence 15s, toggle `LIVE ON/OFF`

## Preferiti: riconoscimento

Stessi id dell'app (`favorites_provider.dart`), quindi app e CLI vedono gli stessi preferiti:

| Tipo | Formato id |
|---|---|
| Fermata | `{userId}_{busStop\|trainStation\|airport}_{code}[_{country}][_{provider}]` |
| Treno | `{userId}_train_{numero}_{partenza}_{arrivo}` |
| Linea bus | `{userId}_bus_{provider}_{linea}` |

Loggato → database via `GET/POST/DELETE /api/favorites` (Bearer); non loggato → file locale `~/.bc_cli_favorites.json`. `--sync` riscarica il DB in locale.

## Compilare l'exe

```bash
pip install pyinstaller customtkinter pillow
python -m PyInstaller --clean --noconfirm --onefile --console --name BC-Transporter --collect-all customtkinter --collect-all darkdetect bc_cli.py
# → dist/BC-Transporter.exe (con console: l'output vive lì)
```

Sessione/preferiti/cache condivisi con la versione Python (stessi file in home).

## Origine dati (file dell'app Flutter)

| CLI | File app originale |
|---|---|
| `treni` base | `features/train/data/repositories/train_repository.dart`, `presentation/providers/train_provider.dart` |
| `treni --match/--live/--track/--routing` | `presentation/widgets/train_details_sheet.dart`, `train_panel_content.dart`, `routing_search_screen.dart`, `pages/train_map_page.dart` |
| finestra timeline (ritardo bacheche, progresso frazionario, marker) | `presentation/widgets/train_details_sheet.dart` (`refreshDelayFromUpcomingStations`, `_calcRouteProgress`, timeline con marker) |
| `treni --stats-* / --monitor / --cerca-treno` | `widgets/train_stats_screen.dart`, `railway_station_stats_screen.dart`, `train_panel_content.dart` |
| `treni --presence` + LIVE finestra | `core/services/train_presence_service.dart` |
| `regionali` (stesso formato nazionale) | `data/repositories/regional_providers_repository.dart`, `screens/regional_*`, `widgets/regional_train_details_sheet.dart` |
| `bus` | `features/bus/data/repositories/bus_repository.dart` (+ legacy `data/repositories/bus_repository.dart`) |
| `voli` | `features/plane/data/repositories/plane_repository.dart`, `presentation/providers/plane_provider.dart` |
| `strade` | `features/roadways/data/services/roadway_service.dart` |
| `meteo` | `core/services/weather_service.dart` |
| `social` | `features/social/data/repositories/social_repository.dart` |
| `auth` | `features/auth/repositories/auth_repository.dart`, `core/services/session_service.dart` |
| `preferiti` (id + sync DB) | `features/favorites/{repositories/favorites_repository.dart, models/favorite_*.dart, providers/favorites_provider.dart}`, `server.js` `/api/favorites` |
| `config --lang` / lingue | `core/services/runtime_localizations.dart`, `l10n/app_{it,en,de,fr}.arb` |
| `config` | `data/services/api_service.dart`, `core/api_constants.dart` |
| `offline` | `core/services/offline_sync_service.dart` |

Stesse regole dell'app: header `User-Agent: BC.Transporter`, retry+backoff+fallback per la config, parsing tollerante (mai crash su payload inattesi), dual-try per i trip regionali, match trip con isteresi, stima arrivi bus con Haversine, heartbeat presence ogni 5s (finestra: 15s).
