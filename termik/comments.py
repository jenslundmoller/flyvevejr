"""Generate Danish-language thermal forecast comments for glider pilots.

Tekststrukturen følger popup-redesignet (2026-08-26): tal der står i
popup'ens felter og grafik (skybase, blandingslag, spread) gentages ikke i
teksten. I stedet har sætningerne tre faste roller:

1. Den bindende faktor: hvad begrænser termikken lige nu (fra
   thermal_top_limited_by), eller stabiliteten når dagen er død.
2. Op til to advarsler/observationer i prioriteret rækkefølge.

Termikvinduet ("Termik ca. 11 til 19") beregnes i frontenden af
dagsforløbet og hører ikke til her. Ingen tankestreger i teksterne.
"""


def _stability_line(lapse_rate: float) -> str:
    if lapse_rate < 0.50:
        return "Inversion: ingen termik."
    if lapse_rate < 0.65:
        return "Stabil atmosfære: meget begrænset termik."
    if lapse_rate < 0.80:
        return "Svagt labil: begrænset termikhøjde."
    if lapse_rate < 1.0:
        return "Betinget labil: moderat termikhøjde."
    if lapse_rate < 1.2:
        return "Labil atmosfære: god konvektion."
    return "Meget labil atmosfære: kraftig konvektion."


def _binding_line(thermal_top_m: float, limited_by: str) -> str | None:
    """Sætning for den faktor der begrænser toppen, når dagen er brugbar."""
    top = round(thermal_top_m / 50) * 50
    if limited_by == "lcl":
        return f"Toppen begrænses af skybasen, regn med ca. {top} m."
    if limited_by == "ti_zero":
        return f"Toppen begrænses af temperaturen i højden, regn med ca. {top} m."
    if limited_by == "cap":
        return f"Dyb konvektion, regn med mindst {top} m."
    if limited_by in ("weak_solar", "margin_collapse"):
        return f"Svag sol: termikken bærer kun til ca. {top} m."
    if limited_by == "inversion":
        return "Jordinversion: termikken er ikke kommet i gang."
    if limited_by == "saturated":
        return "Luften er mættet: tåge eller lave skyer."
    return None


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
    # Multi-level diagnostics (optional)
    wind_shear_kt: float | None = None,
    boundary_layer_height: float | None = None,
    # Popup-redesignets nye input (optional)
    thermal_top_m: float | None = None,
    thermal_top_limited_by: str | None = None,
    cloud_cover_high: float | None = None,
    wind_speed_180m_kt: float | None = None,
) -> str:
    """Build a 2-3 sentence Danish comment explaining the thermal forecast.

    Leder med den bindende faktor (eller stabiliteten når dagen er død eller
    termiktoppen mangler), og tilføjer de 1-2 vigtigste observationer.
    Sigter mod maks ~210 tegn.
    """
    parts: list[str] = []

    # 1. Ledende sætning
    if precipitation > 0:
        parts.append("Aktiv nedbør: ingen termik.")
    else:
        binding = None
        if score >= 3 and thermal_top_m is not None and thermal_top_limited_by:
            binding = _binding_line(thermal_top_m, thermal_top_limited_by)
        parts.append(binding if binding else _stability_line(lapse_rate))

    # 2. Kandidat-observationer i prioriteret rækkefølge
    extras: list[str] = []

    if precipitation <= 0 and cloud_cover >= 80:
        extras.append("Overskyet: solindstrålingen er blokeret.")

    # Cirrus-banker dæmper solen (hæftet s. 20); kun interessant på
    # brugbare dage, på døde dage er det sky-cappet der taler
    if cloud_cover_high is not None and cloud_cover_high >= 40 and score >= 3:
        extras.append(f"{int(round(cloud_cover_high))} % cirrus dæmper solen.")

    if seabreeze_risk >= 2:
        extras.append("Høj søbrise-risiko: termikken dør tidligt.")
    elif seabreeze_risk >= 1:
        extras.append("Søbrise-risiko om eftermiddagen.")

    effective_wind = wind_kt + (wind_gusts_kt / 2)
    gust_factor = wind_gusts_kt / max(wind_kt, 1)
    if wind_gusts_kt >= 35:
        extras.append(f"Vindstød {int(wind_gusts_kt)} kt: kan ikke flyves.")
    elif wind_gusts_kt >= 30:
        extras.append(f"Vindstød {int(wind_gusts_kt)} kt: kraftig reduktion.")
    elif effective_wind > 30:
        extras.append(f"Effektiv vind {int(effective_wind)} kt: kun meget erfarne piloter.")
    elif effective_wind > 25:
        extras.append(f"Effektiv vind {int(effective_wind)} kt: nedsat flyvevejr.")
    elif gust_factor >= 2.0 and wind_gusts_kt > 15:
        extras.append(f"Bøjet vind (faktor {gust_factor:.1f}): turbulent.")

    if wind_kt > 20 and wind_gusts_kt <= 25:
        extras.append("Kraftig vind: turbulent termik.")

    # Vinden øger i højden: afdrift og tiltede bobler
    if (
        wind_speed_180m_kt is not None
        and wind_speed_180m_kt - wind_kt >= 3
        and wind_speed_180m_kt >= 12
        and score >= 3
    ):
        extras.append(f"Vinden øger til {int(round(wind_speed_180m_kt))} kt i højden.")

    if cape > 1000:
        extras.append("Risiko for overudvikling (Cb).")

    if pressure_trend > 1.5 and lapse_rate >= 0.8:
        extras.append("Bagsidevejr: klar luft og gode cumulus.")

    if spread > 20:
        extras.append("Tørtermik: ingen cumulus at navigere efter.")

    if 3 <= spread < 5 and lapse_rate >= 0.65 and score >= 3:
        extras.append("Risiko for udkagning pga. lav spread.")

    if wind_shear_kt is not None and wind_shear_kt > 15:
        extras.append(f"Kraftig vindforskydning ({int(wind_shear_kt)} kt): brudt termik.")
    elif wind_shear_kt is not None and wind_shear_kt > 12:
        extras.append("Moderat vindforskydning: termik kan være tiltet.")

    # 3. Op til 2 ekstra sætninger inden for ~210 tegn
    max_extras = 2
    for line in extras:
        if max_extras <= 0:
            break
        candidate = " ".join(parts + [line])
        if len(candidate) <= 210 or len(parts) == 1:
            parts.append(line)
            max_extras -= 1

    return " ".join(parts)
