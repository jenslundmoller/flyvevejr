"""Thermal scoring module for the Termik Forecast system.

Computes a thermal soaring score (0-10) from weather parameters,
designed for Danish glider pilots.
"""

from termik.config import WEIGHTS, SCORE_LABELS, SEA_TEMP_BY_MONTH


def score_lapse_rate(lapse_rate: float) -> int:
    """Score atmospheric instability based on lapse rate (°C per 100m).

    Higher lapse rate = more unstable = better thermals.
    """
    if lapse_rate >= 1.2:
        return 10
    elif lapse_rate >= 1.0:
        return 8
    elif lapse_rate >= 0.8:
        return 5
    elif lapse_rate >= 0.65:
        return 2
    else:
        return 0


def score_solar(cloud_cover: float, shortwave_radiation: float) -> float:
    """Score solar heating potential from cloud cover and radiation.

    Cloud cover in %, shortwave radiation in W/m².
    """
    cloud_factor = (100 - cloud_cover) / 100
    radiation_factor = min(shortwave_radiation / 800, 1.0)
    return (cloud_factor * 0.4 + radiation_factor * 0.6) * 10


def score_spread(spread: float) -> int:
    """Score temperature-dewpoint spread.

    Optimal range 8-15°C gives cumulus clouds at good height.
    Too low = fog/overdevelopment risk. Too high = blue/dry thermals.
    """
    if 8 <= spread <= 15:
        return 10
    elif 5 <= spread < 8:
        return 7
    elif 15 < spread <= 20:
        return 7
    elif 3 <= spread < 5:
        return 3
    elif spread > 20:
        return 5
    else:
        return 0


def score_wind(wind_kt: float) -> int:
    """Score wind speed for thermal triggering.

    5-15 kt is optimal. Too calm = no triggering. Too strong = shear/turbulence.
    """
    if 5 <= wind_kt <= 15:
        return 10
    elif 3 <= wind_kt < 5:
        return 7
    elif 15 < wind_kt <= 25:
        return 6
    elif 0 < wind_kt < 3:
        return 4
    elif wind_kt == 0:
        return 3
    elif 25 < wind_kt <= 35:
        return 2
    else:
        return 0


def score_gusts(wind_gusts_kt: float, wind_speed_kt: float) -> int:
    """Score wind gusts impact on flyability.

    Both absolute gust strength and the gust factor (gusts/wind) matter.
    High gusts = turbulence and dangerous conditions for gliders.
    Gust factor > 2 indicates severe turbulence even at lower wind speeds.
    """
    if wind_gusts_kt <= 20:
        return 10
    gust_factor = wind_gusts_kt / max(wind_speed_kt, 1)
    if wind_gusts_kt <= 25 and gust_factor < 2.0:
        return 8
    if wind_gusts_kt <= 30 and gust_factor < 2.0:
        return 5
    if wind_gusts_kt <= 30:
        return 3  # gust factor >= 2
    if wind_gusts_kt <= 40:
        return 2
    return 0


def score_temperature(temp: float) -> float:
    """Score surface temperature. Higher = more heating potential.

    Linear scale from 5°C (score 0) to 30°C (score 10).
    """
    return min(max((temp - 5) / 2.5, 0), 10)


def score_precipitation(precip: float, precip_last_6h: float) -> int:
    """Score precipitation impact on thermals.

    Active rain kills thermals. Recent rain wets the ground (reduced heating).
    """
    if precip > 0:
        return 0
    if precip_last_6h == 0:
        return 10
    if precip_last_6h < 2:
        return 6
    return 3


def calculate_seabreeze_penalty(
    coast_distance_km: float,
    coast_direction_deg: float,
    wind_dir: float,
    wind_speed_kt: float,
    temp_2m: float,
    month: int,
) -> float:
    """Calculate sea breeze penalty for coastal locations.

    Denmark is very coastal; sea breeze convergence kills thermals near the coast.
    """
    if coast_distance_km >= 80:
        return 0

    sea_temp = SEA_TEMP_BY_MONTH[month]
    land_sea_diff = temp_2m - sea_temp

    # Is wind blowing FROM the coast (onshore)?
    # wind_dir is where wind comes FROM. coast_direction_deg is bearing TO coast.
    # If wind comes from coast direction, it's onshore.
    angle_diff = abs(wind_dir - coast_direction_deg)
    if angle_diff > 180:
        angle_diff = 360 - angle_diff
    is_onshore = angle_diff < 90

    if not is_onshore and wind_speed_kt > 15:
        return 0  # Strong offshore wind prevents sea breeze

    if is_onshore:
        seabreeze_risk = 3
    elif land_sea_diff > 8 and wind_speed_kt < 8:
        seabreeze_risk = 2
    elif land_sea_diff > 4:
        seabreeze_risk = 1
    else:
        return 0

    distance_factor = max(0, 1 - coast_distance_km / 80)
    return round(seabreeze_risk * distance_factor, 1)


def calculate_modifiers(
    cape: float, pressure_trend: float, temp_850hpa_trend: float
) -> float:
    """Calculate bonus/penalty modifiers from secondary indicators.

    CAPE: convective available potential energy.
    Pressure trend: rising = subsidence inversion clearing, falling = frontal.
    850hPa temp trend: cooling aloft = destabilisation.
    """
    mod = 0.0
    if cape > 700:
        mod += 1.0
    elif cape > 300:
        mod += 0.5
    if pressure_trend > 1.5:
        mod += 0.5
    elif pressure_trend < -1.5:
        mod -= 0.5
    if temp_850hpa_trend < -1.0:
        mod += 0.5  # Cold air advection = destabilisation
    return mod


def apply_dealbreakers(
    score: float,
    lapse_rate: float,
    cloud_cover: float,
    precipitation: float,
    wind_kt: float,
    wind_gusts_kt: float,
    temp: float,
) -> float:
    """Apply hard caps for conditions that prevent usable thermals."""
    max_score = 10.0
    if lapse_rate < 0.50:
        max_score = min(max_score, 1)
    elif lapse_rate < 0.65:
        max_score = min(max_score, 3)
    if cloud_cover >= 87:
        max_score = min(max_score, 2)
    if precipitation > 0:
        max_score = min(max_score, 1)
    if wind_kt > 35:
        max_score = min(max_score, 2)
    if wind_gusts_kt > 40:
        max_score = min(max_score, 1)
    elif wind_gusts_kt > 30:
        max_score = min(max_score, 3)
    if temp < 5:
        max_score = min(max_score, 3)
    return min(score, max_score)


def compute_thermal_score(
    temp_2m: float,
    dewpoint_2m: float,
    temp_850hpa: float,
    cloud_cover: float,
    shortwave_radiation: float,
    wind_speed_kt: float,
    wind_dir: float,
    wind_gusts_kt: float,
    precipitation: float,
    precip_last_6h: float,
    cape: float,
    surface_pressure: float,
    pressure_trend: float,
    temp_850hpa_trend: float,
    coast_distance_km: float,
    coast_direction_deg: float,
    month: int,
) -> dict:
    """Compute the full thermal score from weather parameters.

    Returns a dict with score (0-10), label, and diagnostic values.
    """
    # Derived values
    spread = temp_2m - dewpoint_2m
    # Lapse rate: temperature drop per 100m between surface and 850hPa (~1500m)
    lapse_rate = (temp_2m - temp_850hpa) / 15.0
    # Cloud base estimate (Henning formula: spread * 125m)
    skybase_m = round(spread * 125)
    skybase_ft = round(skybase_m * 3.281)

    # Score each factor
    scores = {
        "lapse_rate": score_lapse_rate(lapse_rate),
        "solar": score_solar(cloud_cover, shortwave_radiation),
        "spread": score_spread(spread),
        "wind": score_wind(wind_speed_kt),
        "gusts": score_gusts(wind_gusts_kt, wind_speed_kt),
        "temperature": score_temperature(temp_2m),
        "precipitation": score_precipitation(precipitation, precip_last_6h),
    }

    # Weighted sum
    weighted = sum(scores[k] * WEIGHTS[k] for k in WEIGHTS)

    # Scale to 0-10
    total = weighted * 10 / sum(w * 10 for w in WEIGHTS.values())

    # Add modifiers
    modifiers = calculate_modifiers(cape, pressure_trend, temp_850hpa_trend)
    total += modifiers

    # Subtract sea breeze penalty
    seabreeze_penalty = calculate_seabreeze_penalty(
        coast_distance_km, coast_direction_deg,
        wind_dir, wind_speed_kt, temp_2m, month,
    )
    total -= seabreeze_penalty

    # Apply dealbreakers
    total = apply_dealbreakers(
        total, lapse_rate, cloud_cover, precipitation,
        wind_speed_kt, wind_gusts_kt, temp_2m,
    )

    # Clamp and round
    total = round(max(0, min(10, total)), 1)

    return {
        "score": total,
        "label": get_score_label(total),
        "spread": round(spread, 1),
        "skybase_m": skybase_m,
        "skybase_ft": skybase_ft,
        "lapse_rate": round(lapse_rate, 2),
        "seabreeze_penalty": seabreeze_penalty,
    }


def get_score_label(score: float) -> str:
    """Return a Danish label for the given score."""
    s = int(score)
    for min_score, max_score, label in SCORE_LABELS:
        if min_score <= s <= max_score:
            return label
    return "Ingen brugbar termik"
