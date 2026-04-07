# Termik Scoring — Scenariereference

Referencedokument til validering og finjustering af scoring-systemet.
Genereret 2026-04-07 med multi-level data (80m/120m/180m vind+temp, boundary layer height).

## Scoreskala

| Score | Label | Betydning |
|-------|-------|-----------|
| 9-10 | Fremragende termik | Stærke, velorganiserede termikker. Top-dag. |
| 7-8 | God termik | Gode betingelser, flybart for de fleste. |
| 5-6 | Moderat termik | Termik til stede men svag/lav. Kræver erfaring. |
| 3-4 | Svag termik | Marginale betingelser. Kort flyvetid. |
| 0-2 | Ingen brugbar termik | Ikke flybart pga. vejr, stabilitet eller sikkerhed. |

## Dealbreakers (hårde lofter)

| Betingelse | Maks score | Begrundelse |
|---|---|---|
| Lapse rate < 0.50 | 1 | Inversion |
| Lapse rate < 0.65 | 3 | Stabil atmosfære |
| Lapse rate < 0.70 | 5 | Marginal, svag termik |
| Surface lapse < 0.3 | 1 | Overfladeinversion |
| Surface lapse < 0.5 | 2 | Stabilt overfladelag |
| Skydække >= 87% | 2 | Sol blokeret |
| Nedbør > 0 | 1 | Aktiv regn |
| Vind > 35 kt | 2 | Stormvind |
| Vindstød >= 35 kt | 1 | Farlige vindstød |
| Vindstød >= 30 kt | 2 | Kraftig reduktion |
| Effektiv vind > 35 | 1 | Uflyvbart |
| Effektiv vind > 30 | 2 | Kun meget erfarne |
| Effektiv vind > 25 | 4 | Nedsat flyvevejr |
| Temperatur < 5 | 3 | For koldt |
| CAPE > 1500 | 5 | Tordenbygerisiko |
| CAPE > 1000 | 7 | Overudviklingsrisiko |

## Scenarieresultater

### Fremragende betingelser (score 8-10)

| Scenario | Score | Lapse | Surface lapse | Vind 10m | Vind 80m | Spread | CAPE | BL-højde |
|---|---|---|---|---|---|---|---|---|
| Perfekt bagsidevejr (juni) | **10.0** | 1.27 | 1.97 | 12 kt | 14 kt | 14°C | 600 | 2000m |
| Stærk Cu-dag (maj) | **10.0** | 1.20 | 1.69 | 10 kt | 12 kt | 13°C | 450 | 1800m |
| Varm sommerdag (august) | **10.0** | 1.20 | 1.69 | 7 kt | 9 kt | 14°C | 350 | 2200m |

Kendetegn: Lapse rate >= 1.0, superadiabatisk overfladelag, lav vindforskydning, velmixet BL.

### Gode betingelser (score 6-8)

| Scenario | Score | Lapse | Surface lapse | Vind 10m | Vind 80m | Spread | Bemærkning |
|---|---|---|---|---|---|---|---|
| Moderat dag, noget sky | **7.5** | 0.87 | 1.12 | 8 kt | 10 kt | 10°C | 50% skydække reducerer sol |
| Tidlig sæson (april) | **7.6** | 0.93 | 1.12 | 10 kt | 12 kt | 10°C | Lavere temp, OK lapse |
| Tørtermik / blue day | **9.1** | 1.00 | 1.69 | 8 kt | 10 kt | 22°C | Stærk termik men ingen Cu |
| Vindstille, varmt | **8.6** | 1.13 | 1.69 | 2 kt | 3 kt | 14°C | Termik uden trigger-vind |

Bemærk: Blue day scorer højt fordi termikkerne ER stærke — piloter skal bare finde dem uden Cu-markering.

### Moderat/marginal (score 3-6)

| Scenario | Score | Lapse | Surface lapse | Vindforsk. | Bemærkning |
|---|---|---|---|---|---|
| Kraftig vindforskydning | **7.0** | 1.00 | 1.69 | -1.0 | Shear trækker 1.5 point ned |
| Svag lapse rate (0.67) | **5.0** | 0.67 | 0.84 | +0.5 | Capped af <0.70 dealbreaker |
| Efterår, svag sol | **5.9** | 0.73 | 1.12 | +0.5 | Lav solhøjde, kort vindue |
| Våd jord fra regn | **6.6** | 0.87 | 0.84 | +0.5 | Nedbør-vægt (7%) er lav |
| Overudvikling (CAPE 1500) | **7.0** | 1.33 | 1.69 | +0.5 | Capped af CAPE >1500 |

### Stabil luftmasse (score 1-4)

| Scenario | Score | Lapse | Surface lapse | Temp | 850hPa | Bemærkning |
|---|---|---|---|---|---|---|
| Saharaluft (30°C, stabil) | **3.0** | 0.53 | 0.84 | 30°C | 22°C | Varmt hele vejen op |
| Subsidensinversion | **1.0** | 0.47 | 0.56 | 22°C | 15°C | Højtrykslåg, <0.50 dealbreaker |

### No-fly betingelser (score 0-2)

| Scenario | Score | Primær dealbreaker |
|---|---|---|
| Blæsende + vindstød (eff 33kt) | **2.0** | Effektiv vind > 30 |
| Morgen, overflade ikke opvarmet | **1.0** | Surface lapse 0.28 + bulk lapse <0.70 |
| Aktiv regn | **1.0** | Precipitation > 0 |
| Vinter, overskyet, koldt | **1.0** | Lapse <0.50 + skydække + temp <5 |
| Snevejr, -5°C | **0.1** | Alle dealbreakers aktive |
| Vindstød 42kt | **1.0** | Gusts >= 35 + effektiv vind > 35 |
| Overfladeinversion (efterår) | **1.0** | Surface lapse -1.12 (inversion) |

### Kysteffekt

| Scenario | Score | Søbrise-straf | Bemærkning |
|---|---|---|---|
| Kyst, pålandsvind (15km fra kyst) | **7.7** | -2.4 | Samme vejr som inland |
| Inland (65km fra kyst) | **9.9** | -0.2 | 2.2 point forskel! |

## Multi-level data effekt

| Situation | Uden multi-level | Med multi-level | Forskel |
|---|---|---|---|
| Skjult overfladeinversion | ~5+ (bulk lapse OK) | 1.0 (surface inversion fanget) | Forhindrer falsk positiv |
| Velmixet BL | base score | base + 0.8 (shear + mixing bonus) | Belønner gode forhold |
| Kraftig vindforskydning | base score | base - 1.3 (shear + mixing penalty) | Straffer brudt termik |

## Vægte

| Faktor | Vægt | Bemærkning |
|---|---|---|
| Lapse rate | 30% | Primær stabilitetsmåling |
| Sol/stråling | 20% | Opvarmningspotentiale |
| Spread | 15% | Skybase og overudvikling |
| Vind | 10% | Trigger-mekanisme |
| Vindstød | 10% | Sikkerhed |
| Temperatur | 8% | Opvarmningspotentiale |
| Nedbør | 7% | Våd jord, aktiv regn |

## Modifiers (bonus/straf oven på vægtede score)

| Modifier | Værdi | Betingelse |
|---|---|---|
| CAPE > 700 | +1.0 | Konvektivt potentiale |
| CAPE > 300 | +0.5 | Moderat konvektion |
| Stigende tryk | +0.5 | Bagsidevejr |
| Faldende tryk | -0.5 | Frontalpassage |
| Afkøling i 850hPa | +0.5 | Destabilisering |
| Vindforskydning < 5kt | +0.5 | Velorganiseret termik |
| Vindforskydning > 12kt | -0.5 | Tiltet/brudt termik |
| Vindforskydning > 20kt | -1.0 | Termik ødelagt af shear |
| BL velmixet (gradient < 4kt) | +0.3 | Konvektiv BL |
| BL dårligt mixet (gradient > 8kt) | -0.3 | Stabil/transitional |
| Søbrise | -0 til -3 | Afstandsbaseret kysteffekt |

## Kendte begrænsninger

1. **Nedbør-vægt (7%)** er lav — våd jord straffes ikke hårdt nok
2. **Spread-vægt (15%)** — blue thermals (spread >20) scorer stadig højt fordi termikkerne er stærke
3. **Vindstille dage** scorer højt trods manglende trigger-mekanisme
4. **CAPE-bonus + CAPE-dealbreaker** kan modvirke hinanden ved CAPE ~1000-1500

## Brug af dette dokument

- Kør scenarietests: `python3 -m pytest termik/tests/test_scenarios_multilevel.py -v`
- Tilføj nye scenarier i `termik/tests/test_scenarios_multilevel.py`
- Justér dealbreakers i `termik/scoring.py:apply_dealbreakers()`
- Justér vægte i `termik/config.py:WEIGHTS`
- Justér modifiers i `termik/scoring.py:calculate_modifiers()`, `calculate_wind_shear_modifier()`, `calculate_bl_mixing_modifier()`
