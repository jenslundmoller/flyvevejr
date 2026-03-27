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


# --- Lapse rate (30% weight) ---
# Measures atmospheric instability. Higher = more thermal potential.
# Lapse rate = (temp_surface - temp_850hPa) / 15 (approx °C per 100m)

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


# --- Solar (20% weight) ---
# Combines cloud cover and shortwave radiation

def test_solar_clear_sky_strong():
    score = score_solar(10, 800)
    assert 9 <= score <= 10

def test_solar_overcast():
    score = score_solar(95, 50)
    assert score < 2

def test_solar_partly_cloudy():
    score = score_solar(50, 400)
    assert 3 < score < 7


# --- Spread (15% weight) ---
# Spread = temp - dewpoint. Determines cloud base height and overdev risk.
# Optimal 8-15°C. Too low = fog/overdev. Too high = dry thermal only.

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


# --- Wind (15% weight) ---
# 5-15 kt optimal for thermal triggering. Too calm = no triggering. Too strong = turbulent.

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


# --- Temperature (10% weight) ---
# Higher surface temp = more heating. Linear scale.

def test_temp_warm():
    score = score_temperature(25)
    assert score >= 8

def test_temp_cold():
    score = score_temperature(3)
    assert score == 0

def test_temp_moderate():
    score = score_temperature(15)
    assert 2 < score < 6


# --- Precipitation (10% weight) ---
# No rain = best. Active rain = worst. Recent rain = moderate (wet ground).

def test_precip_dry():
    assert score_precipitation(0, 0) == 10

def test_precip_active():
    assert score_precipitation(2.0, 5.0) == 0

def test_precip_recent():
    assert score_precipitation(0, 3.0) == 3

def test_precip_light_recent():
    assert score_precipitation(0, 1.0) == 6


# --- Sea breeze penalty ---
# Denmark is very coastal. Sea breeze kills thermals.
# Penalty based on: distance to coast, wind direction, land/sea temp diff.

def test_seabreeze_inland():
    penalty = calculate_seabreeze_penalty(
        coast_distance_km=80, coast_direction_deg=270,
        wind_dir=270, wind_speed_kt=10, temp_2m=22, month=6
    )
    assert penalty == 0

def test_seabreeze_coastal_onshore():
    penalty = calculate_seabreeze_penalty(
        coast_distance_km=10, coast_direction_deg=270,
        wind_dir=270, wind_speed_kt=5, temp_2m=22, month=6
    )
    assert penalty >= 2

def test_seabreeze_coastal_strong_offshore():
    penalty = calculate_seabreeze_penalty(
        coast_distance_km=10, coast_direction_deg=270,
        wind_dir=90, wind_speed_kt=20, temp_2m=22, month=6
    )
    assert penalty == 0


# --- Modifiers ---

def test_modifiers_cape_bonus():
    mods = calculate_modifiers(cape=500, pressure_trend=0, temp_850hpa_trend=0)
    assert mods == 0.5

def test_modifiers_high_cape():
    mods = calculate_modifiers(cape=800, pressure_trend=0, temp_850hpa_trend=0)
    assert mods == 1.0

def test_modifiers_pressure_rising():
    mods = calculate_modifiers(cape=0, pressure_trend=2.0, temp_850hpa_trend=0)
    assert mods == 0.5

def test_modifiers_pressure_falling():
    mods = calculate_modifiers(cape=0, pressure_trend=-2.0, temp_850hpa_trend=0)
    assert mods == -0.5

def test_modifiers_cold_advection():
    mods = calculate_modifiers(cape=0, pressure_trend=0, temp_850hpa_trend=-1.5)
    assert mods == 0.5

def test_modifiers_combined():
    mods = calculate_modifiers(cape=500, pressure_trend=2.0, temp_850hpa_trend=-1.5)
    assert mods == 1.5  # 0.5 + 0.5 + 0.5


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

def test_dealbreaker_extreme_wind():
    score = apply_dealbreakers(8.0, lapse_rate=1.0, cloud_cover=30,
                                precipitation=0, wind_kt=40, temp=15)
    assert score <= 2

def test_dealbreaker_cold():
    score = apply_dealbreakers(6.0, lapse_rate=1.0, cloud_cover=30,
                                precipitation=0, wind_kt=10, temp=3)
    assert score <= 3

def test_no_dealbreaker():
    score = apply_dealbreakers(8.0, lapse_rate=1.0, cloud_cover=30,
                                precipitation=0, wind_kt=10, temp=15)
    assert score == 8.0


# --- Full scenario tests ---

def test_scenario_perfect_day():
    """Perfect backside weather after cold front in June."""
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

def test_scenario_sahara():
    """30°C but stable Sahara air — dealbreaker must cap score."""
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

def test_scenario_winter():
    """Overcast winter day — multiple dealbreakers."""
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
    """Same weather, coast vs inland — coast must score lower."""
    params = dict(
        temp_2m=21, dewpoint_2m=11, temp_850hpa=7,
        cloud_cover=20, shortwave_radiation=750,
        wind_speed_kt=5, wind_dir=90, wind_gusts_kt=8,
        precipitation=0, precip_last_6h=0,
        cape=300, surface_pressure=1020, pressure_trend=0,
        temp_850hpa_trend=0, month=6,
    )
    coast = compute_thermal_score(**params, coast_distance_km=15, coast_direction_deg=90)
    inland = compute_thermal_score(**params, coast_distance_km=65, coast_direction_deg=270)
    assert inland["score"] > coast["score"]
    assert inland["score"] - coast["score"] >= 1.5

def test_scenario_moderate_day():
    """Typical moderate Danish summer day."""
    result = compute_thermal_score(
        temp_2m=24, dewpoint_2m=14, temp_850hpa=12,
        cloud_cover=45, shortwave_radiation=550,
        wind_speed_kt=8, wind_dir=220, wind_gusts_kt=14,
        precipitation=0, precip_last_6h=0,
        cape=200, surface_pressure=1018, pressure_trend=0,
        temp_850hpa_trend=0,
        coast_distance_km=50, coast_direction_deg=270, month=7,
    )
    assert 5 <= result["score"] <= 8


# --- Score label ---

def test_score_label():
    assert get_score_label(9.5) == "Fremragende termik"
    assert get_score_label(7.0) == "God termik"
    assert get_score_label(5.0) == "Moderat termik"
    assert get_score_label(3.0) == "Svag termik"
    assert get_score_label(1.0) == "Ingen brugbar termik"


# --- Return structure ---

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
    assert "seabreeze_penalty" in result
    assert 0 <= result["score"] <= 10
