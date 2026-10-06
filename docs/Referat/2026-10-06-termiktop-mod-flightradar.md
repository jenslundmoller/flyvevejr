# Termik-tophøjden mod flyvninger fra FlightRadar

Dato: 2026-10-06. Data: FlightRadars `thermals`-tabel (read-only kopi af
prod-databasen på OMV), 19/5-4/10 2026. Scripts i
[analysemappen](2026-10-06-analyse/README.md).

## Spørgsmålet

Ligger den publicerede termik-tophøjde (`thermal_top_m`) i det rigtige
område? Mod TopMeteo 4/10 så den ud til at være cirka halvdelen af det
der blev fløjet.

## Metode

- FlightRadar registrerer hver termikboble med tid, position og højden
  piloten forlod boblen i (`end_alt`, MSL, GPS-baseret fra OGN/FLARM).
  27.506 bobler, 111 dage.
- Hver boble knyttes til nærmeste flyveplads inden for 20 km og til den
  lokale time den sluttede i, kl. 10-18. Kun timer med mindst 3 bobler fra
  mindst 2 flyvninger: **1.612 plads-timer, 541 plads-dage, 89 dage**.
- Observeret top = 90 %-fraktilen af `end_alt` i timen.
- Modellen: timedata fra historical-forecast for 26 flyvepladser,
  18/5-4/10, gennem `process_point_hour` (produktionsstien). Både
  `thermal_top_m` og rå base, min(LCL, TI-nul), er MSL som `end_alt`, så
  der sammenlignes direkte; højder over terræn er minus pladsens
  `elevation_m`.
- 25 timer med dommen "inversion" (top 0) er holdt ude af
  margin-sammenligningen, se fund 4.

## Fund

**1. Hele sæsonen: rigtigt område, men toppen ligger for lavt.**

| | Observeret (median, AGL) | Publiceret top | Afv. | Rå base | Afv. |
|---|---|---|---|---|---|
| Hele sæsonen | 1110 m | 1012 m | -117 | 1234 m | +108 |
| Maj-august | 1040-1240 m | | -60 til -112 | | +92 til +151 |
| September | 914 m | 600 m | **-323** | 862 m | -63 |
| 3.-4. oktober | 754 m | 405 m | **-396** | 761 m | -66 |

Korrelation 0.70. Om sommeren ligger den rå base 100-150 m over hvor
piloterne forlader boblen, hvilket er forventeligt. Om efteråret ligger
den publicerede top 300-400 m under.

**2. Luftrumslofter på Sjælland.** Piloterne må forlade boblen ved dagens
loft, typisk ~750 m og ~1400 m (oplyst af brugeren). Sjællands
`end_alt`-fordeling topper ved 700-800 m og har et knæk efter 1450-1500 m
(GPS mod QNH); Jyllands er glat op til 2000 m. 128 af 445 sjællandske timer
har 90 %-fraktilen ved 700-820 eller 1380-1520 m. De timer er censurerede
("mindst så højt"), og selv uden dem ser prognosen 100-200 m for høj ud på
Sjælland, sandsynligvis andre lofter eller pilotmargin. **Jylland og Fyn
(1.142 timer) er referencen.** Sjælland kan ikke kalibrere toppen uden
dagens loft.

**3. Margin-fradraget er for stort og ikke sæsonskaleret.**
`_hcrit_margin` trækker 200 m fra i fuld sol og op til 500 m uden sol, med
fuld sol = 600 W/m² (absolut, sat om sommeren). I september-oktober når
strålingen sjældent 600, så fradraget er næsten altid 300-450 m. Samme
fejltype som strålingstærsklerne i fix 2 (Referat 2026-10-05).

Varianter, timer uden loft (afvigelse / gennemsnitlig fejl i m):

| Margin | Jylland+Fyn | Alle uden loft | Maj-aug | Sep-okt |
|---|---|---|---|---|
| Nuværende 200-500, fuld sol 600 | -152 / 232 | -122 / 228 | -99 / 216 | -340 / 333 |
| **100-300, fuld sol 600 x sæsonfaktor** | **-43 / 191** | -9 / 197 | +8 / 198 | -170 / 189 |
| Fast 100 | -26 / 182 | +2 / 191 | +23 / 192 | -150 / 173 |
| Fast 150 | -76 / 192 | -48 / 195 | -27 / 193 | -200 / 210 |
| Intet fradrag | +74 / 191 | +102 / 208 | +123 / 218 | -50 / 122 |

I de 128 loft-timer ligger den nuværende top under loftet i 40 % af
timerne (sikkert for lavt, piloterne nåede mindst loftet); med 100-300
sæsonskaleret 25 %.

**4. "Inversion"-dommen er forkert i 25 timer.** Toppen vises som 0 m, men
piloterne nåede median 644 m AGL (11 dage, mest september-oktober).

**5. Om efteråret er selve den rå base ~150 m for lav.** Selv uden
fradrag ligger september-oktober 50 m under det fløjne, hvor sommeren
ligger 130 m over. Noget i LCL/TI-nul reagerer på årstiden (måske 2 m-
dugpunktet). Hviler på ~10 efterårsdage.

## Implementeret

Margin 100 m i fuld sol til 300 m uden sol (v2), fuld sol = 600 W/m²
ganget med strålingens sæsonfaktor (samme `radiation_season_factor` som
fix 2): `hcrit_margin_v2` i `scoring_v2.py`, konstanterne
`HCRIT_V2_*` i config, og `compute_thermal_top` tager et `margin_m` fra
kalderen. v1 er urørt. Ændrer kun den viste top og kommentarteksten:
scoren bruger den rå base (punkt 4 i v2), og `margin_collapse` er uændret
fordi fradraget allerede er klampet til halvdelen af den rå højde.

Kontrol på de 1.612 timer med produktionskoden: scoren er uændret i alle
timer, og `thermal_top_limited_by` ligeså. Jylland og Fyn (1.142 timer):
afvigelse -152 -> -43 m, gennemsnitlig fejl 232 -> 191 m; september-
oktober (104 timer) -379 -> -212 m, fejl 368 -> 209 m.

Valgt frem for fast 100 m (lidt lavere fejl) fordi den beholder den
fysiske idé: svagere sol giver svagere termik og større afstand til
toppen. Forskellen er under 10 m i gennemsnitlig fejl.

## Forbehold

- 90 %-fraktilen af hvor piloter forlader boblen er én definition af
  toppen. Piloter forlader ofte før toppen, så den reelle top ligger
  snarere højere end lavere.
- GPS-højde fra FLARM/OGN kan afvige op til ~40 m fra MSL.
- Historical-forecast er ikke præcis det publicerede.
- 20 km-radius blander pladsens terræn med omegnens; Danmark er fladt
  nok til at det er under 50 m de fleste steder.

## Åbne punkter

1. Efterårets lave rå base (fund 5): saml flere efterårsdage og se på
   dugpunktet.
2. Den falske "inversion"-dom (fund 4): 25 timer hvor der blev fløjet til
   ~640 m AGL.
3. Sjælland: hvis dagens loft kan registreres (FlightRadar eller
   klubberne), kan Sjælland indgå som censurerede data.
