# Referat: Stråle-gate og cirrus i hard caps

**Dato:** 2026-08-12
**Branch:** `fix/straale-gate-og-cirrus-caps`
**Plan:** `docs/plans/2026-08-12-straaling-og-cirrus-i-caps.md`

## Referencedage

To piloter fra Midtsjællands Svæveflyveklub (Ringsted, 55.451748, 11.642456) rapporterede:

- **Lørdag 2026-08-08:** fremragende. Svært at komme fra 300 til 500 m, men massiv termik derover, og stadig godt kl. 19.
- **Søndag 2026-08-09:** umuligt at finde noget hele dagen.

Systemet gav lørdag 7.1 i top, præcis 5.0 kl. 18 og 19, og præcis 3.0 kl. 20. Søndag fik flad 2.0 fra kl. 10 til 14 og 7.4 som bedste time kl. 18. Begge dele er forkerte, og modsatrettede.

Felterne blev først persisteret i Task 1, så de to dage findes ikke i arkivet. De er i stedet hentet fra Open-Meteo med `termik/tools/fetch_reference_day.py`.

### Kildevalg: forecast-endpointet, ikke arkivet

ERA5 dækker ikke dagene endnu (`&models=era5` gav `null` hele vejen igennem for 2026-08-08, den forventede ca. 5 dages forsinkelse). `archive-api` falder derfor tilbage til `ecmwf_ifs`, som er en **anden model end den `best_match`-blanding produktionen kører på**. De to er ikke udskiftelige:

| kl (lør) | forecast-hindcast SW | arkiv (ecmwf_ifs) SW |
|---|---|---|
| 13 | 736 | 546 |
| 17 | 523 | 485 |
| 18 | 398 | 298 |
| 19 | 274 | 186 |
| 20 | 139 | 92 |

Afgørelsen er ikke et skøn. Den nuværende gate klipper til 5 ved 250 til 400 W/m² og til 3 ved 100 til 250. Produktionen udgav 5.0, 5.0 og 3.0 kl. 18, 19 og 20:

- Forecast-hindcast (398, 274, 139) giver 5, 5, 3. **Rammer præcis.**
- Arkivet (298, 186, 92) giver 5, 3, 1. Rammer ikke.

`cloud_cover_low/mid/high` var derimod bit-identiske mellem de to kilder, begge dage, alle 24 timer. **Al kalibrering i Task 3 til 5 skal ske mod forecast-endpointet.**

### Sidefund: `cloud_cover` modsiger sine egne lag

Det samlede `cloud_cover` var *ikke* identisk mellem kilderne, og det er ikke bare støj. I `best_match`-svaret fra forecast-endpointet er totalen uforenelig med lagene:

| | total | low | mid | high |
|---|---|---|---|---|
| søndag kl. 10 | **74** | 0 | 0 | **99** |
| lørdag kl. 13 | **67** | **95** | 0 | 0 |

En total på 74 med 99 % cirrus er fysisk umuligt. Arkivets total følger derimod pænt lagenes maksimum (søndag kl. 10: 99). Totalen og lagene i produktionens svar kommer altså fra hver sin model i blandingen.

Det er relevant for Task 5, som stiller `effective_cloud_cover(...)` og `cloud_cover_high` op i samme `if`-kæde: de to felter er ikke to målinger af det samme. Den `cloud_cover >= 87` der fangede søndag i morgen-runnet aflæste totalen, altså det felt der her siger 74 mens himlen var lukket.

### Lørdag 2026-08-08 (pilot: fremragende, god termik til kl. 19)

```
   kl     SW  direct   cc  low  mid  high    BL_m      T   dir      hPa
06:00    3.0     0.0   24    2    0     2   265.0   12.4   241   1017.9
07:00   46.0     6.1   18    2    0    57   350.0   14.0   242   1018.3
08:00  169.0    68.1   10    2    0    45   800.0   15.6   274   1018.4
09:00  244.0    99.4   26    5    0     1  1085.0   16.7   273   1018.6
10:00  381.0   200.6   76    8    0    12  1155.0   17.8   274   1019.0
11:00  426.0   199.6   66   18    0    13  1270.0   19.1   272   1019.0
12:00  585.0   354.6   31   65    0    23  1515.0   20.0   264   1019.1
13:00  736.0   535.4   67   95    0     0  1600.0   20.6   258   1018.9
14:00  726.0   511.2   64   47    0     0  1760.0   21.5   249   1018.5
15:00  708.0   505.4   57   66   58     1  1750.0   22.2   256   1018.4
16:00  657.0   476.0   61   52   33     0  1570.0   21.9   246   1018.1
17:00  523.0   347.2   48   58   30     0  1685.0   22.2   232   1017.5
18:00  398.0   243.3   32   67   31     0  1250.0   21.9   237   1017.3
19:00  274.0   148.8   31   62   38     0  1000.0   21.5   236   1017.3
20:00  139.0    55.1   26  100    1     0   225.0   20.6   223   1017.4
21:00   30.0     4.5   28   40    0     0    90.0   18.2   205   1017.6
```

Vestlig vind (232 til 274 grader), lavt skydække i eftermiddagstimerne (cumulus), stort set ingen cirrus efter kl. 12.

### Søndag 2026-08-09 (pilot: umuligt at finde noget hele dagen)

```
   kl     SW  direct   cc  low  mid  high    BL_m      T   dir      hPa
06:00    3.0     0.0   58    0    0    90   185.0   11.5   150   1014.9
07:00   57.0    12.3   67    0    0    98   210.0   13.8   152   1014.7
08:00  141.0    44.7   64    0    0    98   245.0   15.9   158   1014.4
09:00  252.0   108.6   72    0    0    99   315.0   18.4   161   1014.0
10:00  380.0   201.0   74    0    0    99   410.0   20.9   178   1013.7
11:00  486.0   276.7   79    0    0    81  1210.0   22.2   177   1013.0
12:00  630.0   421.0   55    0    0    59  1280.0   23.7   175   1012.4
13:00  690.0   470.5   64    0    0    84  1295.0   24.6   174   1011.7
14:00  560.0   278.5   75    0    0   100  1260.0   25.2   179   1011.1
15:00  442.0   158.2   67    0    1    88  1170.0   25.7   174   1010.3
16:00  503.0   264.7   63    0   43    13  1070.0   26.2   161   1009.7
17:00  453.0   256.0   36    0    1     7   980.0   25.7   158   1008.9
18:00  429.0   283.1   15    0    1     0   780.0   25.4   155   1008.2
19:00  284.0   160.9   37    0    0     0   355.0   23.6   127   1007.4
20:00  144.0    60.7   51    0   13     0   165.0   22.2   132   1007.1
21:00   27.0     3.4   89    0    0     1   110.0   20.7   132   1006.9
```

Sydlig vind (150 til 179 grader), faldende tryk, 4 til 5 grader varmere end lørdag, og **nul lavt skydække hele dagen**.

## Hvad tallene siger

### 1. Stråle-gaten forklarer lørdagens klemme præcist

398, 274 og 139 W/m² kl. 18, 19 og 20 falder i hver sin gate-bakke (5, 5 og 3). Lørdagens aften blev ikke nedvægtet, den blev **klippet**, af et enkelt `if`.

Eftermiddagens peak er **736 W/m² kl. 13**, ikke de ca. 640 planen antog. Med `RADIATION_MEMORY_HOURS = 3` er det dog ikke peaken der binder, men de tre foregående timer:

| kl | SW nu | max(3 foregående) | eff. ved faktor 0.65 | gate |
|---|---|---|---|---|
| 18 | 398 | 708 (kl. 15) | 460 | fri |
| 19 | 274 | 657 (kl. 16) | **427** | fri |
| 20 | 139 | 523 (kl. 17) | 340 | cap 5 (var 3) |
| 21 | 30 | 398 (kl. 18) | 259 | cap 5 (var 1) |

**0.65 holder, men kun lige.** Kriterie 1 binder kl. 19, hvor minimum er 400 / 657 = **0.609**. Der er ca. 7 % luft, og den luft afhænger af at hukommelsen rækker tre timer tilbage til kl. 16.

**Bagsiden skal måles i Task 4:** ved faktor 0.65 får kl. 21 med 30 W/m² en cap på 5 i stedet for 1. Solen er nede. Hukommelsen bør formentlig ikke kunne løfte en time hvor den aktuelle stråling er under den nederste tærskel.

### 2. Præmissen for Task 5 holder: søndagens sky var cirrus

Utvetydigt. Kl. 10 til 14:

| kl | cc total | low | mid | **high** |
|---|---|---|---|---|
| 10 | 74 | 0 | 0 | **99** |
| 11 | 79 | 0 | 0 | **81** |
| 12 | 55 | 0 | 0 | **59** |
| 13 | 64 | 0 | 0 | **84** |
| 14 | 75 | 0 | 0 | **100** |

`cloud_cover_low` er **0 i hver eneste time hele dagen**, og `cloud_cover_mid` er 0 indtil kl. 15. Sammen med sydlig vind passer det på pilotens beskrivelse. Task 5 er ikke bygget på en fejlantagelse.

### 3. Men `CIRRUS_SHIELD_THRESHOLD = 85` rammer ikke kriterie 2

Med den foreslåede regel `cloud_cover_high >= 85` fanges kun kl. 10 (99) og 14 (100). Kl. 11 (81), 12 (59) og 13 (84) slipper fri. En tærskel der fangede alle fem timer skulle ned på 59, hvilket ville klippe enhver dag med moderat cirrus.

Bemærk også at den blunte `cloud_cover >= 87` ikke fyrer på disse tal (55 til 79). Den 90 til 96 % planen refererer kom fra morgen-runnet, ikke herfra. I et replay er søndag altså **helt uden cloud-cap** i dag, hvilket er præcis de 6.2 planen nævner.

**Observation til Task 5:** cirrus-skjoldet havde hukommelse på samme måde som opvarmningen. Kl. 06 til 10 lå cirrus på 90, 98, 98, 99, 99. Testes `max(nu, de 3 foregående timer)` mod planens egen tærskel på 85, fanges hele blokken:

| kl | high nu | max(3 foregående) | max af begge |
|---|---|---|---|
| 10 | 99 | 99 | 99 |
| 11 | 81 | 99 | 99 |
| 12 | 59 | 99 | 99 |
| 13 | 84 | 99 | 99 |
| 14 | 100 | 84 | 100 |

Det er den samme mekanik som Task 3 indfører for stråling, brugt på skyen: et skjold der har stået siden solopgang har allerede taget morgenens opvarmning, uanset at det tynder ud en time midt på dagen. Til kontrol rammer reglen ikke lørdag, hvor cirrus toppede på 57 kl. 07 og lå på 0 til 23 resten af dagen.

### 4. Grænselagshøjden adskiller dagene, hvor lapse rate ikke gjorde

| kl | lørdag BL | søndag BL | forhold |
|---|---|---|---|
| 08 | 800 | 245 | 3.3 |
| 09 | 1085 | 315 | 3.4 |
| 10 | 1155 | 410 | **2.8** |
| 11 | 1270 | 1210 | 1.05 |
| 12 | 1515 | 1280 | 1.18 |
| 13 | 1600 | 1295 | 1.24 |
| 14 | 1760 | 1260 | 1.40 |
| 16 | 1570 | 1070 | 1.47 |
| 17 | 1685 | 980 | **1.72** |
| 18 | 1250 | 780 | **1.60** |
| 19 | 1000 | 355 | **2.8** |

Til sammenligning adskilte lapse rate dagene med 0.90 til 1.16 mod 0.89 til 0.99, altså stort set ikke.

Grænselagshøjden skiller rent i **begge de vinduer planen kalibrerer mod**: lørdag aften kl. 17 til 19 (som skal op) og søndag morgen kl. 10 (som skal ned). Feltet hentes allerede (`config.py:38`), gemmes allerede og vises i popup'en, men **bruges ikke i scoringen**, kun i kommentargenereringen (`comments.py:106`).

Forbeholdet: kl. 11 til 13 er de to dage næsten ens (1270 mod 1210). Grænselagshøjde alene løser ikke kriterie 2.

### 5. Strålingen adskiller **ikke** dagene

Det ubehagelige resultat. Søndag kl. 13 fik 690 W/m² mod lørdags 736, og direkte-andelen var 68 % mod 73 %. Akkumuleret morgenstråling kl. 06 til 10 var 833 W/m² søndag mod 843 lørdag, altså identisk.

Modellens SW-felt reagerer med andre ord næsten ikke på dens eget cirrus-felt. Det er samme observation som maj-referatet noterede, og den betyder at hverken `shortwave_radiation` eller `direct_radiation` kan bære kriterie 2. Kun `cloud_cover_high` ved at søndag var overtrukket.

## Konsekvenser for de resterende tasks

1. **Task 3 og 4** kalibreres mod forecast-endpointets tal, ikke arkivets. `RADIATION_MEMORY_FACTOR = 0.65` opfylder kriterie 1 med ca. 7 % margin. Bagsiden efter solnedgang (kl. 21 løftes fra cap 1 til cap 5) skal måles, ikke antages væk.
2. **Task 5** kan fortsætte: skyen *var* cirrus. Men `CIRRUS_SHIELD_THRESHOLD = 85` på øjebliksværdien opfylder ikke kriterie 2, og skal enten sænkes til 81 (fanger 4 af 5 timer) eller gives samme trailing-max-hukommelse som stråle-gaten (fanger alle 5).
3. **Åbent spørgsmål ud over planen:** `boundary_layer_height` er det eneste felt der skiller de to dage rent i begge kalibreringsvinduer, og det indgår ikke i scoringen i dag.
