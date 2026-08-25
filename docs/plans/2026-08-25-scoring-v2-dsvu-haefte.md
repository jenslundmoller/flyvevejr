# Scoring v2 (DSvU-hæftet) Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** En ny termik-score (v2) der implementerer de 7 justeringer fra hæftet "Svæveflyvningen og vejret", med den gamle score bevaret urørt som rollback, og en sæson-sammenligning (april-oktober) af gammel mod ny score.

**Architecture:** `termik/scoring.py` røres ikke (v1 = rollback). Ny modul `termik/scoring_v2.py` genbruger v1's uændrede funktioner via import og erstatter de ændrede. `SCORING_VERSION` i `termik/config.py` styrer hvilken version `fetch_weather.process_point_hour` kalder; replay-værktøjet følger automatisk med. Et nyt værktøj `termik/tools/compare_scores.py` henter rigtige dage april-oktober fra Open-Meteos historical-forecast-endpoint (samme best_match-model som produktionen) og printer v1 mod v2 time for time.

**Tech Stack:** Python 3, pytest, requests, Open-Meteo forecast + historical-forecast API.

**Branch:** `scoring-v2-dsvu` (main forbliver ren; rollback = flip `SCORING_VERSION` eller drop branchen).

---

## De 7 punkter og deres nedslag

| # | Punkt (hæftets belæg) | Nedslag i v2 |
|---|---|---|
| 1 | Vind: 5-10 kt "absolut mest ideelle"; 10-20 kt kortere boble-levetid; >20 kt meget kort (s. 13, 28). Skygader ved koldluftsadvektion 15-25 kt (s. 29) | `score_wind_v2(wind_kt, cold_advection)` |
| 2 | 1-4/8 lav cumulus er optimalt skybillede, ikke et minus (Skema 1 s. 13; s. 21) | `score_solar_v2`: de første 40 % lav sky er gratis |
| 3 | Allerede cirrus-banker svækker op til 1 m/s (s. 20) | Gradueret fradrag -0.5/-1.0 ved høj sky >= 40/60 % |
| 4 | Termikstyrke følger basehøjden: <600 m svag, 600-1200 moderat, >1200 kraftig (Skema 1; s. 41) | Cap 4 ved brugbar top < 600 m AGL, +0.5 ved > 1200 m |
| 5 | Søbrise kræver svag vind + stor land/hav-forskel, april-juni værst (s. 22-23) | `calculate_seabreeze_penalty_v2` skalerer med land/hav-diff |
| 6 | Koldluftsadvektion holder termikken længere; varm luft dør før solnedgang (s. 14) | Varmehukommelsens faktor skaleres med 850 hPa-trend |
| 7 | Kold luftmasse behøver ikke høje temperaturer (s. 14) | Temperaturvægt 0.08 -> 0.04, sol 0.20 -> 0.24 |

## Bevidste fravalg

- Punkternes caps fra v1 (strålings-gate, cirrus-skjold, mellemhøj pendant, BL-gate) genbruges uændret: de er kalibreret mod referencedagene 2026-08-08/09, og v2 må ikke tabe dem.
- `effective_cloud_cover`, `score_lapse_rate`, `score_surface_lapse_rate`, `score_spread`, `score_gusts`, `score_precipitation`, shear/mixing-modifiers, `compute_thermal_top`: uændret, importeres fra v1.
- Ingen ny hentning af fugtighed på trykniveauer (vestside-af-højtryk Sc-risiko): for stor feature, ikke i de 7 punkter.

---

### Task 1: Branch + config-kontakt

**Files:**
- Modify: `termik/config.py`
- Test: `termik/tests/test_scoring_v2.py` (ny)

**Step 1:** `git checkout -b scoring-v2-dsvu`

**Step 2:** Failing test:

```python
def test_scoring_version_defaults_to_v2():
    from termik.config import SCORING_VERSION
    assert SCORING_VERSION in ("v1", "v2")
```

**Step 3:** I config.py, under WEIGHTS, tilføj:

```python
# Hvilken scoring produktionen kører: "v1" (scoring.py, den gamle) eller
# "v2" (scoring_v2.py, DSvU-hæftets justeringer). Rollback = sæt "v1".
SCORING_VERSION = "v2"

# v2-vægte (punkt 7): temperatur ned, sol op. Kold luftmasse behøver ikke
# høje temperaturer for at danne termik (hæftet s. 14); instabiliteten bor
# allerede i lapse rate-scoren.
WEIGHTS_V2 = {
    "lapse_rate": 0.30,
    "solar": 0.24,
    "spread": 0.15,
    "wind": 0.10,
    "gusts": 0.10,
    "temperature": 0.04,
    "precipitation": 0.07,
}
```

**Step 4:** `python3 -m pytest termik/tests/test_scoring_v2.py -v` -> PASS. Commit.

### Task 2: score_wind_v2

**Files:** Create `termik/scoring_v2.py`; Test `termik/tests/test_scoring_v2.py`

Tests: 7 kt -> 10; 12 kt -> 8; 4 kt -> 7; 17 kt -> 5; 17 kt med cold_advection=True -> 7 (skygader); 22 kt -> 3; 1 kt -> 4; 0 -> 3; 28 kt -> 2; 40 kt -> 0. Grænser: 10 kt -> 10, 15 kt -> 8, 20 kt -> 5 (cold_advection: 20 -> 7, 25 -> 3).

```python
def score_wind_v2(wind_kt: float, cold_advection: bool = False) -> int:
    if 5 <= wind_kt <= 10:
        return 10
    elif 10 < wind_kt <= 15:
        return 8
    elif 3 <= wind_kt < 5:
        return 7
    elif 15 < wind_kt <= 20:
        return 7 if cold_advection else 5
    elif 20 < wind_kt <= 25:
        return 5 if cold_advection else 3
    elif 0 < wind_kt < 3:
        return 4
    elif wind_kt == 0:
        return 3
    elif 25 < wind_kt <= 35:
        return 2
    else:
        return 0
```

`cold_advection` = `temp_850hpa_trend <= -1.0` (sættes i compute_thermal_score_v2).

### Task 3: score_solar_v2 (cumulus-venlig)

Tests: low=40, mid=0, high=0, direct=600 -> samme score som low=0 (fuld credit); low=60 -> kun 20 punkter tæller; stratus-morgen (low=90, direct=50) stadig lav; fallback uden lag-data = v1-adfærd.

```python
CU_ALLOWANCE = 40  # 1-4/8 lav cumulus er et sundhedstegn, ikke skygge (Skema 1)

def score_solar_v2(cloud_cover, shortwave_radiation, cloud_cover_low=None,
                   cloud_cover_mid=None, cloud_cover_high=None, direct_radiation=None):
    if cloud_cover_low is None or cloud_cover_mid is None or cloud_cover_high is None:
        effective = cloud_cover
    else:
        effective = min(100.0, max(0.0, cloud_cover_low - CU_ALLOWANCE) * 1.0
                        + cloud_cover_mid * 0.7 + cloud_cover_high * 0.5)
    cloud_factor = max(0.0, (100 - effective) / 100)
    if direct_radiation is not None:
        radiation_factor = min(direct_radiation / 600, 1.0)
    else:
        radiation_factor = min(shortwave_radiation / 800, 1.0)
    return (cloud_factor * 0.4 + radiation_factor * 0.6) * 10
```

### Task 4: Gradueret cirrus-fradrag

Tests: high=30 -> 0; high=45 -> -0.5; high=70 -> -1.0; high=None -> 0; high=90 -> -1.0 (cappet af skjoldet alligevel).

```python
CIRRUS_BANK_LIGHT = 40   # banker af cirrus: op til -1 m/s (hæftet s. 20)
CIRRUS_BANK_HEAVY = 60

def cirrus_penalty_v2(cloud_cover_high):
    if cloud_cover_high is None:
        return 0.0
    if cloud_cover_high >= CIRRUS_BANK_HEAVY:
        return -1.0
    if cloud_cover_high >= CIRRUS_BANK_LIGHT:
        return -0.5
    return 0.0
```

### Task 5: calculate_seabreeze_penalty_v2

Tests: (a) maj, onshore, diff 10, 30 km -> ~3-værdi skaleret med afstand; (b) oktober, onshore 18 kt, diff 2 -> 0; (c) april, svag vind, offshore, diff 9 -> 2 * afstandsfaktor; (d) 80+ km -> 0; (e) diff <= 2 -> 0 uanset retning.

```python
def calculate_seabreeze_penalty_v2(coast_distance_km, coast_direction_deg,
                                   wind_dir, wind_speed_kt, temp_2m, month):
    if coast_distance_km >= 80:
        return 0
    land_sea_diff = temp_2m - SEA_TEMP_BY_MONTH[month]
    if land_sea_diff <= 2:
        return 0  # ingen drivkraft, ingen kold hav-luft af betydning
    angle_diff = abs(wind_dir - coast_direction_deg)
    if angle_diff > 180:
        angle_diff = 360 - angle_diff
    is_onshore = angle_diff < 90
    if not is_onshore and wind_speed_kt > 15:
        return 0  # kraftig fralandsvind holder søbrisen ude
    if land_sea_diff > 8:
        drive = 2.0
    elif land_sea_diff > 4:
        drive = 1.0
    else:
        drive = 0.5
    if is_onshore:
        risk = min(3.0, drive + 1.0)  # generel pålandsvind skubber fronten ind
    elif wind_speed_kt < 8:
        risk = drive  # svag vind: søbrise kan dannes ved alle kyster
    else:
        risk = drive * 0.5
    distance_factor = max(0, 1 - coast_distance_km / 80)
    return round(risk * distance_factor, 1)
```

### Task 6: effective_radiation_v2 (luftmasse-skaleret hukommelse)

Tests: neutral trend -> som v1 (0.65); trend -1.5 -> faktor 0.75; trend +1.5 -> faktor 0.55; deck-arrival blokerer stadig; floor gælder stadig.

```python
def memory_factor_v2(temp_850hpa_trend):
    # Bagsidevejr holder termikken længere, varm luft dør før solnedgang (s. 14)
    if temp_850hpa_trend <= -1.0:
        return min(0.75, RADIATION_MEMORY_FACTOR + 0.10)
    if temp_850hpa_trend >= 1.0:
        return max(0.55, RADIATION_MEMORY_FACTOR - 0.10)
    return RADIATION_MEMORY_FACTOR
```

`effective_radiation_v2(current, trailing, cloud_cover, trailing_cloud_cover, temp_850hpa_trend=0.0)`: som v1 men med faktoren ovenfor. `apply_dealbreakers_v2` tager `temp_850hpa_trend` og bruger v2-varianten i strålings-gaten.

### Task 7: Termiktop-kobling

Tests: top 400 AGL -> cap 4; top 800 -> ingen ændring; top 1400 -> +0.5; None -> ingen ændring; limited_by i ("no_data","no_dewpoint") -> ingen cap (men bonus stadig ok ved målt top).

```python
THERMAL_TOP_WEAK_AGL_M = 600      # < 600 m: svag termik (< 1 m/s), s. 41
THERMAL_TOP_STRONG_AGL_M = 1200   # > 1200 m: kraftig termik (> 2 m/s)

def thermal_top_adjustment_v2(thermal_top_agl_m, limited_by):
    """Returnerer (bonus, cap). cap=None når ingen cap."""
    if thermal_top_agl_m is None or limited_by in ("no_data", "no_dewpoint"):
        return 0.0, None
    if thermal_top_agl_m < THERMAL_TOP_WEAK_AGL_M:
        return 0.0, 4
    if thermal_top_agl_m > THERMAL_TOP_STRONG_AGL_M:
        return 0.5, None
    return 0.0, None
```

### Task 8: compute_thermal_score_v2 + apply_dealbreakers_v2

Samme signatur som v1 plus `thermal_top_agl_m=None, thermal_top_limited_by=None`. Bruger WEIGHTS_V2, score_wind_v2 (cold_advection fra temp_850hpa_trend), score_solar_v2, cirrus_penalty_v2, seabreeze_v2, termiktop-justering; dealbreakers som v1 men med effective_radiation_v2 og termiktop-cap. Resultat-dict udvides med `"version": "v2"` og `"thermal_top_adjustment"`.

Tests: perfekt junidag scorer >= 9; identisk input med 12 kt vind scorer lavere end 8 kt; cirrus 70 % trækker fra; alle v1-regressionstests i `test_scoring.py` kører stadig grønt (urørt fil).

### Task 9: Wire ind i fetch_weather

**Files:** Modify `termik/fetch_weather.py`; Test `termik/tests/test_fetch_weather.py` (tilføj)

- `compute_thermal_top` flyttes FØR score-kaldet (den er uafhængig af scoren).
- Ved `SCORING_VERSION == "v2"`: kald `compute_thermal_score_v2(..., thermal_top_agl_m=top_m - elevation, thermal_top_limited_by=...)`, ellers v1 præcis som i dag.
- Test: monkeypatch SCORING_VERSION til "v1" hhv. "v2" og se at begge stier kører på syntetisk hourly-data, og at v1-stien giver bit-identisk resultat med før (guld-værdi fra eksisterende testdata).

### Task 10: Sæson-scenarietests (april-oktober)

**Files:** Create `termik/tests/test_scenarios_v2_season.py`

Syntetiske månedsarketyper med forventede intervaller (v2), bygget på hæftets vejrsituationer:

| Måned | Arketype (hæftet) | Forventet v2 | Nøgleinput |
|---|---|---|---|
| April | Bagsidevejr, kold ustabil polarluft (fig. 22) | 7-10 | temp 14, 850hPa -2, trend -1.5, vind 12 kt, CAPE 400 |
| Maj | Søbrisedag ved kyst, 25 km, onshore (s. 22-23) | 3-6 | diff ~11, vind 8 kt onshore |
| Maj | Samme dag inland 85 km | 7-10 | søbrise-straf 0 |
| Juni | Klassisk cu-dag, 3/8 lav sky (Skema 1) | 8-10 | low 38 %, direct 650, base 1300 m |
| Juli | Varm sydluft, stabil, diset (fig. 25, Saharaluft-scenariet) | <= 4 | temp 29, 850hPa 21, spread 18 |
| August | Cirrus-skjold 90 % (referencedag 2026-08-09) | <= 3 | trailing cirrus 99 |
| August | Cirrus-banker 50 % | 1-1.5 point under samme dag uden cirrus | high 50 |
| September | Efterår, svag sol, lav top (600 m BL) | <= 5 | BL 700, direct 300 |
| Oktober | Sen sæson, koldluft men lav sol, top < 600 AGL | <= 4 | termiktop-cap |

Hver test kalder både v1 og v2 og asserter v2-intervallet plus den forventede RETNING af ændringen mod v1 (fx søbrise-oktober: v2 >= v1; vind 17 kt: v2 <= v1).

### Task 11: Sammenligningsværktøj mod rigtige dage

**Files:** Create `termik/tools/compare_scores.py`

- Henter én dag/lokation fra historical-forecast-api.open-meteo.com (samme best_match som produktionen; verificér først med et enkelt kald at alle HOURLY_PARAMS leveres, ellers noteres hullet i output).
- Kører hver dagtime gennem BÅDE v1 og v2 (direkte kald, ikke via SCORING_VERSION), printer markdown-rækker: kl, v1, v2, diff, label-skift, samt nøgleinput.
- Kørsel: `python3 -m termik.tools.compare_scores <airfield-id> <YYYY-MM-DD>`.
- Dage der køres (15. i hver måned 2026 april-august + 2025 september-oktober, plus referencedagene og en søbrise-kandidat i maj ved kystplads):
  - arnborg 2026-04-15, 2026-05-15, 2026-06-15, 2026-07-15, 2026-08-15
  - arnborg 2025-09-15, 2025-10-15
  - ringsted 2026-08-08 (pilot fløj, god), 2026-08-09 (cirrus, død)
  - en kystplads 2026-05-15 (søbrise-test)
- Resultaterne samles i `docs/Referat/2026-08-25-scoring-v2-sammenligning.md` med skemaet gammel/ny.

### Task 12: Fuld regression + referat + commit

- `python3 -m pytest termik/ -v` -> alt grønt (v1-tests urørte).
- Replay af referencedagene via `replay_day` (kører nu v2 via SCORING_VERSION): 2026-08-08 skal stadig ende "God termik" om eftermiddagen, 2026-08-09 skal stadig være nede.
- Referat i `docs/Referat/` med sammenligningsskemaet og rollback-instruks.
- Commit alt på branchen; main røres ikke.

## Rollback

1. Hurtig: sæt `SCORING_VERSION = "v1"` i `termik/config.py` (én linje).
2. Fuld: bliv på main / drop branchen `scoring-v2-dsvu`.
