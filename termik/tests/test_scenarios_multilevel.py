"""
Comprehensive scenario tests for the multi-level scoring system.

Each scenario represents a realistic Danish weather situation with
multi-level wind/temperature data. We test that the scoring system
produces results a pilot would expect.

Run with: python3 -m pytest termik/tests/test_scenarios_multilevel.py -v
"""

import pytest
from termik.scoring import compute_thermal_score


# Helper: common inland location (Arnborg area, central Jutland)
INLAND = {"coast_distance_km": 65, "coast_direction_deg": 270}
# Helper: coastal location (Kongsted, east Zealand)
COASTAL = {"coast_distance_km": 15, "coast_direction_deg": 90}


def score(**kwargs):
    """Shorthand for compute_thermal_score with defaults."""
    return compute_thermal_score(**kwargs)


# =====================================================================
# 1. EXCELLENT CONDITIONS (score 8-10)
# =====================================================================

class TestExcellentConditions:
    """Scenarios where a pilot would expect outstanding thermals."""

    def test_perfect_backside_june(self):
        """Classic post-cold-front day in June. NW wind, cold air aloft,
        strong surface heating, well-mixed BL. Every pilot's dream."""
        r = score(
            temp_2m=23, dewpoint_2m=9, temp_850hpa=4,
            cloud_cover=25, shortwave_radiation=750,
            wind_speed_kt=12, wind_dir=310, wind_gusts_kt=18,
            precipitation=0, precip_last_6h=0,
            cape=600, surface_pressure=1022, pressure_trend=2.0,
            temp_850hpa_trend=-1.5,
            month=6, **INLAND,
            # Multi-level: superadiabatic surface, low shear, well-mixed
            temp_180m=19.5,           # surface lapse = 1.97°C/100m
            wind_speed_80m_kt=14,     # shear = 2kt (excellent)
            wind_speed_180m_kt=15,    # gradient = 1kt (perfectly mixed)
            boundary_layer_height=2000,
        )
        assert r["score"] >= 8.5, f"Perfect backside day scored {r['score']}, expected >= 8.5"
        assert r["label"] in ("Fremragende termik", "God termik")

    def test_strong_cu_day_may(self):
        """Late May, strong heating, cumulus at good height. Inland."""
        r = score(
            temp_2m=21, dewpoint_2m=8, temp_850hpa=3,
            cloud_cover=35, shortwave_radiation=700,
            wind_speed_kt=10, wind_dir=280, wind_gusts_kt=16,
            precipitation=0, precip_last_6h=0,
            cape=450, surface_pressure=1018, pressure_trend=1.0,
            temp_850hpa_trend=-0.5,
            month=5, **INLAND,
            temp_180m=18.0,           # surface lapse = 1.69
            wind_speed_80m_kt=12,
            wind_speed_180m_kt=13,
            boundary_layer_height=1800,
        )
        assert r["score"] >= 8.0, f"Strong Cu day scored {r['score']}, expected >= 8.0"

    def test_late_summer_hot_day(self):
        """August, 27°C, good lapse rate, light wind. Hot but excellent."""
        r = score(
            temp_2m=27, dewpoint_2m=13, temp_850hpa=9,
            cloud_cover=20, shortwave_radiation=780,
            wind_speed_kt=7, wind_dir=200, wind_gusts_kt=12,
            precipitation=0, precip_last_6h=0,
            cape=350, surface_pressure=1016, pressure_trend=0,
            temp_850hpa_trend=0,
            month=8, **INLAND,
            temp_180m=24.0,           # surface lapse = 1.69
            wind_speed_80m_kt=9,
            wind_speed_180m_kt=10,
            boundary_layer_height=2200,
        )
        assert r["score"] >= 8.0, f"Hot summer day scored {r['score']}, expected >= 8.0"


# =====================================================================
# 2. GOOD CONDITIONS (score 6-8)
# =====================================================================

class TestGoodConditions:
    """Flyable days with decent thermals, but something limiting."""

    def test_moderate_day_some_cloud(self):
        """Decent instability but 50% cloud cover reducing heating."""
        r = score(
            temp_2m=20, dewpoint_2m=10, temp_850hpa=7,
            cloud_cover=50, shortwave_radiation=450,
            wind_speed_kt=8, wind_dir=240, wind_gusts_kt=14,
            precipitation=0, precip_last_6h=0,
            cape=200, surface_pressure=1018, pressure_trend=0,
            temp_850hpa_trend=0,
            month=6, **INLAND,
            temp_180m=18.0,           # surface lapse = 1.12
            wind_speed_80m_kt=10,
            wind_speed_180m_kt=12,
            boundary_layer_height=1200,
        )
        assert 5.0 <= r["score"] <= 8.0, f"Moderate cloudy day scored {r['score']}, expected 5-8"

    def test_windy_but_unstable(self):
        """Good lapse rate but wind 20kt + gusts 26kt.
        Effective wind = 20 + 26/2 = 33kt → dealbreaker caps to 2.
        This is correct: 33kt effective is genuinely dangerous."""
        r = score(
            temp_2m=18, dewpoint_2m=6, temp_850hpa=2,
            cloud_cover=30, shortwave_radiation=650,
            wind_speed_kt=20, wind_dir=290, wind_gusts_kt=26,
            precipitation=0, precip_last_6h=0,
            cape=400, surface_pressure=1015, pressure_trend=1.0,
            temp_850hpa_trend=-1.0,
            month=4, **INLAND,
            temp_180m=15.5,
            wind_speed_80m_kt=23,
            wind_speed_180m_kt=24,
            boundary_layer_height=1500,
        )
        assert r["score"] <= 2.0, f"33kt effective wind should be capped, got {r['score']}"

    def test_early_season_april(self):
        """April, moderate heating, short thermal window."""
        r = score(
            temp_2m=14, dewpoint_2m=4, temp_850hpa=0,
            cloud_cover=30, shortwave_radiation=550,
            wind_speed_kt=10, wind_dir=250, wind_gusts_kt=15,
            precipitation=0, precip_last_6h=0,
            cape=150, surface_pressure=1020, pressure_trend=0.5,
            temp_850hpa_trend=-0.5,
            month=4, **INLAND,
            temp_180m=12.0,           # surface lapse = 1.12
            wind_speed_80m_kt=12,
            wind_speed_180m_kt=13,
            boundary_layer_height=1000,
        )
        assert 4.0 <= r["score"] <= 8.0, f"April day scored {r['score']}, expected 4-8"


# =====================================================================
# 3. MARGINAL CONDITIONS (score 3-5)
# =====================================================================

class TestMarginalConditions:
    """Days where thermals exist but are weak or hard to use."""

    def test_high_spread_blue_day(self):
        """Very dry air — thermals exist but no Cu marking them. Spread > 20."""
        r = score(
            temp_2m=25, dewpoint_2m=3, temp_850hpa=10,
            cloud_cover=5, shortwave_radiation=800,
            wind_speed_kt=8, wind_dir=150, wind_gusts_kt=12,
            precipitation=0, precip_last_6h=0,
            cape=100, surface_pressure=1025, pressure_trend=0,
            temp_850hpa_trend=0,
            month=7, **INLAND,
            temp_180m=22.0,           # surface lapse = 1.69
            wind_speed_80m_kt=10,
            wind_speed_180m_kt=11,
            boundary_layer_height=1500,
        )
        assert 5.0 <= r["score"] <= 10.0, \
            f"Blue dry thermal day scored {r['score']}, expected 5-10 (thermals are strong, just no Cu)"

    def test_high_shear_breaks_thermals(self):
        """Good lapse rate but severe wind shear — thermals torn apart."""
        r = score(
            temp_2m=20, dewpoint_2m=8, temp_850hpa=5,
            cloud_cover=30, shortwave_radiation=650,
            wind_speed_kt=5, wind_dir=270, wind_gusts_kt=10,
            precipitation=0, precip_last_6h=0,
            cape=300, surface_pressure=1018, pressure_trend=0,
            temp_850hpa_trend=0,
            month=6, **INLAND,
            temp_180m=17.0,           # good surface lapse = 1.69
            wind_speed_80m_kt=25,     # massive shear! 5→25kt
            wind_speed_180m_kt=30,    # still increasing = not mixed
            boundary_layer_height=1400,
        )
        # Without shear, this would be a good day. Shear should pull it down.
        r_no_shear = score(
            temp_2m=20, dewpoint_2m=8, temp_850hpa=5,
            cloud_cover=30, shortwave_radiation=650,
            wind_speed_kt=5, wind_dir=270, wind_gusts_kt=10,
            precipitation=0, precip_last_6h=0,
            cape=300, surface_pressure=1018, pressure_trend=0,
            temp_850hpa_trend=0,
            month=6, **INLAND,
            temp_180m=17.0,
        )
        assert r["score"] < r_no_shear["score"], \
            f"High shear ({r['score']}) should score lower than no shear ({r_no_shear['score']})"

    def test_morning_surface_not_heated(self):
        """Surface layer still cool — thermals haven't started yet."""
        r = score(
            temp_2m=12, dewpoint_2m=8, temp_850hpa=2,
            cloud_cover=20, shortwave_radiation=200,  # low sun angle
            wind_speed_kt=5, wind_dir=270, wind_gusts_kt=8,
            precipitation=0, precip_last_6h=0,
            cape=100, surface_pressure=1020, pressure_trend=0,
            temp_850hpa_trend=0,
            month=6, **INLAND,
            temp_180m=11.5,           # surface lapse = 0.28 → inversion!
            wind_speed_80m_kt=8,
            wind_speed_180m_kt=12,    # high gradient = not mixed
            boundary_layer_height=300,
        )
        assert r["score"] <= 2.0, \
            f"Morning with surface inversion scored {r['score']}, expected <= 2"

    def test_weak_lapse_rate(self):
        """Marginally unstable — thermals exist but weak and low."""
        r = score(
            temp_2m=18, dewpoint_2m=10, temp_850hpa=8,
            cloud_cover=40, shortwave_radiation=500,
            wind_speed_kt=8, wind_dir=210, wind_gusts_kt=12,
            precipitation=0, precip_last_6h=0,
            cape=50, surface_pressure=1020, pressure_trend=0,
            temp_850hpa_trend=0,
            month=6, **INLAND,
            temp_180m=16.5,           # surface lapse = 0.84
            wind_speed_80m_kt=10,
            wind_speed_180m_kt=11,
            boundary_layer_height=800,
        )
        assert 3.0 <= r["score"] <= 5.5, \
            f"Weak lapse rate day scored {r['score']}, expected 3-5.5 (capped by <0.70 dealbreaker)"


# =====================================================================
# 4. NO-FLY CONDITIONS (score 0-2)
# =====================================================================

class TestNoFlyConditions:
    """Conditions where no sensible pilot would attempt thermal flight."""

    def test_active_rain(self):
        """Active rain — thermals killed regardless of other parameters."""
        r = score(
            temp_2m=15, dewpoint_2m=13, temp_850hpa=5,
            cloud_cover=90, shortwave_radiation=50,
            wind_speed_kt=12, wind_dir=220, wind_gusts_kt=20,
            precipitation=3.0, precip_last_6h=8.0,
            cape=0, surface_pressure=1005, pressure_trend=-2.0,
            temp_850hpa_trend=0.5,
            month=6, **INLAND,
            temp_180m=14.0,
            wind_speed_80m_kt=15,
            wind_speed_180m_kt=18,
            boundary_layer_height=500,
        )
        assert r["score"] <= 1.0, f"Rainy day scored {r['score']}, expected <= 1"

    def test_winter_overcast_cold(self):
        """December: 2°C, overcast, weak sun. Multiple dealbreakers."""
        r = score(
            temp_2m=2, dewpoint_2m=0, temp_850hpa=-3,
            cloud_cover=95, shortwave_radiation=20,
            wind_speed_kt=15, wind_dir=260, wind_gusts_kt=25,
            precipitation=0, precip_last_6h=1.0,
            cape=0, surface_pressure=1000, pressure_trend=-1.0,
            temp_850hpa_trend=0,
            month=12, **INLAND,
            temp_180m=1.0,
            wind_speed_80m_kt=20,
            wind_speed_180m_kt=25,
            boundary_layer_height=200,
        )
        assert r["score"] <= 2.0, f"Winter overcast scored {r['score']}, expected <= 2"

    def test_snow_and_freezing(self):
        """January blizzard: -5°C, heavy precip, strong wind."""
        r = score(
            temp_2m=-5, dewpoint_2m=-7, temp_850hpa=-10,
            cloud_cover=100, shortwave_radiation=10,
            wind_speed_kt=25, wind_dir=360, wind_gusts_kt=40,
            precipitation=2.0, precip_last_6h=5.0,
            cape=0, surface_pressure=995, pressure_trend=-3.0,
            temp_850hpa_trend=0,
            month=1, **INLAND,
            temp_180m=-6.0,
            wind_speed_80m_kt=30,
            wind_speed_180m_kt=35,
            boundary_layer_height=150,
        )
        assert r["score"] <= 1.0, f"Blizzard scored {r['score']}, expected <= 1"

    def test_extreme_gusts(self):
        """Good lapse rate but gusts 40kt+ — unflyable."""
        r = score(
            temp_2m=20, dewpoint_2m=8, temp_850hpa=4,
            cloud_cover=25, shortwave_radiation=700,
            wind_speed_kt=18, wind_dir=280, wind_gusts_kt=42,
            precipitation=0, precip_last_6h=0,
            cape=500, surface_pressure=1015, pressure_trend=0,
            temp_850hpa_trend=0,
            month=6, **INLAND,
            temp_180m=17.0,
            wind_speed_80m_kt=25,
            wind_speed_180m_kt=28,
            boundary_layer_height=1600,
        )
        assert r["score"] <= 2.0, f"Extreme gust day scored {r['score']}, expected <= 2"

    def test_strong_surface_inversion(self):
        """Warm air aloft trapping cold surface air. Classic autumn morning
        where bulk lapse rate looks OK but nothing can get off the ground."""
        r = score(
            temp_2m=8, dewpoint_2m=6, temp_850hpa=-2,
            cloud_cover=10, shortwave_radiation=400,
            wind_speed_kt=3, wind_dir=180, wind_gusts_kt=5,
            precipitation=0, precip_last_6h=0,
            cape=50, surface_pressure=1025, pressure_trend=0,
            temp_850hpa_trend=0,
            month=10, **INLAND,
            temp_180m=10.0,           # temp_180m > temp_2m! Inversion!
            wind_speed_80m_kt=8,      # surface lapse = (8-10)/1.78 = -1.12
            wind_speed_180m_kt=15,    # strong gradient = stable
            boundary_layer_height=100,
        )
        assert r["score"] <= 2.0, \
            f"Surface inversion scored {r['score']}, expected <= 2 (bulk lapse looks OK but surface is blocked)"


# =====================================================================
# 5. SAHARA / WARM STABLE AIR MASS (score 1-3)
# =====================================================================

class TestStableAirMass:
    """Warm, stable air masses where high temps mislead naive systems."""

    def test_sahara_air_july(self):
        """30°C but 850hPa also very warm → tiny lapse rate."""
        r = score(
            temp_2m=30, dewpoint_2m=12, temp_850hpa=22,
            cloud_cover=5, shortwave_radiation=850,
            wind_speed_kt=5, wind_dir=150, wind_gusts_kt=8,
            precipitation=0, precip_last_6h=0,
            cape=50, surface_pressure=1020, pressure_trend=0,
            temp_850hpa_trend=0,
            month=7, **INLAND,
            temp_180m=28.5,           # surface lapse = 0.84 — not great
            wind_speed_80m_kt=7,
            wind_speed_180m_kt=8,
            boundary_layer_height=600,
        )
        assert r["score"] <= 4.0, \
            f"Sahara air scored {r['score']}, expected <= 4 (stable despite heat)"

    def test_subsidence_inversion(self):
        """High pressure subsidence keeping lid on thermals."""
        r = score(
            temp_2m=22, dewpoint_2m=8, temp_850hpa=15,
            cloud_cover=10, shortwave_radiation=750,
            wind_speed_kt=5, wind_dir=90, wind_gusts_kt=8,
            precipitation=0, precip_last_6h=0,
            cape=20, surface_pressure=1030, pressure_trend=0,
            temp_850hpa_trend=0.5,   # warming aloft = strengthening inversion
            month=6, **INLAND,
            temp_180m=21.0,           # surface lapse = 0.56
            wind_speed_80m_kt=6,
            wind_speed_180m_kt=7,
            boundary_layer_height=500,
        )
        assert r["score"] <= 3.0, \
            f"Subsidence inversion scored {r['score']}, expected <= 3"


# =====================================================================
# 6. SEA BREEZE EFFECTS
# =====================================================================

class TestSeaBreeze:
    """Coastal vs inland comparison — sea breeze should reduce coastal scores."""

    def test_coastal_onshore_vs_inland(self):
        """Same weather, coastal with onshore wind vs far inland."""
        params = dict(
            temp_2m=22, dewpoint_2m=10, temp_850hpa=6,
            cloud_cover=25, shortwave_radiation=700,
            wind_speed_kt=8, wind_dir=90, wind_gusts_kt=12,
            precipitation=0, precip_last_6h=0,
            cape=350, surface_pressure=1018, pressure_trend=0,
            temp_850hpa_trend=0, month=7,
            temp_180m=19.0,
            wind_speed_80m_kt=10,
            wind_speed_180m_kt=11,
            boundary_layer_height=1400,
        )
        coast = score(**params, **COASTAL)
        inland = score(**params, **INLAND)
        assert inland["score"] > coast["score"], \
            f"Inland ({inland['score']}) should beat coastal ({coast['score']})"
        assert inland["score"] - coast["score"] >= 1.0, \
            f"Sea breeze penalty should be >= 1 point, got {inland['score'] - coast['score']:.1f}"


# =====================================================================
# 7. MULTI-LEVEL DATA ADVANTAGE
# =====================================================================

class TestMultiLevelAdvantage:
    """Show that multi-level data catches things single-level misses."""

    def test_hidden_surface_inversion(self):
        """Bulk lapse rate says 'good' but surface layer is inverted.
        Without multi-level data the score looks great. With it, it's capped."""
        params = dict(
            temp_2m=15, dewpoint_2m=7, temp_850hpa=2,
            cloud_cover=20, shortwave_radiation=600,
            wind_speed_kt=8, wind_dir=270, wind_gusts_kt=12,
            precipitation=0, precip_last_6h=0,
            cape=200, surface_pressure=1020, pressure_trend=0,
            temp_850hpa_trend=0,
            month=5, **INLAND,
        )
        # Without multi-level: bulk lapse = (15-2)/15 = 0.87 → decent
        without = score(**params)

        # With multi-level: surface inversion (temp rises from 15 to 15.8 in 180m)
        with_inversion = score(**params,
            temp_180m=15.8,           # surface lapse = (15-15.8)/1.78 = -0.45!
            wind_speed_80m_kt=14,
            wind_speed_180m_kt=20,
            boundary_layer_height=200,
        )

        assert without["score"] >= 4.0, \
            f"Without multi-level data, score should be decent ({without['score']})"
        assert with_inversion["score"] <= 2.0, \
            f"With surface inversion detected, score should be capped ({with_inversion['score']})"

    def test_well_mixed_bl_bonus(self):
        """Well-mixed BL (low wind gradient) should improve score slightly."""
        params = dict(
            temp_2m=20, dewpoint_2m=8, temp_850hpa=5,
            cloud_cover=30, shortwave_radiation=650,
            wind_speed_kt=10, wind_dir=270, wind_gusts_kt=14,
            precipitation=0, precip_last_6h=0,
            cape=300, surface_pressure=1018, pressure_trend=0,
            temp_850hpa_trend=0,
            month=6, **INLAND,
            temp_180m=17.5,
        )
        # Well-mixed: 80m and 180m wind almost identical
        mixed = score(**params, wind_speed_80m_kt=12, wind_speed_180m_kt=13)

        # Poorly mixed: large gradient
        unmixed = score(**params, wind_speed_80m_kt=12, wind_speed_180m_kt=22)

        assert mixed["score"] > unmixed["score"], \
            f"Well-mixed ({mixed['score']}) should beat poorly mixed ({unmixed['score']})"


# =====================================================================
# 8. EDGE CASES
# =====================================================================

class TestEdgeCases:
    """Tricky weather situations that test scoring robustness."""

    def test_overdevelopment_risk(self):
        """Very unstable with CAPE >1000 — thermals become storms.
        Score should still be reasonable (thermals exist!) but not perfect."""
        r = score(
            temp_2m=25, dewpoint_2m=16, temp_850hpa=5,
            cloud_cover=40, shortwave_radiation=600,
            wind_speed_kt=8, wind_dir=210, wind_gusts_kt=15,
            precipitation=0, precip_last_6h=0,
            cape=1500, surface_pressure=1010, pressure_trend=-1.0,
            temp_850hpa_trend=-1.5,
            month=7, **INLAND,
            temp_180m=22.0,
            wind_speed_80m_kt=10,
            wind_speed_180m_kt=11,
            boundary_layer_height=2500,
        )
        # Thermals exist and are strong, but overdevelopment risk.
        # Low spread (9°C) gives OK score, CAPE bonus, but not perfect.
        assert 5.0 <= r["score"] <= 7.0, \
            f"Overdevelopment day scored {r['score']}, expected 5-7 (CAPE >1500 dealbreaker caps to 5)"

    def test_autumn_weak_sun(self):
        """October: sun angle low, short day, but unstable airmass.
        Marginal thermals possible in the middle of the day."""
        r = score(
            temp_2m=12, dewpoint_2m=5, temp_850hpa=1,
            cloud_cover=30, shortwave_radiation=350,
            wind_speed_kt=10, wind_dir=290, wind_gusts_kt=16,
            precipitation=0, precip_last_6h=0,
            cape=100, surface_pressure=1015, pressure_trend=1.0,
            temp_850hpa_trend=-0.5,
            month=10, **INLAND,
            temp_180m=10.0,           # surface lapse = 1.12 (decent)
            wind_speed_80m_kt=13,
            wind_speed_180m_kt=14,
            boundary_layer_height=900,
        )
        assert 3.0 <= r["score"] <= 6.0, \
            f"Autumn weak sun scored {r['score']}, expected 3-6"

    def test_calm_wind_warm_day(self):
        """Very calm conditions — thermals possible but no triggering mechanism.
        Score should be OK but not top tier."""
        r = score(
            temp_2m=24, dewpoint_2m=10, temp_850hpa=7,
            cloud_cover=15, shortwave_radiation=780,
            wind_speed_kt=2, wind_dir=180, wind_gusts_kt=4,
            precipitation=0, precip_last_6h=0,
            cape=250, surface_pressure=1022, pressure_trend=0,
            temp_850hpa_trend=0,
            month=7, **INLAND,
            temp_180m=21.0,           # surface lapse = 1.69
            wind_speed_80m_kt=3,      # still calm aloft
            wind_speed_180m_kt=4,
            boundary_layer_height=1600,
        )
        assert 7.0 <= r["score"] <= 9.5, \
            f"Calm warm day scored {r['score']}, expected 7-9.5 (great thermals, just no trigger wind)"

    def test_recent_rain_wet_ground(self):
        """No active rain but ground is wet from earlier — reduced heating."""
        r = score(
            temp_2m=18, dewpoint_2m=12, temp_850hpa=5,
            cloud_cover=40, shortwave_radiation=500,
            wind_speed_kt=8, wind_dir=260, wind_gusts_kt=12,
            precipitation=0, precip_last_6h=4.0,  # heavy recent rain
            cape=100, surface_pressure=1015, pressure_trend=0.5,
            temp_850hpa_trend=0,
            month=6, **INLAND,
            temp_180m=16.5,
            wind_speed_80m_kt=10,
            wind_speed_180m_kt=11,
            boundary_layer_height=800,
        )
        assert 4.0 <= r["score"] <= 7.0, \
            f"Wet ground day scored {r['score']}, expected 4-7 (precip weight 7% limits impact)"
