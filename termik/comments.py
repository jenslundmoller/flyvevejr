"""Generate Danish-language thermal forecast comments for glider pilots."""


def generate_comment(
    lapse_rate: float,
    spread: float,
    skybase_m: int,
    wind_kt: float,
    wind_gusts_kt: float,
    cloud_cover: float,
    cape: float,
    precipitation: float,
    seabreeze_risk: float,
    pressure_trend: float,
    score: float,
) -> str:
    """Build a 2-3 sentence Danish comment explaining the thermal forecast.

    Always starts with a stability assessment, then appends the 1-2 most
    relevant additional observations. Targets max ~200 characters total.
    """
    parts: list[str] = []

    # 1. Stability line (always included)
    if lapse_rate < 0.50:
        stability = "Inversion \u2014 ingen termik."
    elif lapse_rate < 0.65:
        stability = "Stabil atmosf\u00e6re \u2014 meget begr\u00e6nset termik."
    elif lapse_rate < 0.80:
        stability = "Svagt labil \u2014 begr\u00e6nset termikh\u00f8jde."
    elif lapse_rate < 1.0:
        stability = "Betinget labil \u2014 moderat termikh\u00f8jde."
    elif lapse_rate < 1.2:
        stability = "Labil atmosf\u00e6re \u2014 god konvektion."
    else:
        stability = "Meget labil atmosf\u00e6re \u2014 kraftig konvektion."
    parts.append(stability)

    # 2. Collect candidate additional lines in priority order.
    #    "Kill" conditions first, then warnings, then informational.
    extras: list[str] = []

    # Rain kill (highest priority -- negates everything)
    if precipitation > 0:
        extras.append("Aktiv nedb\u00f8r \u2014 ingen termik.")

    # Overcast kill
    if cloud_cover >= 80:
        extras.append("Overskyet \u2014 solinstr\u00e5ling blokeret.")

    # Sea breeze warning
    if seabreeze_risk >= 2:
        extras.append("H\u00f8j s\u00f8brise-risiko \u2014 termik d\u00f8r tidligt.")
    elif seabreeze_risk >= 1:
        extras.append("S\u00f8brise-risiko om eftermiddagen.")

    # Effective wind rule: wind + (gust/2)
    effective_wind = wind_kt + (wind_gusts_kt / 2)
    gust_factor = wind_gusts_kt / max(wind_kt, 1)
    if wind_gusts_kt > 40:
        extras.append("Vindst\u00f8d over 40 kt \u2014 farligt, kan ikke flyves.")
    elif effective_wind > 30:
        extras.append(f"Effektiv vind {int(effective_wind)} kt (vind+gust/2) \u2014 kun meget erfarne piloter.")
    elif effective_wind > 25:
        extras.append(f"Effektiv vind {int(effective_wind)} kt (vind+gust/2) \u2014 nedsat flyvevejr.")
    elif gust_factor >= 2.0 and wind_gusts_kt > 15:
        extras.append(f"B\u00f8jet vind (faktor {gust_factor:.1f}) \u2014 turbulent.")

    # Strong wind warning
    if wind_kt > 20 and wind_gusts_kt <= 25:
        extras.append("Kraftig vind \u2014 turbulent termik.")

    # Overdevelopment warning
    if cape > 1000:
        extras.append("Risiko for overudvikling (Cb).")

    # Backside weather (good sign)
    if pressure_trend > 1.5 and lapse_rate >= 0.8:
        extras.append("Bagsidevejr \u2014 klar luft og gode cumulus.")

    # Dry thermal
    if spread > 20:
        extras.append("T\u00f8rtermik \u2014 kondensationsniveau n\u00e5s ikke.")

    # Skybase (informational, only when conditions are decent)
    if score >= 3 and 3 <= spread <= 20:
        skybase_ft = round(spread * 400)
        extras.append(f"Skybase ca. {skybase_m}m ({skybase_ft} ft).")

    # Low spread warning
    if 3 <= spread < 5 and lapse_rate >= 0.65:
        extras.append("Risiko for udkagning pga. lav spread.")

    # Pick up to 2 extras, staying within ~200 chars total
    max_extras = 2
    for line in extras:
        if max_extras <= 0:
            break
        candidate = " ".join(parts + [line])
        if len(candidate) <= 200 or len(parts) == 1:
            # Always allow at least one extra even if slightly over 200
            parts.append(line)
            max_extras -= 1

    return " ".join(parts)
