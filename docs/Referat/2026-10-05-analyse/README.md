# Analysescripts fra 2026-10-05

Arbejdskopier fra sessionen bag `../2026-10-05-startlist-weekend-oktober.md`
og `../2026-10-05-overdragelse.md`. Ikke produktionskode: hurtige scripts med
faste stier, bevaret så metoden kan genbruges. Kør fra en arbejdsmappe; data
skrives til `./analyse-data/` (opret den først). Repo-stien
`/home/jens/AI/Flyvevejr` står hardcodet i `sys.path`.

Rækkefølge og formål:

| Script | Gør |
|---|---|
| (curl) | Hent startlister: `curl -sL -A "Mozilla/5.0" https://startlist.club/YYYY-MM-DD -o analyse-data/sl_YYYY-MM-DD.html` |
| `parse.py` | Parser alle `sl_*.html` til `flights.json` (plads, fly, piloter, start/landing, varighed) |
| `summ.py` | Skolefly-filter (fly med 3+ forsædepiloter) og facit-bånd pr. plads-dag -> `facit.json` |
| `pull_hist.py` | Fulde timedata (alle `HOURLY_PARAMS`) fra historical-forecast for 18 pladser -> `hist_full.pkl` |
| `cirrus.py` | Time-niveau-facit: kl. 11-17, "bar" = signalflyvning >= 60 min i luften, "kort" = alle < 30 min -> `cirrus_rows.json` |
| `caps.py` | Opfanger `apply_dealbreakers_v2` og finder hvilket cap der binder hver time -> `caps_rows.json` |
| `ccvar.py` | Afprøver varianter af et cap time for time og dag for dag (mønster til nye cap-forsøg) |
| `pull925.py`, `analyze925.py` | 925/850 hPa for pålandsstudiets dage og 5b-analysen |
| `sst_hist.py` | Målt havtemperatur-historik (marine-API) |
| `validate_sst.py` | Dagsvalidering mod sommer- og oktober-facit (kræver `season_cache.pkl` fra forecast-endpointet, se overdragelsen) |

Faldgruber: Open-Meteo har en minut-grænse (vent 65 s og prøv igen);
forecast-endpointet når kun 92 dage tilbage; historical-forecast er ikke
præcis det produktionen publicerede.

Tilføjet senere samme dag (punkt 13):

| Script | Gør |
|---|---|
| `actions_timing.py` | Varighed pr. kald og fejlrate mod tid siden forrige vellykkede kald, fra update-forecast-loggene (hentes med `gh run view --log`, se docstring) |
| `limit9.py` | Punkt 9: hvilket loft der satte scoren pr. time (afløser `caps.py`, som manglede lapse 2-180 m, CAPE og havde overskyet som cap 2) -> `limit_rows.json`. Produktionens `data.limited_by` gav samme koder og scores i alle 986 timer |
