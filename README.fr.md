# BC.Transporter · CLI Terminal

*Leggimi in : [Italiano](README.md) · [English](README.en.md) · [Deutsch](README.de.md)*

Version terminal de l'app Flutter **BCTransporterMobileApp** — **mêmes logiques et mêmes endpoints**, utilisable en console avec **sortie colorée** et une **fenêtre graphique** pour les timelines de trains.

- 🟢 Trains = vert · 🟡 Bus = jaune · 🔵 Vols = cyan · 🟣 FAL/Social = magenta
- Retards : 🟢 à l'heure/en avance · 🟡 <5 min · 🔴 ≥5 min
- 🌍 Interface en 4 langues (it/en/de/fr + automatique du système)
- ⭐ Favoris synchronisés avec la base une fois connecté (mêmes ids que l'app)
- 📡 Retard pris aux tableaux des gares quand le trip ne le donne pas (comme la sheet de l'app, avec hystérésis)
- 📍 Position fractionnaire du train sur le parcours, avec marqueur mobile
- `bc_cli.py` : base stdlib Python uniquement · fenêtre avancée avec CustomTkinter (+ Pillow), repli tkinter automatique
- `bin/bc_cli.dart` : même portage en Dart pur (`dart:io`+`dart:convert`)
- 🖥️ Compilable en un seul `BC-Transporter.exe` (voir ci-dessous)

## Prérequis

- **Python 3** → `python bc_cli.py` (recommandé, testé en 3.13)
- Graphismes avancés (recommandé) : `pip install customtkinter pillow` — sinon la fenêtre de base s'ouvre
- *Alternative :* [Dart SDK](https://dart.dev/get-started) → `dart bin/bc_cli.dart` (mêmes commandes)
- *Ou :* `dist/BC-Transporter.exe`, aucun runtime requis

> Sous Windows utilisez **Windows Terminal** pour les couleurs. Repli : `--no-color`.

## Démarrage

```bash
cd bc_transporter_cli
python bc_cli.py                        # menu interactif
python bc_cli.py --lang fr              # menu en français (enregistré)
python bc_cli.py --lang auto            # langue système (défaut)
python bc_cli.py --help
```

Menu principal :

| Touche | Ce qu'elle fait |
|---|---|
| `1` | Mode simple : trains (**National / Régional** d'abord), bus, vols, flixbus — touches uniquement |
| `2` | Mode commandes (`bc:treni>` avec préfixe auto, `help` = guide) |
| `3` | Menu avancé (les 12 domaines) |
| `4` / `help` | Guide de toutes les commandes |
| `5` | Favoris : ouvre par type (train→timeline, gare→tableau, bus, aéroport) |
| `6` | Compte (état, login, inscription, pseudo, logout, suppression) |
| `7` | Config (langue préférée : it/en/de/fr/auto) |
| *texte libre* | Nom de gare → recherche immédiate dans le pays actuel |
| `ultimo` | Rouvre le dernier tableau |
| `lingua` | Changer de langue à la volée |

Confort intégré : mémorise pays, opérateur bus, gares/arrêts récents (`R1`, `R2`…), dernier tableau ; **entrée = actualiser** sur les tableaux ; pays = dernier utilisé par défaut (`?` = liste).

## Langues

Mêmes 4 langues que l'app (`l10n` : it/en/de/fr), repli italien si clé manquante :

```bash
python bc_cli.py --lang fr              # enregistre le français
python bc_cli.py config --lang auto     # retour au système
```

Détection auto du système au premier lancement ; `lingua` dans le menu ou entrée `7` pour changer.

## Exemples (toutes les logiques de l'app)

```bash
# TRAINS (train_repository + provider + sheet : recherche, tableau, détails, trip,
#        carte live, FAL, direct RFI, partage, match, live, track, routing, stats, presence)
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
python bc_cli.py treni --categorie   # toutes les catégories live (monde), colorées
python bc_cli.py treni --mappa <tripId> --paese IT   # timeline graphique en fenêtre

# Couleurs catégories (stables, par valeur) : grande vitesse = rouge
# (FR, ICE, TGV…), longue distance = jaune (IC, EC…), régionaux = vert
# (REG, REX, RE…), suburbains = cyan (S), bus = jaune, tram/FAL = magenta.

# RÉGIONAUX (même format que national, base .../api/{country}/trains/{provider})
python bc_cli.py regionali --lista IT
python bc_cli.py regionali --stazioni IT trenord [--cerca milano]
python bc_cli.py regionali --partenze IT trenord <stationId> [--arrivi]
python bc_cli.py regionali --news IT trenord
python bc_cli.py regionali --trip IT trenord <tripId>

# BUS (bus_repository : providers, lignes paginées, arrêts, départs, véhicules,
#      solutions AMTAB, realtime+repli, trip-stops, route-path, pack hors-ligne)
python bc_cli.py bus --providers
python bc_cli.py bus --linee bari | --fermate bari | --veicoli bari
python bc_cli.py bus --partenze bari <stopId>
python bc_cli.py bus --soluzioni <fromStop> <toStop> --provider bari
python bc_cli.py bus --realtime <vehicleId> <tripId> --provider bari
python bc_cli.py bus --trip-stops <tripId> | --route-path <tripId> --provider bari
python bc_cli.py bus --static bari

# VOLS (plane_repository + provider : radar, aéroports, autosuggest IATA)
python bc_cli.py voli --area
python bc_cli.py voli --aeroporto BRI [--arrivi]
python bc_cli.py voli --cerca bari

# FLIXBUS
python bc_cli.py flixbus --stazioni "bari" | --partenze <id> | --trip <id>

# ROUTES (roadway_service) + MÉTÉO (weather_service : geocoding, open-meteo)
python bc_cli.py strade --news [--paese it] [--highways A1]
python bc_cli.py strade --pedaggi | --servizi [--highway A1]
python bc_cli.py meteo --cerca roma | --ora Roma 41.9 12.5

# SOCIAL (social_repository + presence heartbeat/leave)
python bc_cli.py social --feed | --topic <id> | --online | --leaderboard
python bc_cli.py social --publish <trainKey> <nick> | --send <id> <nick> <texte>
python bc_cli.py social --like <id> <nick> | --delete <id> <nick> | --user <nick>

# AUTH (auth_repository web + session comme SessionService)
python bc_cli.py auth --login <email> <pw> | --register <e> <p> <nick>
python bc_cli.py auth --disponibile <nick> | --profilo <nick> | --stato | --logout

# FAVORIS (mêmes ids/modèles que l'app ; connecté = base via API)
python bc_cli.py preferiti --lista [--cloud] | --sync
python bc_cli.py preferiti --treno 5440 Bari Roma
python bc_cli.py preferiti --fermata S11119 "Bari Centrale" --tipo trainStation --paese IT
python bc_cli.py preferiti --bus 11 "Linea 11" --provider bari
python bc_cli.py preferiti --rimuovi <id> | --check <id>

# CONFIG (ApiService : retry 3x + repli) + STATS + LOGOS + LANGUE
python bc_cli.py config --show | --stats-general | --stats-linee | --loghi
python bc_cli.py config --lang <it|en|de|fr|auto>

# HORS-LIGNE (OfflineSyncService sur fichiers)
python bc_cli.py offline --lista | --size | --save train <id> dati.json | --get train <id> | --clear
```

Pays trains : `IT FR DE CH AT ES GLOBAL`, `UK_LONDON` pour Londres.

## Fenêtre timeline des trains

Identique pour nationaux et régionaux (seule l'URL de base change), avec la logique du `train_details_sheet` Flutter :

- En-tête couleur catégorie avec logo opérateur (redimensionné Pillow/LANCZOS), pastille blanche (`À L’HEURE` / `RETARD +n` / `EN AVANCE -n`), voie, `● LIVE`, spectateurs en ligne
- Retard du trip, sinon **des tableaux des prochaines gares** (match tripId → numéro+destination, hystérésis à 2 confirmations) avec source affichée (`RETARD VIA …`)
- **Position fractionnaire** : marqueur-train HD glissant sur le segment (arrêt en gare = `ICI`), vrai pourcentage sur barre et carte (`En route · A → B · 48 %`)
- Timeline par arrêt : heures locales, voie, retard `+n`/`-n`, états `NON PARTI/ICI/EN ROUTE/ARRIVÉ/SUPPRIMÉ`
- Actions : stats, carte/track, partage de lien (copié), social, sauvegarde hors-ligne, alertes, favori (sauve le tripId pour réouverture directe), match multi-pays
- Refresh chirurgical (pas de flicker, scroll conservé), auto-refresh 30 s, heartbeat presence 15 s, bascule `LIVE ON/OFF`

## Favoris : reconnaissance

Mêmes ids que l'app (`favorites_provider.dart`), app et CLI voient donc les mêmes favoris :

| Type | Format id |
|---|---|
| Arrêt | `{userId}_{busStop\|trainStation\|airport}_{code}[_{country}][_{provider}]` |
| Train | `{userId}_train_{numéro}_{départ}_{arrivée}` |
| Ligne bus | `{userId}_bus_{opérateur}_{ligne}` |

Connecté → base via `GET/POST/DELETE /api/favorites` (Bearer) ; déconnecté → fichier local `~/.bc_cli_favorites.json`. `--sync` retélécharge la base en local.

## Compiler l'exe

```bash
pip install pyinstaller customtkinter pillow
python -m PyInstaller --clean --noconfirm --onefile --console --name BC-Transporter --collect-all customtkinter --collect-all darkdetect bc_cli.py
# → dist/BC-Transporter.exe (avec console : la sortie vit là)
```

Session/favoris/cache partagés avec la version Python (mêmes fichiers home).

## Avertissement SmartScreen (« Éditeur inconnu »)

Le setup n'est pas signé numériquement : Windows le bloque jusqu'à
**Informations complémentaires → Exécuter quand même** (c'est notre propre build, aucun risque).
Alternative rapide :

```powershell
Unblock-File installer\out\BC-Transporter-Setup-1.0.0.exe   # retire le blocage web
```

Solution définitive pour distribuer : un certificat **code signing OV/EV**
(payant), puis `installer\sign.bat cert.pfx [password]` (nécessite `signtool` du Windows SDK) —
signe exe + setup avec horodatage. Avec EV l'avertissement disparaît aussitôt, avec OV
quand le fichier accumule de la réputation.

## Origine des données (fichiers de l'app Flutter)

| CLI | Fichier app d'origine |
|---|---|
| base `treni` | `features/train/data/repositories/train_repository.dart`, `presentation/providers/train_provider.dart` |
| `treni --match/--live/--track/--routing` | `presentation/widgets/train_details_sheet.dart`, `train_panel_content.dart`, `routing_search_screen.dart`, `pages/train_map_page.dart` |
| fenêtre timeline (retard tableaux, progrès fractionnaire, marqueur) | `presentation/widgets/train_details_sheet.dart` (`refreshDelayFromUpcomingStations`, `_calcRouteProgress`, timeline à marqueur) |
| `treni --stats-* / --monitor / --cerca-treno` | `widgets/train_stats_screen.dart`, `railway_station_stats_screen.dart`, `train_panel_content.dart` |
| `treni --presence` + LIVE fenêtre | `core/services/train_presence_service.dart` |
| `regionali` (même format national) | `data/repositories/regional_providers_repository.dart`, `screens/regional_*`, `widgets/regional_train_details_sheet.dart` |
| `bus` | `features/bus/data/repositories/bus_repository.dart` (+ legacy `data/repositories/bus_repository.dart`) |
| `voli` | `features/plane/data/repositories/plane_repository.dart`, `presentation/providers/plane_provider.dart` |
| `strade` | `features/roadways/data/services/roadway_service.dart` |
| `meteo` | `core/services/weather_service.dart` |
| `social` | `features/social/data/repositories/social_repository.dart` |
| `auth` | `features/auth/repositories/auth_repository.dart`, `core/services/session_service.dart` |
| `preferiti` (ids + sync DB) | `features/favorites/{repositories/favorites_repository.dart, models/favorite_*.dart, providers/favorites_provider.dart}`, `server.js` `/api/favorites` |
| `config --lang` / langues | `core/services/runtime_localizations.dart`, `l10n/app_{it,en,de,fr}.arb` |
| `config` | `data/services/api_service.dart`, `core/api_constants.dart` |
| `offline` | `core/services/offline_sync_service.dart` |

Mêmes règles que l'app : header `User-Agent: BC.Transporter`, retry+backoff+repli pour la config, parsing tolérant (jamais de crash sur payloads inattendus), double essai pour les trips régionaux, match trip avec hystérésis, estimation arrivées bus par Haversine, heartbeat presence 5 s (fenêtre : 15 s).
