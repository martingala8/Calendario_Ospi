#!/usr/bin/env python3
"""
Genera / aggiorna il calendario .ics delle partite dell'Ospitaletto Franciacorta
(Serie C, Girone A, stagione 2026/27).

Come funziona:
1. Parte da un calendario "seme" (BASE_MATCHES) con tutte le 38 giornate e le date
   ufficiali pubblicate dalla Lega Pro. Questo garantisce che il calendario sia SEMPRE
   corretto anche se lo scraping fallisce.
2. Prova a recuperare online gli orari di calcio d'inizio confermati (che la Lega Pro
   pubblica progressivamente, di solito 2-3 settimane prima di ogni giornata) da
   tuttocampo.it. Se un orario viene trovato, sovrascrive l'orario "segnaposto".
3. Scrive il file docs/ospitaletto.ics, pronto per essere pubblicato con GitHub Pages
   e sottoscritto da iPhone.

Se lo scraping fallisce (sito irraggiungibile, protezione anti-bot, HTML cambiato),
lo script NON si blocca: mantiene semplicemente gli orari già noti/segnaposto e va
comunque a buon fine, così il workflow settimanale non "rompe" mai il calendario.
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

# Orario segnaposto usato finché la Lega Pro non conferma l'orario ufficiale.
PLACEHOLDER_TIME = "15:00"

# Fonte usata per provare ad aggiornare gli orari confermati.
SCRAPE_URL = "https://www.tuttocampo.it/Italia/SerieC/GironeA/Squadra/Ospitaletto/675840/Calendario"

# --------------------------------------------------------------------------------
# Calendario "seme": tutte le 38 giornate, stagione 2026/27, Serie C Girone A.
# Fonte: pubblicazione ufficiale calendari Lega Pro (agosto 2026).
# Formato: (giornata, data ISO, avversario, "H" casa / "A" trasferta, orario o None)
# --------------------------------------------------------------------------------
BASE_MATCHES = [
    (1, "2026-08-22", "Lumezzane", "H", "18:00"),
    (2, "2026-08-31", "AlbinoLeffe", "A", "21:00"),
    (3, "2026-09-06", "Arzignano Valchiampo", "H", None),
    (4, "2026-09-13", "Juventus Next Gen", "H", "18:00"),
    (5, "2026-09-17", "Carpi", "A", None),
    (6, "2026-09-20", "Cittadella", "H", None),
    (7, "2026-09-26", "Novara", "A", None),
    (8, "2026-10-03", "Renate", "H", None),
    (9, "2026-10-11", "Treviso", "A", None),
    (10, "2026-10-18", "Pergolettese", "H", None),
    (11, "2026-10-25", "Pro Vercelli", "A", None),
    (12, "2026-11-01", "Trento", "H", None),
    (13, "2026-11-08", "Desenzano", "A", None),
    (14, "2026-11-15", "Dolomiti Bellunesi", "H", None),
    (15, "2026-11-22", "Alcione Milano", "A", None),
    (16, "2026-11-29", "Union Brescia", "H", None),
    (17, "2026-12-06", "Lecco", "A", None),
    (18, "2026-12-13", "Giana Erminio", "H", None),
    (19, "2026-12-20", "Folgore Caratese", "A", None),
    (20, "2027-01-03", "Lumezzane", "A", None),
    (21, "2027-01-10", "AlbinoLeffe", "H", None),
    (22, "2027-01-17", "Arzignano Valchiampo", "A", None),
    (23, "2027-01-24", "Juventus Next Gen", "A", None),
    (24, "2027-01-31", "Carpi", "H", None),
    (25, "2027-02-07", "Cittadella", "A", None),
    (26, "2027-02-10", "Novara", "H", None),
    (27, "2027-02-14", "Renate", "A", None),
    (28, "2027-02-21", "Treviso", "H", None),
    (29, "2027-02-28", "Pergolettese", "A", None),
    (30, "2027-03-03", "Pro Vercelli", "H", None),
    (31, "2027-03-07", "Trento", "A", None),
    (32, "2027-03-14", "Desenzano", "H", None),
    (33, "2027-03-21", "Dolomiti Bellunesi", "A", None),
    (34, "2027-03-27", "Alcione Milano", "H", None),
    (35, "2027-04-04", "Union Brescia", "A", None),
    (36, "2027-04-11", "Lecco", "H", None),
    (37, "2027-04-18", "Giana Erminio", "A", None),
    (38, "2027-04-25", "Folgore Caratese", "H", None),
]


def try_scrape_confirmed_times():
    """Prova a recuperare orari confermati da tuttocampo.it.
    Ritorna un dict {"YYYY-MM-DD": "HH:MM"} oppure {} se qualcosa fallisce.
    Non solleva mai eccezioni verso il chiamante.
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
        resp = requests.get(SCRAPE_URL, headers=headers, timeout=20)
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

    # Cerca pattern tipo "22/08/2026 18:00" o "22/08 18:00" nel testo della pagina.
    found = {}
    for m in re.finditer(r"(\d{1,2})/(\d{1,2})/(\d{4}).{0,15}?(\d{1,2}):(\d{2})", text):
        day, month, year, hh, mm = m.groups()
        try:
            iso_date = datetime(int(year), int(month), int(day)).strftime("%Y-%m-%d")
            found[iso_date] = f"{int(hh):02d}:{mm}"
        except ValueError:
            continue

    if found:
        print(f"Trovati {len(found)} orari via scraping.", file=sys.stderr)
    else:
        print("Nessun orario nuovo trovato via scraping.", file=sys.stderr)
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

    for giornata, date_iso, opponent, venue, confirmed_time in matches:
        time_str = confirmed_time or PLACEHOLDER_TIME
        is_placeholder = confirmed_time is None
        dt = datetime.strptime(f"{date_iso} {time_str}", "%Y-%m-%d %H:%M").replace(tzinfo=TZ)
        dt_end = dt + timedelta(hours=2)

        if venue == "H":
            summary = f"{TEAM_NAME} - {opponent}"
            location = "Stadio Comunale, Ospitaletto (BS)"
        else:
            summary = f"{opponent} - {TEAM_NAME}"
            location = opponent

        if is_placeholder:
            summary += " (orario da confermare)"

        uid = f"ospitaletto-g{giornata:02d}-{date_iso}@ospitaletto-calendar"
        desc = f"Giornata {giornata} - Serie C Girone A 2026/27."
        if is_placeholder:
            desc += " Orario provvisorio, verra' aggiornato appena la Lega Pro lo conferma."

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
    confirmed = try_scrape_confirmed_times()
    matches = []
    for giornata, date_iso, opponent, venue, known_time in BASE_MATCHES:
        time_to_use = confirmed.get(date_iso, known_time)
        matches.append((giornata, date_iso, opponent, venue, time_to_use))

    ics_content = build_ics(matches)
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text(ics_content, encoding="utf-8")
    print(f"Scritto {OUTPUT_FILE} con {len(matches)} partite.")


if __name__ == "__main__":
    main()
