# Referat — Cirrus-vægtning og direkte stråling i `score_solar`

**Dato:** 2026-05-24
**Branch:** main
**Commit:** `908a3fc`

## Udgangspunkt

Pilot fra Midtsjællands Svæveflyveklub (Slaglille) rapporterede, at termikken 23. maj 2026 var meget dårligere end forecasten lovede. Forecasten gav **5.9/10 ("Moderat termik")** kl. 17:00, men de erfarne piloter på pladsen tilskrev den svage termik **cirrus-skyer**, der ødelagde indstrålingen. Spørgsmål: tager scoringen overhovedet højde for cirrus?

## Diagnose

### Kort svar
Nej. `score_solar` brugte kun samlet `cloud_cover` (`scoring.py:46-53`), så 90 % cirrus blev behandlet identisk med 90 % stratus. `cloud_cover_low/mid/high` blev hentet fra Open-Meteo, men ikke brugt nogen steder.

### Reanalyse af 23. maj for Slaglille
Hentede både forecast og ERA5-arkiv via Open-Meteo:

| Tid | cc_low | cc_mid | **cc_HIGH** | SW W/m² | Direkte | Diffus | Direkte-andel |
|-----|--------|--------|-------------|---------|---------|--------|---------------|
| 11  | 0 | 0 | **7** | 655 | 466 | 189 | 71 % |
| 12  | 0 | 6 | **77** | 732 | 521 | 211 | 71 % |
| 13  | 0 | 16 | **93** | 735 | 488 | 247 | 66 % |
| 14  | 1 | 5 | **98** | 605 | 298 | 307 | **49 %** |
| 15  | 2 | 30 | **81** | 543 | 243 | 300 | **45 %** |
| 16  | 5 | 52 | **6** | 519 | 257 | 262 | 50 % |
| 17  | 8 | 5 | **0** | 522 | 323 | 199 | 62 % |

Cirrus-skjoldet ramte præcis prime time (peak 98 % kl. 14). Den afgørende observation: **total SW faldt kun 18 % (732 -> 605), men direkte stråling faldt 43 % (521 -> 298)**, og diffus-andelen steg fra 29 % til 51 %. Det er den direkte/diffus-fordeling, der driver differentiel jordopvarmning, og dermed termik-triggering, ikke den samlede stråling.

## Hard research på cirrus-effekt

Bekræftet via fagligt grundlag at piloterne har ret:
- Cirrus-skyer reducerer kortbølget stråling med gennemsnitligt **-120 W/m² pr. enhed optisk tykkelse** (range -80 til -140), ScienceDirect / Copernicus ACP.
- Cirrus virker dobbelt skadeligt for termik: (a) direkte dæmpning af sollys, (b) konvertering af direkte til diffus stråling, der spreder varmen jævnt og kvæler den differentielle opvarmning.
- XC Skies anerkender effekten: cirrus kan variere fra ubetydelig (tynd cirrus, optisk dybde < 0.1) til ødelæggende (cirrostratus, optisk dybde > 1.5).
- Vejrmodeller (ICON/GFS via Open-Meteo) under-estimerer ofte cirrus-attenuation i SW-feltet, men `direct_radiation`-feltet fanger effekten bedre, fordi cirrus' diffuse-omdannelse er meget tydelig der.

Kilder:
- [Effects of cirrus cloudiness on solar irradiance in four spectral bands](https://www.sciencedirect.com/science/article/abs/pii/S0169809511003000)
- [Cirrus-induced shortwave radiative effects](https://www.sciencedirect.com/science/article/abs/pii/S0169809519316758)
- [Long Term Analysis of Cirrus Clouds' Effects on Shortwave Radiation](https://www.researchgate.net/publication/259220218)
- [XC Skies layer documentation](https://docs.xcskies.com/home/documentation/xc-skies-layers)

## Løsningsvalg

Brugeren valgte at kombinere **både** vægtning af skylag **og** brug af direkte stråling, for at fange begge sider af cirrus-effekten.

## Implementering

### 1. Henter `direct_radiation` fra API (`termik/config.py:34`)
Tilføjet til `HOURLY_PARAMS`.

### 2. Ny signatur til `score_solar` (`termik/scoring.py:46-86`)

```python
def score_solar(
    cloud_cover, shortwave_radiation,
    cloud_cover_low=None, cloud_cover_mid=None, cloud_cover_high=None,
    direct_radiation=None,
):
    if all_layers_present:
        effective_cloud = min(100, low*1.0 + mid*0.7 + high*0.5)
    else:
        effective_cloud = cloud_cover
    cloud_factor = max(0, (100 - effective_cloud) / 100)

    if direct_radiation is not None:
        radiation_factor = min(direct_radiation / 600, 1.0)
    else:
        radiation_factor = min(shortwave_radiation / 800, 1.0)
    return (cloud_factor * 0.4 + radiation_factor * 0.6) * 10
```

**Designvalg:**
- Vægtning **low=1.0, mid=0.7, high=0.5** afspejler at cirrus dæmper ca. halvt så meget per % skydække som lav stratus. Mellem-skyer (altostratus) ligger imellem.
- **Direkte stråling normaliseres til 600 W/m²** for fuld score (peak DK sommer ~700). Direkte stråling indfanger cirrus' diffuse-effekt automatisk.
- **Bagudkompatibel:** 2-argument-kald virker stadig (fallback til gammel formel), så eksisterende tests og evt. andre callers ikke knækker.

### 3. Plumbing (`termik/scoring.py:309-339`, `termik/fetch_weather.py:119-126,217-225`)
`compute_thermal_score` og `process_point_hour` videresender de nye værdier.

## Verifikation

### Slaglille 23. maj (det dårlige tilfælde)

| Tid | cirrus | Gammel solar | Ny solar | Diff |
|-----|--------|--------------|----------|------|
| 11  | 7%   | 7.43 | 8.52 | **+1.09** |
| 12  | 77%  | 8.25 | 7.50 | **-0.75** |
| 13  | 93%  | 7.55 | 6.57 | **-0.98** |
| 14  | 98%  | 5.02 | 4.84 | -0.18 |
| 15  | 81%  | 4.43 | 3.89 | -0.54 |
| 16  | 6%   | 4.37 | 4.79 | +0.42 |
| 17  | 0%   | 5.43 | 6.77 | **+1.34** |
| 18  | 0%   | 4.38 | 6.15 | **+1.77** |

Cirrus-tunge midt-på-dagen-timer trækkes ned, klare aftener får retfærdig kredit (de blev før uretmæssigt straffet, fordi total cloud_cover inkluderede cirrus).

### Effekt på totalscoren afhænger af om andre dealbreakers låser
Solar vejer kun 20 %, så +1 i solar = +0.2 i totalscore. Dealbreakers (især lapse rate < 0.65 -> max 3) kan låse scoren før solar-ændringen rykker noget. Effekten af cirrus-fixet ses tydeligst på dage med (a) meget cirrus og (b) ingen andre låsende faktorer.

## Tests

Tre nye tests i `termik/tests/test_scoring.py:88-115`:
- `test_solar_cirrus_shield_penalised_when_total_cloud_low` — fanger 23. maj kl. 13-scenariet.
- `test_solar_thin_cirrus_only_minor_penalty` — sikrer at vi ikke overstraffer tynd cirrus.
- `test_solar_thick_low_cloud_heavily_penalised` — sikrer at stratus stadig straffes fuldt.

**Resultat:** alle 158 tests består.

## Commit og deploy

```
908a3fc scoring: weight cirrus separately and use direct radiation in score_solar
```

4 filer ændret, 92 linjer tilføjet. Pushed til main, GitHub Actions `update-forecast.yml` trigget manuelt (run 26357049435), ny data committet som `96150bf` kl. 09:27 UTC, deploy automatisk trigget.

## Opfølgning og åbne emner

- **Cap-fortrængning:** På 23. maj var lapse rate 0.81 (ingen lapse-cap) og scoren landede på 5.9. Med ny formel ville scoren formentlig være faldet til 4.5-5.0 i de cirrus-tunge timer. Hverken UI eller dagbøjle viser hvilken faktor der er begrænsende, kunne være nyttigt at tilføje en "begrænsende faktor"-indikator senere.
- **UI-eksponering:** `cloud_cover_high` og `direct_radiation` plumbes til scoring, men vises ikke i airfield-popup'en. Overvej at vise "Skydække 50% (deraf cirrus 80%)" så piloter selv kan vurdere.
- **Vejrmodel-præcision:** Open-Meteo's `cloud_cover_high` baseres på ICON/GFS, som kan miste tynd cirrus. Hvis dette bliver et tilbagevendende problem, kunne man supplere med satellit-observationer (SEVIRI cloud type), men det er stor ekstra kompleksitet.
