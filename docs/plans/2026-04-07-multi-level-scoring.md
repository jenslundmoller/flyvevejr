# Multi-Level Wind & Temperature Scoring Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Integrate wind (80m/120m/180m), temperature (80m/120m/180m), and boundary layer height data from Open-Meteo into the thermal scoring system, improving forecast accuracy for pilots based on meteorological research.

**Architecture:** Keep the existing scoring framework intact. Add new data as modifiers and dealbreakers on top of the current weighted score, following the principle that the bulk lapse rate (2m-850hPa) remains the primary stability indicator. New data provides: (1) surface lapse rate as an initiation gate, (2) wind shear as a thermal quality modifier, (3) BL mixing as a stability diagnostic, (4) enriched output for frontend display.

**Tech Stack:** Python 3, Open-Meteo API, pytest, vanilla JS frontend

**Scientific basis (from research):**
- Surface lapse rate (2m→180m): >0.98°C/100m = superadiabatic = thermals initiating. <0.5 = stable, no initiation. (Stull 1988, DrJack RASP)
- Wind shear (10m→80m): Low shear on convective day = well-organized thermals. High shear = broken/tilted thermals. (RASP B/S ratio concept)
- BL mixing (80m→180m wind gradient): Small difference = well-mixed convective BL. Large difference = stable/transitional. (Boundary layer meteorology, power law)
- Boundary layer height: Key parameter for thermal height estimation. (All major soaring forecast systems)

---

### Task 1: Fix pre-existing test failure

**Files:**
- Modify: `termik/tests/test_fetch_weather.py:13`

The test expects `forecast_days=3` but config has `FORECAST_DAYS=7`. Fix the test to match reality.

**Step 1: Fix the test**

```python
# In test_build_api_url_single, change:
    assert "forecast_days=3" in url
# To:
    assert "forecast_days=7" in url
```

**Step 2: Run test to verify it passes**

Run: `python3 -m pytest termik/tests/test_fetch_weather.py::test_build_api_url_single -v`
Expected: PASS

**Step 3: Commit**

```bash
git add termik/tests/test_fetch_weather.py
git commit -m "fix: update test to match current FORECAST_DAYS=7 config"
```

---

### Task 2: Extend API parameters in config.py

**Files:**
- Modify: `termik/config.py:10-29`

**Step 1: Write the test**

Add to `termik/tests/test_fetch_weather.py`:

```python
def test_build_api_url_includes_altitude_params():
    points = [{"lat": 55.92, "lon": 9.07}]
    url = build_api_url(points)
    assert "wind_speed_80m" in url
    assert "wind_speed_120m" in url
    assert "wind_speed_180m" in url
    assert "wind_direction_80m" in url
    assert "temperature_80m" in url
    assert "temperature_180m" in url
    assert "boundary_layer_height" in url
```

**Step 2: Run test to verify it fails**

Run: `python3 -m pytest termik/tests/test_fetch_weather.py::test_build_api_url_includes_altitude_params -v`
Expected: FAIL

**Step 3: Add new parameters to config.py**

In `termik/config.py`, update `HOURLY_PARAMS` to:

```python
HOURLY_PARAMS = [
    "temperature_2m",
    "dewpoint_2m",
    "relative_humidity_2m",
    "wind_speed_10m",
    "wind_direction_10m",
    "wind_gusts_10m",
    # Multi-level wind (80m/120m/180m)
    "wind_speed_80m",
    "wind_direction_80m",
    "wind_speed_120m",
    "wind_direction_120m",
    "wind_speed_180m",
    "wind_direction_180m",
    # Multi-level temperature
    "temperature_80m",
    "temperature_120m",
    "temperature_180m",
    # Standard parameters
    "cloud_cover",
    "cloud_cover_low",
    "cloud_cover_mid",
    "cloud_cover_high",
    "precipitation",
    "shortwave_radiation",
    "cape",
    "surface_pressure",
    "boundary_layer_height",
    # Pressure levels
    "temperature_850hPa",
    "temperature_700hPa",
    "wind_speed_850hPa",
    "wind_direction_850hPa",
]
```

**Step 4: Run test to verify it passes**

Run: `python3 -m pytest termik/tests/test_fetch_weather.py -v`
Expected: ALL PASS

**Step 5: Commit**

```bash
git add termik/config.py termik/tests/test_fetch_weather.py
git commit -m "feat: add multi-level wind, temperature, and BL height API parameters"
```

---

### Task 3: Surface lapse rate scoring function

**Files:**
- Modify: `termik/scoring.py` (new function)
- Modify: `termik/tests/test_scoring.py` (new tests)

The surface lapse rate (2m→180m) indicates whether thermals can initiate. Height difference is 178m = 1.78 hectometers. DALR is 0.98°C/100m. In the surface layer, superadiabatic (>0.98) is normal on sunny days due to 2m sensor proximity to heated ground.

**Step 1: Write failing tests**

Add to `termik/tests/test_scoring.py`:

```python
from termik.scoring import score_surface_lapse_rate

# --- Surface lapse rate (2m → 180m) ---
# Measures thermal initiation potential. Superadiabatic (>0.98°C/100m) = thermals starting.
# The 2m→180m layer is expected to be superadiabatic on sunny days.

def test_surface_lapse_superadiabatic():
    """1.5°C/100m — strong surface heating, thermals initiating."""
    assert score_surface_lapse_rate(1.5) == 10

def test_surface_lapse_adiabatic():
    """1.0°C/100m — near DALR, convection developing."""
    assert score_surface_lapse_rate(1.0) == 7

def test_surface_lapse_marginal():
    """0.7°C/100m — sub-adiabatic, marginal initiation."""
    assert score_surface_lapse_rate(0.7) == 3

def test_surface_lapse_stable():
    """0.4°C/100m — stable, no thermal initiation."""
    assert score_surface_lapse_rate(0.4) == 0

def test_surface_lapse_inversion():
    """Negative — inversion layer, thermals completely suppressed."""
    assert score_surface_lapse_rate(-0.5) == 0
```

**Step 2: Run tests to verify they fail**

Run: `python3 -m pytest termik/tests/test_scoring.py -k "surface_lapse" -v`
Expected: FAIL (ImportError)

**Step 3: Implement the function**

Add to `termik/scoring.py`:

```python
def score_surface_lapse_rate(surface_lapse: float) -> int:
    """Score thermal initiation potential from the 2m→180m lapse rate.

    The surface layer is expected to be superadiabatic (>0.98°C/100m)
    during active convection. Values well above DALR are normal here
    due to the 2m sensor's proximity to the heated ground.
    """
    if surface_lapse >= 1.3:
        return 10
    elif surface_lapse >= 0.98:
        return 7
    elif surface_lapse >= 0.65:
        return 3
    elif surface_lapse >= 0.5:
        return 1
    else:
        return 0
```

**Step 4: Run tests to verify they pass**

Run: `python3 -m pytest termik/tests/test_scoring.py -k "surface_lapse" -v`
Expected: ALL PASS

**Step 5: Commit**

```bash
git add termik/scoring.py termik/tests/test_scoring.py
git commit -m "feat: add surface lapse rate scoring function (2m→180m)"
```

---

### Task 4: Wind shear modifier function

**Files:**
- Modify: `termik/scoring.py` (new function)
- Modify: `termik/tests/test_scoring.py` (new tests)

Wind shear between 10m and 80m indicates thermal quality. Based on the RASP Buoyancy/Shear ratio concept: low shear = well-organized thermals, high shear = broken/tilted thermals.

**Step 1: Write failing tests**

Add to `termik/tests/test_scoring.py`:

```python
from termik.scoring import calculate_wind_shear_modifier

# --- Wind shear modifier (10m vs 80m) ---
# Low shear = well-organized thermals. High shear = broken thermals.

def test_wind_shear_low():
    """3kt difference — well-organized thermals, bonus."""
    assert calculate_wind_shear_modifier(10, 13) == 0.5

def test_wind_shear_moderate():
    """8kt difference — normal, no modifier."""
    assert calculate_wind_shear_modifier(10, 18) == 0.0

def test_wind_shear_high():
    """16kt difference — thermals tilted/broken, penalty."""
    assert calculate_wind_shear_modifier(8, 24) == -0.5

def test_wind_shear_extreme():
    """22kt difference — severe shear, strong penalty."""
    assert calculate_wind_shear_modifier(5, 27) == -1.0

def test_wind_shear_calm():
    """Both calm — no meaningful shear assessment."""
    assert calculate_wind_shear_modifier(0, 2) == 0.0
```

**Step 2: Run tests to verify they fail**

Run: `python3 -m pytest termik/tests/test_scoring.py -k "wind_shear" -v`
Expected: FAIL (ImportError)

**Step 3: Implement the function**

Add to `termik/scoring.py`:

```python
def calculate_wind_shear_modifier(wind_10m_kt: float, wind_80m_kt: float) -> float:
    """Calculate thermal quality modifier from low-level wind shear.

    Based on RASP B/S ratio concept: thermals need to overcome shear
    to remain organized. Shear is concentrated in the surface layer (0-100m).
    """
    shear = abs(wind_80m_kt - wind_10m_kt)
    if shear < 5:
        return 0.5   # Well-organized thermals
    elif shear < 12:
        return 0.0   # Normal shear
    elif shear < 20:
        return -0.5  # Thermals tilted/broken
    else:
        return -1.0  # Severe shear, thermals destroyed
```

**Step 4: Run tests to verify they pass**

Run: `python3 -m pytest termik/tests/test_scoring.py -k "wind_shear" -v`
Expected: ALL PASS

**Step 5: Commit**

```bash
git add termik/scoring.py termik/tests/test_scoring.py
git commit -m "feat: add wind shear modifier for thermal quality (10m vs 80m)"
```

---

### Task 5: BL mixing diagnostic function

**Files:**
- Modify: `termik/scoring.py` (new function)
- Modify: `termik/tests/test_scoring.py` (new tests)

In a well-mixed convective boundary layer, wind speed is nearly uniform with height above the surface layer. A large difference between 80m and 180m wind indicates the boundary layer is NOT well-mixed (stable or transitional = poor thermals).

**Step 1: Write failing tests**

Add to `termik/tests/test_scoring.py`:

```python
from termik.scoring import calculate_bl_mixing_modifier

# --- BL mixing diagnostic (80m vs 180m wind gradient) ---
# Small gradient = well-mixed CBL (good thermals). Large = stable/transitional.

def test_bl_mixing_wellmixed():
    """2kt difference — well-mixed convective BL, bonus."""
    assert calculate_bl_mixing_modifier(12, 14) == 0.3

def test_bl_mixing_moderate():
    """6kt difference — partially mixed, no modifier."""
    assert calculate_bl_mixing_modifier(10, 16) == 0.0

def test_bl_mixing_poor():
    """10kt difference — not well-mixed, penalty."""
    assert calculate_bl_mixing_modifier(10, 20) == -0.3
```

**Step 2: Run tests to verify they fail**

Run: `python3 -m pytest termik/tests/test_scoring.py -k "bl_mixing" -v`
Expected: FAIL (ImportError)

**Step 3: Implement the function**

Add to `termik/scoring.py`:

```python
def calculate_bl_mixing_modifier(wind_80m_kt: float, wind_180m_kt: float) -> float:
    """Assess boundary layer mixing from the 80m-180m wind gradient.

    In a well-mixed convective BL, wind is nearly uniform above the surface
    layer. A large gradient indicates stable or transitional conditions.
    """
    gradient = abs(wind_180m_kt - wind_80m_kt)
    if gradient < 4:
        return 0.3   # Well-mixed CBL
    elif gradient < 8:
        return 0.0   # Moderate mixing
    else:
        return -0.3  # Poor mixing, stable/transitional
```

**Step 4: Run tests to verify they pass**

Run: `python3 -m pytest termik/tests/test_scoring.py -k "bl_mixing" -v`
Expected: ALL PASS

**Step 5: Commit**

```bash
git add termik/scoring.py termik/tests/test_scoring.py
git commit -m "feat: add BL mixing diagnostic from 80m-180m wind gradient"
```

---

### Task 6: Integrate new scoring into compute_thermal_score

**Files:**
- Modify: `termik/scoring.py` (`compute_thermal_score`, `apply_dealbreakers`)
- Modify: `termik/tests/test_scoring.py` (update existing tests + new integration tests)

This is the critical integration step. New parameters default to `None` so all existing tests continue to pass unchanged. When data is provided, the new scoring enhances the result.

**Step 1: Write failing integration tests**

Add to `termik/tests/test_scoring.py`:

```python
# --- Integration: multi-level data improves scoring ---

def test_surface_inversion_caps_score():
    """Good bulk lapse rate but surface inversion → score capped."""
    result = compute_thermal_score(
        temp_2m=22, dewpoint_2m=8, temp_850hpa=5,
        cloud_cover=30, shortwave_radiation=700,
        wind_speed_kt=12, wind_dir=290, wind_gusts_kt=16,
        precipitation=0, precip_last_6h=0,
        cape=500, surface_pressure=1020, pressure_trend=2.0,
        temp_850hpa_trend=-1.0,
        coast_distance_km=65, coast_direction_deg=270, month=6,
        # Good bulk lapse but surface inversion (temp_180m > temp_2m adjusted)
        temp_180m=21.5,  # surface lapse = (22 - 21.5) / 1.78 = 0.28 → inversion
    )
    assert result["score"] <= 2.0


def test_high_shear_penalizes():
    """Good conditions but high wind shear → reduced score."""
    base_params = dict(
        temp_2m=22, dewpoint_2m=8, temp_850hpa=5,
        cloud_cover=30, shortwave_radiation=700,
        wind_speed_kt=8, wind_dir=290, wind_gusts_kt=14,
        precipitation=0, precip_last_6h=0,
        cape=400, surface_pressure=1020, pressure_trend=1.0,
        temp_850hpa_trend=-0.5,
        coast_distance_km=65, coast_direction_deg=270, month=6,
        temp_180m=18.5,  # surface lapse = (22-18.5)/1.78 = 1.97 → superadiabatic
    )
    # Low shear
    low_shear = compute_thermal_score(**base_params, wind_speed_80m_kt=10, wind_speed_180m_kt=11)
    # High shear
    high_shear = compute_thermal_score(**base_params, wind_speed_80m_kt=25, wind_speed_180m_kt=30)
    assert low_shear["score"] > high_shear["score"]


def test_multilevel_data_in_result():
    """Result dict includes new diagnostic fields when data is provided."""
    result = compute_thermal_score(
        temp_2m=22, dewpoint_2m=8, temp_850hpa=5,
        cloud_cover=30, shortwave_radiation=700,
        wind_speed_kt=10, wind_dir=270, wind_gusts_kt=15,
        precipitation=0, precip_last_6h=0,
        cape=300, surface_pressure=1018, pressure_trend=0,
        temp_850hpa_trend=0,
        coast_distance_km=50, coast_direction_deg=270, month=6,
        temp_180m=19.0,
        wind_speed_80m_kt=13,
        wind_speed_180m_kt=14,
    )
    assert "surface_lapse_rate" in result
    assert "wind_shear_modifier" in result
    assert "bl_mixing_modifier" in result


def test_existing_scoring_unchanged_without_new_data():
    """When no multi-level data provided, score is identical to before."""
    result = compute_thermal_score(
        temp_2m=22, dewpoint_2m=8, temp_850hpa=5,
        cloud_cover=30, shortwave_radiation=700,
        wind_speed_kt=12, wind_dir=290, wind_gusts_kt=16,
        precipitation=0, precip_last_6h=0,
        cape=500, surface_pressure=1020, pressure_trend=2.0,
        temp_850hpa_trend=-1.0,
        coast_distance_km=65, coast_direction_deg=270, month=6,
    )
    # This is the same scenario as test_scenario_perfect_day
    assert result["score"] >= 9.0
```

**Step 2: Run tests to verify they fail**

Run: `python3 -m pytest termik/tests/test_scoring.py -k "surface_inversion_caps or high_shear_penalizes or multilevel_data_in or existing_scoring_unchanged" -v`
Expected: FAIL (unexpected keyword arguments)

**Step 3: Update compute_thermal_score**

Modify `compute_thermal_score` in `termik/scoring.py` to add new optional parameters and integrate them:

```python
def compute_thermal_score(
    temp_2m: float,
    dewpoint_2m: float,
    temp_850hpa: float,
    cloud_cover: float,
    shortwave_radiation: float,
    wind_speed_kt: float,
    wind_dir: float,
    wind_gusts_kt: float,
    precipitation: float,
    precip_last_6h: float,
    cape: float,
    surface_pressure: float,
    pressure_trend: float,
    temp_850hpa_trend: float,
    coast_distance_km: float,
    coast_direction_deg: float,
    month: int,
    # Multi-level data (optional — enhances scoring when available)
    temp_180m: float | None = None,
    wind_speed_80m_kt: float | None = None,
    wind_speed_180m_kt: float | None = None,
    boundary_layer_height: float | None = None,
) -> dict:
    """Compute the full thermal score from weather parameters.

    Returns a dict with score (0-10), label, and diagnostic values.
    When multi-level data is provided, enhances scoring with:
    - Surface lapse rate (2m→180m) as thermal initiation gate
    - Wind shear modifier (10m vs 80m) for thermal quality
    - BL mixing diagnostic (80m vs 180m) for stability assessment
    """
    # Derived values
    spread = temp_2m - dewpoint_2m
    # Bulk lapse rate: temperature drop per 100m between surface and 850hPa (~1500m)
    lapse_rate = (temp_2m - temp_850hpa) / 15.0
    # Cloud base estimate (Henning formula: spread * 125m)
    skybase_m = round(spread * 125)
    skybase_ft = round(skybase_m * 3.281)

    # Surface lapse rate (2m→180m, height diff = 1.78 hectometers)
    surface_lapse = None
    if temp_180m is not None:
        surface_lapse = (temp_2m - temp_180m) / 1.78

    # Score each factor
    scores = {
        "lapse_rate": score_lapse_rate(lapse_rate),
        "solar": score_solar(cloud_cover, shortwave_radiation),
        "spread": score_spread(spread),
        "wind": score_wind(wind_speed_kt),
        "gusts": score_gusts(wind_gusts_kt, wind_speed_kt),
        "temperature": score_temperature(temp_2m),
        "precipitation": score_precipitation(precipitation, precip_last_6h),
    }

    # Weighted sum
    weighted = sum(scores[k] * WEIGHTS[k] for k in WEIGHTS)

    # Scale to 0-10
    total = weighted * 10 / sum(w * 10 for w in WEIGHTS.values())

    # Add modifiers
    modifiers = calculate_modifiers(cape, pressure_trend, temp_850hpa_trend)
    total += modifiers

    # Multi-level modifiers
    wind_shear_mod = 0.0
    bl_mixing_mod = 0.0

    if wind_speed_80m_kt is not None:
        wind_shear_mod = calculate_wind_shear_modifier(wind_speed_kt, wind_speed_80m_kt)
        total += wind_shear_mod

    if wind_speed_80m_kt is not None and wind_speed_180m_kt is not None:
        bl_mixing_mod = calculate_bl_mixing_modifier(wind_speed_80m_kt, wind_speed_180m_kt)
        total += bl_mixing_mod

    # Subtract sea breeze penalty
    seabreeze_penalty = calculate_seabreeze_penalty(
        coast_distance_km, coast_direction_deg,
        wind_dir, wind_speed_kt, temp_2m, month,
    )
    total -= seabreeze_penalty

    # Apply dealbreakers (including surface lapse rate gate)
    total = apply_dealbreakers(
        total, lapse_rate, cloud_cover, precipitation,
        wind_speed_kt, wind_gusts_kt, temp_2m,
        surface_lapse_rate=surface_lapse,
    )

    # Clamp and round
    total = round(max(0, min(10, total)), 1)

    result = {
        "score": total,
        "label": get_score_label(total),
        "spread": round(spread, 1),
        "skybase_m": skybase_m,
        "skybase_ft": skybase_ft,
        "lapse_rate": round(lapse_rate, 2),
        "seabreeze_penalty": seabreeze_penalty,
    }

    # Add multi-level diagnostics when available
    if surface_lapse is not None:
        result["surface_lapse_rate"] = round(surface_lapse, 2)
    if wind_speed_80m_kt is not None:
        result["wind_shear_modifier"] = wind_shear_mod
    if wind_speed_80m_kt is not None and wind_speed_180m_kt is not None:
        result["bl_mixing_modifier"] = bl_mixing_mod
    if boundary_layer_height is not None:
        result["boundary_layer_height"] = round(boundary_layer_height)

    return result
```

**Step 4: Update apply_dealbreakers to accept surface lapse rate**

```python
def apply_dealbreakers(
    score: float,
    lapse_rate: float,
    cloud_cover: float,
    precipitation: float,
    wind_kt: float,
    wind_gusts_kt: float,
    temp: float,
    surface_lapse_rate: float | None = None,
) -> float:
    """Apply hard caps for conditions that prevent usable thermals."""
    max_score = 10.0

    # Bulk lapse rate dealbreakers (existing)
    if lapse_rate < 0.50:
        max_score = min(max_score, 1)
    elif lapse_rate < 0.65:
        max_score = min(max_score, 3)

    # Surface lapse rate dealbreaker (new — thermal initiation gate)
    # If the 2m→180m layer is stable, thermals cannot initiate regardless
    # of the bulk lapse rate above.
    if surface_lapse_rate is not None:
        if surface_lapse_rate < 0.3:
            max_score = min(max_score, 1)
        elif surface_lapse_rate < 0.5:
            max_score = min(max_score, 2)

    if cloud_cover >= 87:
        max_score = min(max_score, 2)
    if precipitation > 0:
        max_score = min(max_score, 1)
    if wind_kt > 35:
        max_score = min(max_score, 2)
    if wind_gusts_kt >= 35:
        max_score = min(max_score, 1)
    elif wind_gusts_kt >= 30:
        max_score = min(max_score, 2)
    effective_wind = wind_kt + (wind_gusts_kt / 2)
    if effective_wind > 35:
        max_score = min(max_score, 1)
    elif effective_wind > 30:
        max_score = min(max_score, 2)
    elif effective_wind > 25:
        max_score = min(max_score, 4)
    if temp < 5:
        max_score = min(max_score, 3)
    return min(score, max_score)
```

**Step 5: Run all scoring tests**

Run: `python3 -m pytest termik/tests/test_scoring.py -v`
Expected: ALL PASS (including all existing tests — backward compatible)

**Step 6: Commit**

```bash
git add termik/scoring.py termik/tests/test_scoring.py
git commit -m "feat: integrate multi-level data into thermal scoring

Surface lapse rate (2m→180m) as initiation dealbreaker.
Wind shear (10m→80m) and BL mixing (80m→180m) as modifiers.
Backward compatible — new params default to None."
```

---

### Task 7: Update fetch_weather.py to extract and pass new data

**Files:**
- Modify: `termik/fetch_weather.py` (`process_point_hour`)
- Modify: `termik/tests/test_fetch_weather.py`

**Step 1: Write the test**

Add to `termik/tests/test_fetch_weather.py`:

```python
def test_process_point_hour_extracts_multilevel_data(monkeypatch):
    """process_point_hour should extract multi-level wind/temp and pass to scoring."""
    from termik import fetch_weather

    # Capture what gets passed to compute_thermal_score
    captured_kwargs = {}
    original_compute = fetch_weather.compute_thermal_score

    def mock_compute(**kwargs):
        captured_kwargs.update(kwargs)
        return original_compute(
            temp_2m=kwargs["temp_2m"],
            dewpoint_2m=kwargs["dewpoint_2m"],
            temp_850hpa=kwargs["temp_850hpa"],
            cloud_cover=kwargs["cloud_cover"],
            shortwave_radiation=kwargs["shortwave_radiation"],
            wind_speed_kt=kwargs["wind_speed_kt"],
            wind_dir=kwargs["wind_dir"],
            wind_gusts_kt=kwargs["wind_gusts_kt"],
            precipitation=kwargs["precipitation"],
            precip_last_6h=kwargs["precip_last_6h"],
            cape=kwargs["cape"],
            surface_pressure=kwargs["surface_pressure"],
            pressure_trend=kwargs["pressure_trend"],
            temp_850hpa_trend=kwargs["temp_850hpa_trend"],
            coast_distance_km=kwargs["coast_distance_km"],
            coast_direction_deg=kwargs["coast_direction_deg"],
            month=kwargs["month"],
            temp_180m=kwargs.get("temp_180m"),
            wind_speed_80m_kt=kwargs.get("wind_speed_80m_kt"),
            wind_speed_180m_kt=kwargs.get("wind_speed_180m_kt"),
            boundary_layer_height=kwargs.get("boundary_layer_height"),
        )

    monkeypatch.setattr(fetch_weather, "compute_thermal_score", mock_compute)

    point = {
        "id": "test", "lat": 55.5, "lon": 9.5,
        "coast_distance_km": 50, "coast_direction_deg": 270,
    }
    hourly_data = {
        "time": ["2026-06-15T12:00"],
        "temperature_2m": [22.0],
        "dewpoint_2m": [8.0],
        "relative_humidity_2m": [40],
        "temperature_850hPa": [5.0],
        "temperature_700hPa": [0.0],
        "wind_speed_10m": [10.0],
        "wind_direction_10m": [270.0],
        "wind_gusts_10m": [15.0],
        "wind_speed_80m": [13.0],
        "wind_direction_80m": [275.0],
        "wind_speed_120m": [14.0],
        "wind_direction_120m": [278.0],
        "wind_speed_180m": [14.5],
        "wind_direction_180m": [280.0],
        "temperature_80m": [20.5],
        "temperature_120m": [19.8],
        "temperature_180m": [19.0],
        "cloud_cover": [30.0],
        "cloud_cover_low": [10.0],
        "cloud_cover_mid": [20.0],
        "cloud_cover_high": [5.0],
        "precipitation": [0.0],
        "shortwave_radiation": [700.0],
        "cape": [300.0],
        "surface_pressure": [1018.0],
        "boundary_layer_height": [1200.0],
        "wind_speed_850hPa": [20.0],
        "wind_direction_850hPa": [290.0],
    }

    result = fetch_weather.process_point_hour(point, hourly_data, 0, 6)

    assert captured_kwargs["temp_180m"] == 19.0
    assert captured_kwargs["wind_speed_80m_kt"] == 13.0
    assert captured_kwargs["wind_speed_180m_kt"] == 14.5
    assert captured_kwargs["boundary_layer_height"] == 1200.0

    # Check that output data includes multi-level fields
    assert result["data"]["wind_speed_80m_kt"] == 13.0
    assert result["data"]["wind_speed_120m_kt"] == 14.0
    assert result["data"]["wind_speed_180m_kt"] == 14.5
    assert result["data"]["wind_dir_80m"] == 275.0
    assert result["data"]["temp_180m"] == 19.0
    assert result["data"]["boundary_layer_height"] == 1200.0
```

**Step 2: Run test to verify it fails**

Run: `python3 -m pytest termik/tests/test_fetch_weather.py::test_process_point_hour_extracts_multilevel_data -v`
Expected: FAIL

**Step 3: Update process_point_hour in fetch_weather.py**

Modify the `process_point_hour` function to extract new fields and pass them through:

```python
def process_point_hour(point: dict, hourly_data: dict, hour_index: int, month: int) -> dict:
    """Process one hour of forecast data for one point."""
    # Extract raw values
    temp = hourly_data["temperature_2m"][hour_index]
    dewpoint = hourly_data["dewpoint_2m"][hour_index]
    temp_850 = hourly_data["temperature_850hPa"][hour_index]
    cloud_cover = hourly_data["cloud_cover"][hour_index]
    shortwave = hourly_data["shortwave_radiation"][hour_index]
    wind_speed = hourly_data["wind_speed_10m"][hour_index]
    wind_dir = hourly_data["wind_direction_10m"][hour_index]
    wind_gusts = hourly_data["wind_gusts_10m"][hour_index]
    precipitation = hourly_data["precipitation"][hour_index]
    cape = hourly_data["cape"][hour_index]
    pressure = hourly_data["surface_pressure"][hour_index]
    humidity = hourly_data["relative_humidity_2m"][hour_index]

    # Multi-level wind
    wind_speed_80m = hourly_data.get("wind_speed_80m", [None] * (hour_index + 1))[hour_index]
    wind_dir_80m = hourly_data.get("wind_direction_80m", [None] * (hour_index + 1))[hour_index]
    wind_speed_120m = hourly_data.get("wind_speed_120m", [None] * (hour_index + 1))[hour_index]
    wind_dir_120m = hourly_data.get("wind_direction_120m", [None] * (hour_index + 1))[hour_index]
    wind_speed_180m = hourly_data.get("wind_speed_180m", [None] * (hour_index + 1))[hour_index]
    wind_dir_180m = hourly_data.get("wind_direction_180m", [None] * (hour_index + 1))[hour_index]

    # Multi-level temperature
    temp_80m = hourly_data.get("temperature_80m", [None] * (hour_index + 1))[hour_index]
    temp_120m = hourly_data.get("temperature_120m", [None] * (hour_index + 1))[hour_index]
    temp_180m = hourly_data.get("temperature_180m", [None] * (hour_index + 1))[hour_index]

    # Boundary layer height
    bl_height = hourly_data.get("boundary_layer_height", [None] * (hour_index + 1))[hour_index]

    # Check for critical None values
    critical = [temp, dewpoint, temp_850, cloud_cover, wind_speed, wind_dir, pressure]
    if any(v is None for v in critical):
        return {
            "time": hourly_data["time"][hour_index],
            "score": 0,
            "label": "Data mangler",
            "comment": "",
            "data": {
                "temp": temp,
                "dewpoint": dewpoint,
                "spread": None,
                "skybase_m": None,
                "skybase_ft": None,
                "cloud_cover": cloud_cover,
                "wind_speed_kt": wind_speed,
                "wind_dir": wind_dir,
                "wind_gusts_kt": wind_gusts,
                "wind_speed_80m_kt": wind_speed_80m,
                "wind_speed_120m_kt": wind_speed_120m,
                "wind_speed_180m_kt": wind_speed_180m,
                "wind_dir_80m": wind_dir_80m,
                "wind_dir_120m": wind_dir_120m,
                "wind_dir_180m": wind_dir_180m,
                "temp_80m": temp_80m,
                "temp_120m": temp_120m,
                "temp_180m": temp_180m,
                "boundary_layer_height": bl_height,
                "lapse_rate": None,
                "cape": cape,
                "precipitation": precipitation,
                "pressure": pressure,
                "relative_humidity": humidity,
            },
        }

    # Derived values
    precip_last_6h = calculate_precip_last_6h(
        hourly_data["precipitation"], hour_index
    )
    pressure_trend = calculate_pressure_trend(
        hourly_data["surface_pressure"], hour_index
    )
    temp_850_trend = calculate_temp_850_trend(
        hourly_data["temperature_850hPa"], hour_index
    )

    # Safe fallbacks for non-critical None values
    shortwave = shortwave if shortwave is not None else 0
    wind_gusts = wind_gusts if wind_gusts is not None else wind_speed
    precipitation = precipitation if precipitation is not None else 0
    cape = cape if cape is not None else 0

    result = compute_thermal_score(
        temp_2m=temp,
        dewpoint_2m=dewpoint,
        temp_850hpa=temp_850,
        cloud_cover=cloud_cover,
        shortwave_radiation=shortwave,
        wind_speed_kt=wind_speed,
        wind_dir=wind_dir,
        wind_gusts_kt=wind_gusts,
        precipitation=precipitation,
        precip_last_6h=precip_last_6h,
        cape=cape,
        surface_pressure=pressure,
        pressure_trend=pressure_trend,
        temp_850hpa_trend=temp_850_trend,
        coast_distance_km=point["coast_distance_km"],
        coast_direction_deg=point["coast_direction_deg"],
        month=month,
        temp_180m=temp_180m,
        wind_speed_80m_kt=wind_speed_80m,
        wind_speed_180m_kt=wind_speed_180m,
        boundary_layer_height=bl_height,
    )

    comment = generate_comment(
        lapse_rate=result["lapse_rate"],
        spread=result["spread"],
        skybase_m=result["skybase_m"],
        wind_kt=wind_speed,
        wind_gusts_kt=wind_gusts,
        cloud_cover=cloud_cover,
        cape=cape,
        precipitation=precipitation,
        seabreeze_risk=result["seabreeze_penalty"],
        pressure_trend=pressure_trend,
        score=result["score"],
    )

    return {
        "time": hourly_data["time"][hour_index],
        "score": result["score"],
        "label": result["label"],
        "comment": comment,
        "data": {
            "temp": temp,
            "dewpoint": dewpoint,
            "spread": result["spread"],
            "skybase_m": result["skybase_m"],
            "skybase_ft": result["skybase_ft"],
            "cloud_cover": cloud_cover,
            "wind_speed_kt": wind_speed,
            "wind_dir": wind_dir,
            "wind_gusts_kt": wind_gusts,
            "wind_speed_80m_kt": wind_speed_80m,
            "wind_speed_120m_kt": wind_speed_120m,
            "wind_speed_180m_kt": wind_speed_180m,
            "wind_dir_80m": wind_dir_80m,
            "wind_dir_120m": wind_dir_120m,
            "wind_dir_180m": wind_dir_180m,
            "temp_80m": temp_80m,
            "temp_120m": temp_120m,
            "temp_180m": temp_180m,
            "boundary_layer_height": bl_height,
            "lapse_rate": result["lapse_rate"],
            "surface_lapse_rate": result.get("surface_lapse_rate"),
            "cape": cape,
            "precipitation": precipitation,
            "pressure": pressure,
            "relative_humidity": humidity,
        },
    }
```

**Step 4: Run all fetch_weather tests**

Run: `python3 -m pytest termik/tests/test_fetch_weather.py -v`
Expected: ALL PASS

**Step 5: Run ALL tests to verify nothing is broken**

Run: `python3 -m pytest termik/tests/ -v`
Expected: ALL PASS

**Step 6: Commit**

```bash
git add termik/fetch_weather.py termik/tests/test_fetch_weather.py
git commit -m "feat: extract multi-level data in fetch_weather and pass to scoring"
```

---

### Task 8: Update comments.py for multi-level diagnostics

**Files:**
- Modify: `termik/comments.py`
- Modify: `termik/tests/test_comments.py`

Add wind shear and BL height info to pilot-facing comments. Keep the function signature backward compatible.

**Step 1: Write failing tests**

Add to `termik/tests/test_comments.py`:

```python
def test_comment_warns_wind_shear():
    """High wind shear should produce a warning."""
    comment = generate_comment(
        lapse_rate=1.1, spread=10, skybase_m=1250, wind_kt=8, wind_gusts_kt=14,
        cloud_cover=30, cape=300, precipitation=0,
        seabreeze_risk=0, pressure_trend=0, score=7.0,
        wind_shear_kt=18,
    )
    assert "vindforskydning" in comment.lower() or "shear" in comment.lower()


def test_comment_shows_bl_height():
    """BL height should appear in comments when conditions are decent."""
    comment = generate_comment(
        lapse_rate=1.0, spread=10, skybase_m=1250, wind_kt=10, wind_gusts_kt=15,
        cloud_cover=30, cape=200, precipitation=0,
        seabreeze_risk=0, pressure_trend=0, score=7.0,
        boundary_layer_height=1500,
    )
    assert "1500" in comment


def test_comment_no_new_params_still_works():
    """Existing calls without new params still work."""
    comment = generate_comment(
        lapse_rate=1.0, spread=10, skybase_m=1250, wind_kt=10, wind_gusts_kt=15,
        cloud_cover=30, cape=200, precipitation=0,
        seabreeze_risk=0, pressure_trend=0, score=7.0,
    )
    assert isinstance(comment, str)
    assert len(comment) > 10
```

**Step 2: Run tests to verify they fail**

Run: `python3 -m pytest termik/tests/test_comments.py -k "wind_shear or bl_height or no_new_params" -v`
Expected: FAIL (unexpected keyword argument)

**Step 3: Update generate_comment**

Add optional parameters to `generate_comment` in `termik/comments.py`:

```python
def generate_comment(
    lapse_rate: float,
    spread: float,
    skybase_m: int,
    wind_kt: float,
    wind_gusts_kt: float,
    cloud_cover: float,
    cape: float,
    precipitation: float,
    seabreeze_risk: float,
    pressure_trend: float,
    score: float,
    # Multi-level diagnostics (optional)
    wind_shear_kt: float | None = None,
    boundary_layer_height: float | None = None,
) -> str:
```

Add these candidates to the `extras` list, after the existing `extras` entries and before the "Pick up to 2 extras" loop:

```python
    # Wind shear warning (from multi-level data)
    if wind_shear_kt is not None and wind_shear_kt > 15:
        extras.append(f"Kraftig vindforskydning ({int(wind_shear_kt)} kt) — brudt termik.")
    elif wind_shear_kt is not None and wind_shear_kt > 12:
        extras.append("Moderat vindforskydning — termik kan være tiltet.")

    # BL height (informational, when conditions are decent)
    if boundary_layer_height is not None and score >= 3:
        bl_m = round(boundary_layer_height)
        bl_ft = round(bl_m * 3.281)
        extras.append(f"Blandingslag op til {bl_m}m ({bl_ft} ft).")
```

**Step 4: Run all comments tests**

Run: `python3 -m pytest termik/tests/test_comments.py -v`
Expected: ALL PASS

**Step 5: Commit**

```bash
git add termik/comments.py termik/tests/test_comments.py
git commit -m "feat: add wind shear and BL height info to forecast comments"
```

---

### Task 9: Pass new diagnostics from fetch_weather to comments

**Files:**
- Modify: `termik/fetch_weather.py` (update generate_comment call)

**Step 1: Update the generate_comment call in process_point_hour**

In `termik/fetch_weather.py`, update the `generate_comment` call to pass the new data:

```python
    # Calculate wind shear for comments
    wind_shear_for_comment = None
    if wind_speed_80m is not None:
        wind_shear_for_comment = abs(wind_speed_80m - wind_speed)

    comment = generate_comment(
        lapse_rate=result["lapse_rate"],
        spread=result["spread"],
        skybase_m=result["skybase_m"],
        wind_kt=wind_speed,
        wind_gusts_kt=wind_gusts,
        cloud_cover=cloud_cover,
        cape=cape,
        precipitation=precipitation,
        seabreeze_risk=result["seabreeze_penalty"],
        pressure_trend=pressure_trend,
        score=result["score"],
        wind_shear_kt=wind_shear_for_comment,
        boundary_layer_height=bl_height,
    )
```

**Step 2: Run all tests**

Run: `python3 -m pytest termik/tests/ -v`
Expected: ALL PASS

**Step 3: Commit**

```bash
git add termik/fetch_weather.py
git commit -m "feat: pass wind shear and BL height to comment generation"
```

---

### Task 10: Update frontend popup to display new data

**Files:**
- Modify: `termik/output/app.js` (popup content)

No TDD for frontend (vanilla JS without test framework). Changes are display-only and backward compatible (check for null/undefined before displaying).

**Step 1: Update createPopupContent in app.js**

Add new fields to the popup grid, after the existing wind gusts line:

```javascript
// After the existing wind gusts popupItem, add:
+   (d.wind_speed_80m_kt != null
+       ? popupItem('Vind 80m', Math.round(d.wind_speed_80m_kt) + ' kt', 'Vindhastighed i 80m højde — tættere på flyvehøjde end 10m')
+       : '')
+   (d.wind_speed_180m_kt != null
+       ? popupItem('Vind 180m', Math.round(d.wind_speed_180m_kt) + ' kt', 'Vindhastighed i 180m højde')
+       : '')
+   (d.surface_lapse_rate != null
+       ? popupItem('Overfladelag', d.surface_lapse_rate + '°C/100m', 'Lapse rate 2m→180m. Over 0.98 = termik starter. Under 0.5 = ingen initiering.')
+       : '')
+   (d.boundary_layer_height != null
+       ? popupItem('Blandingslag', Math.round(d.boundary_layer_height) + 'm', 'Højde på det konvektive blandingslag — estimat for maksimal termikhøjde')
+       : '')
```

Also update the wind tooltip text:

```javascript
// Change existing wind tooltip from:
    'Gennemsnitlig vindretning og -hastighed i 10m højde'
// To:
    'Vindretning og -hastighed i 10m højde (jordniveau)'
```

**Step 2: Verify frontend manually**

Run: `python3 -m http.server 8000 -d termik/output/`
Open browser to localhost:8000 and verify popup shows new fields.

**Step 3: Commit**

```bash
git add termik/output/app.js
git commit -m "feat: display multi-level wind, surface lapse rate, and BL height in popup"
```

---

### Task 11: Run full test suite and do a live API test

**Step 1: Run all tests**

Run: `python3 -m pytest termik/tests/ -v`
Expected: ALL PASS

**Step 2: Run a live API call to verify new parameters work**

Run: `python3 -c "from termik.fetch_weather import build_api_url; print(build_api_url([{'lat': 55.5, 'lon': 9.5}]))"` and verify the URL includes the new parameters.

Optionally run `python3 -m termik` to do a full live run and verify the output JSON includes the new fields.

**Step 3: Spot-check output data**

Run: `python3 -c "import json; d=json.load(open('termik/output/data/current.json')); h=d['points'][0]['hours'][12]; print(json.dumps(h['data'], indent=2))"` and verify multi-level fields are present.

**Step 4: Final commit (if any fixups needed)**

---

## Risk Assessment

| Change | Risk | Mitigation |
|--------|------|------------|
| New API params | Low — additive, more data fetched | Backward compatible `.get()` extraction |
| Surface lapse dealbreaker | Medium — can cap previously good scores | Only triggers at extreme values (<0.5°C/100m); None default preserves existing behavior |
| Wind shear modifier | Low — max ±1.0 point | Small magnitude, only applied when data present |
| BL mixing modifier | Low — max ±0.3 point | Very small magnitude |
| Frontend changes | Low — display only | Null checks before rendering |
| API response size | Low — ~30% more data | Same number of API calls, just more columns |

## Scoring Impact Summary

When multi-level data is present, the maximum impact on the final score:
- Surface lapse rate dealbreaker: can cap score to 1-2 (prevents false positives where bulk lapse is good but surface is blocked)
- Wind shear modifier: -1.0 to +0.5
- BL mixing modifier: -0.3 to +0.3
- **Net maximum change: -1.3 to +0.8 points on top of existing score**
- **When multi-level data is absent (None): score is 100% identical to before**
