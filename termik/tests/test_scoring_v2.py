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
    # Hæftet: "svækkes med OP TIL 1 m/s": fuldt fradrag kræver et næsten tæt
    # lag. Kalibreret mod Sæby 2026-08-08 kl. 11 (67 % høj sky, pilot fløj
    # alligevel 108 min) og 2026-05-27 kl. 15 (83 %, reelt svækket).
    (60, -0.5), (67, -0.5),
    (70, -1.0), (83, -1.0), (95, -1.0),
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


# --- Punkt 5b: stabil havluft i pålandsvind (kryds-plads-studiet 2026-08-25) ---

def test_seabreeze_v2_stable_marine_air_escalates():
    # Maj (hav 10), land 15 (diff 5, drive 1), påland 10 kt, 850-temp 6:
    # instab 4 < 7: stabil havluft, drivkraft løftes til maksimum (risk 3)
    penalty = calculate_seabreeze_penalty_v2(30, 270, 270, 10, 15, 5, temp_850hpa=6.0)
    assert penalty == pytest.approx(1.9)


def test_seabreeze_v2_convective_marine_air_keeps_scaled_drive():
    # Samme dag men 850-temp -2: instab 12: konvektiv havluft, uændret risk 2
    penalty = calculate_seabreeze_penalty_v2(30, 270, 270, 10, 15, 5, temp_850hpa=-2.0)
    assert penalty == pytest.approx(1.2)


def test_seabreeze_v2_weak_onshore_wind_no_escalation():
    # Under 8 kt bærer vinden ikke havluften ind: evidensen dækker kun >= 8 kt
    penalty = calculate_seabreeze_penalty_v2(30, 270, 270, 6, 15, 5, temp_850hpa=6.0)
    assert penalty == pytest.approx(1.2)


def test_seabreeze_v2_missing_850_temp_behaves_as_before():
    penalty = calculate_seabreeze_penalty_v2(30, 270, 270, 10, 15, 5)
    assert penalty == pytest.approx(1.2)


def test_seabreeze_v2_small_diff_still_free_despite_stable_air():
    # Diff <= 2-hjørnet forbliver straffrit: alle målte dage der var BAR
    assert calculate_seabreeze_penalty_v2(30, 270, 270, 10, 11, 5, temp_850hpa=6.0) == 0


# --- Task 6 / punkt 6: luftmasse-skaleret varmehukommelse ---

def test_memory_factor_v2_neutral_matches_v1():
    assert memory_factor_v2(0.0) == RADIATION_MEMORY_FACTOR


def test_memory_factor_v2_cold_advection_extends():
    assert memory_factor_v2(-1.5) == pytest.approx(0.75)


def test_memory_factor_v2_warm_advection_keeps_calibrated_factor():
    # Bevidst INGEN varme-malus: 2026-08-08 kl. 18 havde trend +1.0 mens
    # piloten fløj; en lavere faktor ville cappe de fredede aftentimer.
    assert memory_factor_v2(1.5) == RADIATION_MEMORY_FACTOR


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

# Båndene testes mod den UKORRIGEREDE base (min(LCL, TI-nul) AGL), ikke mod
# den Hcrit-korrigerede top. Skema 1's rækker er basehøjder; margin-fradraget
# fik cappet til at ramme dage med reel base op til ~850 m, målt på Sæby
# 2026-07-26 (LCL 664 m, korrigeret 408 m, to flyvninger på 169 og 134 min
# i præcis de cappede timer).
@pytest.mark.parametrize("base,limited_by,sw,bonus,cap", [
    (400, "ti_zero", 600, 0.0, 4),      # base < 600 m AGL i fuld sol: svag
    (599, "lcl", 450, 0.0, 4),
    (664, "lcl", 600, 0.0, None),       # Sæby 26/7 kl. 13: må IKKE cappe
    (800, "lcl", 600, 0.0, None),       # 600-1200: moderat, ingen justering
    (1400, "ti_zero", 600, 0.5, None),  # > 1200: kraftig termik
    (None, "no_data", 600, 0.0, None),
    (400, "no_dewpoint", 600, 0.0, None),  # utroværdig base må ikke cappe
    # Aftentimer: parcel-toppen kollapser men varmehukommelsen bærer termikken
    # (2026-08-08 kl. 18-19). Under 400 W/m² må lav base ikke cappe.
    (300, "ti_zero", 250, 0.0, None),
    (1400, "ti_zero", 250, 0.5, None),  # bonus gælder hele dagen
    # "inversion"-dom fra de grove trykniveauer må ikke cappe alene;
    # overfladelaget måles direkte af surface-lapse-dealbreakeren
    (0, "inversion", 700, 0.0, None),
    (4000, "cap", 600, 0.5, None),  # dyb konvektiv lagdeling: bonus
])
def test_thermal_top_adjustment_v2(base, limited_by, sw, bonus, cap):
    assert thermal_top_adjustment_v2(base, limited_by, sw) == (bonus, cap)


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
        thermal_base_agl_m=1600, thermal_top_limited_by="lcl",
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
        thermal_base_agl_m=400, thermal_top_limited_by="ti_zero",
    ))
    assert result["score"] <= 4.0


def test_v2_result_shape_matches_v1_consumers():
    # comments.py og fetch_weather læser disse nøgler; de skal alle findes
    result = compute_thermal_score_v2(**base_kwargs())
    for key in ("score", "label", "spread", "skybase_m", "skybase_ft",
                "lapse_rate", "seabreeze_penalty"):
        assert key in result


# --- Task 9: versionskontakten i fetch_weather ---

def _synthetic_hourly():
    """Én god junimiddagstime med 13 kt vind."""
    return {
        "time": ["2026-06-15T13:00"],
        "temperature_2m": [22.0],
        "dewpoint_2m": [11.0],
        "temperature_850hPa": [6.0],
        "cloud_cover": [15.0],
        "cloud_cover_low": [15.0],
        "cloud_cover_mid": [0.0],
        "cloud_cover_high": [0.0],
        "shortwave_radiation": [650.0],
        "direct_radiation": [550.0],
        "wind_speed_10m": [13.0],
        "wind_direction_10m": [270.0],
        "wind_gusts_10m": [18.0],
        "precipitation": [0.0],
        "cape": [400.0],
        "surface_pressure": [1015.0],
        "relative_humidity_2m": [50.0],
    }


def _inland_point():
    return {
        "id": "testpunkt",
        "lat": 56.0,
        "lon": 9.5,
        "coast_distance_km": 90.0,
        "coast_direction_deg": 270.0,
    }


def test_process_point_hour_respects_scoring_version(monkeypatch):
    from termik.fetch_weather import process_point_hour
    import termik.config as config_module

    monkeypatch.setattr(config_module, "SCORING_VERSION", "v1")
    v1_result = process_point_hour(_inland_point(), _synthetic_hourly(), 0, month=6)

    monkeypatch.setattr(config_module, "SCORING_VERSION", "v2")
    v2_result = process_point_hour(_inland_point(), _synthetic_hourly(), 0, month=6)

    # Kontakten skal vælge den rigtige motor, og valget skal kunne revideres
    # i den publicerede JSON
    assert v1_result["data"]["scoring_version"] == "v1"
    assert v2_result["data"]["scoring_version"] == "v2"
    # Begge stier skal levere den fulde datablok til frontend/kommentarer
    for result in (v1_result, v2_result):
        assert "thermal_top_m" in result["data"]
        assert result["label"]


# --- Sæsonskaleret stråling (startlist 2026-10-03/04, se Referat 2026-10-05) ---
#
# Strålingstærsklerne er absolutte W/m² kalibreret i august. I oktober når
# solen knap 400 W/m² ved middag, så gaten cappede hele den stærke søndag
# 4/10 (Slaglille 228 min, Kalundborg 326 min) på 5. Tærsklerne skaleres
# med middagssolens højde i forhold til kalibreringsdagen 8/8.

from termik.scoring_v2 import (
    radiation_season_factor,
    apply_dealbreakers_v2,
)
from termik.config import RADIATION_SEASON_MIN_FACTOR


def test_season_factor_is_one_at_calibration_day():
    assert radiation_season_factor(55.5, 220) == pytest.approx(1.0)


def test_season_factor_never_exceeds_one_in_high_summer():
    # Maj-august er kalibreret og valideret; de må ikke flytte sig
    for doy in (135, 172, 200):
        assert radiation_season_factor(55.5, doy) == 1.0


def test_season_factor_early_october():
    # 4/10 (doy 277): middagssol ~30° mod ~51° 8/8
    assert radiation_season_factor(55.5, 277) == pytest.approx(0.63, abs=0.02)


def test_season_factor_is_floored_in_winter():
    assert radiation_season_factor(55.5, 355) == RADIATION_SEASON_MIN_FACTOR


def _gate_only(sw, scale, trailing=None):
    """Kun strålings-gaten: alt andet er sat så intet andet cap rammer."""
    return apply_dealbreakers_v2(
        10.0, 1.0, 30.0, 0.0, 8.0, 12.0, 15.0,
        shortwave_radiation=sw, trailing_radiation=trailing,
        radiation_scale=scale,
    )


def test_radiation_gate_unchanged_at_full_scale():
    assert _gate_only(350.0, 1.0) == 5


def test_radiation_gate_scales_with_season():
    # 343 W/m² var Slaglilles bedste søndagstime; i oktober er det en god sol
    assert _gate_only(343.0, 0.63) == 10.0
    # og tierne følger med ned: 200 er under 0.63 x 400, 120 under 0.63 x 250
    assert _gate_only(200.0, 0.63) == 5
    assert _gate_only(120.0, 0.63) == 3


def test_memory_floor_scales_with_the_gate():
    # Gulvet er bevidst lig gatens nederste tærskel og skal følge den:
    # 80 W/m² en oktobereftermiddag er stadig over det skalerede gulv (63)
    assert effective_radiation_v2(80.0, [300.0], radiation_scale=0.63) > 80.0
    assert effective_radiation_v2(80.0, [300.0]) == 80.0


def test_solar_score_full_direct_credit_scales():
    full = score_solar_v2(10.0, 400.0, 10.0, 0.0, 0.0, direct_radiation=600.0)
    october = score_solar_v2(10.0, 300.0, 10.0, 0.0, 0.0,
                             direct_radiation=380.0, radiation_scale=0.63)
    assert october == pytest.approx(full)


def test_low_base_cap_fires_in_october_sun():
    # SW 300 er fuld sol i oktober; en base på 400 m AGL er stadig svag termik
    assert thermal_top_adjustment_v2(400, "lcl", 300.0) == (0.0, None)
    assert thermal_top_adjustment_v2(400, "lcl", 300.0, radiation_scale=0.63) == (0.0, 4)


def test_convective_october_hour_no_longer_capped_at_5():
    # Slaglille 2026-10-04 kl. 14 (publiceret 08:36Z): SW 343, direkte 168,
    # 70 % sky, base ~730 m AGL; fløjet 228 min. Lapse er her sat til
    # blandingslagets 1.06 (2 m -> 925 hPa). Med den publicerede 0.72
    # (2 m -> 850 hPa, over inversionen) er det lapse-scoren og ikke
    # strålingen der holder timen nede; det er fix 3 i referatet, ikke
    # implementeret.
    kwargs = base_kwargs(
        temp_2m=15.9, dewpoint_2m=9.8, temp_850hpa=15.9 - 15 * 1.06,
        cloud_cover=70.0, cloud_cover_low=13.0, cloud_cover_high=24.0,
        shortwave_radiation=343.0, direct_radiation=168.0,
        wind_speed_kt=8.0, wind_gusts_kt=14.8, wind_dir=284.0,
        cape=0.0, month=10, coast_distance_km=33.0, coast_direction_deg=239.0,
        trailing_radiation=[264.0, 284.0, 340.0],
        thermal_base_agl_m=730, thermal_top_limited_by="lcl",
    )
    assert compute_thermal_score_v2(**kwargs)["score"] == 5.0
    assert compute_thermal_score_v2(**kwargs, radiation_scale=0.63)["score"] > 6.0


def test_process_point_hour_applies_season_from_timestamp():
    from termik.fetch_weather import process_point_hour

    june = _synthetic_hourly()
    october = dict(june, time=["2026-10-04T13:00"],
                   shortwave_radiation=[340.0], direct_radiation=[300.0])
    june_dim = dict(october, time=["2026-06-15T13:00"])
    # Samme svage sol: cappes i juni, ikke i oktober
    assert process_point_hour(_inland_point(), june_dim, 0, month=6)["score"] <= 5.0
    assert process_point_hour(_inland_point(), october, 0, month=10)["score"] > 5.0


# --- Fix 3: blandingslagets lapse (Referat 2026-10-05) ---
#
# 2 m -> 850 hPa måler hen over inversionen når den ligger under 850 hPa.
# Søndag 4/10 var laget fra jorden til 925 hPa tør-adiabatisk (radiosonde
# Schleswig og modellen enige), men 850-lapse sagde 0.57-0.73 = "stabil".
# Blandingslagets lapse må kun løfte scoren når laget også er dybt nok til
# at flyve i; ellers ville en tynd overophedet bund om morgenen tælle som
# en god dag.

from termik.scoring_v2 import mixed_layer_lapse_v2, effective_lapse_v2
from termik.config import MIXED_LAYER_LAPSE_MIN, MIXED_LAYER_MIN_DEPTH_M


def test_mixed_layer_lapse_from_925():
    # Slaglille 4/10 kl. 12: 14.6 grader i 33 m, 6.1 grader i 876 m
    assert mixed_layer_lapse_v2(14.6, 6.1, 876.0, 33) == pytest.approx(1.01, abs=0.01)


def test_mixed_layer_lapse_needs_a_real_layer():
    # 925 hPa under/tæt på terrænet (højtryk over høj grund) giver intet mål
    assert mixed_layer_lapse_v2(14.6, 6.1, 300.0, 98) is None
    assert mixed_layer_lapse_v2(14.6, None, 876.0, 33) is None
    assert mixed_layer_lapse_v2(14.6, 6.1, None, 33) is None


@pytest.mark.parametrize("bulk, ml, depth, expected", [
    (0.72, 1.06, 1075.0, 1.06),   # søndag: konvektivt og dybt -> blandingslaget
    (0.72, 1.06, 735.0, 0.72),    # for lavt lag -> 850-målet står
    (0.72, 0.90, 1200.0, 0.72),   # ikke tydeligt konvektivt -> 850-målet står
    (1.10, 1.00, 1200.0, 1.10),   # 850-målet er allerede højest
    (0.72, None, 1200.0, 0.72),   # ingen 925-data
    (0.72, 1.06, None, 0.72),     # ingen dybde -> ingen lempelse
])
def test_effective_lapse_v2(bulk, ml, depth, expected):
    assert effective_lapse_v2(bulk, ml, depth) == expected


def test_effective_lapse_thresholds_are_the_configured_ones():
    just = MIXED_LAYER_LAPSE_MIN
    assert effective_lapse_v2(0.7, just, MIXED_LAYER_MIN_DEPTH_M) == just
    assert effective_lapse_v2(0.7, just - 0.01, MIXED_LAYER_MIN_DEPTH_M) == 0.7
    assert effective_lapse_v2(0.7, just, MIXED_LAYER_MIN_DEPTH_M - 1) == 0.7


def _slaglille_sunday_14(**overrides):
    # Publiceret 2026-10-04 08:36Z, Slaglille kl. 14 med modellens 925 hPa.
    kwargs = base_kwargs(
        temp_2m=15.9, dewpoint_2m=9.8, temp_850hpa=5.1,      # 850-lapse 0.72
        cloud_cover=70.0, cloud_cover_low=13.0, cloud_cover_high=24.0,
        shortwave_radiation=343.0, direct_radiation=168.0,
        wind_speed_kt=8.0, wind_gusts_kt=14.8, wind_dir=284.0,
        cape=0.0, month=10, coast_distance_km=33.0, coast_direction_deg=239.0,
        trailing_radiation=[264.0, 284.0, 340.0],
        thermal_base_agl_m=730, thermal_top_limited_by="lcl",
        boundary_layer_height=1065.0,
        temp_925hpa=6.3, height_925hpa_m=875.0, surface_elevation_m=33,
        radiation_scale=0.63,
    )
    kwargs.update(overrides)
    return kwargs


def test_slaglille_sunday_scores_as_flown():
    # 10 flyvninger over 2 t. Publiceret 4.8 (cap 5). Resten op til facit
    # (staerk, 7.5+) er søbrise-straffen (1.8 i vestenvind 33 km inde), som
    # ligger uden for denne rettelse; se referatets åbne punkter.
    result = compute_thermal_score_v2(**_slaglille_sunday_14())
    assert result["score"] >= 6.0
    assert result["seabreeze_penalty"] > 1.5
    assert result["lapse_rate"] > 1.0          # den lapse der blev scoret
    assert result["lapse_rate_850"] == 0.72    # revisionsspor


def test_fix_2_and_3_need_each_other():
    without_ml = _slaglille_sunday_14(temp_925hpa=None)
    without_season = _slaglille_sunday_14(radiation_scale=1.0)
    assert compute_thermal_score_v2(**without_ml)["score"] <= 5.0
    assert compute_thermal_score_v2(**without_season)["score"] <= 5.0


def test_shallow_morning_layer_is_not_lifted():
    # Samme time, men laget er kun 735 m dybt (lørdag kl. 12 på Slaglille)
    result = compute_thermal_score_v2(**_slaglille_sunday_14(boundary_layer_height=735.0))
    assert result["lapse_rate"] == 0.72
    assert result["score"] <= 5.0


def test_process_point_hour_feeds_the_925_level():
    from termik.fetch_weather import process_point_hour

    hourly = dict(
        _synthetic_hourly(),
        time=["2026-10-04T14:00"],
        temperature_2m=[15.9], dewpoint_2m=[9.8],
        temperature_850hPa=[5.1], temperature_925hPa=[6.3],
        geopotential_height_850hPa=[1566.0], geopotential_height_925hPa=[875.0],
        boundary_layer_height=[1065.0],
        shortwave_radiation=[343.0], direct_radiation=[168.0],
        cloud_cover=[40.0], cloud_cover_low=[30.0],
        wind_speed_10m=[8.0], wind_gusts_10m=[14.8],
    )
    point = dict(_inland_point(), elevation_m=33)
    result = process_point_hour(point, hourly, 0, month=10)
    assert result["data"]["lapse_rate"] > 1.0
    assert result["data"]["lapse_rate_850"] == 0.72
    assert result["score"] > 6.0
