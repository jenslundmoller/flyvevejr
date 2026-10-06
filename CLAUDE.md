# CLAUDE.md

Flyvevejr er en automatisk termik-prognose for danske svæveflyvere på
**https://flyvevejr.dk**. Et Python-script henter vejrdata fra Open-Meteo for
262 punkter (30 flyvepladser plus 232 gitterpunkter), regner en termik-score
(0-10) og en termiktop (m QNH) for hver time 7 dage frem, og skriver JSON.
En statisk Leaflet-side på GitHub Pages viser det. Ingen server, ingen
database, ingen API-nøgler. Ejer: Jens (privat projekt, selv svæveflyver).

## Sprog og stil

- **Dokumentation, referater og UI-tekst er på dansk.** Commit-beskeder og
  prompts til at fortsætte er på engelsk.
- **Brug aldrig tankestreg (—)**, heller ikke i kode, UI, commits eller svar.
  Brug komma, kolon, parentes eller punktum.
- Commit-præfikser som i historikken: `feat(v2):`, `fix(v2):`, `fix(ui):`,
  `web:`, `ops:`, `docs:`, `security:`. Emnelinjen siger hvad der ændres og
  hvorfor, på almindeligt engelsk.
- Højder har altid et datum: termiktop i **m QNH** (over havet), skybase i
  **m QFE** (over terræn). Tider i data og workflows er **UTC**; UI viser
  dansk tid.

## Kommandoer

| Hvad | Kommando |
|---|---|
| Tests (fra worktreen, system-Python) | `python3 -m pytest termik/tests -q` (509 tests, ~2 s, ingen netkald) |
| Én testfil | `python3 -m pytest termik/tests/test_scoring_v2.py -q` |
| Kør prognosen lokalt | `python3 -m termik` (koster ~1.000 Open-Meteo-kald, se Drift) |
| Se siden lokalt | `cd termik/output && python3 -m http.server 8090` |
| Manuel produktionskørsel | `gh workflow run update-forecast.yml -f runner=self-hosted` |

Der er ingen linter eller build-trin. Frontenden er ren HTML/CSS/JS.

## Kode

| Fil | Rolle |
|---|---|
| `termik/fetch_weather.py` | Open-Meteo-kald i batches, parcel-beregning, `process_point_hour`, JSON-output |
| `termik/scoring_v2.py` | **Produktionens score** (DSvU-hæftet, rettelser 1-14) |
| `termik/scoring.py` | v1, urørt rollback-sti (`SCORING_VERSION` i `config.py`) |
| `termik/config.py` | Alle vægte, tærskler og API-parametre |
| `termik/comments.py` | Den danske kommentar i popup'en |
| `termik/locations.py` | Flyvepladser og gitter |
| `termik/tools/` | Engangsværktøjer og drift (`forecast_watchdog`, `dispatch_workflow`, `replay_day`, `compare_scores`) |
| `termik/output/` | Siden: `index.html`, `app.js`, `style.css`, `sw.js`; `data/` skrives af botten |
| `docs/Referat/*-analyse/` | Analysescripts bag referaterne. Ikke produktionskode |

## Skal altid overholdes

- **Ingen workflow må få en `pull_request`-trigger.** Repoet er offentligt,
  og forecast-jobbet kører på en maskine derhjemme (OMV). En fork kunne ellers
  køre kode dér. Kun `actions/*` og `github/*` må bruges i workflows.
- **Ændres noget i `termik/output/` (ikke `data/`), tælles `CACHE_VERSION` i
  `sw.js` op i samme push.** Ellers ser tilbagevendende besøgende og PWA'en
  den gamle side.
- **En scoringsændring valideres på dage den ikke er tilpasset på**, og
  fundene vises brugeren før produktionskoden ændres. Se
  `.claude/rules/scoring.md`.
- **Rør ikke `termik/scoring.py` (v1)** og ikke `termik/output/data/` i hånden.
- **Tests rammer aldrig nettet.** `conftest.py` stubber havtemperatur-kaldet;
  nye netkald i koden skal stubbes på samme måde.
- **Open-Meteos gratis kvote (10.000 kald/døgn) deles** mellem produktionen
  (~6.000) og alt andet fra hjemme-IP'en. Analyser henter så lidt som muligt.
- **Spørg før push.** Push er synligt for alle og starter et deploy.

## Arbejdsgang

**Start altid i en separat worktree.** Flere sessioner arbejder ofte
samtidig i dette repo. Deler de mappe, deler de også commits: 5. og 6.
oktober 2026 pushede én session to gange en anden sessions commits med.
Rør ikke hovedmappen `/home/jens/AI/Flyvevejr`.

```bash
git -C /home/jens/AI/Flyvevejr fetch origin
git -C /home/jens/AI/Flyvevejr worktree add .claude/worktrees/<emne> -b <emne> origin/main
cd /home/jens/AI/Flyvevejr/.claude/worktrees/<emne>
```

(Eller Claude Codes egen worktree-funktion, som også bruger `.claude/worktrees/`.)

1. **Læs først** den nyeste `docs/Referat/*-overdragelse*.md` og
   `docs/AABNE-PUNKTER.md`. Et åbent punkt nævnes ved sit nummer.
2. **Mål før du ændrer.** Analysér med data (startlist, FlightRadar,
   radiosonder), vis brugeren tallene, og vent på et ja før en
   scoringsregel ændres. Mange undersøgelser ender med "uændret"; det er et
   gyldigt resultat og skal skrives ned.
3. **Test først** (`superpowers:test-driven-development`), derefter koden.
4. **Opdatér dokumentationen i samme commit-serie:** referatet for emnet,
   `docs/PROJEKT-DOKUMENTATION.md` hvis adfærd eller tal ændres, og
   `docs/AABNE-PUNKTER.md`.
5. **Commit på worktreens gren. Spørg før push.** Ved push til main:
   `git fetch origin && git rebase origin/main && git push origin HEAD:main`.
   main flytter sig seks gange om dagen (botten committer
   `termik/output/data/`); den rebase er altid ren. Tjek med `git log
   origin/main..HEAD`, at kun dine egne commits kommer med.
6. **Afslut med en overdragelse** efter `docs/Referat/SKABELON-overdragelse.md`
   og ryd op: `git worktree remove .claude/worktrees/<emne>` og
   `git branch -d <emne>`.

## Hvor tingene står

| Sti | Indhold |
|---|---|
| `docs/PROJEKT-DOKUMENTATION.md` | Hele systemet: scoringsmodellen, API, frontend, Actions, drift |
| `docs/AABNE-PUNKTER.md` | Alle åbne punkter med faste numre |
| `docs/Referat/YYYY-MM-DD-<emne>.md` | Én undersøgelse eller ændring: data, tal, beslutning |
| `docs/Referat/*-overdragelse*.md` | Sessionens status og prompt til næste session |
| `docs/plans/` | Designs og planer for større ændringer |
| `docs/scoring-scenarios.md` | De syntetiske v1-scenarier |
| `.claude/rules/` | Detaljerede regler; indlæses når Claude rører de tilhørende filer |

## Drift i én sætning

Forecast-jobbet kører kl. 05:15-20:15 UTC hver 3. time på en selvhostet
runner på OMV (10.71.21.238); er den nede, flytter `forecast-fallback.yml`
kørslen til GitHub efter 15 min. Detaljer i `.claude/rules/drift.md` og
`docs/Referat/2026-09-02-api-robusthed.md`.
