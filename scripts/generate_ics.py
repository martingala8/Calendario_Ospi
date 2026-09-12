#!/usr/bin/env python3
"""
Genera / aggiorna il calendario .ics delle partite dell'Ospitaletto Franciacorta
(Serie C, Girone A, stagione 2026/27).

Fonte dati: la pagina calendario del sito UFFICIALE della Lega Pro
(https://www.seriec.com/calendario). Questa pagina pubblica fin da subito
data e orario di TUTTE le giornate della stagione (per le giornate lontane
l'orario e' spesso un default, es. 15:00 la domenica, e viene poi affinato
dalla Lega Pro con gli anticipi/posticipi) - quindi ogni volta che lo script
gira, legge semplicemente l'orario piu' aggiornato disponibile in quel
momento, senza bisogno di indovinare nulla.

Come funziona:
1. Parte da un calendario "seme" (BASE_MATCHES) con tutte le 38 giornate,
   cosi' il calendario e' sempre corretto anche se il sito non risponde.
2. Scarica la pagina https://www.seriec.com/calendario e cerca tutte le
   partite che coinvolgono "OSPITALETTO F.", estraendo data, ora e avversario.
3. Scrive il file docs/ospitaletto.ics, pronto per GitHub Pages e per essere
   sottoscritto da iPhone.

Se lo scraping fallisce (rete assente, sito irraggiungibile, HTML cambiato),
lo script NON si blocca: mantiene gli orari gia' noti e va comunque a buon
fine, cosi' il workflow settimanale non "rompe" mai il calendario.
"""

import re
import sys
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

try:
    import requests
    from bs4 import BeautifulSoup
    SCRAPING_AVAILABLE = True
except ImportError:
    SCRAPING_AVAILABLE = False

TZ = ZoneInfo("Europe/Rome")
TEAM_NAME = "Ospitaletto Franciacorta"
OUTPUT_FILE = Path(__file__).resolve().parent.parent / "docs" / "ospitaletto.ics"

CALENDAR_URL = "https://www.seriec.com/calendario"
TEAM_MARKER = "OSPITALETTO F."

MONTHS = {
    "gen": 1, "feb": 2, "mar": 3, "apr": 4, "mag": 5, "giu": 6,
    "lug": 7, "ago": 8, "set": 9, "ott": 10, "nov": 11, "dic": 12,
}

# Squadre possibili nel Girone A 2026/27 (usate per riconoscere l'avversario
# dentro il testo grezzo della pagina). L'ordine conta: i nomi piu' lunghi
# vanno controllati per primi per evitare match parziali sbagliati.
# Squadre possibili nel Girone A 2026/27: mappa da stringa cercata nel testo
# al nome canonico da usare nel titolo dell'evento. Le chiavi piu' lunghe
# vengono controllate per prime per evitare match parziali sbagliati.
OPPONENT_MAP = {
    "Dolomiti Bellunesi": "Dolomiti Bellunesi",
    "Folgore Caratese": "Folgore Caratese",
    "Alcione Milano": "Alcione Milano",
    "Union Brescia": "Union Brescia",
    "Pro Vercelli": "Pro Vercelli",
    "Giana Erminio": "Giana Erminio",
    "Arzignano Valchiampo": "Arzignano Valchiampo",
    "Arzignano V.": "Arzignano Valchiampo",
    "Arzignano": "Arzignano Valchiampo",
    "Juventus Next Gen": "Juventus Next Gen",
    "Pergolettese": "Pergolettese",
    "AlbinoLeffe": "AlbinoLeffe",
    "Cittadella": "Cittadella",
    "Desenzano": "Desenzano",
    "Lumezzane": "Lumezzane",
    "Novara": "Novara",
    "Renate": "Renate",
    "Treviso": "Treviso",
    "Trento": "Trento",
    "Lecco": "Lecco",
    "Carpi": "Carpi",
}
KNOWN_OPPONENTS = sorted(OPPONENT_MAP.keys(), key=len, reverse=True)

# Pattern che identifica l'inizio di ogni singola partita nel testo della
# pagina, es: "Dom 13 Set 15:00"
MATCH_START_RE = re.compile(
    r"(Lun|Mar|Mer|Gio|Ven|Sab|Dom)\s+(\d{1,2})\s+"
    r"(Gen|Feb|Mar|Apr|Mag|Giu|Lug|Ago|Set|Ott|Nov|Dic)\s+(\d{1,2}):(\d{2})",
    re.IGNORECASE,
)

# --------------------------------------------------------------------------------
# Calendario "seme": tutte le 38 giornate, stagione 2026/27, Serie C Girone A.
# Usato come base sicura se lo scraping dal sito ufficiale dovesse fallire.
# Formato: (giornata, data ISO, avversario, "H" casa / "A" trasferta, orario)
# --------------------------------------------------------------------------------
BASE_MATCHES = [
    (1, "2026-08-22", "Lumezzane", "H", "18:00"),
    (2, "2026-08-31", "AlbinoLeffe", "A", "21:00"),
    (3, "2026-09-06", "Arzignano Valchiampo", "H", "21:00"),
    (4, "2026-09-13", "Juventus Next Gen", "H", "18:00"),
    (5, "2026-09-17", "Carpi", "A", "21:00"),
    (6, "2026-09-20", "Cittadella", "H", "14:30"),
    (7, "2026-09-26", "Novara", "A", "17:30"),
    (8, "2026-10-03", "Renate", "H", "20:30"),
    (9, "2026-10-11", "Treviso", "A", "15:00"),
    (10, "2026-10-18", "Pergolettese", "H", "15:00"),
    (11, "2026-10-25", "Pro Vercelli", "A", "15:00"),
    (12, "2026-11-01", "Trento", "H", "15:00"),
    (13, "2026-11-08", "Desenzano", "A", "15:00"),
    (14, "2026-11-15", "Dolomiti Bellunesi", "H", "15:00"),
    (15, "2026-11-22", "Alcione Milano", "A", "15:00"),
    (16, "2026-11-29", "Union Brescia", "H", "15:00"),
    (17, "2026-12-06", "Lecco", "A", "15:00"),
    (18, "2026-12-13", "Giana Erminio", "H", "15:00"),
    (19, "2026-12-20", "Folgore Caratese", "A", "15:00"),
    (20, "2027-01-03", "Lumezzane", "A", "15:00"),
    (21, "2027-01-10", "AlbinoLeffe", "H", "15:00"),
    (22, "2027-01-17", "Arzignano Valchiampo", "A", "15:00"),
    (23, "2027-01-24", "Juventus Next Gen", "A", "15:00"),
    (24, "2027-01-31", "Carpi", "H", "15:00"),
    (25, "2027-02-07", "Cittadella", "A", "15:00"),
    (26, "2027-02-10", "Novara", "H", "20:45"),
    (27, "2027-02-14", "Renate", "A", "15:00"),
    (28, "2027-02-21", "Treviso", "H", "15:00"),
    (29, "2027-02-28", "Pergolettese", "A", "15:00"),
    (30, "2027-03-03", "Pro Vercelli", "H", "20:45"),
    (31, "2027-03-07", "Trento", "A", "15:00"),
    (32, "2027-03-14", "Desenzano", "H", "15:00"),
    (33, "2027-03-21", "Dolomiti Bellunesi", "A", "15:00"),
    (34, "2027-03-27", "Alcione Milano", "H", "15:00"),
    (35, "2027-04-04", "Union Brescia", "A", "15:00"),
    (36, "2027-04-11", "Lecco", "H", "15:00"),
    (37, "2027-04-18", "Giana Erminio", "A", "15:00"),
    (38, "2027-04-25", "Folgore Caratese", "H", "15:00"),
]


def scrape_official_calendar():
    """Scarica e legge https://www.seriec.com/calendario, ritornando un dict
    {"YYYY-MM-DD": (orario, avversario, venue)} con tutte le partite trovate
    dell'Ospitaletto. Non solleva mai eccezioni: in caso di problemi ritorna
    un dict vuoto, cosi' lo script prosegue con i dati gia' noti (BASE_MATCHES).
    """
    if not SCRAPING_AVAILABLE:
        print("requests/bs4 non disponibili, salto lo scraping.", file=sys.stderr)
        return {}

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
        ),
        "Accept-Language": "it-IT,it;q=0.9",
    }
    try:
        resp = requests.get(CALENDAR_URL, headers=headers, timeout=30)
        resp.raise_for_status()
    except Exception as exc:  # noqa: BLE001
        print(f"Scraping fallito ({exc}), mantengo gli orari noti.", file=sys.stderr)
        return {}

    try:
        soup = BeautifulSoup(resp.text, "html.parser")
        text = soup.get_text(" ", strip=True)
    except Exception as exc:  # noqa: BLE001
        print(f"Parsing HTML fallito ({exc}).", file=sys.stderr)
        return {}

    starts = list(MATCH_START_RE.finditer(text))
    found = {}

    for i, m in enumerate(starts):
        seg_start = m.start()
        seg_end = starts[i + 1].start() if i + 1 < len(starts) else len(text)
        segment = text[seg_start:seg_end]

        if TEAM_MARKER not in segment:
            continue

        day, month_str, hh, mm = m.group(2), m.group(3).lower(), m.group(4), m.group(5)
        month = MONTHS.get(month_str)
        if not month:
            continue
        # Ago-Dic = 2026, Gen-Lug = 2027 (stagione a cavallo d'anno)
        year = 2026 if month >= 8 else 2027
        try:
            date_iso = datetime(year, month, int(day)).strftime("%Y-%m-%d")
        except ValueError:
            continue
        time_str = f"{int(hh):02d}:{mm}"

        # Determina casa/trasferta: se "OSPITALETTO F." compare nei primi ~40
        # caratteri del segmento (subito dopo l'orario) e' in casa, altrimenti
        # e' in trasferta (compare verso la fine, dopo lo score o il "VS").
        marker_pos = segment.find(TEAM_MARKER)
        header_len = len(m.group(0))
        is_home = marker_pos <= header_len + 15

        opponent = None
        for name in KNOWN_OPPONENTS:
            if name.lower() in segment.lower():
                opponent = OPPONENT_MAP[name]
                break

        if opponent is None:
            continue  # non sono riuscito a capire l'avversario, salto per sicurezza

        found[date_iso] = (time_str, opponent, "H" if is_home else "A")

    if found:
        print(f"Trovate {len(found)} partite via seriec.com.", file=sys.stderr)
    else:
        print("Nessuna partita trovata via scraping (pagina cambiata?).", file=sys.stderr)
    return found


def build_ics(matches):
    now_stamp = datetime.now(ZoneInfo("UTC")).strftime("%Y%m%dT%H%M%SZ")
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//ospitaletto-calendar//IT",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        "X-WR-CALNAME:Ospitaletto Franciacorta - Serie C Girone A",
        "X-WR-TIMEZONE:Europe/Rome",
        "REFRESH-INTERVAL;VALUE=DURATION:P1D",
        "X-PUBLISHED-TTL:P1D",
    ]

    for giornata, date_iso, opponent, venue, time_str in matches:
        dt = datetime.strptime(f"{date_iso} {time_str}", "%Y-%m-%d %H:%M").replace(tzinfo=TZ)
        dt_end = dt + timedelta(hours=2)

        if venue == "H":
            summary = f"{TEAM_NAME} - {opponent}"
            location = "Stadio Comunale, Ospitaletto (BS)"
        else:
            summary = f"{opponent} - {TEAM_NAME}"
            location = opponent

        uid = f"ospitaletto-g{giornata:02d}-{date_iso}@ospitaletto-calendar"
        desc = f"Giornata {giornata} - Serie C Girone A 2026/27."

        lines += [
            "BEGIN:VEVENT",
            f"UID:{uid}",
            f"DTSTAMP:{now_stamp}",
            f"DTSTART;TZID=Europe/Rome:{dt.strftime('%Y%m%dT%H%M%S')}",
            f"DTEND;TZID=Europe/Rome:{dt_end.strftime('%Y%m%dT%H%M%S')}",
            f"SUMMARY:{summary}",
            f"LOCATION:{location}",
            f"DESCRIPTION:{desc}",
            "END:VEVENT",
        ]

    lines.append("END:VCALENDAR")
    return "\r\n".join(lines) + "\r\n"


def main():
    scraped = scrape_official_calendar()
    matches = []
    for giornata, date_iso, opponent, venue, known_time in BASE_MATCHES:
        if date_iso in scraped:
            time_str, scraped_opponent, scraped_venue = scraped[date_iso]
            matches.append((giornata, date_iso, scraped_opponent, scraped_venue, time_str))
        else:
            matches.append((giornata, date_iso, opponent, venue, known_time))

    ics_content = build_ics(matches)
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text(ics_content, encoding="utf-8")
    print(f"Scritto {OUTPUT_FILE} con {len(matches)} partite.")


if __name__ == "__main__":
    main()
