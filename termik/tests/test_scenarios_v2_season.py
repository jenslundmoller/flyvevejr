"""Sæson-scenarier april-oktober: forventet v2-score og retning mod v1.

Arketyperne er bygget på hæftets vejrsituationer (bagsidevejr fig. 22,
søbrise s. 22-23, varm sydluft fig. 25, cirrus s. 20, Skema 1 s. 13).
Hver test kører SAMME input gennem den gamle score (v1) og den nye (v2)
og asserter dels v2's forventede niveau, dels den forventede retning af
ændringen. Se docs/plans/2026-08-25-scoring-v2-dsvu-haefte.md.
"""

from termik.scoring import compute_thermal_score
from termik.scoring_v2 import compute_thermal_score_v2

V2_ONLY_KEYS = ("thermal_base_agl_m", "thermal_top_limited_by")


def day(**overrides):
    """Neutral, pæn indlandsdag; scenarierne overskriver det de handler om."""
    kwargs = dict(
        temp_2m=20.0,
        dewpoint_2m=9.0,
        temp_850hpa=5.0,          # lapse 1.0
        cloud_cover=15.0,
        shortwave_radiation=650.0,
        wind_speed_kt=8.0,
        wind_dir=270.0,
        wind_gusts_kt=12.0,
        precipitation=0.0,
        precip_last_6h=0.0,
        cape=300.0,
        surface_pressure=1015.0,
        pressure_trend=0.0,
        temp_850hpa_trend=0.0,
        coast_distance_km=90.0,
        coast_direction_deg=270.0,
        month=6,
        cloud_cover_low=15.0,
        cloud_cover_mid=0.0,
        cloud_cover_high=0.0,
        direct_radiation=550.0,
    )
    kwargs.update(overrides)
    return kwargs


def both_scores(**kwargs):
    """(v1-score, v2-score) for samme vejr. v2-only nøgler fjernes for v1."""
    v1_kwargs = {k: v for k, v in kwargs.items() if k not in V2_ONLY_KEYS}
    v1 = compute_thermal_score(**v1_kwargs)["score"]
    v2 = compute_thermal_score_v2(**kwargs)["score"]
    return v1, v2


# --- April: bagsidevejr, kold ustabil polarluft (fig. 22) ---

def test_april_bagsidevejr_scores_high():
    v1, v2 = both_scores(**day(
        month=4,
        temp_2m=14.0, dewpoint_2m=4.0, temp_850hpa=-4.0,   # lapse 1.2
        temp_850hpa_trend=-1.5, pressure_trend=2.0,
        cloud_cover=30.0, cloud_cover_low=30.0,
        shortwave_radiation=620.0, direct_radiation=550.0,
        wind_speed_kt=12.0, wind_gusts_kt=18.0, cape=400.0,
        temp_180m=11.8,
        wind_speed_80m_kt=13.0, wind_speed_180m_kt=14.0,
        boundary_layer_height=1500.0,
        thermal_base_agl_m=1500, thermal_top_limited_by="ti_zero",
    ))
    # Kold luftmasse ved kun 14 grader er en topdag (punkt 7): v2 må ikke
    # straffe den lave temperatur
    assert v2 >= 9.0
    assert v2 >= v1


# --- Maj: søbrise ved kysten mod samme vejr inde i landet (s. 22-23) ---

def test_may_seabreeze_coast_scores_below_inland():
    coastal = day(
        month=5, temp_2m=19.0,
        coast_distance_km=25.0, coast_direction_deg=270.0,
        wind_dir=270.0, wind_speed_kt=8.0,   # pålandsvind, hav 10 grader
    )
    inland = dict(coastal, coast_distance_km=90.0)
    _, v2_coast = both_scores(**coastal)
    _, v2_inland = both_scores(**inland)
    assert v2_inland - v2_coast >= 1.5


def test_october_coast_v2_kinder_than_v1():
    # Oktober: havet er stadig 12 grader, land 14: næsten ingen forskel, så
    # v1's faste pålandsvinds-straf på 3 er for hård (punkt 5)
    coastal_october = day(
        month=10, temp_2m=14.0, temp_850hpa=0.0,
        coast_distance_km=25.0, coast_direction_deg=270.0,
        wind_dir=270.0, wind_speed_kt=8.0,
        shortwave_radiation=420.0, direct_radiation=380.0,
    )
    v1, v2 = both_scores(**coastal_october)
    assert v2 > v1


# --- Juni: Skema 1, 3/8 lav cumulus er gratis (punkt 2) ---

def test_june_cumulus_day_not_punished():
    clear = day(cloud_cover=5.0, cloud_cover_low=5.0)
    cu_day = day(cloud_cover=38.0, cloud_cover_low=38.0)
    v1_clear, v2_clear = both_scores(**clear)
    v1_cu, v2_cu = both_scores(**cu_day)
    v1_cost = v1_clear - v1_cu
    v2_cost = v2_clear - v2_cu
    assert v2_cost <= 0.11  # praktisk taget gratis i v2 (afrunding)
    assert v2_cost < v1_cost or v1_cost == 0


# --- Juli: varm stabil sydluft (fig. 25) mod april-bagsidevejret ---

def test_july_warm_stable_airmass_scores_low():
    v1, v2 = both_scores(**day(
        month=7,
        temp_2m=29.0, dewpoint_2m=11.0, temp_850hpa=21.0,  # lapse 0.53
        shortwave_radiation=750.0, direct_radiation=680.0,
        cloud_cover=5.0, cloud_cover_low=5.0,
    ))
    # Stabil luftmasse: dealbreakeren binder uanset 29 grader og fuld sol
    assert v2 <= 4.0


def test_cold_april_beats_warm_july():
    _, v2_april = both_scores(**day(
        month=4, temp_2m=14.0, dewpoint_2m=4.0, temp_850hpa=-4.0,
        temp_850hpa_trend=-1.5, cape=400.0,
    ))
    _, v2_july = both_scores(**day(
        month=7, temp_2m=29.0, dewpoint_2m=11.0, temp_850hpa=21.0,
    ))
    assert v2_april - v2_july >= 3.0


# --- August: cirrus-skjold og cirrus-banker (s. 20, punkt 3) ---

def test_august_cirrus_shield_caps():
    _, v2 = both_scores(**day(
        month=8,
        cloud_cover=90.0, cloud_cover_low=5.0, cloud_cover_high=90.0,
        direct_radiation=200.0,
        trailing_cirrus=[95.0, 99.0, 98.0],
    ))
    assert v2 <= 3.0


def test_august_cirrus_banks_subtract_but_do_not_kill():
    clear = day(month=8)
    banks = day(month=8, cloud_cover=50.0, cloud_cover_high=50.0,
                direct_radiation=450.0)
    _, v2_clear = both_scores(**clear)
    _, v2_banks = both_scores(**banks)
    assert v2_clear - 2.5 <= v2_banks <= v2_clear - 0.5


# --- August-aften: koldluftsadvektion forlænger dagen (punkt 6) ---

def test_evening_cold_advection_outlives_warm_airmass():
    evening = day(
        shortwave_radiation=150.0, direct_radiation=120.0,
        trailing_radiation=[600.0, 520.0, 380.0],
        trailing_cloud_cover=[20.0, 22.0, 25.0],
        cloud_cover=25.0, cloud_cover_low=25.0,
    )
    _, v2_neutral = both_scores(**dict(evening, temp_850hpa_trend=0.0))
    _, v2_cold = both_scores(**dict(evening, temp_850hpa_trend=-1.5))
    # Neutral: 0.65 x 600 = 390 < 400: gate capper til 5.
    # Koldluft: 0.75 x 600 = 450: gaten holder sig væk.
    assert v2_cold > v2_neutral


# --- September: svag sol og lavt blandingslag ---

def test_september_weak_sun_shallow_layer_caps():
    _, v2 = both_scores(**day(
        month=9,
        temp_2m=16.0, temp_850hpa=3.0,
        shortwave_radiation=380.0, direct_radiation=300.0,
        boundary_layer_height=750.0,
    ))
    assert v2 <= 5.0


# --- Oktober: koldluft men lav brugbar top (punkt 4) ---

def test_october_low_thermal_top_caps_where_v1_did_not():
    october = day(
        month=10,
        temp_2m=12.0, dewpoint_2m=8.0, temp_850hpa=-2.0,   # lapse 0.93
        shortwave_radiation=420.0, direct_radiation=380.0,
        cloud_cover=10.0, cloud_cover_low=10.0,
        thermal_base_agl_m=450, thermal_top_limited_by="lcl",
    )
    v1, v2 = both_scores(**october)
    assert v2 <= 4.0
    assert v2 < v1  # v1 så ikke den lave base
