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

---

# Del 2: Løsning, implementering og verifikation

Skrevet ved afslutningen af Task 7, 2026-08-14. Del 1 ovenfor er diagnosen fra Task 2 og står uændret, også hvor den senere viste sig at pege forkert. Hvor det er sket, står det nedenfor.

## Løsningsvalg

Fem mekanismer, hver med sit eget afgrænsede job. Ingen af dem er en generel "gør scoren bedre"-knap, og hver enkelt har målte grænser i begge retninger.

| mekanisme | spørgsmål den svarer på | virker på |
|---|---|---|
| Varmehukommelse på stråle-gaten | Er varmen fra de sidste timer stadig i grænselaget? | lør aften, kriterium 1 |
| Skydække-delta-værn | Faldt strålingen fordi solen gik ned, eller fordi en front kom? | frontcases, C1 |
| Grænselagshøjde-cap | Er der overhovedet vertikal plads at flyve i? | søn kl. 18, kriterium 3 |
| Cirrus-skjold | Har der stået et optisk tykt cirrusdække, og står det der stadig? | søn kl. 10-14, kriterium 2 |
| Mellemhøj dække-cap | Er der et solidt altostratus-dække? | frontcases efter cap-ombytning |

### Det der blev forkastet undervejs

**Cap-ombytningen til lagvægtet skydække blev rullet tilbage.** Del 1's sidefund om at `cloud_cover`-totalen modsiger sine egne lag førte til beslutningen om at caps skulle læse lagene i stedet. Det viste sig at være forkert, og det blev fanget ved replay af lørdag: kl. 13 rapporterer lagene **95 % lav sky under 736 W/m²**, hvilket er fysisk umuligt. Lagvægtet dække bliver 95, over cap'en på 87, og timen faldt til 2.0 "Ingen brugbar termik" i fuld sol. Kl. 18 og 19 faldt med.

Totalen og lagene modsiger altså hinanden i **begge** retninger, og præmissen "lagene er de indbyrdes konsistente" holder ikke. Det er samme lektie som `cloud_deck_arrived` allerede havde lært, se noten ved `CLOUD_ARRIVAL_COVER`: en god dags egne termikcumulus læses som overtrukket, så snart man vægter lagene. Den generelle cloud-cap blev derfor på den rå total, og cirrus når caps gennem de to målrettede skjolde i stedet.

**Overflade-lapse blev fravalgt** som værn mod C1. Det er fysisk det rigtigere signal, men `temperature_180m` er `None` for alle 360 historiske timer i API-svaret, så det kan hverken kalibreres eller regressionstestes på referencedagene.

## Implementering

20 commits på `fix/straale-gate-og-cirrus-caps`. De bærende:

| commit | hvad |
|---|---|
| `e606849` | persistér stråling og skylag, uden dem kan intet revideres bagefter |
| `2466863`, `6bff676` | `effective_radiation` og gaten der bruger den |
| `7443d14` | hukommelsen gælder ikke når et skydække trækker ind (lukker C1) |
| `563d32f` | grænselagshøjde som cap |
| `7e4373d` | `replay_day.py`, så en dag kan måles uden at vente på cron |
| `e65b480` | cirrus-skjold og mellemhøj pendant, og tilbagerulningen af cap-ombytningen |
| `2e09c0b` | cirrus-skjoldet må ikke overleve cirrusen |

Alle konstanter er bundet i begge retninger i `config.py`, med den målte øvre og nedre grænse skrevet ind. Det er bevidst: hver enkelt tærskel ligger i et smalt målt interval, og en senere justering "for at få tallene til at passe" skal støde på grænsen og fejle i testene.

## Verifikation

### Acceptkriterierne

| kriterium | mål | før | efter | status |
|---|---|---|---|---|
| 1, lør 18:00 | > 6.5 | 5.0 | **6.7** | ✅ |
| 1, lør 19:00 | > 6.5 | 5.0 | **5.9** | ❌ åbent, se nedenfor |
| 2, søn 10:00-14:00 | ≤ 3.0 | 6.2 (hindcast) | **3.0** | ✅ |
| 3, søn 18:00 | ≤ 5.0 | 7.4 | **5.0** | ✅ |

Kriterium 3 rammes af grænselagsgaten, som planen tiltænkte, ikke af cirrus-skjoldet.

### Sæsonanalyse pr. mekanisme

Målt ved at gen-score 30 flyvepladser x 11 dage (5280 timer) med hver mekanisme slået til og fra, så hver forskel kan tilskrives ét navngivet greb.

| mekanisme | timer flyttet | trukket ud af det grønne |
|---|---|---|
| Grænselagshøjde-cap | 175 (3,3 %) | 65 (1,2 %) |
| Cirrus-skjold | 242 (4,6 %) | 56 (1,1 %) |
| Mellemhøj dække-cap | 18 (0,3 %) | 2 (0,0 %) |

De 25 % i den oprindelige grænselagsnote overvurderede udslaget: de fleste lave middagstimer lå i forvejen på 5 eller derunder af andre grunde.

**Sæsonanalysen fangede en fejl testene ikke kunne se.** Cirrus-skjoldets trailing-maksimum holdt skjoldet oppe i tre timer efter at himlen var klaret op: 122 timer ud af det grønne, heraf 50 hvor cirrusen allerede lå under 25 % og 14 under en helt skyfri himmel med 400+ W/m². Værst var herning 2026-08-13 kl. 17, 8.4 til 3.0 med høj sky 0 og 558 W/m². Skjoldet stiller nu to spørgsmål, persistens og tilstedeværelse, og fyrer kun når begge svarer ja. Aftrykket halveredes, og de 56 tilbageværende grønne-træk har alle 52 til 94 % aktuel cirrus.

Det er værd at holde fast i: begge referencedage bestod hele vejen igennem den fejl. Kun sæsonmålingen kunne se den.

### Regressionstests

`termik/tests/test_reference_days.py` låser begge dage fast med timedata bagt ind, så de kører offline og ikke kan drive når Open-Meteo reviderer en fortidig dag. Data er hentet fra forecast-endpointet, aldrig arkivet. Fixturen reproducerer replay'et præcist på alle testede timer.

Suiten er på **268 beståede og 1 xfail**.

## Åbne emner

1. **Kriterium 1 kl. 19 er ikke nået, og er bevidst efterladt åbent.** Ingen cap binder timen: 5.9 er den vægtede sum selv. `score_solar` læser 88,6 % lagvægtet skydække, som er den gode dags egne termikcumulus, og 148,8 W/m² **direkte** stråling, som ingen strålingshukommelse rører. Det er markeret `xfail(strict=True)`, så det siger til hvis det nogensinde begynder at bestå.
2. **`score_solar` behandler en termikdags egne cumulus som dæmpning.** Rodårsagen bag punkt 1, og samme fejltype som `cloud_deck_arrived` måtte arbejde udenom. Det rører hver eneste time på hver eneste dag og kræver sin egen kalibrering.
3. **`gate_season.py` kan ikke køres som før-og-efter før deploy.** Den udleder fra udgivet `current.json`-historik, produceret af den gamle kode og uden `shortwave_radiation`. Sæsonmålingerne ovenfor bruger i stedet gen-scoring af cachet rådata.
4. **Vindretning og luftmasse er stadig ikke scoret.** `wind_dir` bruges kun til søbrise. Pilotens tommelfingerregel, højtryk nordvest for Danmark, er ikke kodet. Task 2 bekræftede mønsteret: lørdag W 273 til 236 grader med fladt tryk, søndag S 150 til 179 grader med fald fra 1014,9 til 1007,1 hPa.
5. **Lapse rate-vægten er stadig ikke efterprøvet.** Den tungest vægtede variabel (0,30) adskilte ikke de to dage.
6. **Strålingsfeltet reagerer knap på modellens egen cirrus.** Søn kl. 13 gav 690 W/m² mod lørs 736. Kun `cloud_cover_high` vidste besked.
7. **Begrænsende faktor vises stadig ikke i UI.** Med Task 1 på plads er data der nu.
8. **Kalibreringsgrundlaget er n=2.** Kriterium 1 klarer sig med cirka 7 % margin og afhænger af at hukommelsen når præcis tre timer tilbage. Flere pilot-verificerede dage ville være det billigste næste skridt.
