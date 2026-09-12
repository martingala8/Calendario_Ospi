#!/usr/bin/env python3
"""
Genera / aggiorna il calendario .ics delle partite dell'Ospitaletto Franciacorta
(Serie C, Girone A, stagione 2026/27).

Fonte dati: l'API pubblica e gratuita di TheSportsDB (thesportsdb.com), che
copre la Serie C Girone A 2026/27 (ID lega 5340, ID squadra Ospitaletto 149237)
con date e orari confermati, senza bisogno di scraping HTML fragile.

Come funziona:
1. Parte da un calendario "seme" (BASE_MATCHES) con tutte le 38 giornate e le
   date ufficiali della Lega Pro. Garantisce che il calendario sia sempre
   corretto anche se l'API non risponde.
2. Chiama l'endpoint pubblico "eventsnext" di TheSportsDB, che restituisce le
   prossime partite della squadra con orario ufficiale confermato (quando
   disponibile), e aggiorna gli orari corrispondenti.
3. Scrive il file docs/ospitaletto.ics, pronto per GitHub Pages e per essere
   sottoscritto da iPhone.

Se la chiamata all'API fallisce (rete assente, servizio irraggiungibile),
lo script NON si blocca: mantiene gli orari gia' noti e va comunque a buon
fine, cosi' il workflow settimanale non "rompe" mai il calendario.
"""

import sys
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False

TZ_ROME = ZoneInfo("Europe/Rome")
TZ_UTC = ZoneInfo("UTC")
TEAM_NAME = "Ospitaletto Franciacorta"
OUTPUT_FILE = Path(__file__).resolve().parent.parent / "docs" / "ospitaletto.ics"

# Orario segnaposto usato finche' non e' disponibile un orario confermato.
PLACEHOLDER_TIME = "15:00"

# TheSportsDB: chiave di test pubblica "3" (limitata ma sufficiente per un
# uso leggero come questo, poche chiamate a settimana). ID squadra Ospitaletto.
THESPORTSDB_TEAM_ID = "149237"
THESPORTSDB_URL = f"https://www.thesportsdb.com/api/v1/json/123/eventsnext.php?id={THESPORTSDB_TEAM_ID}"

# --------------------------------------------------------------------------------
# Calendario "seme": tutte le 38 giornate, stagione 2026/27, Serie C Girone A.
# Fonte: pubblicazione ufficiale calendari Lega Pro (agosto 2026), con orari
# confermati per le giornate 1-8 (fonti incrociate: club, avversari, Lega Pro).
# Formato: (giornata, data ISO, avversario, "H" casa / "A" trasferta, orario o None)
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


def fetch_confirmed_times_from_api():
    """Chiama TheSportsDB e ritorna un dict {"YYYY-MM-DD": "HH:MM"} con gli
    orari (convertiti in ora italiana) delle prossime partite dell'Ospitaletto.
    Non solleva mai eccezioni verso il chiamante: in caso di problemi
    ritorna un dict vuoto, cosi' lo script prosegue con i dati gia' noti.
    """
    if not REQUESTS_AVAILABLE:
        print("requests non disponibile, salto l'aggiornamento via API.", file=sys.stderr)
        return {}

    try:
        resp = requests.get(THESPORTSDB_URL, timeout=20)
        resp.raise_for_status()
        data = resp.json()
    except Exception as exc:  # noqa: BLE001
        print(f"Chiamata API fallita ({exc}), mantengo gli orari noti.", file=sys.stderr)
        return {}

    events = data.get("events") or []
    found = {}
    for ev in events:
        date_str = ev.get("dateEvent")
        time_str = ev.get("strTime")
        if not date_str or not time_str:
            continue
        try:
            # L'API ritorna data/ora in UTC: le convertiamo in ora italiana.
            dt_utc = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M:%S").replace(tzinfo=TZ_UTC)
            dt_rome = dt_utc.astimezone(TZ_ROME)
            found[dt_rome.strftime("%Y-%m-%d")] = dt_rome.strftime("%H:%M")
        except ValueError:
            continue

    if found:
        print(f"Trovati {len(found)} orari confermati via TheSportsDB.", file=sys.stderr)
    else:
        print("Nessun nuovo orario trovato via TheSportsDB (normale se sono lontani nel tempo).", file=sys.stderr)
    return found


def build_ics(matches):
    now_stamp = datetime.now(TZ_UTC).strftime("%Y%m%dT%H%M%SZ")
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
        dt = datetime.strptime(f"{date_iso} {time_str}", "%Y-%m-%d %H:%M").replace(tzinfo=TZ_ROME)
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
            desc += " Orario provvisorio, verra' aggiornato appena confermato."

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
    confirmed = fetch_confirmed_times_from_api()
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
