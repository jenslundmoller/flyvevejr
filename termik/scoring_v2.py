"""Scoring v2: DSvU-hæftets justeringer oven på den gamle score.

Implementerer de 7 punkter fra "Svæveflyvningen og vejret" (DSvU), se
docs/plans/2026-08-25-scoring-v2-dsvu-haefte.md. termik/scoring.py er bevidst
urørt og fungerer som rollback: produktionen vælger version via
config.SCORING_VERSION.

Alt der IKKE er et af de 7 punkter genbruges fra v1 via import: lapse-scorer,
spread, gusts, nedbør, shear/mixing-modifiers, cloud_deck_arrived og samtlige
kalibrerede caps (strålings-gate, cirrus-skjold, mellemhøj pendant, BL-gate).
apply_dealbreakers_v2 er en bevidst fork af v1's funktion: de to versioner
skal kunne afvige uden at røre rollback-stien.
"""

from termik.config import (
    WEIGHTS_V2,
    RADIATION_GATE,
    RADIATION_MEMORY_FACTOR,
    RADIATION_MEMORY_FLOOR,
    SHALLOW_BOUNDARY_LAYER_M,
    SHALLOW_BOUNDARY_LAYER_MAX_SCORE,
    CIRRUS_SHIELD_THRESHOLD,
    CIRRUS_SHIELD_PRESENT_MIN,
    CIRRUS_SHIELD_MAX_SCORE,
    MID_LEVEL_DECK_THRESHOLD,
    MID_LEVEL_DECK_MAX_SCORE,
    SEA_TEMP_BY_MONTH,
    SEABREEZE_STABLE_MARINE_INSTAB,
    CU_ALLOWANCE,
    CIRRUS_BANK_LIGHT,
    CIRRUS_BANK_HEAVY,
    THERMAL_TOP_WEAK_AGL_M,
    THERMAL_TOP_WEAK_MAX_SCORE,
    THERMAL_TOP_STRONG_AGL_M,
    THERMAL_TOP_STRONG_BONUS,
    THERMAL_TOP_CAP_MIN_SW,
    MEMORY_FACTOR_COLD_BONUS,
    MEMORY_FACTOR_MAX,
)
from termik.scoring import (
    score_lapse_rate,
    score_surface_lapse_rate,
    score_spread,
    score_gusts,
    score_temperature,
    score_precipitation,
    calculate_wind_shear_modifier,
    calculate_bl_mixing_modifier,
    calculate_modifiers,
    cloud_deck_arrived,
    get_score_label,
)

# Koldluftsadvektion regnes fra samme tærskel som v1's destabiliserings-bonus
# i calculate_modifiers: 850 hPa faldet mindst 1 grad på 3 timer.
COLD_ADVECTION_TREND = -1.0


def score_wind_v2(wind_kt: float, cold_advection: bool = False) -> int:
    """Punkt 1: 5-10 kt er "den absolut mest ideelle" vind (s. 13, 28).

    10-20 kt giver kortere boble-levetid, over 20 kt meget kort. Ved
    koldluftsadvektion mildnes 15-25 kt: hæftet nævner skygader og rimeligt
    svæveflyvevejr på bagsiden af en koldfront (s. 29).
    """
    if 5 <= wind_kt <= 10:
        return 10
    elif 10 < wind_kt <= 15:
        return 8
    elif 3 <= wind_kt < 5:
        return 7
    elif 15 < wind_kt <= 20:
        return 7 if cold_advection else 5
    elif 20 < wind_kt <= 25:
        return 5 if cold_advection else 3
    elif 0 < wind_kt < 3:
        return 4
    elif wind_kt == 0:
        return 3
    elif 25 < wind_kt <= 35:
        return 2
    else:
        return 0


def score_solar_v2(
    cloud_cover: float,
    shortwave_radiation: float,
    cloud_cover_low: float | None = None,
    cloud_cover_mid: float | None = None,
    cloud_cover_high: float | None = None,
    direct_radiation: float | None = None,
) -> float:
    """Punkt 2: lav cumulus i hæftets optimale mængde koster ikke solscore.

    Skema 1 peaker ved 3-4/8, og "det optimale skybillede er små, men relativt
    mange cumulusskyer og ingen skyer ovenover" (s. 21). De første
    CU_ALLOWANCE procentpoint lav sky er derfor gratis; er den lave sky i
    stedet stratus, fanger direct_radiation-leddet dæmpningen alligevel.
    Mellem- og højsky vægtes som i v1.
    """
    if cloud_cover_low is None or cloud_cover_mid is None or cloud_cover_high is None:
        effective = cloud_cover
    else:
        effective = min(
            100.0,
            max(0.0, cloud_cover_low - CU_ALLOWANCE) * 1.0
            + cloud_cover_mid * 0.7
            + cloud_cover_high * 0.5,
        )
    cloud_factor = max(0.0, (100 - effective) / 100)

    if direct_radiation is not None:
        radiation_factor = min(direct_radiation / 600, 1.0)
    else:
        radiation_factor = min(shortwave_radiation / 800, 1.0)
    return (cloud_factor * 0.4 + radiation_factor * 0.6) * 10


def cirrus_penalty_v2(cloud_cover_high: float | None) -> float:
    """Punkt 3: allerede banker af cirrus svækker termikken op til 1 m/s.

    Gradueret fradrag (s. 20) i intervallet under CIRRUS_SHIELD_THRESHOLD,
    hvor v1 lod cirrus være næsten gratis. Det hårde skjolds-cap ved >= 85 %
    er uændret og tager over derover.
    """
    if cloud_cover_high is None:
        return 0.0
    if cloud_cover_high >= CIRRUS_BANK_HEAVY:
        return -1.0
    if cloud_cover_high >= CIRRUS_BANK_LIGHT:
        return -0.5
    return 0.0


def calculate_seabreeze_penalty_v2(
    coast_distance_km: float,
    coast_direction_deg: float,
    wind_dir: float,
    wind_speed_kt: float,
    temp_2m: float,
    month: int,
    temp_850hpa: float | None = None,
) -> float:
    """Punkt 5: søbrisens styrke følger land/hav-forskellen og vinden.

    Hæftet (s. 22-23): søbriser dannes ved svage vinde, stor solindstråling og
    stor temperaturforskel mellem land og vand, værst april-juni. Generel
    pålandsvind flytter fronten hurtigere og dybere ind i landet; kraftig
    fralandsvind holder den ude. v1 gav pålandsvind fast risiko 3 året rundt;
    her skaleres drivkraften med den faktiske forskel, så en kølig
    sensommerdag med lunt hav slipper billigere.

    Punkt 5b: pålandsvind >= 8 kt med STABIL havluft (havtemp minus 850-temp
    under SEABREEZE_STABLE_MARINE_INSTAB) løfter drivkraften til maksimum
    uanset land/hav-diff: den tilførte marine luft skal så genopvarmes og
    destabiliseres over land. Er havluften derimod konvektiv (kold luftmasse
    over varmt hav), bærer pålandsvinden termik med ind: kryds-plads-studiet
    målte 8/8 bar-dage i påland med lille diff, alle med instab >= 12.
    Diff <= 2 forbliver straffri: alle målte dage i det hjørne var
    konvektive, og et ustraffet ukendt hjørne er bedre end et udokumenteret
    straffet.
    """
    if coast_distance_km >= 80:
        return 0

    sea_temp = SEA_TEMP_BY_MONTH[month]
    land_sea_diff = temp_2m - sea_temp
    if land_sea_diff <= 2:
        return 0

    angle_diff = abs(wind_dir - coast_direction_deg)
    if angle_diff > 180:
        angle_diff = 360 - angle_diff
    is_onshore = angle_diff < 90

    if not is_onshore and wind_speed_kt > 15:
        return 0

    if land_sea_diff > 8:
        drive = 2.0
    elif land_sea_diff > 4:
        drive = 1.0
    else:
        drive = 0.5

    if (
        is_onshore
        and wind_speed_kt >= 8
        and temp_850hpa is not None
        and sea_temp - temp_850hpa < SEABREEZE_STABLE_MARINE_INSTAB
    ):
        drive = 2.0

    if is_onshore:
        risk = min(3.0, drive + 1.0)
    elif wind_speed_kt < 8:
        risk = drive
    else:
        risk = drive * 0.5

    distance_factor = max(0, 1 - coast_distance_km / 80)
    return round(risk * distance_factor, 1)


def memory_factor_v2(temp_850hpa_trend: float) -> float:
    """Punkt 6: koldluftsadvektion forlænger varmehukommelsen.

    I koldluftsadvektion holder termikken længere efter peak-opvarmning
    (s. 14). Den spejlvendte varme-malus er bevidst udeladt: referencedagen
    2026-08-08 havde trend +1.0 kl. 18 mens piloten fløj, og en lavere faktor
    capper netop de timer hukommelsen er kalibreret til at redde. Se noten
    ved MEMORY_FACTOR_COLD_BONUS i config.
    """
    if temp_850hpa_trend <= -1.0:
        return min(MEMORY_FACTOR_MAX, RADIATION_MEMORY_FACTOR + MEMORY_FACTOR_COLD_BONUS)
    return RADIATION_MEMORY_FACTOR


def effective_radiation_v2(
    current: float,
    trailing: list[float] | None = None,
    cloud_cover: float | None = None,
    trailing_cloud_cover: list[float] | None = None,
    temp_850hpa_trend: float = 0.0,
) -> float:
    """Som v1's effective_radiation, men med luftmasse-skaleret faktor.

    Gulv og deck-arrival-blokering er uændrede; kun hvor meget af det seneste
    stråleniveau der krediteres afhænger nu af 850 hPa-trenden.
    """
    if not trailing or current < RADIATION_MEMORY_FLOOR:
        return current
    if cloud_deck_arrived(cloud_cover, trailing_cloud_cover):
        return current
    return max(current, memory_factor_v2(temp_850hpa_trend) * max(trailing))


def thermal_top_adjustment_v2(
    thermal_base_agl_m: float | None,
    limited_by: str | None,
    shortwave_radiation: float | None = None,
) -> tuple[float, int | None]:
    """Punkt 4: kobl scoren til termikkens basehøjde.

    Skema 1 og svæveflyveudsigtens bånd (s. 41): under 600 m base er
    termikken svag uanset alt andet, over 1200 m er den typisk kraftig.
    Returnerer (bonus, cap); cap=None betyder intet loft.

    Båndene testes mod den UKORRIGEREDE base, min(LCL, TI-nul) AGL, aldrig
    mod den Hcrit-korrigerede thermal_top: Skema 1's rækker er basehøjder,
    og margin-fradraget fik cappet til at ramme dage med reel base op til
    ~850 m (Sæby 2026-07-26: LCL 664 m, korrigeret 408 m, flyvninger på
    169/134 min i de cappede timer).

    Cappet gælder kun mens solen driver konvektionen (SW >= 400 W/m²): om
    aftenen kollapser parcel-toppen pr. definition, men varmehukommelsen
    holder termikken i live, målt 2026-08-08 kl. 18-19.

    Cappet kræver desuden at parcel-beregningen POSITIVT har fundet en lav
    base ("lcl" eller "ti_zero"). En "inversion"-dom fra de grove
    trykniveauer må ikke cappe alene: overfladelaget måles direkte i
    2m->180m (surface-lapse-dealbreakeren), og den grove profil kan melde
    inversion hen over et superadiabatisk målt overfladelag.
    """
    if thermal_base_agl_m is None or limited_by in ("no_data", "no_dewpoint"):
        return 0.0, None
    if thermal_base_agl_m > THERMAL_TOP_STRONG_AGL_M:
        return THERMAL_TOP_STRONG_BONUS, None
    if (
        thermal_base_agl_m < THERMAL_TOP_WEAK_AGL_M
        and limited_by in ("lcl", "ti_zero")
        and shortwave_radiation is not None
        and shortwave_radiation >= THERMAL_TOP_CAP_MIN_SW
    ):
        return 0.0, THERMAL_TOP_WEAK_MAX_SCORE
    return 0.0, None


def apply_dealbreakers_v2(
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
    trailing_radiation: list[float] | None = None,
    trailing_cloud_cover: list[float] | None = None,
    boundary_layer_height: float | None = None,
    cloud_cover_low: float | None = None,
    cloud_cover_mid: float | None = None,
    cloud_cover_high: float | None = None,
    trailing_cirrus: list[float] | None = None,
    temp_850hpa_trend: float = 0.0,
    thermal_top_cap: int | None = None,
) -> float:
    """v1's hårde caps plus termiktop-loftet og den skalerede varmehukommelse.

    Forket fra scoring.apply_dealbreakers med to ændringer: strålings-gaten
    tester mod effective_radiation_v2 (punkt 6), og punkt 4's cap på lav
    termiktop anvendes til sidst. Alle kalibrerede tærskler er identiske
    med v1's.
    """
    max_score = 10.0
    if shortwave_radiation is not None:
        eff = effective_radiation_v2(
            shortwave_radiation,
            trailing_radiation,
            cloud_cover=cloud_cover,
            trailing_cloud_cover=trailing_cloud_cover,
            temp_850hpa_trend=temp_850hpa_trend,
        )
        for threshold, cap in RADIATION_GATE:
            if eff < threshold:
                max_score = min(max_score, cap)
    if (
        boundary_layer_height is not None
        and boundary_layer_height < SHALLOW_BOUNDARY_LAYER_M
    ):
        max_score = min(max_score, SHALLOW_BOUNDARY_LAYER_MAX_SCORE)
    if lapse_rate < 0.50:
        max_score = min(max_score, 1)
    elif lapse_rate < 0.65:
        max_score = min(max_score, 3)
    elif lapse_rate < 0.70:
        max_score = min(max_score, 5)
    if surface_lapse_rate is not None:
        if surface_lapse_rate < 0.3:
            max_score = min(max_score, 1)
        elif surface_lapse_rate < 0.5:
            max_score = min(max_score, 2)
    if cloud_cover >= 87:
        max_score = min(max_score, 2)
    if cloud_cover_high is not None and cloud_cover_high >= CIRRUS_SHIELD_PRESENT_MIN:
        shield = max([cloud_cover_high] + list(trailing_cirrus or []))
        if shield >= CIRRUS_SHIELD_THRESHOLD:
            max_score = min(max_score, CIRRUS_SHIELD_MAX_SCORE)
    if (
        cloud_cover_mid is not None
        and cloud_cover_mid >= MID_LEVEL_DECK_THRESHOLD
    ):
        max_score = min(max_score, MID_LEVEL_DECK_MAX_SCORE)
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
    if cape > 1500:
        max_score = min(max_score, 5)
    elif cape > 1000:
        max_score = min(max_score, 7)
    if thermal_top_cap is not None:
        max_score = min(max_score, thermal_top_cap)
    return min(score, max_score)


def compute_thermal_score_v2(
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
    temp_180m: float | None = None,
    wind_speed_80m_kt: float | None = None,
    wind_speed_180m_kt: float | None = None,
    boundary_layer_height: float | None = None,
    cloud_cover_low: float | None = None,
    cloud_cover_mid: float | None = None,
    cloud_cover_high: float | None = None,
    direct_radiation: float | None = None,
    trailing_radiation: list[float] | None = None,
    trailing_cloud_cover: list[float] | None = None,
    trailing_cirrus: list[float] | None = None,
    thermal_base_agl_m: float | None = None,
    thermal_top_limited_by: str | None = None,
) -> dict:
    """Den samlede v2-score. Samme signatur og resultatform som v1 plus
    termiktoppen (punkt 4), så fetch_weather kan bruge de to i flæng.
    """
    spread = temp_2m - dewpoint_2m
    lapse_rate = (temp_2m - temp_850hpa) / 15.0
    skybase_m = round(spread * 125)
    skybase_ft = round(skybase_m * 3.281)

    surface_lapse = None
    if temp_180m is not None:
        surface_lapse = (temp_2m - temp_180m) / 1.78

    cold_advection = temp_850hpa_trend <= COLD_ADVECTION_TREND

    scores = {
        "lapse_rate": score_lapse_rate(lapse_rate),
        "solar": score_solar_v2(
            cloud_cover,
            shortwave_radiation,
            cloud_cover_low=cloud_cover_low,
            cloud_cover_mid=cloud_cover_mid,
            cloud_cover_high=cloud_cover_high,
            direct_radiation=direct_radiation,
        ),
        "spread": score_spread(spread),
        "wind": score_wind_v2(wind_speed_kt, cold_advection=cold_advection),
        "gusts": score_gusts(wind_gusts_kt, wind_speed_kt),
        "temperature": score_temperature(temp_2m),
        "precipitation": score_precipitation(precipitation, precip_last_6h),
    }

    weighted = sum(scores[k] * WEIGHTS_V2[k] for k in WEIGHTS_V2)
    total = weighted * 10 / sum(w * 10 for w in WEIGHTS_V2.values())

    total += calculate_modifiers(cape, pressure_trend, temp_850hpa_trend)

    cirrus_penalty = cirrus_penalty_v2(cloud_cover_high)
    total += cirrus_penalty

    seabreeze_penalty = calculate_seabreeze_penalty_v2(
        coast_distance_km, coast_direction_deg,
        wind_dir, wind_speed_kt, temp_2m, month,
        temp_850hpa=temp_850hpa,
    )
    total -= seabreeze_penalty

    wind_shear_mod = 0.0
    bl_mixing_mod = 0.0
    if wind_speed_80m_kt is not None:
        wind_shear_mod = calculate_wind_shear_modifier(wind_speed_kt, wind_speed_80m_kt)
        total += wind_shear_mod
    if wind_speed_80m_kt is not None and wind_speed_180m_kt is not None:
        bl_mixing_mod = calculate_bl_mixing_modifier(wind_speed_80m_kt, wind_speed_180m_kt)
        total += bl_mixing_mod

    top_bonus, top_cap = thermal_top_adjustment_v2(
        thermal_base_agl_m, thermal_top_limited_by, shortwave_radiation
    )
    total += top_bonus

    total = apply_dealbreakers_v2(
        total, lapse_rate, cloud_cover, precipitation,
        wind_speed_kt, wind_gusts_kt, temp_2m,
        cape=cape,
        surface_lapse_rate=surface_lapse,
        shortwave_radiation=shortwave_radiation,
        trailing_radiation=trailing_radiation,
        trailing_cloud_cover=trailing_cloud_cover,
        boundary_layer_height=boundary_layer_height,
        cloud_cover_low=cloud_cover_low,
        cloud_cover_mid=cloud_cover_mid,
        cloud_cover_high=cloud_cover_high,
        trailing_cirrus=trailing_cirrus,
        temp_850hpa_trend=temp_850hpa_trend,
        thermal_top_cap=top_cap,
    )

    total = round(max(0, min(10, total)), 1)

    result = {
        "version": "v2",
        "score": total,
        "label": get_score_label(total),
        "spread": round(spread, 1),
        "skybase_m": skybase_m,
        "skybase_ft": skybase_ft,
        "lapse_rate": round(lapse_rate, 2),
        "seabreeze_penalty": seabreeze_penalty,
        "cirrus_penalty": cirrus_penalty,
        "thermal_top_bonus": top_bonus,
    }
    if surface_lapse is not None:
        result["surface_lapse_rate"] = round(surface_lapse, 2)
    if wind_speed_80m_kt is not None:
        result["wind_shear_modifier"] = wind_shear_mod
    if wind_speed_80m_kt is not None and wind_speed_180m_kt is not None:
        result["bl_mixing_modifier"] = bl_mixing_mod
    if boundary_layer_height is not None:
        result["boundary_layer_height"] = round(boundary_layer_height)

    return result
