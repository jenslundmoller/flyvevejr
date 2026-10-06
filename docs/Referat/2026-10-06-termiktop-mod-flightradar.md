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

**5. Det er ikke efteråret der er for lavt, men sommeren der er for højt.**
Schleswig-sonden (10035) kl. 12 UTC på alle 89 flyvedage mod modellen i
samme punkt (historical-forecast). Sondens LCL er beregnet for
blandingslaget (middel af theta og blandingsforhold i de nederste 500 m),
som er det cumulus faktisk danner base fra:

| | 2 m-temp model-sonde | 2 m-dugpunkt model-sonde | Model-LCL minus sondens |
|---|---|---|---|
| Juni-august (68 dage) | +0.9 | -0.7 | **+133 m** |
| September-oktober (11 dage) | +0.2 | -0.2 | -12 m |

Fejlen følger strålingen (korrelation 0.43 med absolut SW, 0.38 med
sæsonskaleret):

| Modellens SW kl. 12 UTC | Dage | Model-LCL minus sondens |
|---|---|---|
| 0-200 W/m² | 5 | -54 m |
| 200-400 W/m² | 16 | +31 m |
| 400-600 W/m² | 25 | +80 m |
| over 600 W/m² | 43 | **+151 m** |

I stærk sol er modellens 2 m-luft for varm og tør, så LCL ligger for højt.
Flyvningerne viser det samme: i maj-august ligger rå base minus fløjet top
på ~0 m ved 300-500 W/m² og +160 m over 700 W/m². Det sommerkalibrerede
fradrag har altså reelt rettet en modelfejl, og derfor ramte det for lavt
om efteråret, hvor der ikke er nogen fejl at rette. Det oprindelige
fradrag (200-500 m) går den forkerte vej: størst når solen er svagest.

**6. Et fradrag der følger strålingen.** Tilpasset alene på Jylland+Fyn
maj-august (gitter over hældning, tærskel og bund), testet på september-
oktober som modellen ikke har set:

| Fradrag | Maj-aug (tilpasset) | Sep-okt (ikke set) | Hele sæsonen | Sjælland uden loft | Loft-timer under loftet |
|---|---|---|---|---|---|
| v1: 200-500 m | -126 / 219 | -378 / 368 | -152 / 232 | +0 / 212 | 40 % |
| 100-300 m sæsonskaleret (første forslag) | -19 / 189 | -211 / 209 | -43 / 191 | +111 / 222 | 25 % |
| **0.4 x (SW - 400), mindst 0** | **-1 / 173** | **-107 / 135** | **-16 / 170** | +121 / 212 | 20 % |
| Intet fradrag | +94 / 197 | -86 / 129 | +74 / 191 | +215 / 271 | 14 % |

0.4 x (SW - 400) giver 0 m ved 400 W/m² og derunder, 120 m ved 700 og 200 m
ved 900, i tråd med sondens +151 m over 600 W/m². Hældning 0.6 og tærskel
500 er lige så gode på sommeren; 0.4/400 er valgt fordi den har mindst
afvigelse og er mindst stejl. Sjællands +121 er lofterne (fund 2).

Tilbage om efteråret står ~100 m hvor piloterne kommer over modellens base,
selv om modellen og sonden er enige om blandingslagets LCL. Det kan være
basen der stiger over eftermiddagen (sonden er kl. 14 lokal), men det
hviler på 8-10 dage og er ikke tilpasset væk.

## Implementeret

Fradraget fra rå base til vist top er i v2 `hcrit_margin_v2(SW)` =
0.4 m pr. W/m² over 400 W/m², intet under (konstanterne
`HCRIT_V2_SW_FREE_W_M2` og `HCRIT_V2_M_PER_W_M2` i config). Absolut
stråling, ikke sæsonskaleret, fordi fejlen sidder i modellens 2 m-felter.
`compute_thermal_top` tager fradraget fra kalderen (`margin_m`); v1 er
urørt. Klampningen til halvdelen af den rå højde over terræn står stadig.

Kontrol med produktionskoden på alle dagtimer (kl. 8-19) for 26
flyvepladser 18/5-4/10, 43.680 timer: scoren er uændret i alle. 30 timer
skifter `thermal_top_limited_by` fra `margin_collapse` til `weak_solar`
(overskyede timer med base under 100 m AGL); ingen af dem påvirker scoren.
Jylland og Fyn (1.142 timer med flyvninger): afvigelse -152 -> -16 m,
gennemsnitlig fejl 232 -> 170 m; september-oktober -379 -> -106 m, fejl
368 -> 135 m.

Et første forslag (100-300 m med fuld sol sæsonskaleret) blev committet
og erstattet samme dag, da sonden viste at fejlen følger strålingen og
ikke årstiden.

## Forbehold

- 90 %-fraktilen af hvor piloter forlader boblen er én definition af
  toppen. Piloter forlader ofte før toppen, så den reelle top ligger
  snarere højere end lavere.
- GPS-højde fra FLARM/OGN kan afvige op til ~40 m fra MSL.
- Historical-forecast er ikke præcis det publicerede.
- 20 km-radius blander pladsens terræn med omegnens; Danmark er fladt
  nok til at det er under 50 m de fleste steder.

## Åbne punkter

1. De sidste ~100 m om efteråret (fund 6): saml flere efterårsdage, og se
   om basen stiger over eftermiddagen.
2. Den falske "inversion"-dom (fund 4): 25 timer hvor der blev fløjet til
   ~640 m AGL.
3. Sjælland: hvis dagens loft kan registreres (FlightRadar eller
   klubberne), kan Sjælland indgå som censurerede data.
