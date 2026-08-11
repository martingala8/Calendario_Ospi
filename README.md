# Calendario Ospitaletto Franciacorta — Serie C Girone A 2026/27

Calendario iCal che puoi sottoscrivere su iPhone (o Google/Outlook). Un'azione
GitHub lo rigenera automaticamente due volte a settimana.

## Cosa contiene già

- Tutte le **38 giornate** della stagione 2026/27 (Girone A), con date corrette
  prese dal calendario ufficiale Lega Pro.
- Gli orari **confermati** dove già noti (es. 1ª, 2ª e 4ª giornata).
- Per le partite senza orario ancora ufficiale, un orario segnaposto (15:00)
  con scritto "orario da confermare" nel titolo: l'evento c'è comunque, così
  non perdi la data, e verrà aggiornato quando la Lega Pro pubblica gli orari
  definitivi (di solito 2-3 settimane prima).

⚠️ Nota onesta: il sito da cui lo script prova a leggere gli orari confermati
(tuttocampo.it) ha una protezione anti-bot che a volte blocca le richieste
automatiche. Il workflow è scritto per **non rompersi mai** in quel caso — se
non riesce a leggere nuovi orari, semplicemente mantiene quelli già noti.
Se vuoi, in futuro possiamo aggiungere altre fonti o aggiornare tu stesso a
mano le righe in `scripts/generate_ics.py` (sono scritte in chiaro, riga per
riga, giornata per giornata).

## Passo 1 — Crea il repository su GitHub (5 minuti)

1. Vai su https://github.com e crea un account gratuito se non ce l'hai già.
2. Clicca su **New repository** (in alto a destra, "+").
3. Dagli un nome, ad esempio `ospitaletto-calendar`. Deve essere **pubblico**
   (necessario per usare GitHub Pages gratis).
4. Crea il repository (senza aggiungere README, lo hai già).
5. Nella pagina del repository vuoto, clicca **uploading an existing file** e
   trascina dentro TUTTI i file e le cartelle che trovi in questo pacchetto
   (`docs/`, `scripts/`, `.github/`, `README.md`), mantenendo la struttura
   delle cartelle.
6. Fai commit.

## Passo 2 — Attiva GitHub Pages

1. Nel repository, vai su **Settings → Pages**.
2. In "Build and deployment" → **Source**, scegli **Deploy from a branch**.
3. In "Branch" scegli `main` e cartella **`/docs`**, poi salva.
4. Dopo un minuto GitHub ti mostrerà l'URL pubblico, tipo:
   `https://TUONOME.github.io/ospitaletto-calendar/`
5. Il file del calendario sarà quindi raggiungibile a:
   `https://TUONOME.github.io/ospitaletto-calendar/ospitaletto.ics`

## Passo 3 — Attiva l'aggiornamento automatico

Il workflow in `.github/workflows/update-calendar.yml` è già pronto: gira da
solo ogni **lunedì e giovedì alle 08:00 (ora italiana)** e, se trova orari
nuovi, aggiorna il file e lo ripubblica.

Se vuoi forzare un aggiornamento subito: vai su **Actions** nel repository →
seleziona "Aggiorna calendario Ospitaletto" → **Run workflow**.

(La prima volta potrebbe chiederti di abilitare le Actions: basta cliccare
"I understand my workflows, go ahead and enable them".)

## Passo 4 — Sottoscrivi il calendario su iPhone

1. Apri **Impostazioni** sul tuo iPhone.
2. Vai su **App** → **Calendario** → **Account**.
3. Tocca **Aggiungi account** → **Altro**.
4. Tocca **Aggiungi calendario abbonamento**.
5. Come "Server" incolla l'URL del passo 2, ma sostituendo `https://` con
   `webcal://`, cioè:
   `webcal://TUONOME.github.io/ospitaletto-calendar/ospitaletto.ics`
6. Tocca **Avanti**, poi **Salva**.

Fatto: le partite dell'Ospitaletto compariranno nell'app Calendario di iPhone,
in un calendario separato che si aggiorna da solo (iOS lo ricontrolla
periodicamente in background, di solito una volta al giorno).

## Aggiornare a mano, se serve

Se in futuro vuoi correggere/aggiungere un orario a mano, apri
`scripts/generate_ics.py`, trova la riga della giornata interessata dentro
`BASE_MATCHES` e sostituisci `None` con l'orario tra virgolette, es. `"15:00"`.
Poi fai commit: al prossimo giro del workflow (o lanciandolo a mano) il
calendario pubblicato si aggiorna.
