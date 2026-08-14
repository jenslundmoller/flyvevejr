from datetime import datetime, timedelta

import pytest

from termik.config import HOURLY_PARAMS
from termik.fetch_weather import (
    build_api_url,
    parse_api_response,
    calculate_precip_last_6h,
    calculate_pressure_trend,
    calculate_temp_850_trend,
    calculate_trailing_window,
    process_point_hour,
)


# Neutral values for a calm, mildly unstable summer hour: one entry per key in
# HOURLY_PARAMS, so _minimal_hourly_data() always yields a complete API payload.
_NEUTRAL_HOURLY_VALUES = {
    "temperature_2m": 22.0,
    "dewpoint_2m": 8.0,
    "relative_humidity_2m": 40,
    "wind_speed_10m": 10.0,
    "wind_direction_10m": 270.0,
    "wind_gusts_10m": 15.0,
    "wind_speed_80m": 13.0,
    "wind_direction_80m": 275.0,
    "wind_speed_120m": 14.0,
    "wind_direction_120m": 278.0,
    "wind_speed_180m": 14.5,
    "wind_direction_180m": 280.0,
    "temperature_80m": 20.5,
    "temperature_120m": 19.8,
    "temperature_180m": 19.0,
    "cloud_cover": 30.0,
    "cloud_cover_low": 10.0,
    "cloud_cover_mid": 20.0,
    "cloud_cover_high": 5.0,
    "precipitation": 0.0,
    "shortwave_radiation": 700.0,
    "direct_radiation": 500.0,
    "cape": 300.0,
    "surface_pressure": 1015.0,
    "boundary_layer_height": 1200.0,
    "temperature_950hPa": 18.0,
    "temperature_925hPa": 16.0,
    "temperature_900hPa": 13.0,
    "temperature_850hPa": 9.0,
    "temperature_800hPa": 4.0,
    "temperature_700hPa": -5.0,
    "temperature_600hPa": -14.0,
    "geopotential_height_950hPa": 540.0,
    "geopotential_height_925hPa": 760.0,
    "geopotential_height_900hPa": 985.0,
    "geopotential_height_850hPa": 1500.0,
    "geopotential_height_800hPa": 2025.0,
    "geopotential_height_700hPa": 3110.0,
    "geopotential_height_600hPa": 4300.0,
    "wind_speed_850hPa": 20.0,
    "wind_direction_850hPa": 290.0,
}


_HOURLY_START = datetime(2026, 8, 15, 10, 0)


def _minimal_hourly_data(hours: int = 4, **overrides) -> dict:
    """Build an hourly_data dict with every HOURLY_PARAMS key populated.

    Each key gets a flat list of `hours` neutral values, so a test only has to
    state the fields it actually cares about.  Keyword arguments replace whole
    lists, e.g. _minimal_hourly_data(cloud_cover_high=[85] * 4).

    An unknown override key raises, so a typo cannot quietly yield a fixture
    where the value under test was never applied and the assertion passes
    against the neutral default instead.

    An override of the wrong length raises too.  Callers that slice a window
    out of a series (trailing radiation, precipitation totals) would otherwise
    get a silently truncated window (Python slices do not raise on short
    lists) and assert against the wrong values while staying green.
    """
    unknown = set(overrides) - set(HOURLY_PARAMS) - {"time"}
    if unknown:
        raise TypeError(f"unknown hourly_data key(s): {', '.join(sorted(unknown))}")
    wrong_length = {
        f"{k}={len(v)}" for k, v in overrides.items() if len(v) != hours
    }
    if wrong_length:
        raise ValueError(
            f"override(s) not of length hours={hours}: "
            f"{', '.join(sorted(wrong_length))}"
        )
    data = {
        "time": [
            (_HOURLY_START + timedelta(hours=h)).strftime("%Y-%m-%dT%H:%M")
            for h in range(hours)
        ]
    }
    for key in HOURLY_PARAMS:
        data[key] = [_NEUTRAL_HOURLY_VALUES[key]] * hours
    data.update(overrides)
    return data


def _test_point(**overrides) -> dict:
    """An airfield-shaped point; override whichever field a test cares about."""
    point = {"id": "test", "name": "Test", "lat": 55.9, "lon": 9.1,
             "coast_distance_km": 40, "coast_direction_deg": 90}
    point.update(overrides)
    return point


def test_minimal_hourly_data_rejects_bad_overrides():
    """The fixture guards every other test in this file: a typo'd key or a
    short list must raise rather than yield a fixture the test never used."""
    with pytest.raises(TypeError):
        _minimal_hourly_data(shortwave_radiaton=[700.0] * 4)   # typo
    with pytest.raises(ValueError):
        _minimal_hourly_data(hours=6, shortwave_radiation=[700.0, 650.0])
    assert len(_minimal_hourly_data(hours=6)["shortwave_radiation"]) == 6


def test_build_api_url_single():
    points = [{"lat": 55.92, "lon": 9.07}]
    url = build_api_url(points)
    assert "latitude=55.92" in url
    assert "longitude=9.07" in url
    assert "forecast_days=7" in url
    assert "temperature_2m" in url
    assert "temperature_850hPa" in url
    assert "wind_speed_unit=kn" in url
    assert "Europe" in url


def test_build_api_url_multi():
    points = [
        {"lat": 55.92, "lon": 9.07},
        {"lat": 55.28, "lon": 12.10},
    ]
    url = build_api_url(points)
    assert "55.92,55.28" in url
    assert "9.07,12.1" in url


def test_parse_api_response_single():
    raw = {
        "latitude": 55.92,
        "longitude": 9.07,
        "hourly": {"time": ["2026-03-27T10:00"], "temperature_2m": [18.5]}
    }
    result = parse_api_response(raw)
    assert isinstance(result, list)
    assert len(result) == 1
    assert result[0]["hourly"]["temperature_2m"] == [18.5]


def test_parse_api_response_multi():
    raw = [
        {"latitude": 55.92, "hourly": {"time": ["t1"], "temperature_2m": [18]}},
        {"latitude": 55.28, "hourly": {"time": ["t1"], "temperature_2m": [17]}},
    ]
    result = parse_api_response(raw)
    assert len(result) == 2


def test_calculate_precip_last_6h():
    precip_values = [0, 0, 0, 0, 1.0, 0.5, 0.2, 0, 0, 0]
    result = calculate_precip_last_6h(precip_values, 8)
    assert abs(result - 1.7) < 0.01


def test_calculate_precip_last_6h_start():
    precip_values = [0.5, 0.3, 0, 0]
    result = calculate_precip_last_6h(precip_values, 1)
    assert abs(result - 0.8) < 0.01


def test_calculate_pressure_trend():
    pressures = [1010, 1011, 1012, 1013]
    trend = calculate_pressure_trend(pressures, 3)
    assert trend == 3.0


def test_calculate_pressure_trend_start():
    pressures = [1010, 1011]
    trend = calculate_pressure_trend(pressures, 1)
    assert trend == 0  # Not enough data


def test_calculate_temp_850_trend():
    temps = [5.0, 4.5, 4.0, 3.5]
    trend = calculate_temp_850_trend(temps, 3)
    assert trend == -1.5


def test_calculate_temp_850_trend_start():
    temps = [5.0, 4.5]
    trend = calculate_temp_850_trend(temps, 0)
    assert trend == 0


def test_calculate_trailing_window():
    """Exactly the RADIATION_MEMORY_HOURS hours before hour_index.

    Asserted by value, not by length alone: a wider or narrower window, or one
    that reaches into the current hour, changes how much heat the gate
    remembers and must not pass silently.
    """
    radiation = [700.0, 720.0, 650.0, 400.0, 180.0, 60.0]
    assert calculate_trailing_window(radiation, 4) == [720.0, 650.0, 400.0]
    assert calculate_trailing_window(radiation, 5) == [650.0, 400.0, 180.0]


def test_calculate_trailing_window_start():
    """Near the start of the series the window is short, never wrapped.

    A bare hour_index - RADIATION_MEMORY_HOURS is negative here, and a
    negative slice start would silently read from the end of the day.
    """
    radiation = [700.0, 720.0, 650.0, 400.0, 180.0, 60.0]
    assert calculate_trailing_window(radiation, 0) == []
    assert calculate_trailing_window(radiation, 1) == [700.0]
    assert calculate_trailing_window(radiation, 2) == [700.0, 720.0]


def test_calculate_trailing_window_skips_missing_hours():
    """An hour the API left empty is dropped, not counted as darkness."""
    radiation = [700.0, None, 650.0, 400.0, 180.0, 60.0]
    assert calculate_trailing_window(radiation, 4) == [650.0, 400.0]


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


def test_process_point_hour_passes_multilevel_data():
    """process_point_hour extracts multi-level data and includes in output."""
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

    result = process_point_hour(point, hourly_data, 0, 6)

    # Verify multi-level data in output
    d = result["data"]
    assert d["wind_speed_80m_kt"] == 13.0
    assert d["wind_speed_120m_kt"] == 14.0
    assert d["wind_speed_180m_kt"] == 14.5
    assert d["wind_dir_80m"] == 275.0
    assert d["temp_180m"] == 19.0
    assert d["boundary_layer_height"] == 1200.0
    assert d["surface_lapse_rate"] is not None
    # Score should be computed (not 0 / "Data mangler")
    assert result["score"] > 0
    # Thermal-top fields should be present (may be None if no pressure-level sounding)
    assert "thermal_top_m" in d
    assert "ti_zero_m" in d
    assert "lcl_m" in d
    assert "thermal_top_limited_by" in d


def test_process_point_hour_thermal_top_with_full_sounding():
    """When pressure-level temperatures and geopotential heights are supplied,
    thermal_top_m must be a positive number for a clearly unstable sounding."""
    point = {
        "id": "test", "lat": 55.5, "lon": 9.5,
        "coast_distance_km": 50, "coast_direction_deg": 270,
    }
    hourly_data = {
        "time": ["2026-06-15T13:00"],
        "temperature_2m": [24.0],
        "dewpoint_2m": [12.0],
        "relative_humidity_2m": [45],
        "temperature_850hPa": [9.0],
        "temperature_700hPa": [-5.0],
        "wind_speed_10m": [10.0],
        "wind_direction_10m": [270.0],
        "wind_gusts_10m": [15.0],
        "cloud_cover": [30.0],
        "precipitation": [0.0],
        "shortwave_radiation": [700.0],
        "cape": [300.0],
        "surface_pressure": [1015.0],
        # Full pressure-level sounding
        "temperature_950hPa": [18.0],
        "temperature_925hPa": [16.0],
        "temperature_900hPa": [13.0],
        "temperature_800hPa": [4.0],
        "temperature_600hPa": [-14.0],
        "geopotential_height_950hPa": [540.0],
        "geopotential_height_925hPa": [760.0],
        "geopotential_height_900hPa": [985.0],
        "geopotential_height_850hPa": [1500.0],
        "geopotential_height_800hPa": [2025.0],
        "geopotential_height_700hPa": [3110.0],
        "geopotential_height_600hPa": [4300.0],
        "wind_speed_850hPa": [20.0],
        "wind_direction_850hPa": [290.0],
    }

    result = process_point_hour(point, hourly_data, 0, 6)

    d = result["data"]
    assert d["thermal_top_m"] is not None
    assert d["thermal_top_m"] > 0
    assert d["ti_zero_m"] is not None
    assert d["lcl_m"] is not None
    assert d["thermal_top_limited_by"] in ("lcl", "ti_zero", "cap")


def test_process_point_hour_early_return_has_thermal_top_none():
    """When critical data is missing, the early-return dict still carries
    thermal_top fields (as None / 'no_data') for schema consistency."""
    hourly_data = _minimal_hourly_data(
        temperature_2m=[None] * 4,   # critical missing
        cape=[None] * 4,
        shortwave_radiation=[700.0] * 4,
        direct_radiation=[380.0] * 4,
        cloud_cover_low=[5] * 4,
        cloud_cover_mid=[10] * 4,
        cloud_cover_high=[85] * 4,
    )

    result = process_point_hour(_test_point(), hourly_data, 3, month=8)
    assert result["score"] == 0
    assert result["label"] == "Data mangler"
    d = result["data"]
    assert d["thermal_top_m"] is None
    assert d["ti_zero_m"] is None
    assert d["lcl_m"] is None
    assert d["thermal_top_limited_by"] == "no_data"
    # The audit fields carry the real observations through, so a no-data hour
    # still records what the API did supply.
    assert d["shortwave_radiation"] == 700.0
    assert d["direct_radiation"] == 380.0
    assert d["cloud_cover_low"] == 5
    assert d["cloud_cover_mid"] == 10
    assert d["cloud_cover_high"] == 85


def test_process_point_hour_no_data_hour_keeps_shortwave_none():
    """The fallback to 0 belongs to the scored path only.

    Scoring never runs on the early return, so a missing shortwave must stay
    None there rather than be recorded as a real zero-radiation reading.  Only
    observable when shortwave AND a critical field are both missing.
    """
    hourly_data = _minimal_hourly_data(
        temperature_2m=[None] * 4,       # forces the early return
        shortwave_radiation=[None] * 4,
    )

    result = process_point_hour(_test_point(), hourly_data, 3, month=8)
    assert result["label"] == "Data mangler"
    assert result["data"]["shortwave_radiation"] is None


def test_process_point_hour_data_schema_identical_on_both_paths():
    """The no-data early return must expose the same `data` keys as a scored
    hour, so a consumer never has to branch on whether the hour had data."""
    point = _test_point()
    scored = process_point_hour(point, _minimal_hourly_data(), 3, month=8)
    no_data = process_point_hour(
        point, _minimal_hourly_data(temperature_2m=[None] * 4), 3, month=8
    )

    assert scored["label"] != "Data mangler"
    assert no_data["label"] == "Data mangler"
    assert scored["data"].keys() == no_data["data"].keys()


def test_process_point_hour_persists_radiation_and_cloud_layers():
    """Audit fields: without them the gate and cirrus caps cannot be verified."""
    hourly_data = _minimal_hourly_data(
        shortwave_radiation=[520.0] * 4,
        direct_radiation=[380.0] * 4,
        cloud_cover=[60] * 4,
        cloud_cover_low=[5] * 4,
        cloud_cover_mid=[10] * 4,
        cloud_cover_high=[85] * 4,
    )
    result = process_point_hour(_test_point(), hourly_data, 3, month=8)
    d = result["data"]
    assert d["shortwave_radiation"] == 520.0
    assert d["direct_radiation"] == 380.0
    assert d["cloud_cover_low"] == 5
    assert d["cloud_cover_mid"] == 10
    assert d["cloud_cover_high"] == 85


def test_process_point_hour_persists_shortwave_after_fallback():
    """A None shortwave is stored as the 0 the scoring actually used."""
    hourly_data = _minimal_hourly_data(shortwave_radiation=[None] * 4)

    result = process_point_hour(_test_point(), hourly_data, 3, month=8)
    assert result["data"]["shortwave_radiation"] == 0


# A declining afternoon, the shape of a real August day.  The neutral fixture
# holds direct_radiation fixed, so shortwave only reaches the score through the
# radiation gate, so whatever these hours score is the gate's doing.
_DECLINING_AFTERNOON = [700.0, 720.0, 650.0, 400.0, 180.0, 60.0]


def test_process_point_hour_radiation_gate_remembers_recent_peak():
    """The hour after the peak keeps its score: 180 W/m² alone would cap at 3,
    but 0.65 × 720 W/m² from the preceding hours clears the 400 threshold."""
    hourly_data = _minimal_hourly_data(
        hours=6, shortwave_radiation=_DECLINING_AFTERNOON
    )

    result = process_point_hour(_test_point(), hourly_data, 4, month=8)
    assert result["data"]["shortwave_radiation"] == 180.0
    assert result["score"] > 6


def test_process_point_hour_radiation_gate_forgets_after_sunset():
    """One hour later the sun is gone (60 W/m², below the memory floor), and
    the afternoon peak must not keep the score alive."""
    hourly_data = _minimal_hourly_data(
        hours=6, shortwave_radiation=_DECLINING_AFTERNOON
    )

    result = process_point_hour(_test_point(), hourly_data, 5, month=8)
    assert result["score"] <= 1


def test_process_point_hour_radiation_gate_skips_missing_trailing_hours():
    """A None inside the trailing window is skipped, not fatal: the remaining
    hours still carry the memory."""
    series = [700.0, None, 650.0, 400.0, 180.0, 60.0]
    hourly_data = _minimal_hourly_data(hours=6, shortwave_radiation=series)

    result = process_point_hour(_test_point(), hourly_data, 4, month=8)
    assert result["score"] > 6


# The same declining afternoon, but the radiation falls because a deck moves
# in rather than because the sun sets.  Only the cloud series tells the two
# apart, so these two tests are what proves it reaches the gate in production.
_ARRIVING_DECK = [720.0, 700.0, 640.0, 150.0]


def test_process_point_hour_gate_sees_an_arriving_deck():
    """Cover climbing from 10 % to 85 % blocks the memory: the hour scores on
    its own 150 W/m², which caps it at 3."""
    hourly_data = _minimal_hourly_data(
        shortwave_radiation=_ARRIVING_DECK, cloud_cover=[10.0, 15.0, 40.0, 85.0]
    )

    result = process_point_hour(_test_point(), hourly_data, 3, month=8)
    assert result["score"] <= 3


def test_process_point_hour_caps_on_a_shallow_boundary_layer():
    """Full sun and a mixed layer of 400 m: the depth has to reach the caps.

    boundary_layer_height was fetched and stored long before it was scored,
    so nothing else would notice if the score stopped receiving it.
    """
    hourly_data = _minimal_hourly_data(boundary_layer_height=[400.0] * 4)

    result = process_point_hour(_test_point(), hourly_data, 3, month=8)
    assert result["score"] <= 5
    assert result["data"]["boundary_layer_height"] == 400.0


def test_process_point_hour_passes_the_trailing_cirrus_window():
    """A hole at noon in a shield that stood all morning must not lift the hour.

    Mirrors 2026-08-09 at 12:00, where cirrus dipped to 59 between 81 and 84.
    The cap reads the trailing maximum, so the score only stays down if the
    window actually reaches it from the fetch.
    """
    hourly_data = _minimal_hourly_data(
        cloud_cover_high=[99.0, 81.0, 59.0, 84.0],
        shortwave_radiation=[500.0] * 4,
    )

    result = process_point_hour(_test_point(), hourly_data, 2, month=8)
    assert result["score"] <= 3


def test_process_point_hour_deep_boundary_layer_is_not_capped():
    """The control: 1200 m leaves the score alone.

    Passed explicitly rather than left to the fixture default, so that a
    later change to that default cannot weaken this control in silence.
    """
    hourly_data = _minimal_hourly_data(boundary_layer_height=[1200.0] * 4)

    result = process_point_hour(_test_point(), hourly_data, 3, month=8)
    assert result["score"] > 5


def test_process_point_hour_gate_keeps_memory_when_the_sky_stays_clear():
    """The control for the test above: same radiation, cloud never arrives,
    so the fall is the sun going down and the memory still applies."""
    hourly_data = _minimal_hourly_data(
        shortwave_radiation=_ARRIVING_DECK, cloud_cover=[10.0, 15.0, 12.0, 14.0]
    )

    result = process_point_hour(_test_point(), hourly_data, 3, month=8)
    assert result["score"] > 5
