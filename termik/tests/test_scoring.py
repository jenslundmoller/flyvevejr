import pytest
from termik.scoring import (
    score_lapse_rate,
    score_surface_lapse_rate,
    score_solar,
    score_spread,
    score_wind,
    score_gusts,
    score_temperature,
    score_precipitation,
    calculate_seabreeze_penalty,
    calculate_modifiers,
    calculate_wind_shear_modifier,
    calculate_bl_mixing_modifier,
    effective_radiation,
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


# --- Surface lapse rate (2m → 180m) ---
# Measures thermal initiation potential. Superadiabatic (>0.98°C/100m) = thermals starting.

def test_surface_lapse_superadiabatic():
    """1.5°C/100m — strong surface heating, thermals initiating."""
    assert score_surface_lapse_rate(1.5) == 10

def test_surface_lapse_boundary():
    """0.5°C/100m — exact boundary between stable (0) and marginal (1)."""
    assert score_surface_lapse_rate(0.5) == 1

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


def test_solar_cirrus_shield_penalised_when_total_cloud_low():
    # Slaglille 2026-05-23 kl. 13: cc_total looked benign (49%) but was
    # driven by 93% cirrus. Total SW barely fell; direct radiation
    # dropped to ~488. Old formula gave ~7.5 (too optimistic).
    new = score_solar(
        49, 735,
        cloud_cover_low=0, cloud_cover_mid=16, cloud_cover_high=93,
        direct_radiation=488,
    )
    legacy = score_solar(49, 735)
    assert new < legacy - 0.5

def test_solar_thin_cirrus_only_minor_penalty():
    # 80% cirrus alone (no low/mid), strong direct sun = still mostly OK.
    score = score_solar(
        80, 700,
        cloud_cover_low=0, cloud_cover_mid=0, cloud_cover_high=80,
        direct_radiation=550,
    )
    # Effective cloud = 80*0.5 = 40%, direct/600 = 0.92 → solid score.
    assert 6 < score < 9

def test_solar_thick_low_cloud_heavily_penalised():
    # 80% low cloud (stratus): full weight, direct sun gone.
    score = score_solar(
        80, 250,
        cloud_cover_low=80, cloud_cover_mid=0, cloud_cover_high=0,
        direct_radiation=80,
    )
    assert score < 2


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


# --- Gusts (10% weight) ---
# Pilot rule: effective wind = wind + (gust/2). >25 = reduced, >30 = experienced only.

def test_gusts_low_effective():
    """effective = 10 + 7.5 = 17.5 → fine."""
    assert score_gusts(15, 10) == 10

def test_gusts_moderate_effective():
    """effective = 12 + 10 = 22 → slightly elevated."""
    assert score_gusts(20, 12) == 7

def test_gusts_reduced_effective():
    """effective = 15 + 11.5 = 26.5 → significantly reduced."""
    assert score_gusts(23, 15) == 2

def test_gusts_experienced_only():
    """effective = 18 + 14 = 32 → only very experienced pilots."""
    assert score_gusts(28, 18) == 0

def test_gusts_high_factor():
    """effective = 10 + 14 = 24 → under 25, but gust factor 2.8 → turbulent."""
    assert score_gusts(28, 10) == 4

def test_gusts_absolute_30():
    """Gusts >= 30 kt → cap to 2 regardless of effective wind."""
    assert score_gusts(30, 20) == 2

def test_gusts_absolute_35():
    """Gusts >= 35 kt → cap to 0 regardless of effective wind."""
    assert score_gusts(35, 20) == 0

def test_gusts_extreme():
    """Gusts 45 kt → 0."""
    assert score_gusts(45, 25) == 0


# --- Temperature (8% weight) ---
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


# --- Dealbreakers ---

def test_dealbreaker_stable():
    score = apply_dealbreakers(7.0, lapse_rate=0.55, cloud_cover=30,
                                precipitation=0, wind_kt=10, wind_gusts_kt=15, temp=15)
    assert score <= 3

def test_dealbreaker_inversion():
    score = apply_dealbreakers(5.0, lapse_rate=0.4, cloud_cover=30,
                                precipitation=0, wind_kt=10, wind_gusts_kt=15, temp=15)
    assert score <= 1

def test_dealbreaker_overcast():
    score = apply_dealbreakers(5.0, lapse_rate=1.0, cloud_cover=90,
                                precipitation=0, wind_kt=10, wind_gusts_kt=15, temp=15)
    assert score <= 2

def test_dealbreaker_surface_inversion():
    """Surface lapse < 0.3 should cap to 1."""
    score = apply_dealbreakers(8.0, lapse_rate=1.0, cloud_cover=30,
                                precipitation=0, wind_kt=10, wind_gusts_kt=15, temp=15,
                                surface_lapse_rate=0.2)
    assert score <= 1

def test_dealbreaker_surface_stable():
    """Surface lapse < 0.5 should cap to 2."""
    score = apply_dealbreakers(8.0, lapse_rate=1.0, cloud_cover=30,
                                precipitation=0, wind_kt=10, wind_gusts_kt=15, temp=15,
                                surface_lapse_rate=0.4)
    assert score <= 2

def test_dealbreaker_marginal_lapse():
    """Lapse rate < 0.70 should cap to 5 (marginal conditions)."""
    score = apply_dealbreakers(8.0, lapse_rate=0.68, cloud_cover=30,
                                precipitation=0, wind_kt=10, wind_gusts_kt=15, temp=15)
    assert score <= 5

def test_dealbreaker_cape_overdevelopment():
    """CAPE > 1000 should cap to 7 (overdevelopment risk)."""
    score = apply_dealbreakers(9.0, lapse_rate=1.2, cloud_cover=30,
                                precipitation=0, wind_kt=10, wind_gusts_kt=15, temp=20,
                                cape=1200)
    assert score <= 7

def test_dealbreaker_cape_thunderstorm():
    """CAPE > 1500 should cap to 5 (thunderstorm risk)."""
    score = apply_dealbreakers(10.0, lapse_rate=1.3, cloud_cover=30,
                                precipitation=0, wind_kt=10, wind_gusts_kt=15, temp=20,
                                cape=1800)
    assert score <= 5

def test_dealbreaker_cape_normal():
    """CAPE <= 1000 should not trigger overdevelopment cap."""
    score = apply_dealbreakers(9.0, lapse_rate=1.2, cloud_cover=30,
                                precipitation=0, wind_kt=10, wind_gusts_kt=15, temp=20,
                                cape=800)
    assert score == 9.0

def test_dealbreaker_rain():
    score = apply_dealbreakers(5.0, lapse_rate=1.0, cloud_cover=50,
                                precipitation=2.0, wind_kt=10, wind_gusts_kt=15, temp=15)
    assert score <= 1

def test_dealbreaker_extreme_wind():
    score = apply_dealbreakers(8.0, lapse_rate=1.0, cloud_cover=30,
                                precipitation=0, wind_kt=40, wind_gusts_kt=50, temp=15)
    assert score <= 1

def test_dealbreaker_extreme_gusts():
    """Gusts > 40 kt should cap score to 1 even with moderate avg wind."""
    score = apply_dealbreakers(8.0, lapse_rate=1.0, cloud_cover=30,
                                precipitation=0, wind_kt=20, wind_gusts_kt=45, temp=15)
    assert score <= 1

def test_dealbreaker_effective_wind_over_35():
    """effective = 15 + 17.5 = 32.5 → but change to wind 20, gusts 35: eff = 20+17.5 = 37.5 → cap 1."""
    score = apply_dealbreakers(8.0, lapse_rate=1.0, cloud_cover=30,
                                precipitation=0, wind_kt=20, wind_gusts_kt=35, temp=15)
    assert score <= 1

def test_dealbreaker_effective_wind_over_30():
    """effective = 15 + 17.5 = 32.5 → cap to 2."""
    score = apply_dealbreakers(8.0, lapse_rate=1.0, cloud_cover=30,
                                precipitation=0, wind_kt=15, wind_gusts_kt=35, temp=15)
    assert score <= 2

def test_dealbreaker_effective_wind_over_25():
    """effective = 15 + 13.5 = 28.5 → cap to 4 (reduced conditions)."""
    score = apply_dealbreakers(8.0, lapse_rate=1.0, cloud_cover=30,
                                precipitation=0, wind_kt=15, wind_gusts_kt=27, temp=15)
    assert score <= 4

def test_dealbreaker_cold():
    score = apply_dealbreakers(6.0, lapse_rate=1.0, cloud_cover=30,
                                precipitation=0, wind_kt=10, wind_gusts_kt=15, temp=3)
    assert score <= 3

def test_no_dealbreaker():
    score = apply_dealbreakers(8.0, lapse_rate=1.0, cloud_cover=30,
                                precipitation=0, wind_kt=10, wind_gusts_kt=15, temp=15)
    assert score == 8.0


# --- Effective radiation (boundary-layer heat memory) ---

def test_effective_radiation_remembers_recent_peak():
    # 19:00 in August: radiation has fallen to 220, but at 16:00 it was 640.
    # The boundary layer is still mixed, the thermals are alive.
    eff = effective_radiation(current=220.0, trailing=[640.0, 480.0, 330.0])
    assert eff > 400

def test_effective_radiation_no_credit_on_a_dead_day():
    # Overcast all day: nothing to remember.
    eff = effective_radiation(current=180.0, trailing=[260.0, 240.0, 210.0])
    assert eff < 250

def test_effective_radiation_never_below_current():
    eff = effective_radiation(current=700.0, trailing=[100.0, 120.0, 140.0])
    assert eff == 700.0

def test_effective_radiation_no_memory_after_sunset():
    # 2026-08-08 at 21:00: 30 W/m², with 398/274/139 over the preceding hours.
    # Without the floor the memory would lift the cap from 1 to 5 (0.65 x 398
    # = 259, which clears the 250 threshold) an hour after sunset.
    eff = effective_radiation(current=30.0, trailing=[398.0, 274.0, 139.0])
    assert eff == 30.0


def test_dealbreaker_radiation_night():
    """Radiation < 100 W/m² (night/dusk) should cap to 1."""
    score = apply_dealbreakers(7.0, lapse_rate=1.0, cloud_cover=30,
                                precipitation=0, wind_kt=10, wind_gusts_kt=15, temp=15,
                                shortwave_radiation=0)
    assert score <= 1

def test_dealbreaker_radiation_twilight():
    """Radiation < 250 W/m² (twilight/heavy overcast) should cap to 3."""
    score = apply_dealbreakers(7.0, lapse_rate=1.0, cloud_cover=30,
                                precipitation=0, wind_kt=10, wind_gusts_kt=15, temp=15,
                                shortwave_radiation=200)
    assert score <= 3

def test_dealbreaker_radiation_low():
    """Radiation < 400 W/m² (low sun / overcast) should cap to 5."""
    score = apply_dealbreakers(8.0, lapse_rate=1.0, cloud_cover=30,
                                precipitation=0, wind_kt=10, wind_gusts_kt=15, temp=15,
                                shortwave_radiation=350)
    assert score <= 5

def test_dealbreaker_radiation_sufficient():
    """Radiation ≥ 400 W/m² should not trigger any cap."""
    score = apply_dealbreakers(8.0, lapse_rate=1.0, cloud_cover=30,
                                precipitation=0, wind_kt=10, wind_gusts_kt=15, temp=15,
                                shortwave_radiation=500)
    assert score == 8.0

def test_dealbreaker_radiation_none():
    """When radiation not provided, gate should not apply."""
    score = apply_dealbreakers(8.0, lapse_rate=1.0, cloud_cover=30,
                                precipitation=0, wind_kt=10, wind_gusts_kt=15, temp=15,
                                shortwave_radiation=None)
    assert score == 8.0

def test_dealbreaker_radiation_boundary_100():
    """Radiation exactly 100 W/m² is at the < 100 boundary (no longer < 100)."""
    score = apply_dealbreakers(8.0, lapse_rate=1.0, cloud_cover=30,
                                precipitation=0, wind_kt=10, wind_gusts_kt=15, temp=15,
                                shortwave_radiation=100)
    assert score <= 3  # falls under the < 250 tier
    assert score > 1   # but not under the < 100 tier


def test_dealbreaker_gate_uses_effective_radiation():
    # A good evening: everything else allows 8+, instantaneous radiation is
    # 220 but the peak an hour ago was 640. Must not be clamped to 5.
    score = apply_dealbreakers(
        8.2, lapse_rate=1.05, cloud_cover=35, precipitation=0,
        wind_kt=8.0, wind_gusts_kt=16.0, temp=21.5,
        shortwave_radiation=220.0,
        trailing_radiation=[640.0, 480.0, 330.0],
    )
    assert score > 6.5

def test_dealbreaker_gate_still_kills_a_genuinely_dark_hour():
    score = apply_dealbreakers(
        8.2, lapse_rate=1.05, cloud_cover=35, precipitation=0,
        wind_kt=8.0, wind_gusts_kt=16.0, temp=21.5,
        shortwave_radiation=60.0,
        trailing_radiation=[90.0, 80.0, 70.0],
    )
    assert score <= 1

@pytest.mark.parametrize("radiation, expected_score", [
    (0, 1), (50, 1), (99.9, 1),
    (100, 3), (150, 3), (249.9, 3),
    (250, 5), (350, 5), (399.9, 5),
    (400, 8.0), (500, 8.0), (900, 8.0),
])
def test_dealbreaker_gate_without_trailing_caps_on_instantaneous_radiation(
    radiation, expected_score
):
    """Pins every cap tier for the no-trailing case, boundaries included.

    The memory must not change what an hour scores when no trailing series is
    supplied: an hour below several thresholds still gets the lowest cap.
    """
    score = apply_dealbreakers(8.0, lapse_rate=1.0, cloud_cover=30,
                                precipitation=0, wind_kt=10, wind_gusts_kt=15, temp=15,
                                shortwave_radiation=radiation)
    assert score == expected_score


# Ringsted (55.4517, 11.6425) on 2026-08-08, shortwave_radiation in W/m² per
# local hour, from the Open-Meteo forecast endpoint: the best_match blend
# production scores against.  Not the archive endpoint, which falls back to a
# different model for days ERA5 does not cover yet and disagrees by up to
# 253 W/m².  These are the numbers RADIATION_MEMORY_FACTOR was calibrated on.
_RINGSTED_2026_08_08 = {
    13: 736.0, 14: 726.0, 15: 708.0, 16: 657.0, 17: 523.0,
    18: 398.0, 19: 274.0, 20: 139.0, 21: 30.0,
}


@pytest.mark.parametrize("hour, expected_cap", [
    (18, 10.0),  # freed:   0.65 x 708 = 460, clears 400
    (19, 10.0),  # freed:   0.65 x 657 = 427, the hour the factor is fitted to
    (20, 5.0),   # clamped: 0.65 x 523 = 340, below 400 but above 250
    (21, 1.0),   # dead:    30 W/m² is under the floor, no memory applies
])
def test_radiation_gate_on_the_calibration_day(hour, expected_cap):
    """The published cap for the evening the memory was calibrated against.

    What this test contributes is the upper bound on
    RADIATION_MEMORY_FACTOR and both bounds on RADIATION_MEMORY_FLOOR.
    20:00 must not reach 400 off a 523 W/m² peak, so the factor stays under
    0.765; without that, widening it would silently free hours the plan
    requires to stay clamped.  20:00 also pins the floor from above (<= 139,
    or the hour drops to cap 3) and 21:00 pins it from below (> 30, or the
    memory revives it to cap 5).

    The factor's lower bound is not this test's.  At 0.609 the 19:00 case here
    still passes, since 0.609 x 657 = 400.1.  The bound comes from the three
    tests built on a 640 W/m² peak, which need 400/640 = 0.625:
    test_effective_radiation_remembers_recent_peak,
    test_dealbreaker_gate_uses_effective_radiation and
    test_process_point_hour_radiation_gate_skips_missing_trailing_hours.
    Re-tuning below 0.625 fails there, not here.

    The interval those bounds leave open is equivalent on this day only.  Its
    width is an artifact of one afternoon's radiation curve, not a physically
    justified tolerance: on a day with a different peak shape 0.65 and 0.70
    diverge.  A green suite at some other value is not evidence for it.

    Scored with an incoming 10.0 and everything else neutral, so the returned
    value is the gate's cap and nothing else.
    """
    trailing = [_RINGSTED_2026_08_08[h] for h in range(hour - 3, hour)]
    cap = apply_dealbreakers(
        10.0, lapse_rate=1.0, cloud_cover=30, precipitation=0,
        wind_kt=10, wind_gusts_kt=15, temp=15,
        shortwave_radiation=_RINGSTED_2026_08_08[hour],
        trailing_radiation=trailing,
    )
    assert cap == expected_cap


# --- Full scenario tests ---

def test_scenario_perfect_day():
    """Perfect backside weather after cold front in June."""
    result = compute_thermal_score(
        temp_2m=22, dewpoint_2m=8, temp_850hpa=5,
        cloud_cover=30, shortwave_radiation=700,
        wind_speed_kt=12, wind_dir=290, wind_gusts_kt=16,
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

def test_scenario_evening_after_sunset():
    """Late evening with otherwise favourable conditions: radiation gate must
    prevent a misleading 'moderate thermals' score after sunset.
    Mirrors the real Kongsted 2026-04-27 21:00 case.
    """
    result = compute_thermal_score(
        temp_2m=8.2, dewpoint_2m=-1.1, temp_850hpa=-2.1,
        cloud_cover=66, shortwave_radiation=0,
        wind_speed_kt=4.5, wind_dir=358, wind_gusts_kt=12.2,
        precipitation=0, precip_last_6h=0,
        cape=0, surface_pressure=1021, pressure_trend=0,
        temp_850hpa_trend=0,
        coast_distance_km=16, coast_direction_deg=110, month=4,
        temp_180m=7.3, wind_speed_80m_kt=9.1, wind_speed_180m_kt=15.6,
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

def test_scenario_gusty_day():
    """Good thermals but strong gusts — must score low due to safety."""
    result = compute_thermal_score(
        temp_2m=22, dewpoint_2m=10, temp_850hpa=6,
        cloud_cover=25, shortwave_radiation=700,
        wind_speed_kt=15, wind_dir=270, wind_gusts_kt=38,
        precipitation=0, precip_last_6h=0,
        cape=400, surface_pressure=1015, pressure_trend=0,
        temp_850hpa_trend=0,
        coast_distance_km=65, coast_direction_deg=270, month=4,
    )
    assert result["score"] <= 3.0

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
        # surface lapse = (22 - 21.5) / 1.78 = 0.28 → inversion dealbreaker
        temp_180m=21.5,
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
    # This is the same scenario as test_scenario_perfect_day — must still score >= 9.0
    assert result["score"] >= 9.0


# ---------------------------------------------------------------------------
# compute_thermal_top — parcel-theory TI=0 + LCL cap + Hcrit margin
# ---------------------------------------------------------------------------
from termik.scoring import (
    compute_thermal_top,
    _hcrit_margin,
    _bolton_lcl_temp_k,
    HCRIT_MARGIN_AT_FULL_SUN_M,
    HCRIT_MARGIN_AT_NO_SUN_M,
)


# Idealised classic Danish summer day used as a baseline sounding.
# Surface 1013 hPa, T=22°C, Td=10°C → LCL ≈ 1300m (Bolton)
# 925hPa @ 640m, T=15
# 850hPa @ 1500m, T=10
# 700hPa @ 3000m, T=2
CLASSIC_DK_SUMMER = dict(
    surface_temp_c=24.0,
    surface_dewpoint_c=12.0,
    surface_pressure_hpa=1015.0,
    surface_elevation_m=0,
    # Cold air aloft → surface parcel buoyant up to ~1300m, then LCL caps it.
    level_temps_c={950: 18.0, 925: 16.0, 900: 13.0, 850: 9.0, 800: 4.0, 700: -5.0, 600: -14.0},
    level_heights_m={950: 540, 925: 760, 900: 985, 850: 1500, 800: 2025, 700: 3110, 600: 4300},
    shortwave_radiation=600.0,
)


def test_thermal_top_classic_summer_day():
    r = compute_thermal_top(**CLASSIC_DK_SUMMER)
    assert r["thermal_top_m"] is not None
    assert 900 <= r["thermal_top_m"] <= 1700
    assert r["ti_zero_m"] >= 1100
    assert 1100 <= r["lcl_m"] <= 1700
    assert r["limited_by"] in ("lcl", "ti_zero")


def test_thermal_top_inversion():
    r = compute_thermal_top(
        surface_temp_c=15.0,
        surface_dewpoint_c=10.0,
        surface_pressure_hpa=1013.0,
        surface_elevation_m=0,
        # Warm air aloft → surface parcel immediately colder than environment
        level_temps_c={950: 18.0, 925: 16.0, 900: 14.0, 850: 12.0, 800: 8.0, 700: 2.0, 600: -8.0},
        level_heights_m={950: 540, 925: 760, 900: 985, 850: 1500, 800: 2025, 700: 3110, 600: 4300},
        shortwave_radiation=600.0,
    )
    assert r["thermal_top_m"] == 0
    assert r["ti_zero_m"] == 0
    assert r["limited_by"] == "inversion"


def test_thermal_top_super_unstable():
    r = compute_thermal_top(
        surface_temp_c=30.0,
        surface_dewpoint_c=5.0,
        surface_pressure_hpa=1013.0,
        surface_elevation_m=0,
        # Hot surface + cold troposphere → deep dry convection up past 700hPa
        # Warm-ish 700hPa so parcel crosses below LCL, giving ti_zero as limiter
        level_temps_c={950: 24.0, 925: 22.0, 900: 19.0, 850: 14.0, 800: 8.0, 700: 4.0, 600: -8.0},
        level_heights_m={950: 540, 925: 760, 900: 985, 850: 1500, 800: 2025, 700: 3110, 600: 4300},
        shortwave_radiation=700.0,
    )
    assert r["thermal_top_m"] is not None
    assert 2000 <= r["thermal_top_m"] <= 3500
    assert r["limited_by"] == "ti_zero"


def test_thermal_top_no_sounding_data():
    r = compute_thermal_top(
        surface_temp_c=20.0,
        surface_dewpoint_c=10.0,
        surface_pressure_hpa=1013.0,
        surface_elevation_m=0,
        level_temps_c={p: None for p in (950, 925, 900, 850, 800, 700, 600)},
        level_heights_m={p: None for p in (950, 925, 900, 850, 800, 700, 600)},
        shortwave_radiation=400.0,
    )
    assert r["thermal_top_m"] is None
    assert r["ti_zero_m"] is None
    assert r["limited_by"] == "no_data"


def test_thermal_top_missing_dewpoint():
    r = compute_thermal_top(
        **{**CLASSIC_DK_SUMMER, "surface_dewpoint_c": None}
    )
    assert r["thermal_top_m"] is not None
    assert r["thermal_top_m"] > 0
    assert r["lcl_m"] is None
    assert r["limited_by"] == "no_dewpoint"


def test_thermal_top_missing_surface_temp():
    r = compute_thermal_top(
        **{**CLASSIC_DK_SUMMER, "surface_temp_c": None}
    )
    assert r["thermal_top_m"] is None
    assert r["limited_by"] == "no_data"


def test_thermal_top_saturated():
    # CLASSIC_DK_SUMMER has surface_temp_c=24.0 — pass dewpoint just below to trigger
    # the spread<0.1K saturated branch.
    r = compute_thermal_top(
        **{**CLASSIC_DK_SUMMER, "surface_dewpoint_c": 23.95}
    )
    assert r["thermal_top_m"] == 0
    assert r["limited_by"] == "saturated"


def test_thermal_top_weak_solar():
    """Use no-dewpoint sounding so LCL doesn't dominate limited_by, then
    confirm weak SW flips it to weak_solar."""
    sounding = {**CLASSIC_DK_SUMMER, "surface_dewpoint_c": None, "shortwave_radiation": 150.0}
    r = compute_thermal_top(**sounding)
    assert r["thermal_top_m"] is not None
    assert r["thermal_top_m"] > 0
    assert r["limited_by"] == "weak_solar"


def test_thermal_top_margin_scaling_end_to_end():
    """Same sounding with SW=700 vs SW=0 — full-sun result must exceed no-sun by
    at least 200m (margin difference, modulo raw_top/2 cap)."""
    sounding = {**CLASSIC_DK_SUMMER, "surface_dewpoint_c": None}
    full_sun = compute_thermal_top(**{**sounding, "shortwave_radiation": 700.0})
    no_sun = compute_thermal_top(**{**sounding, "shortwave_radiation": 0.0})
    assert full_sun["thermal_top_m"] is not None and no_sun["thermal_top_m"] is not None
    assert full_sun["thermal_top_m"] > no_sun["thermal_top_m"]
    # Expect at least 200m gap (margin 200 vs 500, cap'd by raw_top/2)
    assert full_sun["thermal_top_m"] - no_sun["thermal_top_m"] >= 200


def test_hcrit_margin_table():
    assert _hcrit_margin(700) == HCRIT_MARGIN_AT_FULL_SUN_M
    assert _hcrit_margin(600) == HCRIT_MARGIN_AT_FULL_SUN_M
    assert _hcrit_margin(0) == HCRIT_MARGIN_AT_NO_SUN_M
    assert _hcrit_margin(None) == HCRIT_MARGIN_AT_NO_SUN_M
    assert _hcrit_margin(-5) == HCRIT_MARGIN_AT_NO_SUN_M
    # Linear midpoint: SW=300 → halfway between 500 and 200 = 350
    assert _hcrit_margin(300) == 350


def test_bolton_lcl_temp_sanity():
    """Bolton 1980 eq. 22 — sanity check against a known reference.

    T=20°C (293.15K), Td=10°C (283.15K) → T_LCL ≈ 280K-281K → LCL height ≈ 1200-1330m
    """
    t_lcl_k = _bolton_lcl_temp_k(293.15, 283.15)
    assert 278 < t_lcl_k < 285
    lcl_height = (293.15 - t_lcl_k) / 0.0098
    assert 1100 < lcl_height < 1400


def test_thermal_top_geopotential_sanity():
    """Sanity test: ensure typical geopotential heights are in expected range.

    Protects against a future Open-Meteo unit change (geopotential m²/s² vs
    geopotential_height m).
    """
    heights = CLASSIC_DK_SUMMER["level_heights_m"]
    assert 0 < heights[850] < 3000
    assert heights[925] < heights[850] < heights[700]
    assert heights[700] < heights[600]


def test_thermal_top_levels_below_surface_filtered():
    """If surface_pressure is low (e.g. lavtryk 980 hPa), 950hPa is also valid;
    if surface_pressure is very high, no filter applies. Verify both cases.
    """
    # surface_pressure=1013 → 950 is above ground (filter passes)
    r = compute_thermal_top(**CLASSIC_DK_SUMMER)
    assert r["thermal_top_m"] is not None  # used all available levels

    # surface_pressure=940 (very low) → 950 below ground, must be filtered
    r2 = compute_thermal_top(
        **{**CLASSIC_DK_SUMMER, "surface_pressure_hpa": 940.0}
    )
    # Still works; just one fewer level used
    assert r2["thermal_top_m"] is not None


def test_thermal_top_with_elevation():
    """Airfield at 500m elevation: same surface temp launched from a higher
    point means the parcel is warmer at every MSL altitude than the sea-level
    launch (less cooling along the dry adiabat). Verify elevation is used by
    checking LCL shifts up by exactly the elevation difference (Bolton output
    is AGL added to surface_elevation_m)."""
    base = compute_thermal_top(**CLASSIC_DK_SUMMER)
    high = compute_thermal_top(**{**CLASSIC_DK_SUMMER, "surface_elevation_m": 500})
    assert base["lcl_m"] is not None and high["lcl_m"] is not None
    assert high["lcl_m"] - base["lcl_m"] == pytest.approx(500, abs=2)
    # ti_zero_m must also be at least as high as base (parcel never colder
    # than the sea-level case at any given MSL altitude)
    assert high["ti_zero_m"] >= base["ti_zero_m"]
