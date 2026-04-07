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
    from termik.fetch_weather import process_point_hour

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
