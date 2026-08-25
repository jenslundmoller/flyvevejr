"""Tests for scoring_v2: DSvU-hæftets justeringer.

Hvert afsnit svarer til et af de 7 punkter i
docs/plans/2026-08-25-scoring-v2-dsvu-haefte.md. v1 (termik/scoring.py) er
bevidst urørt; disse tests dækker kun den nye sti.
"""

import pytest

from termik.config import (
    SCORING_VERSION,
    WEIGHTS_V2,
    RADIATION_MEMORY_FACTOR,
)
from termik.scoring_v2 import (
    score_wind_v2,
    score_solar_v2,
    cirrus_penalty_v2,
    calculate_seabreeze_penalty_v2,
    memory_factor_v2,
    effective_radiation_v2,
    thermal_top_adjustment_v2,
    compute_thermal_score_v2,
)


# --- Task 1: config-kontakt ---

def test_scoring_version_is_valid():
    assert SCORING_VERSION in ("v1", "v2")


def test_weights_v2_sum_to_one():
    assert sum(WEIGHTS_V2.values()) == pytest.approx(1.0)


def test_weights_v2_temperature_below_solar_shift():
    # Punkt 7: temperatur ned, sol op i forhold til v1
    assert WEIGHTS_V2["temperature"] == 0.04
    assert WEIGHTS_V2["solar"] == 0.24


# --- Task 2 / punkt 1: vindscore med 5-10 kt som ideal ---

@pytest.mark.parametrize("wind,expected", [
    (5, 10), (7, 10), (10, 10),   # "den absolut mest ideelle" (s. 13, 28)
    (12, 8), (15, 8),             # brugbart men kortere boble-levetid
    (4, 7),                       # let vind, få men stærkere bobler
    (17, 5), (20, 5),             # mekanisk turbulens vokser
    (22, 3), (25, 3),             # meget kort levetid
    (1, 4), (0, 3),               # luften "klistrer" til jorden
    (28, 2), (35, 2), (40, 0),
])
def test_score_wind_v2(wind, expected):
    assert score_wind_v2(wind) == expected


def test_score_wind_v2_cold_advection_softens_15_25():
    # Skygader ved koldluftsadvektion (s. 29): 15-25 kt kan stadig flyves
    assert score_wind_v2(17, cold_advection=True) == 7
    assert score_wind_v2(22, cold_advection=True) == 5
    # Under 15 kt ændrer flaget intet
    assert score_wind_v2(8, cold_advection=True) == 10


# --- Task 3 / punkt 2: lav cumulus er et sundhedstegn ---

def test_score_solar_v2_cumulus_allowance_is_free():
    # 3/8 lav cu (~38 %) må ikke koste noget i forhold til skyfrit
    clear = score_solar_v2(0, 700, 0, 0, 0, direct_radiation=650)
    cu_day = score_solar_v2(38, 700, 38, 0, 0, direct_radiation=650)
    assert cu_day == pytest.approx(clear)


def test_score_solar_v2_low_cloud_above_allowance_costs():
    cu_day = score_solar_v2(40, 700, 40, 0, 0, direct_radiation=650)
    overcast = score_solar_v2(90, 700, 90, 0, 0, direct_radiation=650)
    assert overcast < cu_day


def test_score_solar_v2_stratus_morning_still_low():
    # 90 % lav sky og næsten ingen direkte stråling: lav score uanset allowance
    assert score_solar_v2(90, 120, 90, 0, 0, direct_radiation=40) < 3.5


def test_score_solar_v2_without_layers_matches_v1_behaviour():
    from termik.scoring import score_solar
    assert score_solar_v2(50, 400) == pytest.approx(score_solar(50, 400))


# --- Task 4 / punkt 3: gradueret cirrus-fradrag ---

@pytest.mark.parametrize("high,expected", [
    (None, 0.0), (0, 0.0), (30, 0.0), (39, 0.0),
    (40, -0.5), (55, -0.5),
    (60, -1.0), (70, -1.0), (95, -1.0),
])
def test_cirrus_penalty_v2(high, expected):
    assert cirrus_penalty_v2(high) == expected


# --- Task 5 / punkt 5: søbrise skaleret med land/hav-forskel ---

def test_seabreeze_v2_classic_may_onshore():
    # Maj (hav 10°), 20° på land, pålandsvind, 30 km fra kyst: fuld risiko
    penalty = calculate_seabreeze_penalty_v2(30, 270, 270, 8, 20, 5)
    assert 1.8 <= penalty <= 2.0


def test_seabreeze_v2_october_small_diff_is_free():
    # Oktober (hav 12°), 14° på land: diff 2, ingen drivkraft
    assert calculate_seabreeze_penalty_v2(30, 270, 270, 18, 14, 10) == 0


def test_seabreeze_v2_april_weak_wind_all_coasts():
    # April (hav 6°), 15° på land, svag fralandsvind: søbrise ved alle kyster
    penalty = calculate_seabreeze_penalty_v2(30, 270, 90, 5, 15, 4)
    assert 1.1 <= penalty <= 1.4


def test_seabreeze_v2_far_inland_is_free():
    assert calculate_seabreeze_penalty_v2(85, 270, 270, 8, 20, 5) == 0


def test_seabreeze_v2_strong_offshore_wind_blocks():
    assert calculate_seabreeze_penalty_v2(30, 270, 90, 18, 20, 5) == 0


# --- Task 6 / punkt 6: luftmasse-skaleret varmehukommelse ---

def test_memory_factor_v2_neutral_matches_v1():
    assert memory_factor_v2(0.0) == RADIATION_MEMORY_FACTOR


def test_memory_factor_v2_cold_advection_extends():
    assert memory_factor_v2(-1.5) == pytest.approx(0.75)


def test_memory_factor_v2_warm_advection_shortens():
    assert memory_factor_v2(1.5) == pytest.approx(0.55)


def test_effective_radiation_v2_uses_scaled_factor():
    # 300 W/m² nu, 657 i vinduet: koldluft giver 0.75 * 657 = 492.75
    eff = effective_radiation_v2(300, [657], temp_850hpa_trend=-1.5)
    assert eff == pytest.approx(492.75)


def test_effective_radiation_v2_floor_still_applies():
    assert effective_radiation_v2(50, [657], temp_850hpa_trend=-1.5) == 50


def test_effective_radiation_v2_deck_arrival_still_blocks():
    eff = effective_radiation_v2(
        150, [657], cloud_cover=95, trailing_cloud_cover=[20],
        temp_850hpa_trend=-1.5,
    )
    assert eff == 150


# --- Task 7 / punkt 4: termiktop-kobling ---

@pytest.mark.parametrize("top,limited_by,bonus,cap", [
    (400, "ti_zero", 0.0, 4),      # < 600 m AGL: svag termik (s. 41)
    (599, "lcl", 0.0, 4),
    (800, "lcl", 0.0, None),       # 600-1200: moderat, ingen justering
    (1400, "ti_zero", 0.5, None),  # > 1200: kraftig termik
    (None, "no_data", 0.0, None),
    (400, "no_dewpoint", 0.0, None),  # utroværdig top må ikke cappe
])
def test_thermal_top_adjustment_v2(top, limited_by, bonus, cap):
    assert thermal_top_adjustment_v2(top, limited_by) == (bonus, cap)


# --- Task 8: samlet v2-score ---

def base_kwargs(**overrides):
    """Moderat pæn dag uden multi-level data, langt fra kyst."""
    kwargs = dict(
        temp_2m=19.0,
        dewpoint_2m=9.0,
        temp_850hpa=4.0,          # lapse 1.0
        cloud_cover=10.0,
        shortwave_radiation=600.0,
        wind_speed_kt=8.0,
        wind_dir=270.0,
        wind_gusts_kt=12.0,
        precipitation=0.0,
        precip_last_6h=0.0,
        cape=200.0,
        surface_pressure=1015.0,
        pressure_trend=0.0,
        temp_850hpa_trend=0.0,
        coast_distance_km=100.0,
        coast_direction_deg=270.0,
        month=6,
        cloud_cover_low=10.0,
        cloud_cover_mid=0.0,
        cloud_cover_high=0.0,
        direct_radiation=500.0,
    )
    kwargs.update(overrides)
    return kwargs


def test_v2_perfect_june_day_scores_high():
    result = compute_thermal_score_v2(**base_kwargs(
        temp_2m=24.0, dewpoint_2m=12.0, temp_850hpa=6.0,
        cloud_cover=20.0, cloud_cover_low=20.0,
        shortwave_radiation=700.0, direct_radiation=650.0,
        cape=500.0,
        temp_180m=21.5,
        wind_speed_80m_kt=10.0, wind_speed_180m_kt=11.0,
        boundary_layer_height=1800.0,
        thermal_top_agl_m=1600, thermal_top_limited_by="lcl",
    ))
    assert result["score"] >= 9.0
    assert result["version"] == "v2"


def test_v2_wind_12kt_scores_below_8kt():
    low_wind = compute_thermal_score_v2(**base_kwargs())
    high_wind = compute_thermal_score_v2(**base_kwargs(
        wind_speed_kt=12.0, wind_gusts_kt=16.0,
    ))
    assert high_wind["score"] < low_wind["score"]


def test_v2_cirrus_banks_subtract():
    clear = compute_thermal_score_v2(**base_kwargs())
    cirrus = compute_thermal_score_v2(**base_kwargs(
        cloud_cover=70.0, cloud_cover_high=70.0,
    ))
    assert cirrus["score"] <= clear["score"] - 1.0


def test_v2_shallow_thermal_top_caps_at_4():
    result = compute_thermal_score_v2(**base_kwargs(
        thermal_top_agl_m=400, thermal_top_limited_by="ti_zero",
    ))
    assert result["score"] <= 4.0


def test_v2_result_shape_matches_v1_consumers():
    # comments.py og fetch_weather læser disse nøgler; de skal alle findes
    result = compute_thermal_score_v2(**base_kwargs())
    for key in ("score", "label", "spread", "skybase_m", "skybase_ft",
                "lapse_rate", "seabreeze_penalty"):
        assert key in result
