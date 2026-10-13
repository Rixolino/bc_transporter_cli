// BC.Transporter — versione Terminale (Dart puro, zero dipendenze).
//
// Uso:
//   dart bin/bc_cli.dart                  -> menu interattivo colorato
//   dart bin/bc_cli.dart --help           -> ayuda comandi
//   dart bin/bc_cli.dart treni --cerca "bari" [--paese IT]
//   dart bin/bc_cli.dart treni --partenze <stationId> [--paese IT] [--arrivi]
//   dart bin/bc_cli.dart treni --treno <numero> --stazione <stationId> [--paese IT]
//   dart bin/bc_cli.dart treni --trip <tripId> [--paese IT]
//   dart bin/bc_cli.dart treni --numero <testo>            (cerca per numero in mappa live)
//   dart bin/bc_cli.dart treni --fal <stationId>           (Ferrovie Appulo Lucane)
//   dart bin/bc_cli.dart bus --providers
//   dart bin/bc_cli.dart bus --linee <provider> [--paese it]
//   dart bin/bc_cli.dart bus --fermate <provider> [--paese it]
//   dart bin/bc_cli.dart bus --partenze <provider> <stopId> [--paese it]
//   dart bin/bc_cli.dart bus --veicoli <provider> [--paese it]
//   dart bin/bc_cli.dart voli --area                        (voli sull'Italia)
//   dart bin/bc_cli.dart voli --aeroporto <IATA> [--arrivi]
//   dart bin/bc_cli.dart flixbus --stazioni "bari"
//   dart bin/bc_cli.dart flixbus --partenze <stationId>
//   dart bin/bc_cli.dart flixbus --trip <tripId>
//
// Opzioni globali: --paese <codice>  --no-color  --help
//
// Stessi endpoint dell'app Flutter (lib/core/api_constants.dart,
// features/train, bus, plane repositories). Solo dart:io + dart:convert.

import 'dart:async';
import 'dart:convert';
import 'dart:io';
import 'dart:math' as math;

// ---------------------------------------------------------------------------
// Colori ANSI
// ---------------------------------------------------------------------------

bool useColor = true;

class C {
  static const reset = '\x1B[0m';
  static const bold = '\x1B[1m';
  static const dim = '\x1B[2m';
  static const red = '\x1B[31m';
  static const green = '\x1B[32m';
  static const yellow = '\x1B[33m';
  static const blue = '\x1B[34m';
  static const magenta = '\x1B[35m';
  static const cyan = '\x1B[36m';
  static const white = '\x1B[37m';
  static const gray = '\x1B[90m';
  static const bgBlue = '\x1B[44m';
  static const bgGreen = '\x1B[42m';
  static const bgRed = '\x1B[41m';

  static String wrap(String s, String code) =>
      useColor ? '$code$s$reset' : s;

  static String b(String s) => wrap(s, bold);
  static String ok(String s) => wrap(s, green);
  static String err(String s) => wrap(s, red);
  static String warn(String s) => wrap(s, yellow);
  static String info(String s) => wrap(s, cyan);
  static String title(String s) => wrap(s, '$bold$blue');
  static String dim_(String s) => wrap(s, dim);
  static String bus(String s) => wrap(s, '$bold$yellow'); // bus = giallo
  static String train(String s) => wrap(s, '$bold$green'); // treni = verde
  static String plane(String s) => wrap(s, '$bold$cyan'); // aerei = ciano
  static String fal(String s) => wrap(s, '$bold$magenta'); // FAL = magenta
}

void printTitle(String s) => print('\n${C.title('━━ $s ━━')}');
void printOk(String s) => print('${C.ok('✔')} $s');
void printErr(String s) => print('${C.err('✘')} $s');
void printWarn(String s) => print('${C.warn('!')} $s');
void printInfo(String s) => print('${C.info('›')} $s');
void printDim(String s) => print(C.dim_(s));

// ---------------------------------------------------------------------------
// HTTP (dart:io, nessuna dipendenza esterna)
// ---------------------------------------------------------------------------

const String kBase = 'https://betacloud-transporter.is-cool.dev';
const String kTrainBoard = 'https://prod.cuzimmartin.dev/api';
const String kFlix = 'https://prod.cuzimmartin.dev/api/flixbus';
const Map<String, String> kHeaders = {'User-Agent': 'BC.Transporter'};

Future<dynamic> getJson(String url, {int timeoutSec = 15}) async {
  final client = HttpClient();
  try {
    final req = await client
        .getUrl(Uri.parse(url))
        .timeout(Duration(seconds: timeoutSec));
    kHeaders.forEach(req.headers.set);
    final res =
        await req.close().timeout(Duration(seconds: timeoutSec));
    final body = await res.transform(utf8.decoder).join();
    if (res.statusCode != 200) {
      throw HttpException('HTTP ${res.statusCode} su $url\n$body');
    }
    if (body.trim().isEmpty) return {};
    return json.decode(body);
  } finally {
    client.close(force: true);
  }
}

List<dynamic> asList(dynamic v) {
  if (v is List) return v;
  if (v is Map && v['data'] is List) return v['data'] as List;
  return [];
}

// ---------------------------------------------------------------------------
// Helpers formattazione
// ---------------------------------------------------------------------------

String fmtTime(dynamic t) {
  if (t == null) return '—';
  try {
    DateTime? dt;
    if (t is int) {
      dt = t < 100000000000
          ? DateTime.fromMillisecondsSinceEpoch(t * 1000)
          : DateTime.fromMillisecondsSinceEpoch(t);
    } else if (t is num) {
      final ms = (t < 1e11) ? (t * 1000).toInt() : t.toInt();
      dt = DateTime.fromMillisecondsSinceEpoch(ms);
    } else {
      dt = DateTime.tryParse(t.toString());
    }
    if (dt == null) return t.toString();
    final hh = dt.hour.toString().padLeft(2, '0');
    final mm = dt.minute.toString().padLeft(2, '0');
    return '$hh:$mm';
  } catch (_) {
    return t.toString();
  }
}

String delayBadge(dynamic d) {
  final n = d is int ? d : int.tryParse(d?.toString() ?? '0') ?? 0;
  if (n <= 0) return C.ok('in orario');
  if (n < 5) return C.warn('+$n min');
  return C.err('+$n min');
}

String shortStr(dynamic v, [int max = 34]) {
  final s = (v ?? '—').toString();
  return s.length <= max ? s : '${s.substring(0, max - 1)}…';
}

String? readInput(String prompt) {
  stdout.write(C.info(prompt));
  return stdin.readLineSync()?.trim();
}

// ---------------------------------------------------------------------------
// TRENI
// ---------------------------------------------------------------------------

Future<void> cmdTrainSearch(String q, String country) async {
  printTitle('🚂 Stazioni · "$q" [$country]');
  final url =
      '$kTrainBoard/${Uri.encodeComponent(country)}/stations?query=${Uri.encodeComponent(q)}&limit=10';
  printDim('GET $url');
  try {
    final data = await getJson(url);
    final list = asList(data);
    if (list.isEmpty) {
      printWarn('Nessuna stazione trovata.');
      return;
    }
    for (var i = 0; i < list.length; i++) {
      final e = list[i] is Map ? Map<String, dynamic>.from(list[i] as Map) : <String, dynamic>{};
      final id = e['id'] ?? e['stationId'] ?? '?';
      final name = e['name'] ?? e['stationName'] ?? '?';
      print('  ${C.train('[${i + 1}]')} ${C.b(name.toString())}  ${C.dim_('id=$id')}');
    }
    printDim('Usa l\'id con: treni --partenze <id> --paese $country');
  } catch (e) {
    printErr('Errore ricerca stazioni: $e');
  }
}

int vlen(String s) =>
    s.replaceAll(RegExp('\x1B\\[[0-9;]*m'), '').length;

String padV(String s, int w) {
  final p = w - vlen(s);
  return p <= 0 ? s : s + ' ' * p;
}

DateTime? parseUtc(dynamic t) {
  // ISO aware in UTC per stimare la posizione (come la versione Python).
  try {
    if (t == null) return null;
    if (t is num) {
      final ms = t < 1e11 ? (t * 1000).toInt() : t.toInt();
      return DateTime.fromMillisecondsSinceEpoch(ms, isUtc: true);
    }
    final s = '$t'.trim();
    if (s.isEmpty || s == '—') return null;
    return DateTime.tryParse(s);
  } catch (_) {
    return null;
  }
}

DateTime? stopEffTime(Map<String, dynamic> s) =>
    parseUtc(s['estimatedDeparture']) ??
    parseUtc(s['departure']) ??
    parseUtc(s['time']) ??
    parseUtc(s['estimatedArrival']) ??
    parseUtc(s['arrival']);

void printTimeline(List<dynamic> stops) {
  // Timeline verticale: ● partenza, ○ intermedie, ■ arrivo, ✖ soppressa
  // + 🚂 stima posizione (ultima fermata con orario <= adesso UTC).
  final items = stops.whereType<Map>().toList();
  if (items.isEmpty) {
    printWarn('Nessuna fermata nella timeline.');
    return;
  }
  final now = DateTime.now().toUtc();
  final times = items.map((x) => stopEffTime(Map<String, dynamic>.from(x as Map))).toList();
  var at = -1; // -1 = non partito
  for (var i = 0; i < times.length; i++) {
    final t = times[i];
    if (t != null && !t.isAfter(now)) at = i;
  }
  print('\n  ${C.b('Timeline (${items.length} fermate):')}');
  for (var i = 0; i < items.length; i++) {
    final s = Map<String, dynamic>.from(items[i] as Map);
    final name = '${s['station'] ?? s['stop'] ?? s['stationName'] ?? s['name'] ?? '?'}';
    final arr = fmtTime(s['scheduledArrival'] ?? s['arrival']);
    final dep = fmtTime(s['scheduledDeparture'] ?? s['departure'] ?? s['time']);
    final delay = s['delay'] ?? s['arrivalDelay'] ?? s['departureDelay'] ?? 0;
    final cancelled = s['cancelled'] == true || s['canceled'] == true || s['isCancelled'] == true;
    final mark = cancelled
        ? C.err('✖')
        : i == 0
            ? C.ok('●')
            : i == items.length - 1
                ? C.info('■')
                : C.dim_('○');
    final timeStr = arr == dep ? arr : '$arr/$dep';
    final nDelay = delay is int ? delay : int.tryParse('$delay') ?? 0;
    var here = '';
    var moving = false;
    if (at == -1 && i == 0) {
      here = '  ${C.ok('🚂 non partito')}';
    } else if (at == items.length - 1 && i == items.length - 1) {
      here = '  ${C.ok('🚂 arrivato')}';
    } else if (at == i && times[at] != null) {
      if (now.difference(times[at]!).inSeconds <= 180) {
        here = '  ${C.ok('🚂 qui')}';
      } else {
        moving = true;
      }
    }
    print('  $mark ${C.dim_(timeStr.padRight(11))} $name${nDelay != 0 ? '  ${delayBadge(nDelay)}' : ''}$here');
    if (i < items.length - 1) {
      print(moving && at == i ? '  ${C.dim_('│')} ${C.ok('🚂 ↓ in viaggio')}' : '  ${C.dim_('│')}');
    }
  }
}

Future<List<Map<String, dynamic>>> cmdTrainBoard(String stationId, String country, bool arrivi) async {
  final ep = arrivi ? 'arrivals' : 'departures';
  final label = arrivi ? 'Arrivi' : 'Partenze';
  printTitle('🚂 $label · stazione $stationId [$country]');
  final url = '$kTrainBoard/$country/$ep?stationId=${Uri.encodeComponent(stationId)}';
  printDim('GET $url');
  try {
    final data = await getJson(url);
    final list = asList(data);
    if (list.isEmpty) {
      printWarn('Nessun treno trovato.');
      return [];
    }
    final headPlace = arrivi ? 'PROVENIENZA' : 'DESTINAZIONE';
    final rows = <List<String>>[];
    final dataRows = <Map<String, dynamic>>[];
    for (final raw in list.take(30)) {
      if (raw is! Map) continue;
      final e = Map<String, dynamic>.from(raw);
      final inner = e['data'] is Map ? Map<String, dynamic>.from(e['data']) : e;
      final line = (inner['line'] ?? inner['category'] ?? '').toString();
      final num = (inner['tripNumber'] ?? inner['trainNumber'] ?? '').toString();
      final label = (num.isNotEmpty && line.contains(num)) ? line : '$line $num'.trim();
      // Arrivi → provenienza (origin), Partenze → destinazione (come TrainDeparture.fromJson)
      final dest = ((arrivi ? inner['origin'] : inner['destination']) ?? inner['stationName'] ?? '—').toString();
      final cat = trainCategory(
          (inner['line'] ?? inner['category'] ?? '').toString(),
          (inner['category'] ?? '').toString().isEmpty ? null : (inner['category'] ?? '').toString());
      final t = fmtTime(inner['scheduledTime'] ?? inner['time']);
      final plat = (inner['platform'] ?? inner['plannedPlatform'] ?? '—').toString();
      final delay = delayBadge(inner['delay'] ?? inner['delayMinutes'] ?? 0);
      rows.add([t, catPaint(cat, shortStr(label, 18)), shortStr(dest, 32), C.warn(plat), delay]);
      dataRows.add(inner);
    }
    // Larghezze dinamiche: STATO resta allineato anche con binari lunghi ("3 Ovest")
    var wN = 'N'.length, w0 = 'ORA'.length, w1 = 'TRENO'.length, w2 = headPlace.length, w3 = 'BIN'.length;
    for (var i = 0; i < rows.length; i++) {
      final r = rows[i];
      if ('${i + 1}'.length > wN) wN = '${i + 1}'.length;
      if (vlen(r[0]) > w0) w0 = vlen(r[0]);
      if (vlen(r[1]) > w1) w1 = vlen(r[1]);
      if (vlen(r[2]) > w2) w2 = vlen(r[2]);
      if (vlen(r[3]) > w3) w3 = vlen(r[3]);
    }
    print(
        '  ${C.dim_(padV('N', wN))} ${C.dim_(padV('ORA', w0))} ${C.dim_(padV('TRENO', w1))} ${C.dim_(padV(headPlace, w2))} ${C.dim_(padV('BIN', w3))} ${C.dim_('STATO')}');
    for (var i = 0; i < rows.length; i++) {
      final r = rows[i];
      print(
          '  ${C.train(padV('${i + 1}', wN))} ${C.b(padV(r[0], w0))} ${padV(r[1], w1)} ${padV(r[2], w2)} ${padV(r[3], w3)} ${r[4]}');
    }
    printDim('Totale: ${list.length} (mostrati max 30) · tasto 4 = timeline del treno');
    return dataRows;
  } catch (e) {
    printErr('Errore tabellone: $e');
    return [];
  }
}

String stopName(dynamic v) {
  // Origine/destinazione a volte oggetto {stationName,...} (come nel trip)
  if (v is Map) return '${v['stationName'] ?? v['name'] ?? '?'}';
  return '${v ?? ''}';
}

Future<void> cmdTrainDetails(String numero, String stazione, String country) async {
  printTitle('🚂 Dettaglio treno $numero @ $stazione [$country]');
  final url =
      '$kTrainBoard/$country/details?trainNumber=${Uri.encodeComponent(numero)}&stationId=${Uri.encodeComponent(stazione)}';
  printDim('GET $url');
  try {
    final data = await getJson(url);
    final e = data is Map ? Map<String, dynamic>.from(data['data'] ?? data) : <String, dynamic>{};
    print('  ${C.b('Categoria:')} ${e['category'] ?? e['line'] ?? '—'}');
    print('  ${C.b('Origine:')} ${stopName(e['origin'] ?? e['stationName']).isEmpty ? '—' : stopName(e['origin'] ?? e['stationName'])}');
    print('  ${C.b('Destinazione:')} ${stopName(e['destination']).isEmpty ? '—' : stopName(e['destination'])}');
    print('  ${C.b('Orario:')} ${fmtTime(e['scheduledTime'] ?? e['time'])}  stimato ${fmtTime(e['estimatedTime'])}  ${delayBadge(e['delay'] ?? 0)}');
    print('  ${C.b('Binario:')} ${e['platform'] ?? '—'}');
    printTimeline(e['stops'] ?? e['stopovers'] ?? []);
  } catch (e) {
    printErr('Errore dettaglio treno: $e');
  }
}

Future<void> cmdTrainTrip(String tripId, String country) async {
  printTitle('🚂 Trip $tripId [$country]');
  final url =
      '$kTrainBoard/$country/trip?tripId=${Uri.encodeComponent(tripId)}';
  printDim('GET $url');
  try {
    final data = await getJson(url);
    final e = data is Map ? Map<String, dynamic>.from(data['data'] ?? data) : <String, dynamic>{};
    print('  ${C.b('Linea:')} ${e['line'] ?? e['category'] ?? '—'}');
    print('  ${C.b('Destinazione:')} ${stopName(e['destination']).isEmpty ? '—' : stopName(e['destination'])}');
    printTimeline(e['stops'] ?? e['stopovers'] ?? []);
  } catch (e) {
    printErr('Errore trip: $e');
  }
}

Future<void> cmdTrainNumber(String q) async {
  printTitle('🔎 Treni live · filtro "$q"');
  const url =
      'https://data.cuzimmartin.dev/train-map?north=85&south=-5&east=91&west=-64&duration=300&results=1000&polylines=false';
  printDim('GET $url');
  try {
    final data = await getJson(url);
    final mov = data is Map ? (data['movements'] as List? ?? []) : [];
    final term = q.toLowerCase();
    final found = mov.where((m) {
      if (m is! Map) return false;
      final line = (m['line'] is Map)
          ? '${m['line']['name'] ?? ''} ${m['line']['id'] ?? ''}'
          : '';
      return line.toLowerCase().contains(term);
    }).toList();
    if (found.isEmpty) {
      printWarn('Nessun treno live corrisponde.');
      return;
    }
    for (final m in found.take(20)) {
      final mm = Map<String, dynamic>.from(m as Map);
      final line = mm['line'] is Map ? mm['line'] : {};
      final name = (line['name'] ?? line['id'] ?? '?').toString();
      final cat = trainCategory(name, (line['productName'] ?? '').toString().isEmpty ? null : '${line['productName']}');
      print(
          '  ${catPaint(cat, name)}  ${shortStr(mm['destination'] ?? mm['tripId'] ?? '', 30)}');
    }
    printDim('Trovati: ${found.length} (mostrati max 20)');
  } catch (e) {
    printErr('Errore mappa live: $e');
  }
}

Future<void> cmdFal(String stationId) async {
  printTitle('🟣 FAL · stazione $stationId');
  final url = '$kBase/api/fal/stop-updates?stationId=${Uri.encodeComponent(stationId)}';
  printDim('GET $url');
  try {
    final data = await getJson(url);
    if (data is! Map || data['grouped'] is! Map) {
      printWarn('Nessuna partenza FAL.');
      return;
    }
    final grouped = Map<String, dynamic>.from(data['grouped']);
    grouped.forEach((dest, list) {
      print('\n  ${C.fal('→ $dest')}');
      if (list is List) {
        for (final item in list.take(8)) {
          if (item is! Map) continue;
          final trip = item['trip'] is Map ? Map<String, dynamic>.from(item['trip']) : <String, dynamic>{};
          final stop = item['stopInfo'] is Map ? Map<String, dynamic>.from(item['stopInfo']) : <String, dynamic>{};
          final t = fmtTime(stop['expected_passing_date']);
          final rit = stop['ritardo'];
          print(
              '    ${C.b(t)}  ${trip['LineCode'] ?? trip['id_documento'] ?? ''}  ${delayBadge(rit is int ? rit : 0)}');
        }
      }
    });
  } catch (e) {
    printErr('Errore FAL: $e');
  }
}

// ---------------------------------------------------------------------------
// BUS
// ---------------------------------------------------------------------------

Future<List<Map<String, dynamic>>> fetchProviders() async {
  final data = await getJson('$kBase/config/bus_providers.json');
  final list = data is Map ? (data['providers'] as List? ?? []) : [];
  return list
      .whereType<Map>()
      .map((e) => Map<String, dynamic>.from(e))
      .toList();
}

String providerCountry(Map<String, dynamic> p) {
  final c = (p['country'] ?? '').toString();
  if (c.isNotEmpty) return c;
  final prefix = (p['apiPrefix'] ?? '').toString();
  if (prefix.contains('/')) return prefix.split('/').first;
  return 'it';
}

Future<void> cmdBusProviders() async {
  printTitle('🚌 Provider bus disponibili');
  try {
    final provs = await fetchProviders();
    for (final p in provs) {
      print('  ${C.bus((p['name'] ?? '?').toString().padRight(18))} ${C.dim_(providerCountry(p))}  ${shortStr(p['provider'] ?? p['city'] ?? '', 30)}');
    }
    printDim('Totale: ${provs.length}');
  } catch (e) {
    printErr('Errore providers: $e');
  }
}

Future<String> resolveCountry(String provider, String fallback) async {
  try {
    final provs = await fetchProviders();
    for (final p in provs) {
      if ((p['name'] ?? '').toString().toLowerCase() ==
          provider.toLowerCase()) {
        return providerCountry(p);
      }
    }
  } catch (_) {}
  return fallback;
}

Future<void> cmdBusLines(String provider, String paese) async {
  final country = paese.isEmpty ? await resolveCountry(provider, 'it') : paese;
  printTitle('🚌 Linee · $provider [$country]');
  try {
    int page = 1, total = 1;
    int count = 0;
    do {
      final url =
          '$kBase/api/$country/bus/$provider/lines?page=$page&chunkSize=100';
      final data = await getJson(url);
      if (data is! Map) break;
      final lines = (data['lines'] as List? ?? []);
      for (final l in lines) {
        if (l is! Map) continue;
        final m = Map<String, dynamic>.from(l);
        final code = (m['code'] ?? m['line'] ?? m['id'] ?? '?').toString();
        final name = (m['name'] ?? m['description'] ?? '').toString();
        print('  ${C.bus(code.padRight(10))} ${shortStr(name, 50)}');
        count++;
        if (count >= 60) break;
      }
      final pag = data['pagination'] is Map
          ? Map<String, dynamic>.from(data['pagination'])
          : null;
      total = (pag?['totalPages'] as num?)?.toInt() ?? 1;
      page++;
    } while (page <= total && page <= 2);
    printDim('Mostrate prime righe (pagina 1-2). Usa --fermate/--partenze per il live.');
  } catch (e) {
    printErr('Errore linee: $e');
  }
}

Future<void> cmdBusStops(String provider, String paese) async {
  final country = paese.isEmpty ? await resolveCountry(provider, 'it') : paese;
  printTitle('🚌 Fermate · $provider [$country]');
  final url = '$kBase/api/$country/bus/$provider/stops';
  printDim('GET $url');
  try {
    final data = await getJson(url);
    List<dynamic> list = [];
    if (data is List) {
      list = data;
    } else if (data is Map && data['stops'] is List) {
      list = data['stops'];
    }
    if (list.isEmpty) {
      printWarn('Nessuna fermata.');
      return;
    }
    for (final s in list.take(30)) {
      if (s is! Map) continue;
      final m = Map<String, dynamic>.from(s);
      // Stessi alias di BariStop.fromJson (bus_model.dart:235-239)
      final id = (m['stop_id'] ?? m['stopId'] ?? m['id'] ?? '?').toString();
      final name = (m['stop_name'] ?? m['stopName'] ?? m['name'] ?? '?').toString();
      print('  ${C.bus(id.padRight(12))} ${shortStr(name, 48)}');
    }
    printDim('Totale: ${list.length} (mostrate 30)');
  } catch (e) {
    printErr('Errore fermate: $e');
  }
}

Future<void> cmdBusDepartures(String provider, String stopId, String paese) async {
  final country = paese.isEmpty ? await resolveCountry(provider, 'it') : paese;
  printTitle('🚌 Partenze fermata $stopId · $provider [$country]');
  final url =
      '$kBase/api/$country/bus/$provider/stops-updates?stopId=${Uri.encodeComponent(stopId)}';
  printDim('GET $url');
  try {
    final data = await getJson(url);
    final deps = data is Map ? (data['departures'] as List? ?? []) : [];
    if (deps.isEmpty) {
      printWarn('Nessuna partenza.');
      return;
    }
    for (final d in deps.take(25)) {
      if (d is! Map) continue;
      final m = Map<String, dynamic>.from(d);
      final line = (m['line'] ?? m['route'] ?? m['code'] ?? '?').toString();
      final dest = (m['destination'] ?? m['headsign'] ?? '—').toString();
      final t = fmtTime(m['expectedTime'] ?? m['scheduledTime'] ?? m['time']);
      print(
          '  ${C.b(t.padRight(7))} ${C.bus(line.padRight(10))} ${shortStr(dest, 40)}  ${delayBadge(m['delay'] ?? 0)}');
    }
    printDim('Totale: ${deps.length}');
  } catch (e) {
    printErr('Errore partenze bus: $e');
  }
}

Future<void> cmdBusVehicles(String provider, String paese) async {
  final country = paese.isEmpty ? await resolveCountry(provider, 'it') : paese;
  printTitle('🚌 Veicoli live · $provider [$country]');
  final url = '$kBase/api/$country/bus/$provider/vehicles';
  printDim('GET $url');
  try {
    final data = await getJson(url);
    List<dynamic> list = [];
    if (data is Map && data['entities'] is List) {
      list = data['entities'];
    } else if (data is List) {
      list = data;
    }
    if (list.isEmpty) {
      printWarn('Nessun veicolo live al momento.');
      return;
    }
    for (final v in list.take(20)) {
      if (v is! Map) continue;
      final m = Map<String, dynamic>.from(v);
      final id = (m['vehicleId'] ?? m['id'] ?? '?').toString();
      final route = (m['routeId'] ?? m['line'] ?? '?').toString();
      print('  ${C.bus(route.padRight(10))} veicolo $id');
    }
    printDim('Totale: ${list.length}');
  } catch (e) {
    printErr('Errore veicoli: $e');
  }
}

// ---------------------------------------------------------------------------
// VOLI
// ---------------------------------------------------------------------------

Future<void> cmdFlightsArea() async {
  printTitle('✈️ Radar voli · Italia');
  const url = '$kBase/api/flightradar?bounds=47.5,35.0,6.0,19.0';
  printDim('GET $url');
  try {
    final data = await getJson(url);
    List<dynamic> flights = [];
    if (data is Map && data['flights'] is List) {
      flights = data['flights'];
    }
    if (flights.isEmpty) {
      printWarn('Nessun volo rilevato.');
      return;
    }
    print(
        '  ${C.dim_('VOLO'.padRight(10))} ${C.dim_('DA'.padRight(6))}→${C.dim_('A'.padRight(6))} ${C.dim_('ALT'.padRight(8))} ${C.dim_('VEL'.padRight(7))}');
    for (final f in flights.take(25)) {
      if (f is! Map) continue;
      final m = Map<String, dynamic>.from(f);
      final num = (m['flightNumber'] ?? m['callsign'] ?? m['id'] ?? '?').toString();
      final o = (m['origin'] ?? '???').toString();
      final d = (m['destination'] ?? '???').toString();
      final alt = (m['altitude'] ?? 0).toString();
      final spd = (m['speed'] ?? 0).toString();
      print(
          '  ${C.plane(num.padRight(10))} ${o.padRight(6)}→${d.padRight(6)} ${alt.padRight(8)} ${spd.padRight(7)}');
    }
    printDim('Totale: ${flights.length}');
  } catch (e) {
    printErr('Errore radar: $e');
  }
}

Future<void> cmdAirport(String iata, bool arrivi) async {
  final type = arrivi ? 'arrivals' : 'departures';
  printTitle('✈️ Aeroporto $iata · $type');
  final url =
      '$kBase/proxy/skyscanner/airport/${Uri.encodeComponent(iata)}/$type';
  printDim('GET $url');
  try {
    final data = await getJson(url);
    final list = data is Map ? (data[type] as List? ?? []) : [];
    if (list.isEmpty) {
      printWarn('Nessun volo trovato.');
      return;
    }
    for (final f in list.take(25)) {
      if (f is! Map) continue;
      final m = Map<String, dynamic>.from(f);
      final num = (m['flightNumber'] ?? m['flight'] ?? '?').toString();
      final other = (m['origin'] ?? m['destination'] ?? m['airport'] ?? '—').toString();
      final t = fmtTime(m['scheduledTime'] ?? m['time']);
      print('  ${C.b(t.padRight(7))} ${C.plane(num.padRight(12))} $other');
    }
    printDim('Totale: ${list.length}');
  } catch (e) {
    printErr('Errore aeroporto: $e');
  }
}

// ---------------------------------------------------------------------------
// FLIXBUS
// ---------------------------------------------------------------------------

Future<void> cmdFlixStations(String q) async {
  printTitle('🟢 Flixbus · stazioni "$q"');
  try {
    final data = await getJson(
        '$kFlix/stations?query=${Uri.encodeComponent(q)}');
    final list = asList(data);
    if (list.isEmpty) {
      printWarn('Nessuna stazione Flixbus.');
      return;
    }
    for (final s in list.take(15)) {
      if (s is! Map) continue;
      final m = Map<String, dynamic>.from(s);
      print(
          '  ${C.ok((m['name'] ?? '?').toString())}  ${C.dim_('id=${m['id'] ?? '?'}')}');
    }
  } catch (e) {
    printErr('Errore Flixbus: $e');
  }
}

Future<void> cmdFlixDepartures(String stationId) async {
  printTitle('🟢 Flixbus · partenze $stationId');
  try {
    final data = await getJson(
        '$kFlix/departures?stationId=${Uri.encodeComponent(stationId)}');
    final list = asList(data);
    if (list.isEmpty) {
      printWarn('Nessuna partenza.');
      return;
    }
    for (final d in list.take(20)) {
      if (d is! Map) continue;
      final m = Map<String, dynamic>.from(d);
      final line = (m['line'] ?? '?').toString();
      final dest = (m['destination'] ?? '—').toString();
      final t = fmtTime(m['scheduledTime'] ?? m['time']);
      print(
          '  ${C.b(t.padRight(7))} ${C.ok(line.padRight(10))} ${shortStr(dest, 40)}');
    }
  } catch (e) {
    printErr('Errore Flixbus: $e');
  }
}

Future<void> cmdFlixTrip(String tripId) async {
  printTitle('🟢 Flixbus · trip $tripId');
  try {
    final data = await getJson(
        '$kFlix/trip?tripId=${Uri.encodeComponent(tripId)}');
    final e = data is Map ? Map<String, dynamic>.from(data['data'] ?? data) : <String, dynamic>{};
    final stops = e['stops'] is List ? e['stops'] as List : [];
    if (stops.isEmpty) {
      printWarn('Trip non trovato.');
      return;
    }
    for (final s in stops) {
      if (s is! Map) continue;
      final m = Map<String, dynamic>.from(s);
      print(
          '  ${C.dim_(fmtTime(m['scheduledTime'] ?? m['time']))}  ${m['name'] ?? m['station'] ?? '?'}');
    }
  } catch (e) {
    printErr('Errore Flixbus trip: $e');
  }
}

// ---------------------------------------------------------------------------
// POST/PATCH/DELETE + stesse logiche di supporto dell'app
// ---------------------------------------------------------------------------

Future<dynamic> postJson(String url,
    Map<String, dynamic> payload, {int timeoutSec = 15, String? token}) async {
  final client = HttpClient();
  try {
    final req = await client
        .postUrl(Uri.parse(url))
        .timeout(Duration(seconds: timeoutSec));
    req.headers.set('Content-Type', 'application/json; charset=utf-8');
    kHeaders.forEach(req.headers.set);
    if (token != null) req.headers.set('Authorization', 'Bearer $token');
    req.write(json.encode(payload));
    final res =
        await req.close().timeout(Duration(seconds: timeoutSec));
    final body = await res.transform(utf8.decoder).join();
    if (res.statusCode < 200 || res.statusCode >= 300) {
      throw HttpException('HTTP ${res.statusCode} su $url\n$body');
    }
    return body.trim().isEmpty ? {} : json.decode(body);
  } finally {
    client.close(force: true);
  }
}

/// ApiService.fetchConfig: 3 retry + backoff + fallback default.
Future<Map<String, dynamic>> fetchConfig() async {
  Object? last;
  for (var attempt = 1; attempt <= 3; attempt++) {
    try {
      final data = await getJson('$kBase/api/config/transports');
      return data is Map<String, dynamic> ? data : {'transports': []};
    } catch (e) {
      last = e;
      await Future.delayed(Duration(seconds: attempt));
    }
  }
  return {
    'transports': [
      {'id': 'default_train', 'name': 'Trainboard', 'type': 'train'},
      {'id': 'default_bus', 'name': 'AMTAB Bari', 'type': 'bus'},
      {'id': 'default_plane', 'name': 'FlightRadar', 'type': 'plane'},
    ],
    '_fallback': true,
    '_error': '$last',
  };
}

/// BusRepository: distanza Haversine + stima arrivo.
double haversineKm(double lat1, double lon1, double lat2, double lon2) {
  const r = 6371.0;
  double rad(double d) => d * math.pi / 180;
  final dLat = rad(lat2 - lat1), dLon = rad(lon2 - lon1);
  final a = math.sin(dLat / 2) * math.sin(dLat / 2) +
      math.cos(rad(lat1)) *
          math.cos(rad(lat2)) *
          math.sin(dLon / 2) *
          math.sin(dLon / 2);
  return r * 2 * math.asin(math.sqrt(a.clamp(0.0, 1.0)));
}

String? arrivalEstimate(
    double busLat, double busLon, double stopLat, double stopLon, double speed) {
  if ((busLat == 0.0 && busLon == 0.0) ||
      (stopLat == 0.0 && stopLon == 0.0)) return null;
  final dist = haversineKm(busLat, busLon, stopLat, stopLon);
  if (dist < 0.1 || (dist < 0.2 && speed < 10)) return 'In arrivo';
  var v = speed > 2 ? (20.0 * 0.6 + speed * 0.4) : 20.0;
  v = v.clamp(5.0, 60.0);
  final mins = (dist / v * 60).ceil();
  if (mins > 60) return null;
  return mins < 1 ? 'In arrivo' : '~$mins min';
}

String _homeDir() =>
    Platform.environment['USERPROFILE'] ??
    Platform.environment['HOME'] ??
    '.';

String get sessFile => '$_home/.bc_cli_session.json';
String get favFile => '$_home/.bc_cli_favorites.json';
String get _home => _homeDir();
String get cacheDir => '$_home/.bc_cli_cache';

Map<String, dynamic> loadJsonFile(String path) {
  try {
    return json.decode(File(path).readAsStringSync()) as Map<String, dynamic>;
  } catch (_) {
    return {};
  }
}

List<dynamic> loadJsonList(String path) {
  try {
    final d = json.decode(File(path).readAsStringSync());
    return d is List ? d : [];
  } catch (_) {
    return [];
  }
}

// ---------------------------------------------------------------------------
// CONFIG / STATS / LOGHI
// ---------------------------------------------------------------------------

Future<void> cmdConfigShow() async {
  printTitle('⚙️ Config trasporti (+ fallback come ApiService)');
  try {
    final data = await fetchConfig();
    if (data['_fallback'] == true) {
      printWarn('Server non raggiungibile, uso default (${data['_error']})');
    }
    final list = (data['transports'] is List) ? data['transports'] as List : [];
    for (final t in list) {
      if (t is! Map) continue;
      print('  ${C.ok((t['name'] ?? '?').toString().padRight(18))} '
          '${C.dim_((t['type'] ?? '').toString())}  id=${t['id'] ?? '?'}');
    }
    if (list.isEmpty) printDim('Risposta grezza: ${shortStr(data, 200)}');
    printDim('Totale: ${list.length}');
  } catch (e) {
    printErr('Errore config: $e');
  }
}

Future<void> cmdStatsGeneral() async {
  printTitle('📊 Statistiche generali treni');
  try {
    final data = await getJson('$kBase/api/stats/trains/general');
    final d = data is Map ? (data['data'] ?? data) : data;
    final s = const JsonEncoder.withIndent('  ').convert(d);
    print(s.substring(0, s.length > 2000 ? 2000 : s.length));
  } catch (e) {
    printErr('Errore stats: $e');
  }
}

Future<void> cmdTrainLogos() async {
  printTitle('🎨 Loghi vettori treni');
  try {
    final data = await getJson('$kBase/api/train-logos');
    final src = data is Map && data['official'] is Map
        ? Map<String, dynamic>.from(data['official'])
        : <String, dynamic>{};
    for (final k in src.keys.take(20)) {
      print('  ${C.ok(k)}');
    }
    printDim('Totale official: ${src.length}');
  } catch (e) {
    printErr('Errore loghi: $e');
  }
}

// ---------------------------------------------------------------------------
// TRENI extra (stessa logica di train_repository / sheet)
// ---------------------------------------------------------------------------

Future<void> cmdTrainDirect(String q) async {
  printTitle('🚂 Ricerca diretta RFI · "$q"');
  final url = '$kBase/proxy/viaggiatreno?q=${Uri.encodeComponent(q)}';
  printDim('GET $url');
  try {
    final data = await getJson(url);
    final list = data is List ? data : [];
    for (final e in list.take(10)) {
      if (e is! Map) continue;
      print('  ${C.train((e['nomestazione'] ?? '?').toString())}  '
          '${C.dim_('cod=${e['codStazione'] ?? '?'}')}');
    }
  } catch (e) {
    printErr('Errore: $e');
  }
}

Future<void> cmdTrainShare(String tripId, String country) async {
  printTitle('🔗 Condividi trip $tripId [$country]');
  try {
    final data = await getJson(
        '$kTrainBoard/$country/trip?tripId=${Uri.encodeComponent(tripId)}');
    final e = data is Map
        ? Map<String, dynamic>.from(data['data'] ?? data)
        : <String, dynamic>{};
    final res = await postJson('$kBase/api/share-trip', {
      'tripId': tripId,
      'country': country,
      'tripNumber': e['tripNumber'] ?? e['trainNumber'],
      'origin': e['origin'],
      'destination': e['destination'],
      'platform': e['platform'],
      'delay': e['delay'] ?? 0,
      'scheduledTime': '${e['scheduledTime'] ?? ''}',
      'estimatedTime': '${e['estimatedTime'] ?? ''}',
      'stops': e['stops'] ?? e['stopovers'] ?? [],
    });
    final sid = res is Map ? res['shareId'] : null;
    if (sid != null) {
      printOk('URL: $kBase/share/?id=$sid');
    } else {
      printWarn('Condivisione fallita.');
    }
  } catch (e) {
    printErr('Share: $e');
  }
}

Future<void> cmdTrainLive() async {
  printTitle('📡 Treni live (snapshot /api/trains/live)');
  try {
    final data = await getJson('$kBase/api/trains/live');
    List list = [];
    if (data is List) {
      list = data;
    } else if (data is Map && data['trains'] is List) {
      list = data['trains'];
    } else {
      list = asListDynamic(data);
    }
    for (final t in list.take(20)) {
      if (t is! Map) continue;
      print('  ${C.train(((t['trip_number'] ?? t['tripNumber'] ?? '?').toString()).padRight(10))} '
          '${shortStr(t['destination'] ?? t['trip_id'] ?? '', 36)}');
    }
    printDim('Totale: ${list.length}');
  } catch (e) {
    printErr('Errore live: $e');
  }
}

List<dynamic> asListDynamic(dynamic v) {
  if (v is List) return v;
  if (v is Map && v['data'] is List) return v['data'] as List;
  return [];
}

Future<void> cmdTrainTrack(String tripId) async {
  printTitle('🗺️ Traccia trip $tripId');
  try {
    final data =
        await getJson('$kBase/api/track-trip/${Uri.encodeComponent(tripId)}');
    final d = data is Map
        ? Map<String, dynamic>.from(data['data'] ?? data)
        : <String, dynamic>{};
    final pos = d['trainPosition'];
    if (pos is Map) print('  ${C.b('Posizione:')} ${pos['lat']}, ${pos['lng']}');
    final stops = d['stops'] is List ? d['stops'] as List : [];
    for (final s in stops.take(25)) {
      if (s is! Map) continue;
      print('    ${s['stationName'] ?? s['name'] ?? '?'}');
    }
  } catch (e) {
    printErr('Errore track: $e');
  }
}

Future<void> cmdStatsTrain(String cat, String num) async {
  printTitle('📊 Comportamento treno $cat $num');
  try {
    final data = await getJson(
        '$kBase/api/stats/train/${Uri.encodeComponent(cat)}/${Uri.encodeComponent(num)}');
    final d = data is Map ? (data['data'] ?? data) : data;
    final s = const JsonEncoder.withIndent('  ').convert(d);
    print(s.substring(0, s.length > 2000 ? 2000 : s.length));
  } catch (e) {
    printErr('Errore (404 = nessun dato): $e');
  }
}

Future<void> cmdTrainCountries() async {
  // Lista NUMERATA paesi/regioni -> codice API (stesso endpoint dell'app).
  printTitle('🌍 Paesi treni (scegli col numero)');
  try {
    final data = await getJson('https://prod.cuzimmartin.dev/api/providers',
        timeoutSec: 10);
    List grouped = [];
    if (data is Map) {
      final d = data['data'];
      if (d is Map && d['grouped'] is List) {
        grouped = d['grouped'] as List;
      } else if (d is List) {
        grouped = d;
      }
    }
    var n = 0;
    final codes = <String>[];
    for (final g in grouped) {
      if (g is! Map) continue;
      final code = '${g['regionCode'] ?? g['countryCode'] ?? '?'}';
      codes.add(code);
      String name = '';
      if (g['providers'] is List && (g['providers'] as List).isNotEmpty) {
        final p0 = (g['providers'] as List).first;
        if (p0 is Map) name = '${p0['displayName'] ?? p0['name'] ?? ''}';
      }
      n++;
      print('  ${C.train('[$n]')} ${C.b(code.padRight(18))} ${C.dim_(name)}');
    }
    for (final extra in ['GLOBAL|ricerca globale', 'UK_LONDON|Londra', 'FAL|Ferrovie Appulo Lucane']) {
      final parts = extra.split('|');
      if (!codes.contains(parts[0])) {
        n++;
        print('  ${C.train('[$n]')} ${C.b(parts[0].padRight(18))} ${C.dim_(parts[1])}');
      }
    }
  } catch (e) {
    printErr('Errore: $e');
  }
}

String trainCategory(String? line, [String? product]) {
  // Come TrainDeparture.fromJson: primo token, solo lettere ("REG 4449"→REG),
  // linee S-Bahn S{numero} raggruppate in "S".
  if (product != null && product.trim().isNotEmpty) {
    return product.trim().toUpperCase();
  }
  final s = (line ?? '').trim();
  if (s.isEmpty) return '';
  final tok =
      s.split(RegExp(r'\s+')).first.replaceAll(RegExp(r'[^A-Za-z0-9\-]'), '');
  if (RegExp(r'^S\d+$', caseSensitive: false).hasMatch(tok)) return 'S';
  final letters = tok.replaceAll(RegExp(r'\d'), '').toUpperCase();
  if (letters.isNotEmpty && RegExp(r'[A-Z]').hasMatch(letters)) return letters;
  return tok.toUpperCase().isEmpty ? '?' : tok.toUpperCase();
}

String catColor(String cat) {
  switch (cat.toUpperCase()) {
    case 'FR':
    case 'AV':
    case 'ICE':
    case 'TGV':
    case 'ES':
    case 'FB':
    case 'OUIGO':
    case 'ETR':
    case 'FRECCIA':
      return C.red; // alta velocità
    case 'IC':
    case 'EC':
    case 'EN':
    case 'RJ':
    case 'ICN':
    case 'INTERCITY':
      return C.yellow; // lunga percorrenza
    case 'NJ':
    case 'FAL':
    case 'TRAM':
    case 'TRAMWAY':
      return C.magenta;
    case 'REG':
    case 'R':
    case 'RE':
    case 'RB':
    case 'TER':
    case 'RV':
    case 'REGIONALE':
    case 'REX':
    case 'IR':
    case 'OS':
      return C.green; // regionali
    case 'S':
      return C.cyan; // suburbane
    case 'U-BAHN':
    case 'METRO':
    case 'M':
      return C.blue;
    case 'BUS':
    case 'O-BUS':
      return C.yellow;
    default:
      const pal = [C.green, C.yellow, C.cyan, C.magenta, C.blue, C.red];
      var h = 0;
      for (final u in cat.toUpperCase().codeUnits) {
        h = (h + u) % pal.length;
      }
      return pal[h];
  }
}

String catPaint(String cat, String text) =>
    useColor ? '${C.bold}${catColor(cat)}$text${C.reset}' : text;

Future<void> cmdTrainCategories() async {
  // Tutte le categorie dalla mappa live MONDIALE (tutti i country insieme).
  printTitle('🏷️ Categorie treno (mappa live mondiale)');
  try {
    final data = await getJson('https://data.cuzimmartin.dev/train-map?north=85&south=-5&east=91'
        '&west=-64&duration=300&results=1000&polylines=false');
    final mov = data is Map && data['movements'] is List
        ? data['movements'] as List
        : [];
    final counts = <String, int>{};
    for (final m in mov) {
      if (m is! Map) continue;
      final line = m['line'] is Map ? Map<String, dynamic>.from(m['line'] as Map) : <String, dynamic>{};
      final cat = trainCategory(
          '${line['name'] ?? ''}', '${line['productName'] ?? ''}');
      if (cat.isEmpty) continue;
      counts[cat] = (counts[cat] ?? 0) + 1;
    }
    final sorted =
        counts.entries.toList()..sort((a, b) => b.value.compareTo(a.value));
    var i = 0;
    for (final e in sorted.take(60)) {
      i++;
      print('  ${C.dim_('$i'.padLeft(3))}  ${catPaint(e.key, e.key.padRight(12))} '
          '${C.dim_('${e.value} mezzi live')}');
    }
    printDim('Categorie distinte: ${counts.length} (mostrate 60).');
  } catch (e) {
    printErr('Errore mappa live: $e');
  }
}

Future<void> cmdPresence(String cmd, String key) async {
  try {
    if (cmd == 'live') {
      printTitle('👁️ Treni seguiti live (presence)');
      print(await getJson('$kBase/api/train-presence/live'));
    } else if (cmd == 'recent') {
      printTitle('👁️ Treni recenti');
      print(await getJson('$kBase/api/train-presence/recent?limit=20'));
    } else if (cmd == 'viewers') {
      final data = await getJson(
          '$kBase/api/train-presence/viewers?trainKey=${Uri.encodeComponent(key)}');
      printInfo('Spettatori $key: $data');
    } else if (cmd == 'heartbeat') {
      for (var i = 0; i < 3; i++) {
        final res = await postJson('$kBase/api/train-presence/heartbeat',
            {'clientId': 'cli-dart', 'trainKey': key, 'screen': 'cli'});
        printOk('battito ${i + 1}: $res');
        await Future.delayed(const Duration(seconds: 5));
      }
    }
  } catch (e) {
    printErr('Errore presence: $e');
  }
}

// ---------------------------------------------------------------------------
// REGIONALI
// ---------------------------------------------------------------------------

Future<void> cmdRegProviders(String country) async {
  printTitle('🏳️ Provider regionali · $country');
  try {
    final data = await getJson(
        '$kBase/api/train/regional_providers/${Uri.encodeComponent(country)}');
    final provs = data is Map && data['providers'] is List
        ? data['providers'] as List
        : asListDynamic(data);
    for (final p in provs) {
      if (p is! Map) continue;
      print('  ${C.ok((p['name'] ?? p['key'] ?? '?').toString())}  '
          '${C.dim_((p['apiPrefix'] ?? '').toString())}');
    }
    printDim('Totale: ${provs.length}');
  } catch (e) {
    printErr('Errore: $e');
  }
}

Future<void> cmdRegStations(String country, String prefix, String q) async {
  final base = '$kBase/api/${prefix.replaceAll(RegExp(r'^/|/\$'), '')}';
  final url = q.isEmpty
      ? '$base/stations?limit=100'
      : '$base/stations?query=${Uri.encodeComponent(q)}&limit=50';
  printTitle('🏳️ Stazioni regionali $prefix · \'$q\'');
  printDim('GET $url');
  try {
    final data = await getJson(url);
    for (final s in asListDynamic(data).take(20)) {
      if (s is! Map) continue;
      print('  ${C.ok((s['name'] ?? s['stationName'] ?? '?').toString())}  '
          '${C.dim_('id=${s['id'] ?? s['stationId'] ?? '?'}')}');
    }
  } catch (e) {
    printErr('Errore: $e');
  }
}

Future<void> cmdRegBoard(
    String country, String prefix, String stationId, bool arrivi) async {
  final base = '$kBase/api/${prefix.replaceAll(RegExp(r'^/|/\$'), '')}';
  final ep = arrivi ? 'arrivals' : 'departures';
  printTitle('🏳️ $ep regionali · $stationId');
  try {
    final data = await getJson(
        '$base/$ep?stationId=${Uri.encodeComponent(stationId)}');
    for (final raw in asListDynamic(data).take(20)) {
      if (raw is! Map) continue;
      final e = Map<String, dynamic>.from(raw);
      print('  ${C.b(fmtTime(e['scheduledTime'] ?? e['time']).padRight(7))} '
          '${C.ok(((e['tripNumber'] ?? e['trainNumber'] ?? '?').toString()).padRight(10))} '
          '${shortStr(e['destination'] ?? e['stationName'], 34)}');
    }
  } catch (e) {
    printErr('Errore: $e');
  }
}

// ---------------------------------------------------------------------------
// BUS extra
// ---------------------------------------------------------------------------

Future<void> cmdBusRealtime(
    String provider, String vehicleId, String tripId, String paese) async {
  final country = paese.isEmpty ? await _country(provider) : paese;
  printTitle('🛰️ Realtime $provider veicolo $vehicleId trip $tripId');
  final urls = [
    '$kBase/api/$country/bus/$provider/realtime?vehicleId=${Uri.encodeComponent(vehicleId)}'
        '&tripId=${Uri.encodeComponent(tripId)}&vehicles=true',
    '$kBase/api/$country/bus/$provider/realtime?routeId=${Uri.encodeComponent(vehicleId)}'
        '&tripId=${Uri.encodeComponent(tripId)}',
  ];
  for (final url in urls) {
    try {
      final data = await getJson(url);
      final vehs =
          data is Map && data['vehicles'] is List ? data['vehicles'] as List : [];
      if (vehs.isNotEmpty) {
        final v = Map<String, dynamic>.from(vehs.first);
        print('  ${C.b('Destinazione:')} ${v['destination'] ?? '—'}');
        for (final s in ((v['stops'] is List ? v['stops'] : []) as List).take(25)) {
          if (s is! Map) continue;
          print('    ${s['stopName'] ?? s['stopId']}  ${s['expectedTime'] ?? ''}  '
              'ritardo=${s['delay'] ?? 0}');
        }
        return;
      }
    } catch (e) {
      printDim('skip: $e');
    }
  }
  printWarn('Nessun dato realtime.');
}

Future<String> _country(String provider) async {
  try {
    final data = await getJson('$kBase/config/bus_providers.json');
    final list = data is Map && data['providers'] is List
        ? data['providers'] as List
        : [];
    for (final p in list) {
      if (p is Map &&
          (p['name'] ?? '').toString().toLowerCase() == provider.toLowerCase()) {
        final c = (p['country'] ?? '').toString();
        if (c.isNotEmpty) return c;
      }
    }
  } catch (_) {}
  return 'it';
}

// ---------------------------------------------------------------------------
// VOLI / STRADE / METEO / SOCIAL / AUTH / PREFERITI / OFFLINE
// ---------------------------------------------------------------------------

Future<void> cmdSearchAirports(String q) async {
  printTitle('✈️ Aeroporti · "$q"');
  if (q.length < 2) {
    printWarn('Scrivi almeno 2 caratteri.');
    return;
  }
  final url = 'https://www.skyscanner.it/g/autosuggest-search/api/v1/search-flight/IT/it-IT/'
      '${Uri.encodeComponent(q)}?isDestination=true&autosuggestExp=';
  try {
    final data = await getJson(url);
    var n = 0;
    for (final it in (data is List ? data : []).take(15)) {
      if (it is Map && it['PlaceId'] != null && '${it['PlaceId']}'.length == 3) {
        print('  ${C.plane('${it['PlaceId']}')}  ${it['PlaceName'] ?? it['name']} '
            '${C.dim_('${it['CityName'] ?? ''}')}');
        n++;
      }
    }
    if (n == 0) printWarn('Nessun aeroporto IATA.');
  } catch (e) {
    printErr('Errore autosuggest: $e');
  }
}

Future<void> cmdRoadNews(String paese) async {
  printTitle('🛣️ News strade [$paese]');
  try {
    final data = await getJson('$kBase/api/roadways/$paese/news');
    final list = data is Map && data['data'] is List ? data['data'] as List : [];
    for (final n in list.take(15)) {
      if (n is! Map) continue;
      print('  [${C.warn('${n['severity'] ?? n['type'] ?? 'news'}')}] '
          '${n['title'] ?? n['event']} ${C.dim_('${n['motorwayName'] ?? n['location'] ?? ''}')}');
    }
  } catch (e) {
    printErr('Errore: $e');
  }
}

Future<void> cmdMeteoSearch(String q) async {
  printTitle('🏙️ Città · "$q"');
  try {
    final data = await getJson(
        'https://geocoding-api.open-meteo.com/v1/search?name=${Uri.encodeComponent(q)}'
        '&count=10&language=it&format=json');
    for (final r in ((data is Map ? data['results'] : null) as List? ?? []).take(10)) {
      if (r is! Map) continue;
      print('  ${C.ok('${r['name']}')}  ${C.dim_('${r['country'] ?? ''}')}  '
          'lat=${r['latitude']} lon=${r['longitude']}');
    }
  } catch (e) {
    printErr('Errore geocoding: $e');
  }
}

Future<void> cmdMeteoNow(double lat, double lon, String city) async {
  printTitle('🌤️ Meteo $city ($lat,$lon)');
  try {
    final data = await getJson('https://api.open-meteo.com/v1/forecast?latitude=$lat&longitude=$lon'
        '&current_weather=true&hourly=precipitation_probability&forecast_days=1&timezone=auto');
    final cw = data is Map && data['current_weather'] is Map
        ? Map<String, dynamic>.from(data['current_weather'])
        : <String, dynamic>{};
    print('  ${C.b('${cw['temperature'] ?? '?'}°C')}  vento ${cw['windspeed'] ?? '?'} km/h  '
        'codice ${cw['weathercode'] ?? '?'}');
  } catch (e) {
    printErr('Errore meteo: $e');
  }
}

Future<void> cmdSocialFeed() async {
  printTitle('💬 Social feed');
  try {
    final data = await getJson('$kBase/api/social/feed?limit=30');
    final list = data is Map && data['topics'] is List ? data['topics'] as List : [];
    for (final t in list.take(15)) {
      if (t is! Map) continue;
      print('  [${C.ok('${t['id']}')}] ${t['title'] ?? t['train_key'] ?? ''}  '
          '${C.dim_('${t['nick'] ?? ''}')}');
    }
  } catch (e) {
    printErr('Errore feed: $e');
  }
}

Future<void> cmdSocialOnline() async {
  try {
    final data = await getJson('$kBase/api/active-connections');
    printInfo('Connessioni attive: ${data is Map ? data['activeConnections'] ?? 0 : data}');
  } catch (e) {
    printErr('Errore: $e');
  }
}

Future<void> cmdAuthStatus() async {
  final s = loadJsonFile(sessFile);
  final u = s['user'];
  if (u is Map) {
    printOk('Loggato come ${u['email'] ?? u['nickname']}');
  } else {
    printInfo('Nessuna sessione. Usa: auth --login <email> <pw>');
  }
}

Future<void> cmdFavList() async {
  printTitle('⭐ Preferiti');
  final favs = loadJsonList(favFile);
  if (favs.isEmpty) {
    printInfo('Nessun preferito.');
    return;
  }
  for (final f in favs) {
    if (f is! Map) continue;
    print('  [${C.warn('${f['id']}')}] ${C.ok('${f['type']}')}');
  }
}

Future<void> cmdOfflineSize() async {
  var total = 0;
  final dir = Directory(cacheDir);
  if (await dir.exists()) {
    await for (final e in dir.list(recursive: true)) {
      if (e is File) total += await e.length();
    }
  }
  printInfo('Dimensione cache: ${total ~/ 1024} KB');
}

// ---------------------------------------------------------------------------
// Help + menu interattivo
// ---------------------------------------------------------------------------

void printHelp() {
  print(C.title('BC.Transporter · CLI terminale'));
  printDim('Stessi dati dell\'app Flutter, nel terminale. Zero dipendenze.\n');
  print('  ${C.b('dart bin/bc_cli.dart')}  → menu interattivo\n');
  print(C.b('TRENI'));
  print('  ${C.train('treni --cerca "bari"')} [--paese IT]');
  print('  ${C.train('treni --partenze <id>')} [--paese IT] [--arrivi]');
  print('  ${C.train('treni --treno <num> --stazione <id>')} [--paese IT]');
  print('  ${C.train('treni --trip <tripId>')} [--paese IT]');
  print('  ${C.train('treni --numero <testo>')}');
  print('  ${C.fal('treni --fal <stationId>')}');
  print('  ${C.train('treni --diretta "bari"')} (proxy RFI diretto)');
  print('  ${C.train('treni --condividi <tripId>')} [--paese IT]');
  print('  ${C.train('treni --live')} / ${C.train('--track <tripId>')}');
  print('  ${C.train('treni --stats-treno <cat> <num>')} / ${C.train('--paesi')}');
  print('  ${C.train('treni --presence live|recent|viewers|heartbeat')} --key <k>');
  print('\n${C.b('BUS')}');
  print('  ${C.bus('bus --providers')}');
  print('  ${C.bus('bus --linee <provider>')} [--paese it]');
  print('  ${C.bus('bus --fermate <provider>')} [--paese it]');
  print('  ${C.bus('bus --partenze "<provider> <stopId>"')} [--paese it]');
  print('  ${C.bus('bus --veicoli <provider>')} [--paese it]');
  print('  ${C.bus('bus --realtime "<vehicleId> <tripId>"')} --provider bari');
  print('\n${C.b('VOLI')}');
  print('  ${C.plane('voli --area')}');
  print('  ${C.plane('voli --aeroporto <IATA>')} [--arrivi]');
  print('  ${C.plane('voli --cerca "bari"')} (autosuggest Skyscanner)');
  print('\n${C.b('FLIXBUS')}');
  print('  flixbus --stazioni "bari" | --partenze <id> | --trip <id>');
  print('\n${C.b('REGIONALI · STRADE · METEO · SOCIAL · SISTEMA')}');
  print('  regionali --lista IT | --stazioni "IT <prefix>" | --partenze "IT <prefix> <id>"');
  print('  strade --news [--paese it] · meteo --cerca roma · social --feed · auth --stato');
  print('  preferiti --lista · config --show · offline --size');
  print('\n${C.dim_('Globale: --paese <cod>  --no-color  --help')}');
  print(C.dim_('Paesi treni: IT FR DE CH AT ES GLOBAL · UK_LONDON per Londra'));
}

void printBanner() {
  if (!useColor) {
    print('=== BC.Transporter · terminale ===');
    return;
  }
  print('${C.bold}${C.blue}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${C.reset}');
  print('   ${C.bold}${C.cyan}BC.Transporter${C.reset}  ${C.dim_('· terminale')}');
  print('${C.bold}${C.blue}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${C.reset}');
  print('  ${C.dim_('Bus · Treni · Aerei nel terminale — stessi endpoint dell\'app Flutter')}');
}

Future<List<dynamic>> fetchStations(String q, String country) async {
  final url =
      '$kTrainBoard/${Uri.encodeComponent(country)}/stations?query=${Uri.encodeComponent(q)}&limit=10';
  final data = await getJson(url);
  if (data is List) return data;
  if (data is Map && data['data'] is List) return data['data'] as List;
  return [];
}

List<String> splitArgs(String line) {
  // Mini-splitter che rispetta le virgolette (come shlex).
  final out = <String>[];
  final buf = StringBuffer();
  var quote = '';
  for (var i = 0; i < line.length; i++) {
    final ch = line[i];
    if (quote.isNotEmpty) {
      if (ch == quote) {
        quote = '';
      } else {
        buf.write(ch);
      }
    } else if (ch == '"' || ch == "'") {
      quote = ch;
    } else if (ch == ' ' || ch == '\t') {
      if (buf.isNotEmpty) {
        out.add(buf.toString());
        buf.clear();
      }
    } else {
      buf.write(ch);
    }
  }
  if (buf.isNotEmpty) out.add(buf.toString());
  return out;
}

Future<String> pickTransport() async {
  // In OGNI modalità prima si seleziona il tipo di trasporto (tasti 1-4).
  print('  ${C.dim_('Tipo di trasporto:')}');
  print('  ${C.train('1)')} 🚂 Treni');
  print('  ${C.bus('2)')} 🚌 Bus');
  print('  ${C.plane('3)')} ✈️  Voli');
  print('  ${C.ok('4)')} 🟢 Flixbus');
  print('  ${C.dim_('[0] Indietro')}');
  final s = ((readInput('Numero trasporto [1]: ') ?? '').trim());
  final v = s.isEmpty ? '1' : s;
  if (v == '0') return '';
  switch (v) {
    case '2':
      return 'bus';
    case '3':
      return 'voli';
    case '4':
      return 'flixbus';
    default:
      return 'treni';
  }
}

Future<void> simpleMode() async {
  // Modalità semplice: 1) trasporto → 2) cerca → 3) tabellone partenze/arrivi
  printTitle('🟢 Modalità semplice (0 = menu)');
  final transport = await pickTransport();
  if (transport.isEmpty) return;
  if (transport == 'bus') {
    await simpleBus();
  } else if (transport == 'voli') {
    await simpleFly();
  } else if (transport == 'flixbus') {
    await simpleFlix();
  } else {
    await simpleTrain();
  }
}

Future<void> simpleTrain() async {
  var country = ((readInput('Codice paese [IT]: ') ?? '').trim());
  if (country.isEmpty) country = 'IT';
  country = country.toUpperCase();
  while (true) {
    final q = (readInput('\nNome stazione (0 = menu): ') ?? '').trim();
    if (q.isEmpty || q == '0') return;
    List<dynamic> lst = [];
    try {
      lst = await fetchStations(q, country);
    } catch (e) {
      printErr('Errore ricerca: $e');
      continue;
    }
    if (lst.isEmpty) {
      printWarn('Nessuna stazione trovata, riprova.');
      continue;
    }
    printTitle('🚂 Stazioni · "$q" [$country]');
    for (var i = 0; i < lst.length; i++) {
      final e = lst[i] is Map ? Map<String, dynamic>.from(lst[i] as Map) : <String, dynamic>{};
      print('  ${C.train('[${i + 1}]')} ${C.b((e['name'] ?? e['stationName'] ?? '?').toString())}');
    }
    final s = (readInput('Numero stazione (0 = nuova ricerca): ') ?? '').trim();
    final idx = int.tryParse(s) ?? -1;
    if (s == '0' || idx < 1 || idx > lst.length) continue;
    final sel = Map<String, dynamic>.from(lst[idx - 1] as Map);
    final sid = '${sel['id'] ?? sel['stationId'] ?? ''}';
    final m = (readInput('Tasto 1) Partenze  2) Arrivi  [1]: ') ?? '').trim();
    var arrivi = m == '2';
    var board = <Map<String, dynamic>>[];
    while (true) {
      board = await cmdTrainBoard(sid, country, arrivi);
      final nxt = (readInput('\nTasto 1) Altra stazione  2) Cambia nazione  '
              '3) Passa a ${arrivi ? 'Partenze' : 'Arrivi'}  4) Timeline treno  0) Menu  [1]: ') ?? '').trim();
      final choice = nxt.isEmpty ? '1' : nxt;
      if (choice == '3') {
        arrivi = !arrivi;
      } else if (choice == '4') {
        if (board.isEmpty) {
          printWarn('Nessuna riga disponibile.');
          continue;
        }
        final r = (readInput('Numero riga del treno [1-${board.length}]: ') ?? '').trim();
        final idx = int.tryParse(r) ?? -1;
        if (idx < 1 || idx > board.length) {
          printWarn('Numero non valido.');
          continue;
        }
        final row = board[idx - 1];
        // Come il sheet dell'app: dettaglio via tripId della riga
        final tripId = '${row['tripId'] ?? ''}';
        if (tripId.isNotEmpty) {
          await cmdTrainTrip(tripId, country);
        } else {
          final num = '${row['tripNumber'] ?? row['trainNumber'] ?? ''}';
          if (num.isEmpty) {
            printWarn('Trip non disponibile per questa riga.');
            continue;
          }
          await cmdTrainDetails(num, sid, country);
        }
      } else if (choice == '2') {
        country = ((readInput('Codice paese [IT]: ') ?? '').trim());
        if (country.isEmpty) country = 'IT';
        country = country.toUpperCase();
        break;
      } else if (choice == '0') {
        return;
      } else {
        break;
      }
    }
  }
}

Future<void> simpleBus() async {
  List<dynamic> provs = [];
  try {
    final data = await getJson('$kBase/config/bus_providers.json');
    if (data is Map && data['providers'] is List) {
      provs = data['providers'] as List;
    }
  } catch (e) {
    printErr('Errore providers: $e');
    return;
  }
  if (provs.isEmpty) {
    printWarn('Nessun provider.');
    return;
  }
  for (var i = 0; i < provs.length; i++) {
    final p = provs[i] is Map ? Map<String, dynamic>.from(provs[i] as Map) : <String, dynamic>{};
    print('  ${C.bus('[${i + 1}]')} ${p['name'] ?? '?'}');
  }
  final s0 = (readInput('Numero provider [1]: ') ?? '').trim();
  final pi = (int.tryParse(s0.isEmpty ? '1' : s0) ?? 1) - 1;
  final sel = Map<String, dynamic>.from(
      provs[(pi < 0 || pi >= provs.length) ? 0 : pi] as Map);
  final provider = '${sel['name']}';
  printInfo('Provider: $provider — scarico fermate…');
  List<dynamic> stops = [];
  try {
    final data = await getJson('$kBase/api/it/bus/$provider/stops');
    if (data is List) {
      stops = data;
    } else if (data is Map && data['stops'] is List) {
      stops = data['stops'] as List;
    }
  } catch (e) {
    printErr('Errore fermate: $e');
    return;
  }
  printOk('${stops.length} fermate caricate.');
  while (true) {
    final q = (readInput('\nNome fermata (0 = menu): ') ?? '').trim();
    if (q.isEmpty || q == '0') return;
    final found = stops.where((x) {
      if (x is! Map) return false;
      final m = Map<String, dynamic>.from(x as Map);
      final name = '${m['stop_name'] ?? m['stopName'] ?? m['name'] ?? ''}';
      final sid = '${m['stop_id'] ?? m['stopId'] ?? m['id'] ?? ''}';
      return name.toLowerCase().contains(q.toLowerCase()) || sid.contains(q);
    }).toList().take(10).toList();
    if (found.isEmpty) {
      printWarn('Nessuna fermata trovata, riprova.');
      continue;
    }
    Map<String, dynamic>? byId;
    for (final f in found) {
      final m = Map<String, dynamic>.from(f as Map);
      if ('${m['stop_id'] ?? m['stopId'] ?? m['id'] ?? ''}' == q) byId = m;
    }
    if (byId != null) {
      // Incollato direttamente l'ID: usa subito la fermata
      await cmdBusDepartures(
          provider, '${byId['stop_id'] ?? byId['stopId'] ?? byId['id'] ?? ''}', 'it');
    } else {
      for (var i = 0; i < found.length; i++) {
        final m = Map<String, dynamic>.from(found[i] as Map);
        print('  ${C.bus('[${i + 1}]')} ${m['stop_name'] ?? m['stopName'] ?? m['name']}');
      }
      final s = (readInput('Numero fermata o ID diretto (0 = nuova ricerca): ') ?? '').trim();
      if (s == '0' || s.isEmpty) continue;
      Map<String, dynamic>? sel;
      for (final f in found) {
        final m = Map<String, dynamic>.from(f as Map);
        if ('${m['stop_id'] ?? m['stopId'] ?? m['id'] ?? ''}' == s) sel = m;
      }
      sel ??= (() {
        final idx = int.tryParse(s) ?? -1;
        if (idx < 1 || idx > found.length) return null;
        return Map<String, dynamic>.from(found[idx - 1] as Map);
      })();
      if (sel == null) {
        printWarn('Numero non valido.');
        continue;
      }
      await cmdBusDepartures(
          provider, '${sel['stop_id'] ?? sel['stopId'] ?? sel['id'] ?? ''}', 'it');
    }
    final nxt = (readInput('\nTasto 1) Altra fermata  0) Menu  [1]: ') ?? '').trim();
    if (nxt == '0') return;
  }
}

Future<void> simpleFly() async {
  while (true) {
    final q = (readInput('\nAeroporto, città o codice (0 = menu): ') ?? '').trim();
    if (q.isEmpty || q == '0') return;
    if (q.length == 3) {
      var arrivi = false;
      final m = (readInput('Tasto 1) Partenze  2) Arrivi  [1]: ') ?? '').trim();
      arrivi = m == '2';
      while (true) {
        await cmdAirport(q.toUpperCase(), arrivi);
        final nxt = (readInput('\nTasto 1) Altro aeroporto  '
                '2) Passa a ${arrivi ? 'Partenze' : 'Arrivi'}  0) Menu  [1]: ') ?? '').trim();
        final choice = nxt.isEmpty ? '1' : nxt;
        if (choice == '2') {
          arrivi = !arrivi;
        } else if (choice == '0') {
          return;
        } else {
          break;
        }
      }
      continue;
    }
    if (q.length < 2) {
      printWarn('Scrivi almeno 2 caratteri.');
      continue;
    }
    await cmdSearchAirports(q);
    printDim('Poi usa: voli --aeroporto <IATA>  (o modalità comandi)');
  }
}

Future<void> simpleFlix() async {
  while (true) {
    final q = (readInput('\nStazione Flixbus (0 = menu): ') ?? '').trim();
    if (q.isEmpty || q == '0') return;
    await cmdFlixStations(q);
    final id = (readInput('ID stazione per partenze (0 = nuova ricerca): ') ?? '').trim();
    if (id.isNotEmpty && id != '0') await cmdFlixDepartures(id);
  }
}

Future<void> commandsMode() async {
  // Modalità comandi: prima il trasporto, poi riga di comando (prefisso automatico)
  printTitle('⌨️ Modalità comandi (0 = menu)');
  print('  ${C.dim_('0) Nessun prefisso (comando libero)')}');
  final t = ((readInput('Numero trasporto per prefisso automatico [0]: ') ?? '').trim());
  const prefix = {'1': 'treni', '2': 'bus', '3': 'voli', '4': 'flixbus'};
  final pre = prefix[t.isEmpty ? '0' : t];
  printDim('Esempi: treni --partenze S11119 --paese IT · voli --area · bus --providers'
      '${pre != null ? '  (oppure solo gli argomenti: prefisso $pre automatico)' : ''}'
      '  ·  help = guida');
  while (true) {
    stdout.write(C.info(pre != null ? 'bc:$pre> ' : 'bc> '));
    final line = stdin.readLineSync()?.trim() ?? '';
    if (line.isEmpty || ['0', 'indietro', 'menu', 'q', 'exit'].contains(line.toLowerCase())) return;
    if (['help', 'aiuto', 'guida', '?'].contains(line.toLowerCase())) {
      printHelp();
      continue;
    }
    final parts = splitArgs(line);
    if (parts.isEmpty) continue;
    if (isCommand(parts.first)) {
      await main(parts);
    } else if (pre != null) {
      await main([pre, ...splitArgs(line)]);
    } else {
      printWarn('Comando sconosciuto.');
    }
  }
}

bool isCommand(String w) {
  switch (w.toLowerCase()) {
    case 'treni':
    case 'bus':
    case 'voli':
    case 'flixbus':
    case 'regionali':
    case 'strade':
    case 'meteo':
    case 'social':
    case 'config':
    case 'auth':
    case 'preferiti':
    case 'offline':
      return true;
    default:
      return false;
  }
}

Future<void> advancedMenu() async {
  while (true) {
    print('\n${C.title('MENU AVANZATO (0 = indietro)')}');
    print('  ${C.train('1)')} 🚂 Treni  (stazioni, partenze, dettagli, FAL, live, share)');
    print('  ${C.bus('2)')} 🚌 Bus    (provider, linee, fermate, live, realtime)');
    print('  ${C.plane('3)')} ✈️  Voli   (radar + aeroporti + ricerca)');
    print('  ${C.ok('4)')} 🟢 Flixbus');
    print('  ${C.train('5)')} 🏳️ Regionali (trenord & co.)');
    print('  ${C.warn('6)')} 🛣️ Strade + 🌤️ Meteo');
    print('  ${C.fal('7)')} 💬 Social + 👁️ Presence');
    print('  ${C.info('8)')} ⚙️ Config/Stats + ⭐ Preferiti + 💾 Offline');
    print('  ${C.dim_('0) Indietro')}');
    final c = readInput('\nScelta [0-8]: ');
    final first = (c ?? '').split(' ').first.toLowerCase();
    if (isCommand(first)) {
      await main(splitArgs(c ?? ''));
      continue;
    }
    switch (c) {
      case '1':
        await menuTreni();
        break;
      case '2':
        await menuBus();
        break;
      case '3':
        await menuVoli();
        break;
      case '4':
        await menuFlix();
        break;
      case '5':
        final pa = (readInput('Paese [IT]: ') ?? '').toUpperCase();
        await cmdRegProviders(pa.isEmpty ? 'IT' : pa);
        break;
      case '6':
        await cmdRoadNews('it');
        await cmdMeteoNow(41.9028, 12.4964, 'Roma');
        break;
      case '7':
        await cmdSocialFeed();
        await cmdSocialOnline();
        break;
      case '8':
        await cmdConfigShow();
        await cmdFavList();
        await cmdOfflineSize();
        break;
      case '0':
      case 'q':
      case 'exit':
      case 'menu':
      case 'indietro':
        return;
      default:
        printWarn('Scelta non valida.');
    }
  }
}

Future<void> interactiveMenu() async {
  printBanner();
  while (true) {
    print('\n${C.title('MENU PRINCIPALE')}');
    print('  ${C.train('1)')} 🟢 Modalità semplice  (nazione → stazione → tabellone)');
    print('  ${C.bus('2)')} ⌨️  Modalità comandi   (scrivi il comando diretto)');
    print('  ${C.fal('3)')} 🧰 Menu avanzato      (tutte le funzioni)');
    print('  ${C.dim_('0) Esci')}');
    final c = (readInput('\nScelta [0-3]: ') ?? '').trim();
    if (c == '1') {
      await simpleMode();
    } else if (c == '2') {
      await commandsMode();
    } else if (c == '3') {
      await advancedMenu();
    } else if (c.isNotEmpty && isCommand(c.split(' ').first)) {
      await main(splitArgs(c));
    } else if (c == '0' || c == 'q' || c == 'exit') {
      printOk('Ciao! 👋');
      return;
    } else {
      printWarn('Scelta non valida: premi 1, 2, 3 oppure scrivi un comando.');
    }
  }
}

Future<void> menuTreni() async {
  printTitle('🚂 Treni');
  print('  1) Cerca stazione');
  print('  2) Partenze/Arrivi stazione (serve id)');
  print('  3) Dettaglio treno (serve numero + id stazione)');
  print('  4) Cerca treno live per numero');
  print('  5) FAL (Puglia/Basilicata)');
  print('  0) Indietro');
  final c = readInput('Scelta: ');
  final paese = readInput('Paese [IT]: ') ?? '';
  final p = paese.isEmpty ? 'IT' : paese.toUpperCase();
  switch (c) {
    case '1':
      final q = readInput('Nome stazione: ') ?? '';
      if (q.isNotEmpty) await cmdTrainSearch(q, p);
      break;
    case '2':
      final id = readInput('ID stazione: ') ?? '';
      final a = readInput('Arrivi? [s/N]: ') ?? '';
      if (id.isNotEmpty) {
        await cmdTrainBoard(id, p, a.toLowerCase().startsWith('s'));
      }
      break;
    case '3':
      final n = readInput('Numero treno: ') ?? '';
      final s = readInput('ID stazione: ') ?? '';
      if (n.isNotEmpty && s.isNotEmpty) await cmdTrainDetails(n, s, p);
      break;
    case '4':
      final q = readInput('Numero/nome linea (es. 5440, FR, S4): ') ?? '';
      if (q.isNotEmpty) await cmdTrainNumber(q);
      break;
    case '5':
      final s = readInput('ID stazione FAL: ') ?? '';
      if (s.isNotEmpty) await cmdFal(s);
      break;
  }
}

Future<void> menuBus() async {
  printTitle('🚌 Bus');
  print('  1) Lista provider');
  print('  2) Linee di un provider');
  print('  3) Fermate di un provider');
  print('  4) Partenze da una fermata');
  print('  5) Veicoli live');
  print('  0) Indietro');
  final c = readInput('Scelta: ');
  switch (c) {
    case '1':
      await cmdBusProviders();
      break;
    case '2':
      final pr = readInput('Provider (es. bari): ') ?? '';
      if (pr.isNotEmpty) await cmdBusLines(pr, '');
      break;
    case '3':
      final pr = readInput('Provider (es. bari): ') ?? '';
      if (pr.isNotEmpty) await cmdBusStops(pr, '');
      break;
    case '4':
      final pr = readInput('Provider (es. bari): ') ?? '';
      final st = readInput('ID fermata: ') ?? '';
      if (pr.isNotEmpty && st.isNotEmpty) {
        await cmdBusDepartures(pr, st, '');
      }
      break;
    case '5':
      final pr = readInput('Provider (es. bari): ') ?? '';
      if (pr.isNotEmpty) await cmdBusVehicles(pr, '');
      break;
  }
}

Future<void> menuVoli() async {
  printTitle('✈️ Voli');
  print('  1) Radar sull\'Italia');
  print('  2) Partenze/arrivi aeroporto (IATA, es. BRI, FCO, MXP)');
  print('  0) Indietro');
  final c = readInput('Scelta: ');
  switch (c) {
    case '1':
      await cmdFlightsArea();
      break;
    case '2':
      final iata = (readInput('Codice IATA: ') ?? '').toUpperCase();
      final a = readInput('Arrivi? [s/N]: ') ?? '';
      if (iata.isNotEmpty) {
        await cmdAirport(iata, a.toLowerCase().startsWith('s'));
      }
      break;
  }
}

Future<void> menuFlix() async {
  printTitle('🟢 Flixbus');
  final q = readInput('Cerca stazione (nome): ') ?? '';
  if (q.isEmpty) return;
  await cmdFlixStations(q);
  final id = readInput('ID stazione per partenze (invio = salta): ') ?? '';
  if (id.isNotEmpty) await cmdFlixDepartures(id);
}

// ---------------------------------------------------------------------------
// Arg parsing minimale
// ---------------------------------------------------------------------------

Map<String, String> parseOpts(List<String> args) {
  final m = <String, String>{};
  for (var i = 0; i < args.length; i++) {
    final a = args[i];
    if (a == '--no-color') {
      m['no-color'] = '1';
    } else if (a == '--help' || a == '-h') {
      m['help'] = '1';
    } else if (a == '--arrivi') {
      m['arrivi'] = '1';
    } else if (a.startsWith('--') && i + 1 < args.length && !args[i + 1].startsWith('--')) {
      m[a.substring(2)] = args[i + 1];
      i++;
    } else if (a.startsWith('--')) {
      m[a.substring(2)] = '1';
    }
  }
  return m;
}

List<String> positionals(List<String> args) =>
    args.where((a) => !a.startsWith('--')).toList();

Future<void> main(List<String> args) async {
  final opts = parseOpts(args);
  if (opts.containsKey('no-color') || !stdout.hasTerminal) {
    // Su terminale non-ANSI o con flag, disattiva i colori.
    if (opts.containsKey('no-color')) useColor = false;
  }
  // Windows: prova ad abilitare ANSI (su Windows Terminal funziona già).
  if (Platform.isWindows) {
    try {
      stdout.write('\x1B[0m');
    } catch (_) {}
  }

  if (opts.containsKey('help') || args.contains('help')) {
    printHelp();
    return;
  }

  final pos = positionals(args);
  if (pos.isEmpty) {
    await interactiveMenu();
    return;
  }

  final cmd = pos[0].toLowerCase();
  final paeseTrain = (opts['paese'] ?? opts['country'] ?? 'IT').toUpperCase();
  final paeseBus = (opts['paese'] ?? opts['country'] ?? '').toLowerCase();
  final arrivi = opts.containsKey('arrivi');

  try {
    switch (cmd) {
      case 'treni':
      case 'treno':
      case 'train':
        if (opts.containsKey('cerca')) {
          await cmdTrainSearch(opts['cerca']!, paeseTrain);
        } else if (opts.containsKey('partenze')) {
          await cmdTrainBoard(opts['partenze']!, paeseTrain, arrivi);
        } else if (opts.containsKey('treno') || opts.containsKey('numero-treno')) {
          final n = opts['treno'] ?? opts['numero-treno'] ?? '';
          final s = opts['stazione'] ?? '';
          if (s.isEmpty) {
            printErr('Serve --stazione <id>. Esempio: --treno 5440 --stazione <id>');
            return;
          }
          await cmdTrainDetails(n, s, paeseTrain);
        } else if (opts.containsKey('trip')) {
          await cmdTrainTrip(opts['trip']!, paeseTrain);
        } else if (opts.containsKey('numero')) {
          await cmdTrainNumber(opts['numero']!);
        } else if (opts.containsKey('fal')) {
          await cmdFal(opts['fal']!);
        } else if (opts.containsKey('diretta')) {
          await cmdTrainDirect(opts['diretta']!);
        } else if (opts.containsKey('condividi')) {
          await cmdTrainShare(opts['condividi']!, paeseTrain);
        } else if (opts.containsKey('live')) {
          await cmdTrainLive();
        } else if (opts.containsKey('track')) {
          await cmdTrainTrack(opts['track']!);
        } else if (opts.containsKey('stats-treno')) {
          final p = opts['stats-treno']!.split(' ');
          if (p.length >= 2) await cmdStatsTrain(p[0], p.sublist(1).join(' '));
        } else if (opts.containsKey('paesi')) {
          await cmdTrainCountries();
        } else if (opts.containsKey('categorie')) {
          await cmdTrainCategories();
        } else if (opts.containsKey('presence')) {
          await cmdPresence(opts['presence']!, opts['key'] ?? '');
        } else if (opts.containsKey('arrivi') && opts['arrivi'] != '1') {
          await cmdTrainBoard(opts['arrivi']!, paeseTrain, true);
        } else {
          printHelp();
        }
        break;
      case 'bus':
        if (opts.containsKey('providers')) {
          await cmdBusProviders();
        } else if (opts.containsKey('linee')) {
          await cmdBusLines(opts['linee']!, paeseBus);
        } else if (opts.containsKey('fermate')) {
          await cmdBusStops(opts['fermate']!, paeseBus);
        } else if (opts.containsKey('partenze')) {
          final parts = opts['partenze']!.split(' ');
          if (parts.length < 2) {
            printErr('Uso: bus --partenze "<provider> <stopId>"');
            return;
          }
          await cmdBusDepartures(parts[0], parts.sublist(1).join(' '), paeseBus);
        } else if (opts.containsKey('veicoli')) {
          await cmdBusVehicles(opts['veicoli']!, paeseBus);
        } else if (opts.containsKey('realtime')) {
          final p = opts['realtime']!.split(' ');
          final prov = opts['provider'] ?? 'bari';
          if (p.length < 2) {
            printErr('Uso: bus --realtime "<vehicleId> <tripId>" --provider bari');
            return;
          }
          await cmdBusRealtime(prov, p[0], p.sublist(1).join(' '), paeseBus);
        } else {
          printHelp();
        }
        break;
      case 'voli':
      case 'aerei':
        if (opts.containsKey('area')) {
          await cmdFlightsArea();
        } else if (opts.containsKey('aeroporto')) {
          await cmdAirport(opts['aeroporto']!.toUpperCase(), arrivi);
        } else if (opts.containsKey('cerca')) {
          await cmdSearchAirports(opts['cerca']!);
        } else {
          printHelp();
        }
        break;
      case 'flixbus':
        if (opts.containsKey('stazioni')) {
          await cmdFlixStations(opts['stazioni']!);
        } else if (opts.containsKey('partenze')) {
          await cmdFlixDepartures(opts['partenze']!);
        } else if (opts.containsKey('trip')) {
          await cmdFlixTrip(opts['trip']!);
        } else {
          printHelp();
        }
        break;
      case 'regionali':
        if (opts.containsKey('lista')) {
          await cmdRegProviders(opts['lista']!.toUpperCase());
        } else if (opts.containsKey('stazioni')) {
          final p = opts['stazioni']!.split(' ');
          if (p.length < 2) {
            printErr('Uso: regionali --stazioni "IT it/trains/trenord" [--cerca q]');
            return;
          }
          await cmdRegStations(p[0].toUpperCase(), p.sublist(1).join(' '), opts['cerca'] ?? '');
        } else if (opts.containsKey('partenze')) {
          final p = opts['partenze']!.split(' ');
          if (p.length < 3) {
            printErr('Uso: regionali --partenze "IT <prefix> <stationId>"');
            return;
          }
          await cmdRegBoard(p[0].toUpperCase(), p[1], p.sublist(2).join(' '), arrivi);
        } else {
          printHelp();
        }
        break;
      case 'strade':
        await cmdRoadNews((opts['paese'] ?? 'it').toLowerCase());
        break;
      case 'meteo':
        if (opts.containsKey('cerca')) {
          await cmdMeteoSearch(opts['cerca']!);
        } else {
          await cmdMeteoNow(41.9028, 12.4964, 'Roma');
        }
        break;
      case 'social':
        if (opts.containsKey('online')) {
          await cmdSocialOnline();
        } else {
          await cmdSocialFeed();
        }
        break;
      case 'config':
        if (opts.containsKey('loghi')) {
          await cmdTrainLogos();
        } else if (opts.containsKey('stats-general')) {
          await cmdStatsGeneral();
        } else {
          await cmdConfigShow();
        }
        break;
      case 'auth':
        await cmdAuthStatus();
        break;
      case 'preferiti':
        await cmdFavList();
        break;
      case 'offline':
        await cmdOfflineSize();
        break;
      default:
        printErr('Comando sconosciuto: $cmd');
        printHelp();
    }
  } catch (e) {
    printErr('Errore: $e');
    exitCode = 1;
  }
}
