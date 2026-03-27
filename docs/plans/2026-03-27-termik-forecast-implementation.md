# Termik-forecast Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build an automated thermal soaring forecast system for Denmark that generates a heatmap website from Open-Meteo weather data.

**Architecture:** Python script runs every 3 hours via cron, fetches weather data from Open-Meteo API for ~98 points across Denmark, computes a thermal score (0-10) per point per hour for 3 days, writes JSON. A static HTML/Leaflet.js page renders the data as a heatmap with clickable airfield markers.

**Tech Stack:** Python 3.12, requests, pytest. Frontend: HTML, CSS, vanilla JS, Leaflet.js, leaflet-heat.

---

### Task 1: Project Setup

**Files:**
- Create: `termik/requirements.txt`
- Create: `termik/tests/__init__.py`

**Step 1: Create directory structure**

```bash
mkdir -p termik/output/data termik/tests
```

**Step 2: Create requirements.txt**

```
requests>=2.31
pytest>=8.0
```

File: `termik/requirements.txt`

**Step 3: Create virtual environment and install**

```bash
cd /home/jens/Documents/Flyveteori
python3 -m venv termik/.venv
source termik/.venv/bin/activate
pip install -r termik/requirements.txt
```

**Step 4: Create empty test init**

File: `termik/tests/__init__.py` (empty file)

**Step 5: Verify pytest works**

```bash
cd /home/jens/Documents/Flyveteori
source termik/.venv/bin/activate
python -m pytest termik/tests/ -v
```

Expected: "no tests ran" (0 collected), exit 0.

**Step 6: Commit**

```bash
git init
git add termik/requirements.txt termik/tests/__init__.py
git commit -m "chore: project setup with venv and pytest"
```

---

### Task 2: Locations Module

**Files:**
- Create: `termik/locations.py`
- Create: `termik/tests/test_locations.py`

**Step 1: Write failing tests**

File: `termik/tests/test_locations.py`

```python
from termik.locations import AIRFIELDS, GRID_POINTS, ALL_POINTS


def test_airfields_is_list_of_dicts():
    assert isinstance(AIRFIELDS, list)
    assert len(AIRFIELDS) >= 25


def test_airfield_has_required_fields():
    for af in AIRFIELDS:
        assert "id" in af
        assert "name" in af
        assert "lat" in af
        assert "lon" in af
        assert "region" in af
        assert "coast_distance_km" in af
        assert "coast_direction_deg" in af


def test_airfield_coordinates_in_denmark():
    for af in AIRFIELDS:
        assert 54.4 < af["lat"] < 58.0, f"{af['id']} lat out of range"
        assert 7.5 < af["lon"] < 15.5, f"{af['id']} lon out of range"


def test_grid_points_cover_denmark():
    assert isinstance(GRID_POINTS, list)
    assert len(GRID_POINTS) >= 40
    lats = [p["lat"] for p in GRID_POINTS]
    lons = [p["lon"] for p in GRID_POINTS]
    assert min(lats) < 55.0  # Southern DK
    assert max(lats) > 57.0  # Northern DK
    assert min(lons) < 9.0   # Western DK
    assert max(lons) > 12.0  # Eastern DK


def test_grid_point_has_required_fields():
    for gp in GRID_POINTS:
        assert "id" in gp
        assert "lat" in gp
        assert "lon" in gp
        assert "coast_distance_km" in gp
        assert "coast_direction_deg" in gp
        assert gp["id"].startswith("grid_")


def test_all_points_combines_both():
    assert len(ALL_POINTS) == len(AIRFIELDS) + len(GRID_POINTS)


def test_arnborg_exists():
    ids = [af["id"] for af in AIRFIELDS]
    assert "arnborg" in ids
    arnborg = next(af for af in AIRFIELDS if af["id"] == "arnborg")
    assert 55.8 < arnborg["lat"] < 56.0
    assert 8.9 < arnborg["lon"] < 9.2
    assert arnborg["coast_distance_km"] > 50  # Inland


def test_kongsted_is_coastal():
    kongsted = next(af for af in AIRFIELDS if af["id"] == "kongsted")
    assert kongsted["coast_distance_km"] < 25
```

**Step 2: Run tests to verify they fail**

```bash
cd /home/jens/Documents/Flyveteori
source termik/.venv/bin/activate
python -m pytest termik/tests/test_locations.py -v
```

Expected: FAIL with ModuleNotFoundError

**Step 3: Implement locations.py**

File: `termik/locations.py`

This file contains three things:
1. `AIRFIELDS` — list of ~28 dicts with id, name, lat, lon, region, coast_distance_km, coast_direction_deg
2. `GRID_POINTS` — programmatically generated 0.4° grid over Denmark, filtered to land points
3. `ALL_POINTS` — concatenation of both

For each airfield, `coast_distance_km` is the approximate distance to nearest coast, and `coast_direction_deg` is the compass bearing TO the nearest coast (used for sea breeze calculation).

Grid points need a `_is_land(lat, lon)` function that filters out sea points. Use a simple polygon bounding box approach: define rough coastline polygons for Jylland, Fyn, Sjælland, Lolland-Falster, Bornholm. A point is "land" if it falls within any polygon with some margin.

The airfield coordinates must be looked up precisely. Use these verified positions:

**Nordjylland:**
- aars: 56.82, 9.51 (Aviator Aalborg, coast ~45km, coast dir 360)
- saeby: 57.33, 10.53 (Nordjysk/Ottestrup, coast ~5km, coast dir 30)
- skive: 56.58, 9.10 (Vinkel, coast ~30km, coast dir 310)
- svaevethy: 56.83, 8.58 (Mors, coast ~10km, coast dir 270)
- viborg: 56.36, 9.40 (coast ~50km, coast dir 290)

**Midtjylland:**
- aarhus: 56.11, 10.06 (True, coast ~20km, coast dir 90)
- arnborg: 55.92, 9.07 (DSvU, coast ~65km, coast dir 270)
- silkeborg: 56.07, 9.43 (Chr. Hede, coast ~45km, coast dir 270)
- herning: 56.16, 9.02 (Skinderholm, coast ~55km, coast dir 270)
- lemvig: 56.55, 8.30 (coast ~10km, coast dir 270)
- holstebro: 56.38, 8.52 (Nr. Felding, coast ~30km, coast dir 270)
- videbaek: 55.98, 8.63 (coast ~40km, coast dir 270)

**Sydjylland:**
- billund: 55.74, 9.15 (coast ~50km, coast dir 270)
- skrydstrup: 55.22, 9.26 (coast ~40km, coast dir 210)
- kolding: 55.52, 9.32 (Gesten, coast ~25km, coast dir 180)
- roedekro: 55.07, 9.34 (coast ~25km, coast dir 180)
- toender: 54.93, 8.84 (coast ~15km, coast dir 210)
- vejle: 55.69, 9.38 (coast ~15km, coast dir 120)
- bolhede: 55.46, 8.56 (coast ~25km, coast dir 270)

**Fyn:**
- broby: 55.27, 10.22 (coast ~20km, coast dir 180)

**Sjælland:**
- goerloese: 55.85, 12.15 (coast ~20km, coast dir 0)
- frederikssund: 55.84, 12.07 (coast ~10km, coast dir 0)
- kalundborg: 55.68, 11.25 (coast ~5km, coast dir 270)
- kongsted: 55.28, 12.10 (coast ~15km, coast dir 120)
- ringsted: 55.45, 11.78 (Midtsjælland, coast ~25km, coast dir 180)
- toelloese: 55.62, 11.75 (coast ~20km, coast dir 0)
- lolland: 54.76, 11.87 (L-F, coast ~10km, coast dir 180)

**Bornholm:**
- roenne: 55.07, 14.75 (coast ~5km, coast dir 270)

**Step 4: Run tests and verify they pass**

```bash
python -m pytest termik/tests/test_locations.py -v
```

Expected: All PASS

**Step 5: Commit**

```bash
git add termik/locations.py termik/tests/test_locations.py
git commit -m "feat: add locations module with airfields and grid points"
```

---

### Task 3: Configuration Module

**Files:**
- Create: `termik/config.py`

**Step 1: Create config.py**

File: `termik/config.py`

```python
"""Configuration for termik forecast system."""

# Open-Meteo API
API_BASE_URL = "https://api.open-meteo.com/v1/forecast"
API_BATCH_SIZE = 50  # Max locations per request
FORECAST_DAYS = 3
TIMEZONE = "Europe/Berlin"

# Hourly parameters to fetch
HOURLY_PARAMS = [
    "temperature_2m",
    "dewpoint_2m",
    "relative_humidity_2m",
    "wind_speed_10m",
    "wind_direction_10m",
    "wind_gusts_10m",
    "cloud_cover",
    "cloud_cover_low",
    "cloud_cover_mid",
    "cloud_cover_high",
    "precipitation",
    "shortwave_radiation",
    "cape",
    "surface_pressure",
    "temperature_850hPa",
    "temperature_700hPa",
    "wind_speed_850hPa",
    "wind_direction_850hPa",
]

# Scoring weights
WEIGHTS = {
    "lapse_rate": 0.30,
    "solar": 0.20,
    "spread": 0.15,
    "wind": 0.15,
    "temperature": 0.10,
    "precipitation": 0.10,
}

# Score labels
SCORE_LABELS = [
    (9, 10, "Fremragende termik"),
    (7, 8, "God termik"),
    (5, 6, "Moderat termik"),
    (3, 4, "Svag termik"),
    (0, 2, "Ingen brugbar termik"),
]

# Dealbreaker thresholds
DEALBREAKERS = {
    "lapse_rate_inversion": {"threshold": 0.50, "max_score": 1},
    "lapse_rate_stable": {"threshold": 0.65, "max_score": 3},
    "cloud_cover": {"threshold": 87, "max_score": 2},
    "precipitation": {"threshold": 0, "max_score": 1},
    "wind_extreme": {"threshold": 35, "max_score": 2},
    "temp_cold": {"threshold": 5, "max_score": 3},
}

# Sea surface temperature estimate (rough, by month index 1-12)
# Based on Danish waters average
SEA_TEMP_BY_MONTH = {
    1: 4, 2: 3, 3: 4, 4: 6, 5: 10, 6: 14,
    7: 17, 8: 18, 9: 16, 10: 12, 11: 9, 12: 6,
}

# Output paths
OUTPUT_DIR = "termik/output"
DATA_DIR = "termik/output/data"
```

**Step 2: Commit**

```bash
git add termik/config.py
git commit -m "feat: add configuration module"
```

---

### Task 4: Scoring Module (TDD)

**Files:**
- Create: `termik/scoring.py`
- Create: `termik/tests/test_scoring.py`

This is the core of the system. We build it function by function with TDD.

#### Step 1: Write tests for individual score functions

File: `termik/tests/test_scoring.py`

```python
import pytest
from termik.scoring import (
    score_lapse_rate,
    score_solar,
    score_spread,
    score_wind,
    score_temperature,
    score_precipitation,
    calculate_seabreeze_penalty,
    calculate_modifiers,
    apply_dealbreakers,
    compute_thermal_score,
    get_score_label,
)


# --- Lapse rate ---

def test_lapse_very_labil():
    assert score_lapse_rate(1.3) == 10

def test_lapse_labil():
    assert score_lapse_rate(1.1) == 8

def test_lapse_conditional():
    assert score_lapse_rate(0.9) == 5

def test_lapse_neutral():
    assert score_lapse_rate(0.65) == 2

def test_lapse_stable():
    assert score_lapse_rate(0.5) == 0

def test_lapse_inversion():
    assert score_lapse_rate(0.3) == 0


# --- Solar ---

def test_solar_clear_sky_strong():
    # 10% cloud, 800 W/m2
    score = score_solar(10, 800)
    assert 9 <= score <= 10

def test_solar_overcast():
    score = score_solar(95, 50)
    assert score < 2

def test_solar_partly_cloudy():
    score = score_solar(50, 400)
    assert 3 < score < 7


# --- Spread ---

def test_spread_optimal():
    assert score_spread(10) == 10

def test_spread_low_risk():
    assert score_spread(4) == 3

def test_spread_fog():
    assert score_spread(1) == 0

def test_spread_dry_only():
    assert score_spread(22) == 5

def test_spread_boundary_low():
    assert score_spread(8) == 10

def test_spread_boundary_high():
    assert score_spread(15) == 10


# --- Wind ---

def test_wind_optimal():
    assert score_wind(10) == 10

def test_wind_calm():
    assert score_wind(0) == 3

def test_wind_storm():
    assert score_wind(40) == 0

def test_wind_moderate_strong():
    assert score_wind(20) == 6

def test_wind_light():
    assert score_wind(4) == 7


# --- Temperature ---

def test_temp_warm():
    score = score_temperature(25)
    assert score >= 8

def test_temp_cold():
    score = score_temperature(3)
    assert score == 0

def test_temp_moderate():
    score = score_temperature(15)
    assert 2 < score < 6


# --- Precipitation ---

def test_precip_dry():
    assert score_precipitation(0, 0) == 10

def test_precip_active():
    assert score_precipitation(2.0, 5.0) == 0

def test_precip_recent():
    assert score_precipitation(0, 3.0) == 3

def test_precip_light_recent():
    assert score_precipitation(0, 1.0) == 6


# --- Sea breeze ---

def test_seabreeze_inland():
    # 80km from coast, irrelevant
    penalty = calculate_seabreeze_penalty(
        coast_distance_km=80, coast_direction_deg=270,
        wind_dir=270, wind_speed_kt=10, temp_2m=22, month=6
    )
    assert penalty == 0

def test_seabreeze_coastal_onshore():
    # 10km from coast, onshore wind
    penalty = calculate_seabreeze_penalty(
        coast_distance_km=10, coast_direction_deg=270,
        wind_dir=270, wind_speed_kt=5, temp_2m=22, month=6
    )
    assert penalty >= 2

def test_seabreeze_coastal_strong_offshore():
    # 10km from coast, strong offshore wind - no sea breeze
    penalty = calculate_seabreeze_penalty(
        coast_distance_km=10, coast_direction_deg=270,
        wind_dir=90, wind_speed_kt=20, temp_2m=22, month=6
    )
    assert penalty == 0


# --- Dealbreakers ---

def test_dealbreaker_stable():
    score = apply_dealbreakers(7.0, lapse_rate=0.55, cloud_cover=30,
                                precipitation=0, wind_kt=10, temp=15)
    assert score <= 3

def test_dealbreaker_inversion():
    score = apply_dealbreakers(5.0, lapse_rate=0.4, cloud_cover=30,
                                precipitation=0, wind_kt=10, temp=15)
    assert score <= 1

def test_dealbreaker_overcast():
    score = apply_dealbreakers(5.0, lapse_rate=1.0, cloud_cover=90,
                                precipitation=0, wind_kt=10, temp=15)
    assert score <= 2

def test_dealbreaker_rain():
    score = apply_dealbreakers(5.0, lapse_rate=1.0, cloud_cover=50,
                                precipitation=2.0, wind_kt=10, temp=15)
    assert score <= 1

def test_no_dealbreaker():
    score = apply_dealbreakers(8.0, lapse_rate=1.0, cloud_cover=30,
                                precipitation=0, wind_kt=10, temp=15)
    assert score == 8.0


# --- Full scenario tests ---

def test_scenario_perfect_day():
    """Perfekt bagsidevejr efter koldfront i juni."""
    result = compute_thermal_score(
        temp_2m=22, dewpoint_2m=8, temp_850hpa=5,
        cloud_cover=30, shortwave_radiation=700,
        wind_speed_kt=12, wind_dir=290, wind_gusts_kt=20,
        precipitation=0, precip_last_6h=0,
        cape=500, surface_pressure=1020, pressure_trend=2.0,
        temp_850hpa_trend=-1.0,
        coast_distance_km=65, coast_direction_deg=270, month=6,
    )
    assert result["score"] >= 9.0
    assert "Fremragende" in result["label"] or "God" in result["label"]


def test_scenario_sahara():
    """30 grader men stabil Sahara-luft."""
    result = compute_thermal_score(
        temp_2m=30, dewpoint_2m=10, temp_850hpa=22,
        cloud_cover=5, shortwave_radiation=850,
        wind_speed_kt=5, wind_dir=150, wind_gusts_kt=8,
        precipitation=0, precip_last_6h=0,
        cape=50, surface_pressure=1025, pressure_trend=0,
        temp_850hpa_trend=0,
        coast_distance_km=65, coast_direction_deg=270, month=7,
    )
    assert result["score"] <= 3.0
    assert "Svag" in result["label"] or "Ingen" in result["label"]


def test_scenario_winter():
    """Overskyet vinterdag."""
    result = compute_thermal_score(
        temp_2m=3, dewpoint_2m=1, temp_850hpa=-2,
        cloud_cover=95, shortwave_radiation=30,
        wind_speed_kt=15, wind_dir=250, wind_gusts_kt=25,
        precipitation=0.5, precip_last_6h=3.0,
        cape=0, surface_pressure=1005, pressure_trend=-1.0,
        temp_850hpa_trend=0,
        coast_distance_km=40, coast_direction_deg=270, month=12,
    )
    assert result["score"] <= 1.0


def test_scenario_seabreeze_coast_vs_inland():
    """Samme vejr, kyst vs indland - kyst skal score lavere."""
    params = dict(
        temp_2m=21, dewpoint_2m=11, temp_850hpa=7,
        cloud_cover=20, shortwave_radiation=750,
        wind_speed_kt=5, wind_dir=90, wind_gusts_kt=8,
        precipitation=0, precip_last_6h=0,
        cape=300, surface_pressure=1020, pressure_trend=0,
        temp_850hpa_trend=0, month=6,
    )
    coast = compute_thermal_score(
        **params, coast_distance_km=15, coast_direction_deg=90
    )
    inland = compute_thermal_score(
        **params, coast_distance_km=65, coast_direction_deg=270
    )
    assert inland["score"] > coast["score"]
    assert inland["score"] - coast["score"] >= 1.5


def test_score_label():
    assert get_score_label(9.5) == "Fremragende termik"
    assert get_score_label(7.0) == "God termik"
    assert get_score_label(5.0) == "Moderat termik"
    assert get_score_label(3.0) == "Svag termik"
    assert get_score_label(1.0) == "Ingen brugbar termik"


def test_score_has_required_fields():
    result = compute_thermal_score(
        temp_2m=20, dewpoint_2m=10, temp_850hpa=8,
        cloud_cover=30, shortwave_radiation=600,
        wind_speed_kt=10, wind_dir=270, wind_gusts_kt=15,
        precipitation=0, precip_last_6h=0,
        cape=200, surface_pressure=1018, pressure_trend=0,
        temp_850hpa_trend=0,
        coast_distance_km=50, coast_direction_deg=270, month=6,
    )
    assert "score" in result
    assert "label" in result
    assert "spread" in result
    assert "skybase_m" in result
    assert "skybase_ft" in result
    assert "lapse_rate" in result
    assert 0 <= result["score"] <= 10
```

#### Step 2: Run tests to verify they fail

```bash
python -m pytest termik/tests/test_scoring.py -v
```

Expected: FAIL with ModuleNotFoundError

#### Step 3: Implement scoring.py

File: `termik/scoring.py`

Implement all functions:
- `score_lapse_rate(lapse_rate: float) -> int` — step function as per design
- `score_solar(cloud_cover: float, shortwave_radiation: float) -> float` — weighted cloud + radiation
- `score_spread(spread: float) -> int` — step function for spread ranges
- `score_wind(wind_kt: float) -> int` — step function for wind ranges
- `score_temperature(temp: float) -> float` — linear scale `min(max((temp - 5) / 2.5, 0), 10)`
- `score_precipitation(precip: float, precip_last_6h: float) -> int` — step function
- `calculate_seabreeze_penalty(...)` — sea breeze model from design section 9
- `calculate_modifiers(cape, pressure_trend, temp_850hpa_trend) -> float` — CAPE bonus + trend modifiers
- `apply_dealbreakers(score, lapse_rate, cloud_cover, precipitation, wind_kt, temp) -> float` — caps score
- `compute_thermal_score(**kwargs) -> dict` — orchestrator: computes all sub-scores, applies weights, modifiers, dealbreakers, returns dict with score + metadata
- `get_score_label(score: float) -> str` — maps score to Danish label text

The `compute_thermal_score` function:
1. Calculate derived values: `spread = temp_2m - dewpoint_2m`, `lapse_rate = (temp_2m - temp_850hpa) / 15`, `skybase_m = spread * 125`, `skybase_ft = spread * 400`
2. Calculate each sub-score
3. Weighted sum
4. Add modifiers (CAPE, pressure trend, cold air advection)
5. Subtract sea breeze penalty
6. Apply dealbreakers
7. Clamp 0-10
8. Return dict with score, label, and all computed values

#### Step 4: Run tests and iterate until all pass

```bash
python -m pytest termik/tests/test_scoring.py -v
```

Expected: All PASS

#### Step 5: Commit

```bash
git add termik/scoring.py termik/tests/test_scoring.py
git commit -m "feat: add thermal scoring model with TDD"
```

---

### Task 5: Comments Module

**Files:**
- Create: `termik/comments.py`
- Create: `termik/tests/test_comments.py`

#### Step 1: Write failing tests

File: `termik/tests/test_comments.py`

```python
from termik.comments import generate_comment


def test_comment_includes_stability():
    comment = generate_comment(
        lapse_rate=1.1, spread=10, skybase_m=1250, wind_kt=12,
        cloud_cover=30, cape=300, precipitation=0,
        seabreeze_risk=0, pressure_trend=1.0, score=8.5,
    )
    assert "Labil" in comment


def test_comment_includes_skybase():
    comment = generate_comment(
        lapse_rate=0.9, spread=10, skybase_m=1250, wind_kt=10,
        cloud_cover=30, cape=200, precipitation=0,
        seabreeze_risk=0, pressure_trend=0, score=6.0,
    )
    assert "1250" in comment or "skybase" in comment.lower()


def test_comment_warns_seabreeze():
    comment = generate_comment(
        lapse_rate=0.9, spread=10, skybase_m=1250, wind_kt=8,
        cloud_cover=20, cape=200, precipitation=0,
        seabreeze_risk=2, pressure_trend=0, score=6.0,
    )
    assert "brise" in comment.lower() or "søbrise" in comment.lower()


def test_comment_warns_overdevelopment():
    comment = generate_comment(
        lapse_rate=1.2, spread=8, skybase_m=1000, wind_kt=10,
        cloud_cover=40, cape=1200, precipitation=0,
        seabreeze_risk=0, pressure_trend=0, score=8.0,
    )
    assert "overudvikling" in comment.lower() or "Cb" in comment


def test_comment_warns_strong_wind():
    comment = generate_comment(
        lapse_rate=1.1, spread=10, skybase_m=1250, wind_kt=28,
        cloud_cover=40, cape=500, precipitation=0,
        seabreeze_risk=0, pressure_trend=1.0, score=7.0,
    )
    assert "vind" in comment.lower() or "turbulent" in comment.lower()


def test_comment_stable_atmosphere():
    comment = generate_comment(
        lapse_rate=0.5, spread=20, skybase_m=2500, wind_kt=5,
        cloud_cover=5, cape=50, precipitation=0,
        seabreeze_risk=0, pressure_trend=0, score=3.0,
    )
    assert "Stabil" in comment or "stabil" in comment


def test_comment_is_string():
    comment = generate_comment(
        lapse_rate=1.0, spread=10, skybase_m=1250, wind_kt=10,
        cloud_cover=30, cape=200, precipitation=0,
        seabreeze_risk=0, pressure_trend=0, score=7.0,
    )
    assert isinstance(comment, str)
    assert len(comment) > 10
    assert len(comment) < 300
```

#### Step 2: Run tests to verify they fail

```bash
python -m pytest termik/tests/test_comments.py -v
```

#### Step 3: Implement comments.py

File: `termik/comments.py`

Function `generate_comment(...)` builds a comment string from 2-3 building blocks:
1. Always: stability assessment based on lapse_rate
2. If termik possible (score >= 3): skybase info
3. Conditionally: warnings (seabreeze, overdevelopment, strong wind, front)
4. Conditionally: positive notes (backside weather, cloud streets)

Returns a single string, max ~200 chars.

#### Step 4: Run tests, iterate

```bash
python -m pytest termik/tests/test_comments.py -v
```

#### Step 5: Commit

```bash
git add termik/comments.py termik/tests/test_comments.py
git commit -m "feat: add comment generation module"
```

---

### Task 6: Weather Fetcher Module

**Files:**
- Create: `termik/fetch_weather.py`
- Create: `termik/tests/test_fetch_weather.py`

#### Step 1: Write tests for data transformation (not API calls)

File: `termik/tests/test_fetch_weather.py`

```python
import json
from termik.fetch_weather import (
    build_api_url,
    parse_api_response,
    calculate_precip_last_6h,
    calculate_pressure_trend,
    calculate_temp_850_trend,
    process_point_hour,
)


def test_build_api_url_single():
    points = [{"lat": 55.92, "lon": 9.07}]
    url = build_api_url(points)
    assert "latitude=55.92" in url
    assert "longitude=9.07" in url
    assert "forecast_days=3" in url
    assert "temperature_2m" in url
    assert "temperature_850hPa" in url


def test_build_api_url_multi():
    points = [
        {"lat": 55.92, "lon": 9.07},
        {"lat": 55.28, "lon": 12.10},
    ]
    url = build_api_url(points)
    assert "55.92,55.28" in url
    assert "9.07,12.1" in url


def test_parse_api_response_single():
    """Single-location response is a dict, not a list."""
    raw = {
        "latitude": 55.92,
        "longitude": 9.07,
        "hourly": {
            "time": ["2026-03-27T10:00"],
            "temperature_2m": [18.5],
        }
    }
    result = parse_api_response(raw)
    assert isinstance(result, list)
    assert len(result) == 1
    assert result[0]["hourly"]["temperature_2m"] == [18.5]


def test_parse_api_response_multi():
    """Multi-location response is a list."""
    raw = [
        {"latitude": 55.92, "hourly": {"time": ["t1"], "temperature_2m": [18]}},
        {"latitude": 55.28, "hourly": {"time": ["t1"], "temperature_2m": [17]}},
    ]
    result = parse_api_response(raw)
    assert len(result) == 2


def test_calculate_precip_last_6h():
    precip_values = [0, 0, 0, 0, 1.0, 0.5, 0.2, 0, 0, 0]
    # At index 8, last 6 hours are indices 3-8: [0, 1.0, 0.5, 0.2, 0, 0] = 1.7
    result = calculate_precip_last_6h(precip_values, 8)
    assert abs(result - 1.7) < 0.01


def test_calculate_precip_last_6h_start():
    """At start of array, sum whatever is available."""
    precip_values = [0.5, 0.3, 0, 0]
    result = calculate_precip_last_6h(precip_values, 1)
    assert abs(result - 0.8) < 0.01


def test_calculate_pressure_trend():
    pressures = [1010, 1011, 1012, 1013]
    trend = calculate_pressure_trend(pressures, 3)
    assert trend == 3.0  # +3 hPa over 3 hours


def test_calculate_temp_850_trend():
    temps = [5.0, 4.5, 4.0, 3.5]
    trend = calculate_temp_850_trend(temps, 3)
    assert trend == -1.5  # cooling = negative
```

#### Step 2: Run tests

```bash
python -m pytest termik/tests/test_fetch_weather.py -v
```

#### Step 3: Implement fetch_weather.py

File: `termik/fetch_weather.py`

Functions:
- `build_api_url(points: list[dict]) -> str` — builds Open-Meteo URL with all params
- `fetch_batch(points: list[dict]) -> list[dict]` — calls API, returns parsed response
- `parse_api_response(raw) -> list[dict]` — normalizes single/multi response to list
- `calculate_precip_last_6h(precip_list, hour_index) -> float` — sums last 6 hours
- `calculate_pressure_trend(pressure_list, hour_index) -> float` — delta over 3 hours
- `calculate_temp_850_trend(temp_list, hour_index) -> float` — delta over 3 hours
- `process_point_hour(point, hourly_data, hour_index, month) -> dict` — extracts values for one hour, calls compute_thermal_score, returns result dict
- `process_all_points() -> dict` — main orchestrator: batches points, fetches data, processes all hours, returns full JSON structure
- `write_output(data: dict)` — writes current.json, airfields.json, meta.json
- `main()` — entry point

#### Step 4: Run tests

```bash
python -m pytest termik/tests/test_fetch_weather.py -v
```

#### Step 5: Test with live API (manual)

```bash
cd /home/jens/Documents/Flyveteori
source termik/.venv/bin/activate
python -m termik.fetch_weather
cat termik/output/data/current.json | python -m json.tool | head -50
```

Verify: JSON file exists, has points, has scores, timestamps look correct.

#### Step 6: Commit

```bash
git add termik/fetch_weather.py termik/tests/test_fetch_weather.py termik/__init__.py
git commit -m "feat: add weather fetcher with Open-Meteo integration"
```

---

### Task 7: Frontend

**Files:**
- Create: `termik/output/index.html`
- Create: `termik/output/style.css`
- Create: `termik/output/app.js`

#### Step 1: Create index.html

Basic structure:
- Loads Leaflet.js + leaflet-heat from CDN
- Map container (full page)
- Control panel: day buttons, time slider
- Side panel: top-5 list
- Popup template for airfield details

```html
<!DOCTYPE html>
<html lang="da">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Termik-forecast Danmark</title>
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9/dist/leaflet.css" />
    <link rel="stylesheet" href="style.css" />
</head>
<body>
    <div id="map"></div>
    <div id="controls">
        <div id="day-selector"><!-- 3 day buttons --></div>
        <div id="time-slider"><!-- range input 6-21 --></div>
        <div id="time-display"></div>
    </div>
    <div id="sidebar">
        <h2>Top 5 pladser</h2>
        <div id="top-list"></div>
        <div id="meta-info"></div>
    </div>
    <script src="https://unpkg.com/leaflet@1.9/dist/leaflet.js"></script>
    <script src="https://unpkg.com/leaflet.heat@0.2/dist/leaflet-heat.js"></script>
    <script src="app.js"></script>
</body>
</html>
```

#### Step 2: Create style.css

- Full-page map
- Semi-transparent control panel at top
- Side panel (desktop: right side, mobile: bottom sheet)
- Score colors: CSS variables for the color ramp
- Popup styling matching the design mockup
- Responsive breakpoints

#### Step 3: Create app.js

Core functionality:
1. `loadData()` — fetch current.json, parse, store in memory
2. `initMap()` — create Leaflet map centered on Denmark (56.2, 10.5, zoom 7)
3. `updateHeatmap(day, hour)` — rebuild heat layer from grid points for selected time
4. `addAirfieldMarkers()` — add colored circle markers for each airfield
5. `updateMarkerColors(day, hour)` — update marker colors based on score
6. `createPopup(airfield, day, hour)` — build popup HTML with score details
7. `createDayChart(airfield, day)` — simple SVG bar chart showing hourly scores
8. `updateTopList(day, hour)` — sort airfields by score, show top 5 in sidebar
9. Event handlers for day buttons and time slider

Color mapping function:
```javascript
function scoreToColor(score) {
    // 0=dark blue, 3=light blue, 5=yellow, 7=orange, 10=red
    const stops = [
        [0, [30, 60, 150]],    // dark blue
        [3, [100, 150, 220]],  // light blue
        [5, [240, 220, 50]],   // yellow
        [7, [240, 140, 30]],   // orange
        [10, [220, 30, 30]],   // red
    ];
    // interpolate between stops
}
```

Heatmap configuration:
```javascript
const heat = L.heatLayer([], {
    radius: 35,
    blur: 25,
    maxZoom: 10,
    gradient: {
        0.0: '#1e3c96',  // dark blue
        0.3: '#6496dc',  // light blue
        0.5: '#f0dc32',  // yellow
        0.7: '#f08c1e',  // orange
        1.0: '#dc1e1e',  // red
    }
});
```

#### Step 4: Test manually in browser

```bash
cd /home/jens/Documents/Flyveteori
# First generate data
source termik/.venv/bin/activate
python -m termik.fetch_weather
# Then open in browser
xdg-open termik/output/index.html
```

Verify:
- Map shows Denmark
- Heatmap overlay is visible
- Airfield markers are clickable
- Time slider updates the heatmap
- Day buttons switch between days
- Popups show correct data

#### Step 5: Commit

```bash
git add termik/output/index.html termik/output/style.css termik/output/app.js
git commit -m "feat: add frontend with Leaflet heatmap and airfield markers"
```

---

### Task 8: Cron Setup and Final Integration

**Files:**
- Create: `termik/cron_setup.sh`
- Create: `termik/__main__.py`

#### Step 1: Create __main__.py entry point

File: `termik/__main__.py`

```python
"""Entry point: python -m termik"""
from termik.fetch_weather import main

if __name__ == "__main__":
    main()
```

#### Step 2: Create cron_setup.sh

File: `termik/cron_setup.sh`

```bash
#!/bin/bash
# Adds cron job to run termik forecast every 3 hours
# Usage: bash termik/cron_setup.sh

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
VENV="$SCRIPT_DIR/.venv/bin/python"
LOG="$SCRIPT_DIR/output/cron.log"

CRON_CMD="0 */3 * * * cd $PROJECT_DIR && $VENV -m termik >> $LOG 2>&1"

# Check if already installed
if crontab -l 2>/dev/null | grep -q "termik"; then
    echo "Cron job already exists. Current crontab:"
    crontab -l | grep termik
    exit 0
fi

# Add to crontab
(crontab -l 2>/dev/null; echo "$CRON_CMD") | crontab -
echo "Cron job installed: $CRON_CMD"
echo "Next run: $(date -d 'next hour' '+%H:00')"
```

#### Step 3: Run full end-to-end test

```bash
cd /home/jens/Documents/Flyveteori
source termik/.venv/bin/activate

# Run all tests
python -m pytest termik/tests/ -v

# Run the full pipeline
python -m termik

# Verify output files exist
ls -la termik/output/data/
cat termik/output/data/meta.json

# Open in browser
xdg-open termik/output/index.html
```

#### Step 4: Commit

```bash
git add termik/__main__.py termik/__init__.py termik/cron_setup.sh
git commit -m "feat: add entry point and cron setup"
```

---

## Task Overview

| Task | Beskrivelse | Estimeret steps |
|------|-------------|----------------|
| 1 | Project setup | 6 |
| 2 | Locations module | 5 |
| 3 | Config module | 2 |
| 4 | Scoring module (TDD) | 5 |
| 5 | Comments module | 5 |
| 6 | Weather fetcher | 6 |
| 7 | Frontend | 5 |
| 8 | Cron + integration | 4 |
| **Total** | | **38 steps** |

## Dependencies

```
Task 1 (setup)
  └── Task 2 (locations) + Task 3 (config)
        └── Task 4 (scoring)
              └── Task 5 (comments)
                    └── Task 6 (fetcher)
                          └── Task 7 (frontend)
                                └── Task 8 (cron)
```

Tasks 2 and 3 can run in parallel. All others are sequential.
