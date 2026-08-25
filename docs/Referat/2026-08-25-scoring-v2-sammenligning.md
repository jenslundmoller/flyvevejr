# Scoring v2 (DSvU-hæftet): implementering og sammenligning med v1

Dato: 2026-08-25. Branch: `scoring-v2-dsvu`.
Plan: `docs/plans/2026-08-25-scoring-v2-dsvu-haefte.md`.

## Hvad der er bygget

Ny score i `termik/scoring_v2.py` med de 7 justeringer fra hæftet
"Svæveflyvningen og vejret" (DSvU). Den gamle score i `termik/scoring.py` er
IKKE rørt og er rollback-stien.

| # | Justering | Hæftets belæg |
|---|---|---|
| 1 | Vind-ideal 5-10 kt (før 5-15); 15-25 kt mildnes ved koldluftsadvektion (skygader) | s. 13, 28-29 |
| 2 | De første 40 procentpoint lav sky er gratis i solscoren (cu-allowance) | Skema 1 s. 13, s. 21 |
| 3 | Gradueret cirrus-fradrag: -0.5 ved >= 40 %, -1.0 ved >= 60 % høj sky | s. 20 |
| 4 | Termiktop-kobling: cap 4 ved brugbar top < 600 m AGL (kun i sol, SW >= 400, og kun ved positiv lcl/ti_zero-dom); +0.5 ved top > 1200 m | Skema 1, s. 41 |
| 5 | Søbrise-straf skalerer med land/hav-temperaturforskellen; kraftig fralandsvind blokerer stadig | s. 22-23 |
| 6 | Varmehukommelsens faktor løftes 0.65 -> 0.75 ved koldluftsadvektion | s. 14 |
| 7 | Temperaturvægt 0.08 -> 0.04, sol 0.20 -> 0.24 (kold luftmasse behøver ikke høje temperaturer) | s. 14 |

To hæfte-punkter blev justeret under kalibrering mod referencedagene:

- **Ingen varme-malus på hukommelsen** (punkt 6's spejlside): 2026-08-08
  kl. 18 havde 850-trend præcis +1.0 mens piloten fløj; en faktor på 0.55
  ville cappe de fredede aftentimer (0.55 x 657 = 361 < 400).
- **Termiktop-cappet kræver sol og en positiv dom**: om aftenen kollapser
  parcel-toppen pr. definition (varmehukommelsen bærer termikken), og de
  grove trykniveauer kan melde "inversion" hen over et superadiabatisk målt
  overfladelag. Cappet gælder derfor kun ved SW >= 400 W/m² og
  limited_by i (lcl, ti_zero).

## Valg af version og rollback

- `termik/config.py`: `SCORING_VERSION = "v2"`. **Rollback = sæt `"v1"`**
  (én linje), eller bliv på main og drop branchen.
- Hver publiceret time bærer nu `data.scoring_version` som revisionsspor.
- Bemærk: testen `test_saturday_1900_reaches_the_target` forventer v2
  (v1 havde et dokumenteret hul kl. 19, som cu-allowancen lukker). Rulles
  tilbage til v1 vil den fejle; det er dokumenteret i testens docstring.

## Tests

- `termik/tests/test_scoring_v2.py`: 55 tests af de nye funktioner + kontakten.
- `termik/tests/test_scenarios_v2_season.py`: 11 sæson-arketyper april-oktober
  (bagsidevejr, søbrise, Skema 1-cu-dag, varm sydluft, cirrus-skjold/banker,
  koldluftsaften, efterår, lav oktober-base), hver med forventet v2-interval
  og retning mod v1.
- Hele suiten: 339 tests grønne, inkl. begge kalibrerede referencedage kørt
  gennem produktionsstien med v2.

## Sammenligning på rigtige dage (historical-forecast, best_match)

Kørt med `python3 -m termik.tools.compare_scores <plads> <dag>`; hver time
gennem `process_point_hour` med begge versioner. "Timer >= 5" er antal timer
med mindst "Moderat termik" i vinduet kl. 8-20.

| Dag | Plads | Vejrtype | Maks v1 | Maks v2 | Timer >= 5 v1/v2 | Vigtigste forskel |
|---|---|---|---|---|---|---|
| 2026-04-15 | Arnborg | Overskyet AC-dæk | 2.0 | 2.0 | 0/0 | Enige: død dag |
| 2026-04-30 | Arnborg | Solrig men stabil | 5.0 | 5.0 | 2/2 | Enige: lapse-caps binder |
| 2026-05-15 | Arnborg | Gråvejr | 1.0 | 1.0 | 0/0 | Enige |
| 2026-05-27 | Arnborg | Klassisk forårsdag | 7.9 | 8.3 | 8/8 | +0.4 middag (cu/sol); kl. 15 med 83 % cirrus: 7.5 -> 6.7 (punkt 3) |
| 2026-05-28 | Sæby (8 km kyst) | Solrig kystdag | 5.6 | 6.7 | 7/9 | Søbrise-straf følger reel land/hav-diff (punkt 5), stadig straffet |
| 2026-06-15 | Arnborg | Omskifteligt | 8.2 | 8.4 | 6/5 | Kl. 17 med top 514 m: 6.8 -> 4.0 (punkt 4) |
| 2026-06-21 | Arnborg | Topdag | 8.6 | 8.8 | 12/12 | Let løft hele dagen |
| 2026-07-08 | Arnborg | Stabil, cirrus-slør | 5.0 | 5.0 | 1/1 | Enige: caps binder |
| 2026-08-08 | Ringsted | **Pilot fløj god termik** | 7.0 | 8.8 | 11/11 | Hele eftermiddagen "God termik" 8.1-8.8; dagens egen cumulus straffes ikke længere |
| 2026-08-09 | Ringsted | **Cirrus-skjold, død dag** | 5.9 | 6.1 | 4/4 | Stadig cappet 3 kl. 9-15; kalibreringen holdt |
| 2026-08-14 | Arnborg | Cirrus det meste af dagen | 5.0 | 5.0 | 3/3 | Enige: skjold + lapse-caps |
| 2025-09-08 | Arnborg | Pæn sensommerdag | 6.5 | 6.7 | 6/7 | Let løft (sol/temp-vægt) |
| 2025-10-01 | Arnborg | Efterårssol, lav base | 5.9 | 5.0 | 5/5 | Kl. 13-14 med base ~550 m: 5.2/5.9 -> 4.0 (punkt 4, Skema 1) |

### Detalje: 2026-08-08, dagen piloten fløj (Ringsted)

| kl | v1 | v2 | diff | lav sky % | v2-label |
|---|---|---|---|---|---|
| 11 | 6.2 | 8.1 | +1.9 | 18 | God termik |
| 13 | 6.6 | 8.4 | +1.8 | 95 | God termik |
| 14 | 7.0 | 8.8 | +1.8 | 47 | God termik |
| 17 | 7.0 | 7.9 | +0.9 | 58 | God termik |
| 19 | 5.9 | 7.0 | +1.1 | 62 | God termik |

Piloten fløj gode termikker hele eftermiddagen; v1 nåede aldrig over 7.0
fordi dagens egen termik-cumulus læstes som skydække. v2 matcher den fløjne
virkelighed markant bedre uden at 2026-08-09 (cirrusdagen) slipper op.

## Vurdering

- v2 ændrer intet på døde og hårdt cappede dage (april, juli, 14. august):
  identiske scores. Ingen falske positiver observeret i materialet.
- v2's gevinster ligger præcis dér, hæftet siger de skal: cu-dage, kystdage
  sidst på sæsonen, koldluftsaftener. Straffene ligger på cirrus-banker og
  lave baser i det tidlige forår og efterår.
- Det åbne kalibreringshul fra v1 (19:00 på pilotdagen, strict xfail) er
  lukket af punkt 2.

## Værktøj

`termik/tools/compare_scores.py`: sammenlign v1/v2 på en vilkårlig dag,
fx `python3 -m termik.tools.compare_scores arnborg 2026-06-21`.
