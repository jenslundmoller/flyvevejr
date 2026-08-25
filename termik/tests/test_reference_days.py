"""Regression tests for the two days a pilot has actually verified.

These are the only ground truth this scoring has. Everything else is physics
argument and season statistics, so if one of these breaks, the change that
broke it is wrong until proven otherwise.

The hourly data is baked in rather than fetched, so the tests run offline and
cannot drift when Open-Meteo revises a past day. It comes from the FORECAST
endpoint, the same best_match blend production runs on, never from the
archive: the archive serves ecmwf_ifs for days ERA5 has not reached and
disagreed by up to 253 W/m² on 2026-08-08, enough to move a published score
by two tiers.

Indices are hours, so DAY_2026_08_08 field lists are indexed 0 to 23 directly.
"""

import pytest

from termik.fetch_weather import process_point_hour

# Midtsjællands Svæveflyveklub, from termik/locations.py
RINGSTED = {
    "id": "ringsted", "name": "Midtsjællands Svæveflyveklub",
    "lat": 55.451748, "lon": 11.642456, "region": "Sjælland",
    "coast_distance_km": 33, "coast_direction_deg": 239,
}

# 2026-08-08: the pilot flew good thermals until 19:00.
DAY_2026_08_08 = {
    "time": [
        '2026-08-08T00:00', '2026-08-08T01:00', '2026-08-08T02:00',
        '2026-08-08T03:00', '2026-08-08T04:00', '2026-08-08T05:00',
        '2026-08-08T06:00', '2026-08-08T07:00', '2026-08-08T08:00',
        '2026-08-08T09:00', '2026-08-08T10:00', '2026-08-08T11:00',
        '2026-08-08T12:00', '2026-08-08T13:00', '2026-08-08T14:00',
        '2026-08-08T15:00', '2026-08-08T16:00', '2026-08-08T17:00',
        '2026-08-08T18:00', '2026-08-08T19:00', '2026-08-08T20:00',
        '2026-08-08T21:00', '2026-08-08T22:00', '2026-08-08T23:00',
    ],
    "temperature_2m": [
        13.1, 13.0, 12.7, 12.5, 12.7, 12.9, 12.4, 14.0, 15.6, 16.7, 17.8, 19.1,
        20.0, 20.6, 21.5, 22.2, 21.9, 22.2, 21.9, 21.5, 20.6, 18.2, 16.6, 15.6,
    ],
    "dewpoint_2m": [
        7.2, 7.9, 9.7, 10.3, 11.0, 11.1, 9.8, 11.0, 11.2, 9.6, 10.2, 10.7, 9.6,
        9.2, 9.8, 9.4, 8.8, 10.7, 11.3, 11.8, 12.3, 11.6, 11.9, 12.7,
    ],
    "relative_humidity_2m": [
        67, 71, 82, 86, 89, 89, 84, 82, 75, 63, 61, 58, 51, 48, 47, 44, 43, 48, 51,
        54, 59, 65, 74, 83,
    ],
    "wind_speed_10m": [
        3.9, 6.2, 6.2, 5.6, 5.2, 5.6, 5.6, 4.7, 6.6, 9.3, 8.6, 7.8, 7.8, 8.4, 7.0,
        7.2, 6.8, 8.2, 8.4, 7.4, 6.2, 4.1, 4.1, 4.5,
    ],
    "wind_direction_10m": [
        261, 250, 256, 262, 257, 251, 241, 242, 274, 273, 274, 272, 264, 258, 249,
        256, 246, 232, 237, 236, 223, 205, 194, 190,
    ],
    "wind_gusts_10m": [
        7.4, 10.3, 10.3, 10.1, 9.3, 9.1, 9.5, 9.1, 11.3, 16.7, 16.9, 15.2, 16.1,
        17.5, 16.3, 15.9, 15.9, 16.3, 16.1, 15.7, 12.4, 10.3, 6.4, 6.6,
    ],
    "wind_speed_80m": [
        13.7, 12.9, 12.7, 12.9, 12.7, 12.6, 12.2, 11.1, 9.5, 11.1, 11.0, 10.7,
        10.0, 10.6, 9.8, 10.2, 9.5, 8.4, 7.8, 7.9, 9.4, 8.4, 7.9, 8.4,
    ],
    "wind_direction_80m": [
        267, 268, 266, 268, 267, 272, 274, 270, 273, 276, 276, 275, 266, 257, 261,
        261, 261, 258, 255, 238, 222, 213, 193, 189,
    ],
    "wind_speed_120m": [
        14.3, 13.5, 13.3, 13.5, 13.3, 13.2, 12.7, 11.6, 9.9, 11.6, 11.5, 11.2,
        10.4, 11.1, 10.2, 10.6, 9.9, 8.8, 8.2, 8.3, 9.8, 8.8, 8.3, 8.8,
    ],
    "wind_direction_120m": [
        267, 268, 266, 268, 267, 272, 274, 270, 273, 276, 276, 275, 266, 257, 261,
        261, 261, 258, 255, 238, 222, 213, 193, 189,
    ],
    "wind_speed_180m": [
        17.5, 16.9, 16.6, 16.9, 16.5, 16.4, 15.9, 14.6, 11.7, 12.4, 12.2, 11.9,
        10.9, 11.5, 10.7, 11.2, 10.4, 9.3, 8.6, 9.2, 10.4, 9.9, 9.0, 9.8,
    ],
    "wind_direction_180m": [
        270, 271, 271, 273, 272, 276, 280, 278, 276, 277, 276, 274, 265, 257, 261,
        261, 260, 257, 255, 240, 225, 219, 202, 197,
    ],
    "temperature_80m": [
        None, None, None, None, None, None, None, None, None, None, None, None,
        None, None, None, None, None, None, None, None, None, None, None, None,
    ],
    "temperature_120m": [
        None, None, None, None, None, None, None, None, None, None, None, None,
        None, None, None, None, None, None, None, None, None, None, None, None,
    ],
    "temperature_180m": [
        None, None, None, None, None, None, None, None, None, None, None, None,
        None, None, None, None, None, None, None, None, None, None, None, None,
    ],
    "cloud_cover": [
        75, 92, 52, 42, 47, 72, 24, 18, 10, 26, 76, 66, 31, 67, 64, 57, 61, 48, 32,
        31, 26, 28, 24, 8,
    ],
    "cloud_cover_low": [
        6, 9, 2, 2, 2, 3, 2, 2, 2, 5, 8, 18, 65, 95, 47, 66, 52, 58, 67, 62, 100,
        40, 2, 2,
    ],
    "cloud_cover_mid": [
        13, 14, 0, 2, 2, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 58, 33, 30, 31, 38, 1, 0, 1,
        1,
    ],
    "cloud_cover_high": [
        0, 2, 29, 0, 0, 10, 2, 57, 45, 1, 12, 13, 23, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0,
        0,
    ],
    "precipitation": [
        0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0,
        0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0,
    ],
    "shortwave_radiation": [
        0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 3.0, 46.0, 169.0, 244.0, 381.0, 426.0, 585.0,
        736.0, 726.0, 708.0, 657.0, 523.0, 398.0, 274.0, 139.0, 30.0, 0.0, 0.0,
    ],
    "direct_radiation": [
        0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 6.1, 68.1, 99.4, 200.6, 199.6, 354.6,
        535.4, 511.2, 505.4, 476.0, 347.2, 243.3, 148.8, 55.1, 4.5, 0.0, 0.0,
    ],
    "cape": [
        10.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 30.0, 20.0, 10.0, 10.0, 10.0,
        10.0, 20.0, 10.0, 10.0, 10.0, 10.0, 10.0, 20.0, 10.0, 0.0, 0.0,
    ],
    "surface_pressure": [
        1017.3, 1017.6, 1017.6, 1017.9, 1017.9, 1017.7, 1017.9, 1018.3, 1018.4,
        1018.6, 1019.0, 1019.0, 1019.1, 1018.9, 1018.5, 1018.4, 1018.1, 1017.5,
        1017.3, 1017.3, 1017.4, 1017.6, 1017.4, 1017.4,
    ],
    "boundary_layer_height": [
        430.0, 400.0, 265.0, 295.0, 290.0, 295.0, 265.0, 350.0, 800.0, 1085.0,
        1155.0, 1270.0, 1515.0, 1600.0, 1760.0, 1750.0, 1570.0, 1685.0, 1250.0,
        1000.0, 225.0, 90.0, 55.0, 60.0,
    ],
    "temperature_950hPa": [
        None, None, None, None, None, None, None, None, None, None, None, None,
        None, None, None, None, None, None, None, None, None, None, None, None,
    ],
    "temperature_925hPa": [
        9.4, 9.2, 9.1, 9.1, 9.2, 9.2, 9.1, 8.9, 8.8, 8.9, 9.1, 9.4, 10.0, 10.7,
        11.4, 11.8, 12.0, 12.3, 12.4, 12.4, 12.4, 12.4, 12.5, 12.6,
    ],
    "temperature_900hPa": [
        None, None, None, None, None, None, None, None, None, None, None, None,
        None, None, None, None, None, None, None, None, None, None, None, None,
    ],
    "temperature_850hPa": [
        3.9, 4.3, 4.8, 5.1, 5.3, 5.4, 5.4, 5.3, 5.2, 5.3, 5.6, 5.6, 5.3, 4.9, 4.7,
        4.8, 5.2, 5.6, 5.8, 6.0, 6.2, 6.3, 6.3, 6.4,
    ],
    "temperature_800hPa": [
        None, None, None, None, None, None, None, None, None, None, None, None,
        None, None, None, None, None, None, None, None, None, None, None, None,
    ],
    "temperature_700hPa": [
        -0.6, -0.9, -1.1, -1.1, -0.8, -0.6, -0.5, -0.2, 0.0, 0.0, 0.2, 0.2, 0.3,
        0.5, 0.8, 1.2, 1.7, 2.1, 2.4, 2.4, 2.6, 2.6, 2.6, 2.6,
    ],
    "temperature_600hPa": [
        -7.9, -8.1, -8.1, -7.9, -7.6, -7.2, -7.2, -7.2, -7.2, -6.8, -6.3, -5.7,
        -5.3, -5.2, -5.0, -4.6, -4.4, -4.2, -4.2, -4.4, -4.4, -4.4, -4.4, -4.2,
    ],
    "geopotential_height_950hPa": [
        None, None, None, None, None, None, None, None, None, None, None, None,
        None, None, None, None, None, None, None, None, None, None, None, None,
    ],
    "geopotential_height_925hPa": [
        832.0, 834.0, 835.0, 835.0, 836.0, 836.0, 837.0, 838.0, 840.0, 843.0,
        847.0, 850.0, 852.0, 853.0, 853.0, 852.0, 850.0, 848.0, 847.0, 847.0,
        846.0, 845.0, 844.0, 843.0,
    ],
    "geopotential_height_900hPa": [
        None, None, None, None, None, None, None, None, None, None, None, None,
        None, None, None, None, None, None, None, None, None, None, None, None,
    ],
    "geopotential_height_850hPa": [
        1528.0, 1530.0, 1531.0, 1532.0, 1532.0, 1532.0, 1533.0, 1533.0, 1535.0,
        1538.0, 1542.0, 1546.0, 1549.0, 1551.0, 1552.0, 1552.0, 1550.0, 1549.0,
        1549.0, 1548.0, 1548.0, 1547.0, 1547.0, 1546.0,
    ],
    "geopotential_height_800hPa": [
        None, None, None, None, None, None, None, None, None, None, None, None,
        None, None, None, None, None, None, None, None, None, None, None, None,
    ],
    "geopotential_height_700hPa": [
        3089.0, 3091.0, 3093.0, 3095.0, 3096.0, 3098.0, 3101.0, 3104.0, 3108.0,
        3112.0, 3116.0, 3119.0, 3122.0, 3125.0, 3127.0, 3128.0, 3129.0, 3129.0,
        3129.0, 3128.0, 3128.0, 3129.0, 3130.0, 3131.0,
    ],
    "geopotential_height_600hPa": [
        4304.0, 4306.0, 4308.0, 4310.0, 4312.0, 4314.0, 4318.0, 4322.0, 4326.0,
        4330.0, 4335.0, 4339.0, 4344.0, 4349.0, 4353.0, 4356.0, 4358.0, 4359.0,
        4360.0, 4360.0, 4360.0, 4361.0, 4362.0, 4363.0,
    ],
    "wind_speed_850hPa": [
        17.5, 17.9, 18.3, 18.7, 19.2, 19.6, 19.5, 19.1, 18.3, 16.8, 14.6, 12.8,
        11.6, 10.9, 10.3, 9.7, 9.0, 8.7, 8.5, 8.9, 9.1, 9.0, 9.1, 9.8,
    ],
    "wind_direction_850hPa": [
        296, 300, 301, 297, 290, 285, 281, 277, 275, 274, 275, 273, 269, 262, 258,
        255, 253, 254, 258, 265, 267, 259, 246, 238,
    ],
}

# 2026-08-09: the pilot found nothing usable all day.
DAY_2026_08_09 = {
    "time": [
        '2026-08-09T00:00', '2026-08-09T01:00', '2026-08-09T02:00',
        '2026-08-09T03:00', '2026-08-09T04:00', '2026-08-09T05:00',
        '2026-08-09T06:00', '2026-08-09T07:00', '2026-08-09T08:00',
        '2026-08-09T09:00', '2026-08-09T10:00', '2026-08-09T11:00',
        '2026-08-09T12:00', '2026-08-09T13:00', '2026-08-09T14:00',
        '2026-08-09T15:00', '2026-08-09T16:00', '2026-08-09T17:00',
        '2026-08-09T18:00', '2026-08-09T19:00', '2026-08-09T20:00',
        '2026-08-09T21:00', '2026-08-09T22:00', '2026-08-09T23:00',
    ],
    "temperature_2m": [
        14.4, 13.4, 12.8, 12.8, 12.3, 11.4, 11.5, 13.8, 15.9, 18.4, 20.9, 22.2,
        23.7, 24.6, 25.2, 25.7, 26.2, 25.7, 25.4, 23.6, 22.2, 20.7, 19.4, 18.1,
    ],
    "dewpoint_2m": [
        13.1, 12.4, 12.2, 11.5, 11.5, 10.5, 10.2, 12.5, 13.4, 12.9, 12.6, 10.7,
        10.1, 9.7, 10.6, 11.1, 12.0, 11.1, 10.4, 11.3, 12.5, 13.2, 13.8, 13.8,
    ],
    "relative_humidity_2m": [
        92, 94, 96, 92, 95, 94, 92, 92, 85, 70, 59, 48, 42, 39, 40, 40, 41, 40, 39,
        46, 54, 62, 70, 76,
    ],
    "wind_speed_10m": [
        4.1, 3.7, 3.7, 4.7, 4.1, 4.7, 5.1, 5.1, 5.6, 6.6, 7.4, 8.7, 9.7, 9.5, 9.3,
        9.5, 8.9, 8.2, 8.6, 9.3, 8.4, 5.2, 3.1, 4.5,
    ],
    "wind_direction_10m": [
        180, 183, 170, 167, 143, 141, 150, 152, 158, 161, 178, 177, 175, 174, 179,
        174, 161, 158, 155, 127, 132, 132, 149, 209,
    ],
    "wind_gusts_10m": [
        6.8, 5.8, 5.2, 8.6, 6.8, 7.0, 7.8, 8.4, 9.5, 11.7, 13.6, 16.3, 18.7, 18.9,
        18.7, 17.9, 17.5, 17.5, 15.7, 16.3, 16.9, 13.8, 8.6, 7.2,
    ],
    "wind_speed_80m": [
        9.2, 9.0, 9.6, 11.6, 12.8, 13.7, 14.4, 13.2, 12.7, 9.9, 8.7, 9.0, 12.0,
        11.8, 10.9, 11.1, 10.6, 10.7, 10.5, 10.4, 11.1, 10.9, 12.8, 15.0,
    ],
    "wind_direction_80m": [
        194, 188, 173, 171, 168, 163, 162, 163, 167, 165, 166, 164, 163, 160, 164,
        165, 159, 155, 153, 142, 137, 153, 222, 271,
    ],
    "wind_speed_120m": [
        9.6, 9.4, 10.1, 12.2, 13.4, 14.3, 15.1, 13.9, 13.3, 10.4, 9.1, 9.4, 12.6,
        12.4, 11.4, 11.6, 11.1, 11.2, 11.0, 10.9, 11.6, 11.4, 13.4, 15.7,
    ],
    "wind_direction_120m": [
        194, 188, 173, 171, 168, 163, 162, 163, 167, 165, 166, 164, 163, 160, 164,
        165, 159, 155, 153, 142, 137, 153, 222, 271,
    ],
    "wind_speed_180m": [
        11.2, 10.7, 10.7, 14.5, 16.9, 18.4, 19.2, 17.9, 16.6, 16.6, 11.2, 10.5,
        13.5, 13.1, 12.1, 12.3, 12.0, 12.0, 12.5, 12.1, 13.4, 14.3, 16.3, 19.6,
    ],
    "wind_direction_180m": [
        198, 192, 184, 180, 175, 169, 168, 173, 177, 178, 171, 167, 165, 161, 165,
        165, 161, 158, 157, 150, 151, 170, 235, 275,
    ],
    "temperature_80m": [
        None, None, None, None, None, None, None, None, None, None, None, None,
        None, None, None, None, None, None, None, None, None, None, None, None,
    ],
    "temperature_120m": [
        None, None, None, None, None, None, None, None, None, None, None, None,
        None, None, None, None, None, None, None, None, None, None, None, None,
    ],
    "temperature_180m": [
        None, None, None, None, None, None, None, None, None, None, None, None,
        None, None, None, None, None, None, None, None, None, None, None, None,
    ],
    "cloud_cover": [
        2, 34, 34, 23, 56, 17, 58, 67, 64, 72, 74, 79, 55, 64, 75, 67, 63, 36, 15,
        37, 51, 89, 87, 100,
    ],
    "cloud_cover_low": [
        0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
    ],
    "cloud_cover_mid": [
        0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 43, 1, 1, 0, 13, 0, 6, 4,
    ],
    "cloud_cover_high": [
        0, 0, 0, 18, 2, 7, 90, 98, 98, 99, 99, 81, 59, 84, 100, 88, 13, 7, 0, 0, 0,
        1, 12, 41,
    ],
    "precipitation": [
        0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0,
        0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0,
    ],
    "shortwave_radiation": [
        0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 3.0, 57.0, 141.0, 252.0, 380.0, 486.0, 630.0,
        690.0, 560.0, 442.0, 503.0, 453.0, 429.0, 284.0, 144.0, 27.0, 0.0, 0.0,
    ],
    "direct_radiation": [
        0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 12.3, 44.7, 108.6, 201.0, 276.7, 421.0,
        470.5, 278.5, 158.2, 264.7, 256.0, 283.1, 160.9, 60.7, 3.4, 0.0, 0.0,
    ],
    "cape": [
        0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 10.0, 0.0, 0.0, 0.0, 0.0,
        0.0, 0.0, 0.0, 0.0, 50.0, 70.0, 20.0, 10.0, 0.0,
    ],
    "surface_pressure": [
        1017.4, 1017.1, 1016.8, 1016.5, 1016.0, 1015.2, 1014.9, 1014.7, 1014.4,
        1014.0, 1013.7, 1013.0, 1012.4, 1011.7, 1011.1, 1010.3, 1009.7, 1008.9,
        1008.2, 1007.4, 1007.1, 1006.9, 1006.6, 1006.7,
    ],
    "boundary_layer_height": [
        65.0, 65.0, 65.0, 90.0, 125.0, 145.0, 185.0, 210.0, 245.0, 315.0, 410.0,
        1210.0, 1280.0, 1295.0, 1260.0, 1170.0, 1070.0, 980.0, 780.0, 355.0, 165.0,
        110.0, 170.0, 310.0,
    ],
    "temperature_950hPa": [
        None, None, None, None, None, None, None, None, None, None, None, None,
        None, None, None, None, None, None, None, None, None, None, None, None,
    ],
    "temperature_925hPa": [
        12.8, 13.0, 13.1, 13.1, 13.1, 13.2, 13.6, 13.9, 14.2, 14.3, 14.2, 14.3,
        14.7, 15.2, 15.6, 15.9, 16.1, 16.4, 17.3, 18.4, 19.0, 18.8, 18.2, 17.6,
    ],
    "temperature_900hPa": [
        None, None, None, None, None, None, None, None, None, None, None, None,
        None, None, None, None, None, None, None, None, None, None, None, None,
    ],
    "temperature_850hPa": [
        6.8, 7.4, 7.7, 7.8, 8.0, 8.0, 7.8, 7.7, 7.7, 8.0, 8.3, 8.8, 9.3, 9.8, 10.4,
        11.1, 11.8, 12.4, 12.7, 12.8, 12.9, 13.4, 14.0, 14.1,
    ],
    "temperature_800hPa": [
        None, None, None, None, None, None, None, None, None, None, None, None,
        None, None, None, None, None, None, None, None, None, None, None, None,
    ],
    "temperature_700hPa": [
        2.6, 2.7, 2.7, 2.7, 2.6, 2.6, 2.6, 2.4, 2.4, 2.4, 2.6, 2.7, 3.0, 3.3, 3.5,
        3.7, 3.7, 3.7, 3.5, 3.3, 3.0, 2.7, 2.4, 2.3,
    ],
    "temperature_600hPa": [
        -4.1, -3.9, -3.7, -3.5, -3.5, -3.5, -3.5, -3.7, -3.7, -3.9, -3.9, -4.1,
        -4.2, -4.2, -4.4, -4.4, -4.2, -4.4, -5.0, -5.7, -6.3, -6.3, -6.1, -5.9,
    ],
    "geopotential_height_950hPa": [
        None, None, None, None, None, None, None, None, None, None, None, None,
        None, None, None, None, None, None, None, None, None, None, None, None,
    ],
    "geopotential_height_925hPa": [
        842.0, 840.0, 838.0, 834.0, 829.0, 825.0, 823.0, 822.0, 821.0, 818.0,
        815.0, 811.0, 807.0, 803.0, 798.0, 793.0, 787.0, 782.0, 778.0, 775.0,
        772.0, 769.0, 765.0, 762.0,
    ],
    "geopotential_height_900hPa": [
        None, None, None, None, None, None, None, None, None, None, None, None,
        None, None, None, None, None, None, None, None, None, None, None, None,
    ],
    "geopotential_height_850hPa": [
        1545.0, 1544.0, 1542.0, 1538.0, 1534.0, 1530.0, 1528.0, 1527.0, 1526.0,
        1523.0, 1520.0, 1517.0, 1514.0, 1511.0, 1508.0, 1504.0, 1500.0, 1497.0,
        1495.0, 1493.0, 1491.0, 1487.0, 1483.0, 1479.0,
    ],
    "geopotential_height_800hPa": [
        None, None, None, None, None, None, None, None, None, None, None, None,
        None, None, None, None, None, None, None, None, None, None, None, None,
    ],
    "geopotential_height_700hPa": [
        3130.0, 3129.0, 3127.0, 3124.0, 3119.0, 3116.0, 3114.0, 3112.0, 3111.0,
        3110.0, 3108.0, 3107.0, 3106.0, 3105.0, 3104.0, 3102.0, 3100.0, 3098.0,
        3095.0, 3093.0, 3090.0, 3088.0, 3085.0, 3082.0,
    ],
    "geopotential_height_600hPa": [
        4362.0, 4361.0, 4359.0, 4355.0, 4351.0, 4347.0, 4345.0, 4343.0, 4342.0,
        4340.0, 4339.0, 4338.0, 4338.0, 4338.0, 4337.0, 4335.0, 4332.0, 4329.0,
        4326.0, 4322.0, 4318.0, 4314.0, 4310.0, 4306.0,
    ],
    "wind_speed_850hPa": [
        10.9, 11.8, 12.2, 11.8, 10.8, 9.7, 8.0, 7.2, 8.5, 11.3, 14.8, 16.8, 16.5,
        16.2, 17.1, 18.7, 20.5, 22.2, 23.8, 25.2, 26.3, 27.0, 27.0, 26.7,
    ],
    "wind_direction_850hPa": [
        237, 239, 240, 244, 249, 249, 236, 211, 190, 181, 180, 183, 194, 210, 224,
        231, 235, 236, 235, 231, 229, 228, 228, 231,
    ],
}


def _score(day, hour):
    """The score production would publish for that hour of that day."""
    return process_point_hour(RINGSTED, day, hour, month=8)["score"]


# --- Acceptance criterion 1: the day the pilot flew ---

def test_saturday_1800_stays_flyable():
    """The pilot was flying good thermals. The gate used to publish 5.0."""
    assert _score(DAY_2026_08_08, 18) > 6.5


def test_saturday_1900_reaches_the_target():
    """Closed by scoring v2's CU_ALLOWANCE (DSvU-hæftets punkt 2).

    Under v1 var dette en strict xfail: 5.9 var den vægtede sum selv, fordi
    score_solar læste dagens egen termik-cumulus som 88.6 % vægtet skydække.
    v2 lader de første 40 procentpoint lav sky være gratis (Skema 1), og
    timen når nu kriteriet. Falder SCORING_VERSION tilbage til v1, fejler
    denne test, hvilket er korrekt: hullet er der stadig i v1.
    """
    assert _score(DAY_2026_08_08, 19) > 6.5


def test_saturday_1900_does_not_regress():
    """What the hour does reach, pinned so it cannot quietly fall further.

    The substantive guarantee for this hour is that nothing caps it: the
    radiation memory keeps the gate off (effective radiation 427 against a
    threshold of 400) and the mixed layer is 1000 m, above the depth gate.
    """
    assert _score(DAY_2026_08_08, 19) >= 5.5


def test_saturday_midday_is_not_dragged_down():
    """13:00 has 736 W/m² and reports 95 % low cloud, which is its own cumulus.

    This is the hour that caught the layer-weighted cloud cap and scored 2.0,
    "Ingen brugbar termik", in full sun. The general cap reads the raw total
    for exactly this reason.
    """
    assert _score(DAY_2026_08_08, 13) > 6.0


# --- Acceptance criterion 2: the day the pilot found nothing ---

@pytest.mark.parametrize("hour", [10, 11, 12, 13, 14])
def test_sunday_midday_is_not_published_as_usable(hour):
    """Cirrus 99, 81, 59, 84, 100 with the ground shut down beneath it.

    12:00 is the one that matters most: the sheet thinned to 59 for an hour,
    and an instantaneous test at 85 would let that hour through.
    """
    assert _score(DAY_2026_08_09, hour) <= 3.0


# --- Acceptance criterion 3: the day's worst prediction ---

def test_sunday_1800_is_capped_by_the_shallow_mixed_layer():
    """429 W/m² under a sky that had cleared to 15 %, and nothing to fly in.

    The mixed layer at 780 m is the only fetched field that separates this
    hour from 1250 m at the same time on the Saturday. It used to publish 7.4.
    """
    assert _score(DAY_2026_08_09, 18) <= 5.0
