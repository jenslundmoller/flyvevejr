from termik.fetch_weather import (
    build_api_url,
    parse_api_response,
    calculate_precip_last_6h,
    calculate_pressure_trend,
    calculate_temp_850_trend,
)


def test_build_api_url_single():
    points = [{"lat": 55.92, "lon": 9.07}]
    url = build_api_url(points)
    assert "latitude=55.92" in url
    assert "longitude=9.07" in url
    assert "forecast_days=3" in url
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
