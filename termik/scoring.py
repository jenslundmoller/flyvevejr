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


def score_surface_lapse_rate(surface_lapse: float) -> int:
    """Score thermal initiation potential from the 2m→180m lapse rate.

    The surface layer is expected to be superadiabatic (>0.98°C/100m)
    during active convection. Values well above DALR are normal here
    due to the 2m sensor's proximity to the heated ground.
    """
    if surface_lapse >= 1.3:
        return 10
    elif surface_lapse >= 0.98:
        return 7
    elif surface_lapse >= 0.65:
        return 3
    elif surface_lapse >= 0.5:
        return 1
    else:
        return 0


def score_solar(
    cloud_cover: float,
    shortwave_radiation: float,
    cloud_cover_low: float | None = None,
    cloud_cover_mid: float | None = None,
    cloud_cover_high: float | None = None,
    direct_radiation: float | None = None,
) -> float:
    """Score solar heating potential from cloud cover and radiation.

    Cloud cover in %, radiation in W/m².

    When layer breakdown is available, weights cirrus less than stratus
    (low=1.0, mid=0.7, high=0.5) because cirrus attenuates less than low
    cloud per unit cover. When direct_radiation is available, uses it
    instead of total shortwave: cirrus boosts the diffuse fraction
    without strongly cutting total SW, but direct radiation drives the
    differential surface heating that triggers thermals.
    """
    if (
        cloud_cover_low is not None
        and cloud_cover_mid is not None
        and cloud_cover_high is not None
    ):
        effective_cloud = min(
            100.0,
            cloud_cover_low * 1.0
            + cloud_cover_mid * 0.7
            + cloud_cover_high * 0.5,
        )
    else:
        effective_cloud = cloud_cover
    cloud_factor = max(0.0, (100 - effective_cloud) / 100)

    if direct_radiation is not None:
        # Peak direct in DK summer ~700 W/m²; 600 = near full credit.
        radiation_factor = min(direct_radiation / 600, 1.0)
    else:
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

    Uses the pilot rule of thumb: effective wind = wind + (gusts / 2).
    >25 = significantly reduced flying conditions.
    >30 = only for very experienced pilots.
    Also considers the gust factor (gusts/wind) for turbulence assessment.
    """
    # Absolute gust limits
    if wind_gusts_kt >= 35:
        return 0
    if wind_gusts_kt >= 30:
        return 2
    # Effective wind rule: wind + (gust/2)
    effective_wind = wind_speed_kt + (wind_gusts_kt / 2)
    if effective_wind > 30:
        return 0
    if effective_wind > 25:
        return 2
    gust_factor = wind_gusts_kt / max(wind_speed_kt, 1)
    if gust_factor >= 2.0 and wind_gusts_kt > 15:
        return 4
    if effective_wind > 20:
        return 7
    return 10


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


def calculate_wind_shear_modifier(wind_10m_kt: float, wind_80m_kt: float) -> float:
    """Calculate thermal quality modifier from low-level wind shear.

    Based on RASP B/S ratio concept: thermals need to overcome shear
    to remain organized. Shear is concentrated in the surface layer (0-100m).
    """
    # Both winds calm — shear measurement not meaningful
    if wind_10m_kt <= 3 and wind_80m_kt <= 3:
        return 0.0
    shear = abs(wind_80m_kt - wind_10m_kt)
    if shear < 5:
        return 0.5   # Well-organized thermals
    elif shear < 12:
        return 0.0   # Normal shear
    elif shear < 20:
        return -0.5  # Thermals tilted/broken
    else:
        return -1.0  # Severe shear, thermals destroyed


def calculate_bl_mixing_modifier(wind_80m_kt: float, wind_180m_kt: float) -> float:
    """Assess boundary layer mixing from the 80m-180m wind gradient.

    In a well-mixed convective BL, wind is nearly uniform above the surface
    layer. A large gradient indicates stable or transitional conditions.
    """
    gradient = abs(wind_180m_kt - wind_80m_kt)
    if gradient < 4:
        return 0.3   # Well-mixed CBL
    elif gradient < 8:
        return 0.0   # Moderate mixing
    else:
        return -0.3  # Poor mixing, stable/transitional


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
    cape: float = 0,
    surface_lapse_rate: float | None = None,
    shortwave_radiation: float | None = None,
) -> float:
    """Apply hard caps for conditions that prevent usable thermals."""
    max_score = 10.0
    # Solar radiation gate: thermals require sufficient surface heating.
    # Caps reflect that low radiation (night, twilight, heavy overcast)
    # cannot drive convection regardless of other favourable conditions.
    if shortwave_radiation is not None:
        if shortwave_radiation < 100:
            max_score = min(max_score, 1)
        elif shortwave_radiation < 250:
            max_score = min(max_score, 3)
        elif shortwave_radiation < 400:
            max_score = min(max_score, 5)
    if lapse_rate < 0.50:
        max_score = min(max_score, 1)
    elif lapse_rate < 0.65:
        max_score = min(max_score, 3)
    elif lapse_rate < 0.70:
        max_score = min(max_score, 5)
    # Surface lapse rate dealbreaker (thermal initiation gate)
    if surface_lapse_rate is not None:
        if surface_lapse_rate < 0.3:
            max_score = min(max_score, 1)
        elif surface_lapse_rate < 0.5:
            max_score = min(max_score, 2)
    if cloud_cover >= 87:
        max_score = min(max_score, 2)
    if precipitation > 0:
        max_score = min(max_score, 1)
    if wind_kt > 35:
        max_score = min(max_score, 2)
    if wind_gusts_kt >= 35:
        max_score = min(max_score, 1)
    elif wind_gusts_kt >= 30:
        max_score = min(max_score, 2)
    effective_wind = wind_kt + (wind_gusts_kt / 2)
    if effective_wind > 35:
        max_score = min(max_score, 1)
    elif effective_wind > 30:
        max_score = min(max_score, 2)
    elif effective_wind > 25:
        max_score = min(max_score, 4)
    if temp < 5:
        max_score = min(max_score, 3)
    # Overdevelopment / thunderstorm risk from high CAPE
    if cape > 1500:
        max_score = min(max_score, 5)
    elif cape > 1000:
        max_score = min(max_score, 7)
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
    # Multi-level data (optional — enhances scoring when available)
    temp_180m: float | None = None,
    wind_speed_80m_kt: float | None = None,
    wind_speed_180m_kt: float | None = None,
    boundary_layer_height: float | None = None,
    # Layered cloud + direct radiation (optional — improves cirrus handling)
    cloud_cover_low: float | None = None,
    cloud_cover_mid: float | None = None,
    cloud_cover_high: float | None = None,
    direct_radiation: float | None = None,
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

    # Surface lapse rate (2m→180m, height diff = 1.78 hectometers)
    surface_lapse = None
    if temp_180m is not None:
        surface_lapse = (temp_2m - temp_180m) / 1.78

    # Score each factor
    scores = {
        "lapse_rate": score_lapse_rate(lapse_rate),
        "solar": score_solar(
            cloud_cover,
            shortwave_radiation,
            cloud_cover_low=cloud_cover_low,
            cloud_cover_mid=cloud_cover_mid,
            cloud_cover_high=cloud_cover_high,
            direct_radiation=direct_radiation,
        ),
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

    # Multi-level modifiers
    wind_shear_mod = 0.0
    bl_mixing_mod = 0.0

    if wind_speed_80m_kt is not None:
        wind_shear_mod = calculate_wind_shear_modifier(wind_speed_kt, wind_speed_80m_kt)
        total += wind_shear_mod

    if wind_speed_80m_kt is not None and wind_speed_180m_kt is not None:
        bl_mixing_mod = calculate_bl_mixing_modifier(wind_speed_80m_kt, wind_speed_180m_kt)
        total += bl_mixing_mod

    # Apply dealbreakers
    total = apply_dealbreakers(
        total, lapse_rate, cloud_cover, precipitation,
        wind_speed_kt, wind_gusts_kt, temp_2m,
        cape=cape,
        surface_lapse_rate=surface_lapse,
        shortwave_radiation=shortwave_radiation,
    )

    # Clamp and round
    total = round(max(0, min(10, total)), 1)

    result = {
        "score": total,
        "label": get_score_label(total),
        "spread": round(spread, 1),
        "skybase_m": skybase_m,
        "skybase_ft": skybase_ft,
        "lapse_rate": round(lapse_rate, 2),
        "seabreeze_penalty": seabreeze_penalty,
    }

    # Add multi-level diagnostics when available
    if surface_lapse is not None:
        result["surface_lapse_rate"] = round(surface_lapse, 2)
    if wind_speed_80m_kt is not None:
        result["wind_shear_modifier"] = wind_shear_mod
    if wind_speed_80m_kt is not None and wind_speed_180m_kt is not None:
        result["bl_mixing_modifier"] = bl_mixing_mod
    if boundary_layer_height is not None:
        result["boundary_layer_height"] = round(boundary_layer_height)

    return result


def get_score_label(score: float) -> str:
    """Return a Danish label for the given score."""
    s = int(score)
    for min_score, max_score, label in SCORE_LABELS:
        if min_score <= s <= max_score:
            return label
    return "Ingen brugbar termik"
