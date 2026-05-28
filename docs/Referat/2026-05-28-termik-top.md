# Referat — Termik-tophøjde via parcel-teori + nyt kortlag

**Dato:** 2026-05-28
**Branch:** main
**Commit:** `17ec592` (feature) + `ec1d0d4` (data efter manuel cron-trigger)
**Plan:** [`docs/plans/2026-05-28-termik-tophojde.md`](../plans/2026-05-28-termik-tophojde.md) (v2)

## Udgangspunkt

Brugeren spurgte om vi kunne tilføje en estimering af **maks. termik-tophøjde** pr. tidspunkt, svarende til hvad RASP, Skysight og TopMeteo viser deres brugere. Eksisterende side viste kun en score (0-10) for "om vejret er godt at flyve i". Open-Meteo's `boundary_layer_height` var allerede med i popup som rå modelværdi, men ikke som et selvstændigt kortlag.

Brugeren ønskede en grundig research-fase først for at afgøre om der overhovedet var nok data tilgængeligt, før der blev brugt tid på at bygge noget.

## Proces — 5-trins workflow med agent-parallel review

Brugeren bad eksplicit om en stringent proces:

1. To research-agenter undersøger implementering (meteorologi + frontend)
2. Plan baseret på fundene
3. To agenter reviewer planen
4. Implementer planen
5. To agenter reviewer implementeringen

### Trin 1 — Research (parallelt)

**Meteorologi-agent** undersøgte parcel-teori, Bolton 1980 LCL, Hcrit-korrektion, og om Open-Meteo's data var tilstrækkelig. Konklusion:

- Brug `geopotential_height_*hPa` direkte fra Open-Meteo (sparer hypsometrisk beregning, fugtighedskorrektion irrelevant ved <20 m fejl).
- Tør-adiabatisk lapse rate **0.0098 K/m** (g/cp ~ 9.8 K/km).
- **Bolton 1980 eq. 22** for LCL-temperatur, langt mere præcis end den eksisterende `spread × 125`-formel (Espy).
- **Hcrit ~ 200-400 m** under TI=0 (RASP-empiri: 225 fpm-tærskel).
- **Egen ~40-linjers implementation** anbefalet over MetPy (~200 MB med matplotlib/scipy/pint som ikke bruges).
- Trykniveauer 950/925/900/850/800/700 hPa er tilstrækkelige for DK (sjældent termik > 700 hPa).

**Frontend-agent** undersøgte Leaflet layer-arkitektur og lag-toggle UX. Vigtigste anbefalinger:

- Genbrug eksisterende `ScoreCanvasLayer` med en `smoothing`-flag + `labels`-array — minimerer regression-risiko.
- Canvas-baserede labels (`ctx.fillText`) frem for `L.divIcon`-DOM-elementer (sidstnævnte gør pan/zoom langsomt på mobil ved 200+ celler).
- Sidebar-afsnit "Kortlag" med radioknapper, ikke en `L.Control` overlay (matcher eksisterende UX).
- **Distinkt viridis-palet** (lilla → orange) for termik-top frem for samme blå-rød som score — undgår forveksling i screenshots.

Frontend-agenten misforstod én ting: foreslog at vise rå `boundary_layer_height` i stedet for at beregne et nyt `thermal_top_m`. Det blev rettet i plan-fasen.

### Trin 2 — Plan v1

Plan-dokument med 11 backend- og frontend-tasks (B1-B6, F1-F11), pseudokode for `compute_thermal_top`, designvalg, test-cases, rollback-strategi.

### Trin 3 — Plan-review (parallelt)

To agenter (meteorologi + kode) fandt tilsammen **5 P0-fejl** og **flere P1/P2**. Vigtigste:

| P | Område | Fund |
|---|--------|------|
| P0 | scoring.py | "Bolton eq. 15" var forkert citation — det er **eq. 22** |
| P0 | scoring.py | `thermal_top_m=0` ved no_data/no_dewpoint var semantisk tvetydigt — burde være `None` |
| P0 | scoring.py | Manglede `limited_by`-tilstande for SW=0 / margin-collapse / mætning / manglende dewpoint |
| P0 | scoring.py | Hcrit-margin i diskrete trin gav synlige 100m-spring mellem nabotimer ved SW=399 vs 401 → linær interpolation i stedet |
| P0 | fetch_weather.py | Early-return `data`-dict glemte at inkludere de nye `thermal_top_*`-felter → schema-inkonsistens |
| P0 | fetch_weather.py | Manglede import af `compute_thermal_top` |
| P0 | fetch_weather.py | Grid- vs airfield-payload-placering var underspecificeret |
| P0 | style.css | Mobil-CSS-regler for `#layer-section` var ikke specificeret → ville være skjult/forvrænget på mobil |
| P1 | scoring.py | 500 hPa droppet (DK termik når sjældent dertil, sparer 1 API-parameter) |

Plan v2 blev skrevet med alle rettelser.

### Trin 4 — Implementering

#### Backend

**`termik/scoring.py`** (+173 linjer):
- `compute_thermal_top()` — parcel-løft med 9 `limited_by`-tilstande (`lcl`, `ti_zero`, `cap`, `inversion`, `weak_solar`, `saturated`, `no_data`, `no_dewpoint`, `margin_collapse`).
- `_hcrit_margin()` — lineær interpolation mellem 200 m (SW≥600 W/m²) og 500 m (SW≤0), cap'd til `raw_top/2` så margin ikke æder hele beregningen.
- `_bolton_lcl_temp_k()` — Bolton 1980 eq. 22.

**`termik/config.py`**: udvidet `HOURLY_PARAMS` med `temperature_950/900/800/600hPa` og `geopotential_height_*hPa` for 950-600 hPa. Eksisterende `dewpoint_2m`, `temperature_925/850/700hPa` bevaret.

**`termik/fetch_weather.py`**: `process_point_hour()` bygger nu `level_temps_c` og `level_heights_m` dicts, kalder `compute_thermal_top`, og lægger resultatet i payload. For grid placeres `thermal_top_m` på top-niveau (sammen med `score`); for airfields placeres alle 4 felter (`thermal_top_m`, `ti_zero_m`, `lcl_m`, `thermal_top_limited_by`) i `data`-dict.

#### Bug under implementering — falsk inversion ved env[0]

Plan-pseudokoden havde:

```python
if i == 1 and d_prev <= 0:
    return "inversion"
```

Men ved `i == 1` er `env[i-1] == env[0]` = overfladen, hvor `t_parcel == t_env == surface_temp` per definition, så `d_prev == 0` ALTID. Resultatet: alle sonderinger returnerede "inversion" og `thermal_top_m=0`.

Fix: trækkede inversions-checken ud af for-loopet og laver den på `env[1]` (første niveau OVER overfladen):

```python
t_parcel_1 = surface_temp_c - DALR_K_PER_M * (h_1 - surface_elevation_m)
if t_parcel_1 - t_env_1 < 0:
    return "inversion"
```

Note: skal være `< 0`, ikke `<= 0` — neutral stabilitet (parcel == env) er IKKE inversion, og krydsningsloopet håndterer det fint.

#### Frontend

**`termik/output/app.js`** (+179 linjer):
- `THERMAL_TOP_STOPS` — 6-stop viridis-palet (lilla → orange).
- `thermalTopToRgb()` — interpoleret farveopslag, returner grå ved `null`.
- `buildThermalTopCanvas()` — paralel til `buildScoreCanvas`, returnerer både canvas og labels.
- `ScoreCanvasLayer` udvidet med `_smoothing` og `_labels` instans-felter; `setScoreCanvas(canvas, smoothing, labels)` med default-args.
- `_drawLabels()` — canvas-tekst med hvid stroke, kun ved `cellPx ≥ 48` (zoom 9+). Filtreret mod `countryMask` så labels ikke flyder over havet.
- `updateHeatmap()` — if/else mellem score/thermal-top, kalder `updateLegend()`.
- `setupLayerControls()` — radio-knappehåndtering med `localStorage`-persistens (try/catch mod private mode).

**`termik/output/index.html`**: nyt `#layer-section` med to radioknapper mellem `#favorite-section` og `#about-link`.

**`termik/output/style.css`**: styling af radioknapper + legend (gradient-bar + tekstlabels) + mobil-regler der skjuler afsnittet i collapsed bottom-sheet.

**`termik/output/sw.js`**: CACHE_VERSION `termik-v12` → `termik-v13` så PWA-brugere tvinges til at hente nye filer.

#### Tests

16 nye tests (158 → 174 grønne):
- `test_scoring.py`: 14 tests for `compute_thermal_top` — klassisk DK sommerdag, inversion, super-instabil, no_data, no_dewpoint, mættet, weak_solar, margin-skalering, Bolton sanity, geopotential sanity, elevation, level-filtering.
- `test_fetch_weather.py`: 2 integrationstests — fuld sondering ender med positiv thermal_top, early-return har `None`/`no_data`-skema.

### Trin 5 — Implementation-review (parallelt)

To agenter (kode + meteorologi) fandt **4 P0** og flere P1/P2 i den faktiske kode:

| P | Fund | Fix |
|---|------|-----|
| P0 | `dew_point_2m` (med underscore) blev tilføjet, men `dewpoint_2m` (uden) var ALLEREDE i config → duplikat hentede samme data to gange | Fjernede den nye linje |
| P0 | `surface_elevation_m = point.get("elevation_m", 0)` — men ingen airfield har `elevation_m` i locations.py, så altid 0 | Dokumenteret som bevidst valg (DK flad, max fejl ~76 m, vel inden for Hcrit-margin 200-500 m) |
| P0 | Inversionscheck brugte `<= 0` → neutral stabilitet blev klassificeret som inversion | Ændret til `< 0` |
| P0 | Labels tegnedes uden mask-filter → "1300m" flød over Kattegat/Storebælt | Tilføjet `ctx.isPointInPath(maskPath, pt.x, pt.y)` per label |
| P1 | Popup-label "Termik-top" vs "Termik-tophøjde" inkonsistens | Ensrettet til "Termik-tophøjde" |
| P1 | Score-legend gradient brugte equidistante stops, men `COLOR_STOPS` har 0/3/5/7/10 (ikke-equidistante) | Specifik CSS-gradient med matchende procent-stops |
| P1 | `_drawLabels` cellPx-tærskel 36 → labels pop'er op midt i zoom 8-animation | Hævet til 48 → kun vises ved zoom 9+ |
| P1 | `test_thermal_top_weak_solar` og `_margin_scaling` brugte `if/assert`-mønster der kunne passere uden at teste den intenderede gren | Skærpet: brugt no-dewpoint-sondering så `weak_solar` garanteret rammes, og assert eksplicit margin-differencen >= 200 m |
| P1 | `test_thermal_top_with_elevation` brugte for løs tolerance (+/- 50 m) til at fange noget | Skiftet til at verificere LCL_high - LCL_base == 500 m ± 2 m |
| P1 | PROJEKT-DOKUMENTATION.md ikke opdateret | Opdateret grid-tal (51→232), test-tæller (78→174), nye parametre, nyt "Kortlag"-afsnit |
| P2 | Magisk konstant `50` i margin_collapse-check | Navngivet `MARGIN_COLLAPSE_THRESHOLD_AGL_M` |

Alle 174 tests fortsat grønne efter rettelserne.

## Deployment og verifikation

1. Commit `17ec592` med 12 filer, +1529/-21 linjer.
2. `git pull --rebase` ovenpå cron-data-commits, derefter `git push origin main`.
3. Den næste scheduled cron-kørsel **fejlede** med race-condition (begge prøvede at pushe data samtidigt med min feature-commit).
4. Manuelt-trigget `workflow_dispatch` på "Update Termik Forecast" succedede 23m28s senere.
5. Verificeret i ny `current.json`:
   - 168 af 232 grid-celler havde positive `thermal_top_m`-værdier ved kl. 14 (range 465-1823 m).
   - Flyvepladser viste realistiske diagnostics (Aalborg kl. 14: thermal_top=1046m, ti_zero=1246m, lcl=1564m, limited_by=ti_zero).
   - `limited_by`-distribution: 21× ti_zero, 7× lcl, 2× inversion (af 30 flyvepladser).

## Klient-cache problem og løsning

Brugeren rapporterede: "Jeg kan godt se det er tilføjet, men der vises ikke noget på kortet."

Diagnose: brugeren havde siden åben fra før data-regenereringen. `forecastData` ligger i JS-hukommelse og hentes kun ved page load → toggling til termik-top læste fra gammel data uden `thermal_top_m` → alle celler grå (default for `null`). Service worker'en var allerede bumpet til v13, så hard refresh løste det.

## Kendte begrænsninger og fremtidigt arbejde

1. **`score_lapse_rate` og `thermal_top_m` kan divergere**: scoring bruger fortsat `(T_2m - T_850)/15` mens termik-top bruger fuld parcel-teori. En grid-celle kan vise lapse_rate-score 8 men thermal_top_m=0 (lav inversion under 850 hPa). Dokumenteret som kendt feature.
2. **Tidsmæssig fortolkning**: `thermal_top_m` er pr. time, ikke dagens maksimum. Bruger navigerer time-slider for at finde peak. Et fremtidigt `thermal_top_max_today_m`-felt kan overvejes.
3. **Hcrit uden surface heat flux**: vores SW-skalerede approksimation har ±100-200 m fejl ift. klassisk RASP der bruger fuld varmestrøm fra modellen.
4. **Airfield-elevation altid 0**: max fejl ~76 m (Billund), vel inden for Hcrit-margin, men kunne tilføjes som `elevation_m`-felt i `locations.py` AIRFIELDS hvis ønsket senere.
5. **Diagnostik tabt for grid-celler**: kun `thermal_top_m` gemmes for grid (payload-budget). `limited_by`, `ti_zero_m`, `lcl_m` findes kun for flyvepladser.
6. **Cumulus over LCL**: i fugtige sommerdage kan rigtige cumulus-toppe stikke 200-500 m over LCL pga. våd-adiabatisk fortsættelse. Vores cap ved LCL er konservativt og sikkert til glider-planlægning.

## Filer ændret

| Fil | Linjer | Indhold |
|-----|--------|---------|
| `termik/scoring.py` | +173 | `compute_thermal_top`, `_hcrit_margin`, `_bolton_lcl_temp_k`, konstanter |
| `termik/config.py` | +14 | Udvidede HOURLY_PARAMS (950/900/800/600 hPa temps + geopotential 950-600) |
| `termik/fetch_weather.py` | +34 | Level-dicts, kald til `compute_thermal_top`, payload-tilføjelser |
| `termik/output/app.js` | +179 | `ThermalTopCanvasLayer`-genbrug, viridis-palet, labels, settings-controls |
| `termik/output/index.html` | +15 | `#layer-section` med radioknapper |
| `termik/output/style.css` | +68 | `#layer-section` + legend + mobil-regler |
| `termik/output/sw.js` | ±1 | CACHE_VERSION v12 → v13 |
| `termik/tests/test_scoring.py` | +200 | 14 nye thermal_top tests |
| `termik/tests/test_fetch_weather.py` | +91 | 2 nye integrationstests |
| `docs/PROJEKT-DOKUMENTATION.md` | +42/-21 | Grid-tal, parametre, kortlag-afsnit, test-tæller |
| `docs/plans/2026-05-28-termik-tophojde.md` | +680 | Plan v2 efter review |
| `docs/Referat/2026-05-28-termik-top.md` | dette dokument | Fuld rapport |

**Total: ~1500 insertions, alle 174 tests grønne, deployet til https://flyvevejr.dk.**

## Kilder

- [DrJack BLIPMAP Parameter Details](http://www.drjack.info/blip/info/parameter_details.html) — Hcrit / TI=0 / wstar definitioner
- [Bolton 1980 LCL-formel](https://romps.berkeley.edu/papers/16lcl.pdf) — eq. 22 reference
- [Open-Meteo Docs](https://open-meteo.com/en/docs) — pressure-level parametre, best_match-model
- [MetPy parcel-funktioner](https://unidata.github.io/MetPy/latest/api/generated/metpy.calc.parcel_profile.html) — reference for parcel-løft (ikke brugt som dependency)
- AMS Glossary: [Convective Condensation Level](https://glossary.ametsoc.org/wiki/Convective_condensation_level)
