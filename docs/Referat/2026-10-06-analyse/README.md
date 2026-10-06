# Analysescripts fra 2026-10-06

Arbejdskopier bag `../2026-10-06-termiktop-mod-flightradar.md`. Ikke
produktionskode. Kør fra en arbejdsmappe med `./analyse-data/` (opret den
først). Repo-stien står hardcodet i `sys.path`.

| Trin | Gør |
|---|---|
| (kopi af prod-DB) | Read-only kopi af FlightRadars `flights.db` til `analyse-data/fr_prod.db`. Kør på din egen maskine, tre trin: (1) `ssh -t omvadmin@10.71.21.238 'sudo -u flightradar python3 -c "import sqlite3; s=sqlite3.connect(\"file:/opt/flightradar/app/flights.db?mode=ro\", uri=True); d=sqlite3.connect(\"/tmp/fr_copy.db\"); s.backup(d); d.close()" && sudo chmod 644 /tmp/fr_copy.db'` (2) `scp omvadmin@10.71.21.238:/tmp/fr_copy.db analyse-data/fr_prod.db` (3) `ssh -t omvadmin@10.71.21.238 'sudo rm /tmp/fr_copy.db'`. Kræver en rigtig terminal (password-prompt), ikke `!` i Claude Code |
| `pull.py` | Timedata fra historical-forecast 18/5-4/10 for 26 flyvepladser -> `wx.pkl` (26 kald) |
| `compare.py` | Knytter hver termikboble til nærmeste plads (<= 20 km) og time, og kører `process_point_hour` -> `rows.json` (observeret 90 %-fraktil/max/median, modellens top, LCL, TI-nul, score) |
| `margins.py` | Første runde varianter af fradraget (faste og sæsonskalerede) mod observeret top, uden sjællandske loft-timer |
| `sondes.py` | Schleswig-sonden (10035) kl. 12 UTC for alle dage i `rows.json` fra Wyoming -> `sondes.json` (89 kald, ~15 min) |
| `sonde_cmp.py` | Modellens 2 m-felter og LCL mod sondens overflade- og blandingslags-LCL pr. måned -> `sonde_rows.json`. Kræver `schleswig.pkl`: historical-forecast i 54.53, 9.55 med `HOURLY_PARAMS` og `timezone=UTC` |

Faldgruber: `end_alt` og modellens højder er begge MSL. Sjællandske timer
stopper ved luftrumslofter (~750 og ~1400 m) og er ikke reelle toppe.
