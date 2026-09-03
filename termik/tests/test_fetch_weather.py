import json
from datetime import datetime, timedelta

import pytest
import requests

import termik.fetch_weather as fetch_weather
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


# --- Netværksfejl: tomme/ikke-JSON svar fra Open-Meteo ------------------------
# Open-Meteo svarer lejlighedsvis 200 OK med et tomt body. response.json()
# kaster da requests.exceptions.JSONDecodeError, som hverken er HTTPError,
# ConnectionError eller Timeout. Den skal behandles som en transient fejl
# på linje med et read-timeout, ikke som noget der vælter hele kørslen.

class _FakeResponse:
    """Minimal stand-in for requests.Response.

    payload=None modellerer et tomt body (response.json() kaster);
    status>=400 modellerer at raise_for_status() kaster som den rigtige gør.
    """

    def __init__(self, payload=None, status=200):
        self._payload = payload
        self.status_code = status

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.exceptions.HTTPError(str(self.status_code), response=self)

    def json(self):
        if self._payload is None:
            raise requests.exceptions.JSONDecodeError("Expecting value", "", 0)
        return self._payload


def _silence_backoff(monkeypatch):
    """Retry-backoffen er 15/30/60 s; tests skal ikke vente på den."""
    monkeypatch.setattr(fetch_weather.time, "sleep", lambda _seconds: None)


def test_fetch_batch_retries_when_response_body_is_not_json(monkeypatch):
    """Et tomt 200-svar skal udløse et genforsøg, ikke en undtagelse."""
    _silence_backoff(monkeypatch)
    payload = {"hourly": _minimal_hourly_data()}
    responses = [_FakeResponse(None), _FakeResponse(payload)]
    calls = []

    def fake_get(url, timeout):
        calls.append(url)
        return responses[len(calls) - 1]

    monkeypatch.setattr(fetch_weather.requests, "get", fake_get)

    result = fetch_weather.fetch_batch([_test_point()])

    assert result == [payload]
    assert len(calls) == 2


def test_fetch_batch_raises_when_every_response_is_not_json(monkeypatch):
    """Holder svaret op med at være JSON i alle forsøg, skal fejlen boble op."""
    _silence_backoff(monkeypatch)
    calls = []

    def fake_get(url, timeout):
        calls.append(url)
        return _FakeResponse(None)

    monkeypatch.setattr(fetch_weather.requests, "get", fake_get)

    with pytest.raises(requests.exceptions.JSONDecodeError):
        fetch_weather.fetch_batch([_test_point()])

    assert len(calls) == 4  # første forsøg + 3 genforsøg


def test_process_all_points_tolerates_a_batch_that_never_returns_json(monkeypatch):
    """En batch der fejler permanent må koste sine punkter, ikke hele kørslen."""
    _silence_backoff(monkeypatch)
    points = [_test_point(id="doomed"), _test_point(id="fine")]
    monkeypatch.setattr(fetch_weather, "ALL_POINTS", points)
    monkeypatch.setattr(fetch_weather, "API_BATCH_SIZE", 1)

    def fake_fetch_batch(batch_points, max_retries=3):
        if batch_points[0]["id"] == "doomed":
            raise requests.exceptions.JSONDecodeError("Expecting value", "", 0)
        return [{"hourly": _minimal_hourly_data()}]

    monkeypatch.setattr(fetch_weather, "fetch_batch", fake_fetch_batch)

    data = fetch_weather.process_all_points()

    assert [p["id"] for p in data["points"]] == ["fine"]


def _replies(monkeypatch, *responses):
    """Lad requests.get svare med responses i rækkefølge; returnér kald-listen."""
    calls = []

    def fake_get(url, timeout):
        calls.append(url)
        reply = responses[min(len(calls) - 1, len(responses) - 1)]
        if isinstance(reply, Exception):
            raise reply
        return reply

    monkeypatch.setattr(fetch_weather.requests, "get", fake_get)
    return calls


def _ok_payload(n: int = 1) -> list:
    return [{"hourly": _minimal_hourly_data()} for _ in range(n)]


# --- Transient vs. permanent: retry-klassificeringen --------------------------

def test_fetch_batch_retries_a_truncated_body(monkeypatch):
    """Forbindelsen lukket midt i et chunked body er lige så transient som et
    read-timeout, og må ikke vælte kørslen."""
    _silence_backoff(monkeypatch)
    calls = _replies(
        monkeypatch,
        requests.exceptions.ChunkedEncodingError("connection broken"),
        _FakeResponse(_ok_payload()),
    )

    assert fetch_weather.fetch_batch([_test_point()]) == _ok_payload()
    assert len(calls) == 2


def test_fetch_batch_retries_a_server_error(monkeypatch):
    """5xx er transient: Open-Meteo har travlt, ikke vi der spørger forkert."""
    _silence_backoff(monkeypatch)
    calls = _replies(monkeypatch, _FakeResponse(status=503), _FakeResponse(_ok_payload()))

    assert fetch_weather.fetch_batch([_test_point()]) == _ok_payload()
    assert len(calls) == 2


def test_fetch_batch_retries_when_rate_limited(monkeypatch):
    """429 skal vente og prøve igen, ikke give op."""
    _silence_backoff(monkeypatch)
    calls = _replies(monkeypatch, _FakeResponse(status=429), _FakeResponse(_ok_payload()))

    assert fetch_weather.fetch_batch([_test_point()]) == _ok_payload()
    assert len(calls) == 2


def test_fetch_batch_does_not_retry_a_client_error(monkeypatch):
    """400 betyder at forespørgslen er forkert; genforsøg ville give samme svar."""
    _silence_backoff(monkeypatch)
    calls = _replies(monkeypatch, _FakeResponse(status=400))

    with pytest.raises(requests.exceptions.HTTPError):
        fetch_weather.fetch_batch([_test_point()])
    assert len(calls) == 1


def test_fetch_batch_does_not_retry_a_malformed_url(monkeypatch):
    """En forkert API_BASE_URL er en programmeringsfejl. Uden denne grænse ville
    27 batches brænde 105 s backoff hver, altså ~47 minutter, på et svar der
    aldrig bliver bedre."""
    _silence_backoff(monkeypatch)
    calls = _replies(monkeypatch, requests.exceptions.MissingSchema("no schema"))

    with pytest.raises(requests.exceptions.MissingSchema):
        fetch_weather.fetch_batch([_test_point()])
    assert len(calls) == 1


# --- Gyldig JSON i forkert form ----------------------------------------------

def test_fetch_batch_retries_an_error_payload(monkeypatch):
    """Open-Meteos fejlsvar {"error": true, ...} er gyldig JSON, men uden
    "hourly". Det skal give genforsøg, ikke KeyError længere nede."""
    _silence_backoff(monkeypatch)
    calls = _replies(
        monkeypatch,
        _FakeResponse({"error": True, "reason": "Cannot initialize"}),
        _FakeResponse(_ok_payload()),
    )

    assert fetch_weather.fetch_batch([_test_point()]) == _ok_payload()
    assert len(calls) == 2


def test_fetch_batch_retries_a_short_response(monkeypatch):
    """Færre svar end punkter i batchen tabte før punkter tavst i zip()."""
    _silence_backoff(monkeypatch)
    points = [_test_point(id=f"p{i}") for i in range(3)]
    calls = _replies(
        monkeypatch,
        _FakeResponse(_ok_payload(1)),
        _FakeResponse(_ok_payload(3)),
    )

    assert len(fetch_weather.fetch_batch(points)) == 3
    assert len(calls) == 2


def test_fetch_batch_retries_a_null_body(monkeypatch):
    """JSON null gav før TypeError i zip(); nu er det bare et dårligt svar."""
    _silence_backoff(monkeypatch)
    calls = _replies(monkeypatch, _FakeResponse(payload=[None]), _FakeResponse(_ok_payload()))

    assert fetch_weather.fetch_batch([_test_point()]) == _ok_payload()
    assert len(calls) == 2


# --- Dækningsgrænsen: delvis data må ikke overskrive komplet data ------------

def _coverage_data(airfields: int, grid: int) -> dict:
    points = [{"id": f"a{i}", "type": "airfield", "hours": []} for i in range(airfields)]
    points += [{"id": f"g{i}", "type": "grid", "hours": []} for i in range(grid)]
    return {"points": points}


def test_check_coverage_accepts_a_complete_run():
    fetch_weather.check_coverage(
        _coverage_data(len(fetch_weather.AIRFIELDS), _grid_total())
    )


def _grid_total() -> int:
    return len(fetch_weather.ALL_POINTS) - len(fetch_weather.AIRFIELDS)


def test_check_coverage_rejects_a_single_missing_airfield(capsys):
    """Flyvepladserne ligger i batch 1-3, så én fejlet batch koster 10 klubber.
    En bruger hvis klub mangler ser et tomt panel uden fejlmeddelelse."""
    with pytest.raises(SystemExit) as exc:
        fetch_weather.check_coverage(
            _coverage_data(len(fetch_weather.AIRFIELDS) - 1, _grid_total())
        )
    assert exc.value.code == 1
    assert "::error::" in capsys.readouterr().out


def test_check_coverage_rejects_grid_below_the_floor(capsys):
    """Under 95 % gitter afvises, så den forrige komplette prognose bliver
    liggende i stedet for at blive overskrevet med huller."""
    grid = _grid_total()
    with pytest.raises(SystemExit) as exc:
        fetch_weather.check_coverage(
            _coverage_data(len(fetch_weather.AIRFIELDS), int(grid * 0.90))
        )
    assert exc.value.code == 1
    assert "::error::" in capsys.readouterr().out


def test_check_coverage_rejects_an_empty_run(capsys):
    with pytest.raises(SystemExit):
        fetch_weather.check_coverage(_coverage_data(0, 0))
    assert "::error::" in capsys.readouterr().out


def test_check_coverage_warns_visibly_on_a_tolerated_gap(capsys):
    """Lige over grænsen skrives der, men kørslen skal efterlade et spor i
    Actions, ellers er en delvis prognose usynlig for ejeren."""
    grid = _grid_total()
    fetch_weather.check_coverage(
        _coverage_data(len(fetch_weather.AIRFIELDS), grid - 1)
    )
    assert "::warning::" in capsys.readouterr().out


# --- process_all_points og meta.json -----------------------------------------

def test_process_all_points_slims_grid_points_but_not_airfields(monkeypatch):
    """Gitterpunkter bærer kun time+score+top; flyvepladser bærer alt."""
    _silence_backoff(monkeypatch)
    airfield = _test_point(id="EKXX")
    grid = {"id": "g1", "lat": 55.5, "lon": 9.5,
            "coast_distance_km": 40, "coast_direction_deg": 90}
    monkeypatch.setattr(fetch_weather, "ALL_POINTS", [airfield, grid])
    monkeypatch.setattr(fetch_weather, "API_BATCH_SIZE", 1)
    monkeypatch.setattr(fetch_weather, "fetch_batch",
                        lambda pts, max_retries=3: _ok_payload(1))

    by_id = {p["id"]: p for p in fetch_weather.process_all_points()["points"]}

    assert by_id["EKXX"]["type"] == "airfield"
    assert set(by_id["g1"]["hours"][0]) == {"time", "score", "thermal_top_m"}
    assert "data" in by_id["EKXX"]["hours"][0]


def test_write_output_records_the_expected_point_count(tmp_path, monkeypatch):
    """meta.json skal kunne afsløre en delvis kørsel bagefter."""
    monkeypatch.setattr(fetch_weather, "DATA_DIR", str(tmp_path))
    data = {"generated": "2026-09-02T10:00:00+00:00", "forecast_days": 7,
            "points": [{"id": "a0", "type": "airfield", "hours": [{}]}]}

    fetch_weather.write_output(data)

    meta = json.loads((tmp_path / "meta.json").read_text(encoding="utf-8"))
    assert meta["point_count"] == 1
    assert meta["expected_point_count"] == len(fetch_weather.ALL_POINTS)


def test_process_all_points_reports_the_expected_point_count(monkeypatch):
    """current.json bærer selv det forventede antal, så frontenden kan se en
    delvis prognose uden en ekstra netværkshentning, og uden at tallet kan
    komme i utakt med de data det beskriver."""
    _silence_backoff(monkeypatch)
    monkeypatch.setattr(fetch_weather, "ALL_POINTS",
                        [_test_point(id="a"), _test_point(id="b")])
    monkeypatch.setattr(fetch_weather, "API_BATCH_SIZE", 1)

    def fake_fetch_batch(pts, max_retries=3):
        if pts[0]["id"] == "b":
            raise requests.exceptions.Timeout("timeout")
        return _ok_payload(1)

    monkeypatch.setattr(fetch_weather, "fetch_batch", fake_fetch_batch)

    data = fetch_weather.process_all_points()

    assert data["expected_point_count"] == 2
    assert len(data["points"]) == 1


# --- Redningsrunde: et sidste forsøg på de fejlede batches -------------------
# Batch 1-3 er flyvepladser, og dækningsgrænsen tåler ingen tabte flyvepladser.
# Et enkelt uheld tidligt i kørslen kostede derfor hele prognosen, selv om
# API'et typisk er kommet sig længe inden de sidste 24 batches er hentet.

def _sweep_setup(monkeypatch, points, batch_size=1):
    monkeypatch.setattr(fetch_weather, "ALL_POINTS", points)
    monkeypatch.setattr(fetch_weather, "API_BATCH_SIZE", batch_size)


def test_process_all_points_saves_a_batch_that_recovers(monkeypatch):
    """En batch der fejler først, men svarer i redningsrunden, tæller med."""
    _silence_backoff(monkeypatch)
    _sweep_setup(monkeypatch, [_test_point(id="a"), _test_point(id="b")])
    seen = []

    def fake_fetch_batch(pts, max_retries=3):
        seen.append(pts[0]["id"])
        if pts[0]["id"] == "a" and seen.count("a") == 1:
            raise requests.exceptions.Timeout("timeout")
        return _ok_payload(1)

    monkeypatch.setattr(fetch_weather, "fetch_batch", fake_fetch_batch)

    data = fetch_weather.process_all_points()

    assert sorted(p["id"] for p in data["points"]) == ["a", "b"]


def test_recovery_sweep_runs_after_every_other_batch(monkeypatch):
    """Pointen er ventetiden: den fejlede batch prøves først når resten er
    hentet, så API'et har haft de ~20 minutter en kørsel tager til at komme
    sig. Prøves den igen med det samme, fejler den bare igen."""
    _silence_backoff(monkeypatch)
    _sweep_setup(monkeypatch, [_test_point(id=n) for n in ("a", "b", "c")])
    seen = []

    def fake_fetch_batch(pts, max_retries=3):
        seen.append(pts[0]["id"])
        if pts[0]["id"] == "a" and seen.count("a") == 1:
            raise requests.exceptions.Timeout("timeout")
        return _ok_payload(1)

    monkeypatch.setattr(fetch_weather, "fetch_batch", fake_fetch_batch)

    fetch_weather.process_all_points()

    assert seen == ["a", "b", "c", "a"]


def test_recovery_sweep_slims_grid_points_like_the_first_pass(monkeypatch):
    """Reddede gitterpunkter skal bære samme slanke payload som de øvrige."""
    _silence_backoff(monkeypatch)
    grid = {"id": "g1", "lat": 55.5, "lon": 9.5,
            "coast_distance_km": 40, "coast_direction_deg": 90}
    _sweep_setup(monkeypatch, [grid])
    seen = []

    def fake_fetch_batch(pts, max_retries=3):
        seen.append(pts[0]["id"])
        if len(seen) == 1:
            raise requests.exceptions.Timeout("timeout")
        return _ok_payload(1)

    monkeypatch.setattr(fetch_weather, "fetch_batch", fake_fetch_batch)

    data = fetch_weather.process_all_points()

    assert set(data["points"][0]["hours"][0]) == {"time", "score", "thermal_top_m"}


def test_recovery_sweep_is_skipped_when_the_api_is_down(monkeypatch):
    """Er mange batches faldet, er API'et nede, ikke ustabilt. Så kan runden
    ikke redde kørslen, og den ville kun brænde runner-tid af mod
    job-timeouten."""
    _silence_backoff(monkeypatch)
    n = fetch_weather.RECOVERY_MAX_BATCHES + 1
    _sweep_setup(monkeypatch, [_test_point(id=f"p{i}") for i in range(n)])
    seen = []

    def fake_fetch_batch(pts, max_retries=3):
        seen.append(pts[0]["id"])
        raise requests.exceptions.Timeout("timeout")

    monkeypatch.setattr(fetch_weather, "fetch_batch", fake_fetch_batch)

    data = fetch_weather.process_all_points()

    assert data["points"] == []
    assert len(seen) == n  # ingen ekstra runde


def test_recovery_sweep_uses_a_short_retry_budget(monkeypatch):
    """Batchen har allerede haft det fulde budget én gang. Er API'et stadig
    nede, skal runden opdage det billigt frem for at bruge 105 s backoff
    pr. batch oveni."""
    _silence_backoff(monkeypatch)
    _sweep_setup(monkeypatch, [_test_point(id="a")])
    budgets = []

    def fake_fetch_batch(pts, max_retries=3):
        budgets.append(max_retries)
        raise requests.exceptions.Timeout("timeout")

    monkeypatch.setattr(fetch_weather, "fetch_batch", fake_fetch_batch)

    fetch_weather.process_all_points()

    assert budgets == [3, fetch_weather.RECOVERY_MAX_RETRIES]
    assert fetch_weather.RECOVERY_MAX_RETRIES < 3


def test_recovery_sweep_pauses_before_retrying(monkeypatch):
    """En batch der fejler til allersidst får ellers ingen pause overhovedet."""
    _sweep_setup(monkeypatch, [_test_point(id="a")])
    slept = []
    monkeypatch.setattr(fetch_weather.time, "sleep", lambda s: slept.append(s))

    def fake_fetch_batch(pts, max_retries=3):
        raise requests.exceptions.Timeout("timeout")

    monkeypatch.setattr(fetch_weather, "fetch_batch", fake_fetch_batch)

    fetch_weather.process_all_points()

    assert fetch_weather.RECOVERY_PAUSE_SECONDS in slept


def test_a_batch_that_fails_twice_stays_failed(monkeypatch):
    """Runden er et ekstra forsøg, ikke en garanti. Dækningsgrænsen skal
    stadig kunne se hullet."""
    _silence_backoff(monkeypatch)
    _sweep_setup(monkeypatch, [_test_point(id="a"), _test_point(id="b")])

    def fake_fetch_batch(pts, max_retries=3):
        if pts[0]["id"] == "a":
            raise requests.exceptions.Timeout("timeout")
        return _ok_payload(1)

    monkeypatch.setattr(fetch_weather, "fetch_batch", fake_fetch_batch)

    data = fetch_weather.process_all_points()

    assert [p["id"] for p in data["points"]] == ["b"]


def test_recovery_count_in_the_warning_is_batches_not_points(monkeypatch, capsys):
    """Sidste batch er en rest-batch med færre punkter end API_BATCH_SIZE.
    Udledes antallet af reddede batches af punkttallet, rapporterer loggen
    nul reddede selv om runden lige har reddet en."""
    _silence_backoff(monkeypatch)
    points = [_test_point(id=f"p{i}") for i in range(4)]
    _sweep_setup(monkeypatch, points, batch_size=3)   # batches: 3 punkter + 1 punkt
    seen = []

    def fake_fetch_batch(pts, max_retries=3):
        ids = [p["id"] for p in pts]
        seen.append(tuple(ids))
        if ids == ["p0", "p1", "p2"]:
            raise requests.exceptions.Timeout("bliver aldrig god")
        if ids == ["p3"] and seen.count(("p3",)) == 1:
            raise requests.exceptions.Timeout("kommer sig")
        return _ok_payload(len(pts))

    monkeypatch.setattr(fetch_weather, "fetch_batch", fake_fetch_batch)

    fetch_weather.process_all_points()

    assert "(1 recovered on the sweep)" in capsys.readouterr().out
