# Startlist-validering 3.-4. oktober 2026: søndagen blev undervurderet

Dato: 2026-10-05. Rådata: `2026-10-05-startlist-weekend.jsonl` (32 plads-dage).
Kilde: startlist.club/2026-10-03 og /2026-10-04, publicerede scores fra
`airfields.json` i git-historikken (aftenen før og morgenen samme dag).

## Spørgsmålet

Piloterne oplevede at Flyvevejr ramte nogenlunde lørdag, men tog fejl søndag,
især på Sjælland, hvor mange fløj i flere timer.

## Metode

Som sæson-valideringen 2026-08-25: et fly med 3+ forskellige forsædepiloter
samme dag er skolefly og tæller ikke (typisk ASK 21 med korte skoleture).
Facit-bånd ud fra signalflyvningerne: staerk (2+ over 60 min og længste
>= 120, forventet 7.5-10), god (>= 90, 6.5-10), mulig (>= 60, 4.5-8.5),
svag (2+ flyvninger, længste < 45, 0-6), tynd (udgår). Plads-mapping som i
august (Slaglille -> ringsted, Christianshede -> silkeborg osv.).

## Facit mod publiceret

Publiceret = dagsgennemsnit kl. 10-18 fra morgenkørslen samme dag.

| Plads | Lør længste | Lør publ. | Søn længste | Søn publ. |
|---|---|---|---|---|
| Slaglille | 10 min | 2.4 | 228 min (10 over 2 t) | 3.6 (max 5) |
| Kalundborg | 20 min | 3.0 | 326 / 285 min | 3.1 (max 5) |
| Gørløse | 74 min | 3.0 | 193 / 143 min | 3.3 (max 5) |
| Christianshede | 150 min | 3.1 | 171 min (5 over 1 t) | 2.1 (max 3) |
| Bolhede | ingen | 3.5 | 122 min | 2.6 (max 3) |
| True | 115 min | 3.8 | 47 min | 2.7 |

Lørdag: Sjælland svag og scoret svag (rigtigt). Jylland lidt undervurderet
(True 115 min og Christianshede 150 min mod ~3-3.8).

Søndag: alle pladser med gode flyvninger lå hele dagen på præcis 3 eller 5.
Runde lofter betyder at et hårdt cap afgør scoren, ikke den vægtede sum.
Hammer (330 og 405 min) er som i august holdt ude: skrænt/bølge.

## Hvad atmosfæren faktisk gjorde

Radiosonde Schleswig (10035) søndag 12 UTC, København havde ingen data:

| Højde | T | RH | theta |
|---|---|---|---|
| 250 m | 13.1 | 70 | 286.3 |
| 750 m | 8.3 | 91 | 286.4 |
| 1000 m | 6.1 | 100 | 286.6 |
| 1250 m | 4.6 | 100 | 287.6 |
| 1500 m | 3.9 | 27 | 289.4 |
| 1750 m | 6.9 | 18 | 295.1 |

Tør-adiabatisk (konstant theta) fra jorden til ~1000 m, cumulus 1000-1250 m,
kraftig inversion 1500-1750 m. En klassisk efterårs-bagsidedag med
brugbar termik til ~1000-1200 m. Modellen (best_match) havde samme
struktur: 2 m -> 925 hPa på 1.0-1.15 grader/100 m, 925 -> 850 hPa stabil,
boundary_layer_height 1000-1300 m. **Vejrdataene var rigtige; scoringen
læste dem forkert.**

## Fire fund

1. **Lapse rate måles 2 m -> 850 hPa.** Søndag lå 850 hPa lige over
   inversionen, så gennemsnittet blev 0.57-0.73 og udløste caps 3 (< 0.65)
   og 5 (< 0.70) samt en lav lapse-score (30 % vægt). Blandingslaget
   under var fuldt konvektivt.
2. **Strålingstærsklerne er absolutte og kalibreret i august.** Under
   400 W/m² capper på 5. Middagssolen i starten af oktober er ~63 % af
   augusts, så cappet ramte næsten alle timer. Samme for solscorens 600
   W/m² for fuld direkte sol og for basehøjde-cappets sol-krav (SW >= 400),
   som derfor slet ikke kunne ramme fra oktober.
3. **Ingen punkter havde elevation_m (fejl).** Parcel-beregningen startede
   alle steder i 0 m, mens geopotentialhøjderne er MSL. På Christianshede
   (98 m) er det ~1 K for koldt ved 925 hPa, og dagen blev til
   "Inversion: ingen termik" hele dagen mens der blev fløjet 171 min.
4. **Døde datafelter.** best_match leverer kun 1000/925/850 hPa i de
   nederste 1.6 km (ECMWF-niveauer); 950/900/800 hPa og 80/120/180 m-
   temperaturen har været tomme siden mindst juli. Overflade-lapse-
   checket (2 m -> 180 m), som v2's kode læner sig op ad, har aldrig kørt
   i produktion. `dmi_seamless` leverer 180 m-temperaturen, `icon_seamless`
   alle trykniveauer plus sensible heat flux. 1000 hPa er tilgængelig men
   hentes ikke.

## Implementeret

**Fix 1: elevation_m på alle punkter.** Hentet én gang fra Open-Meteos
elevation-endpoint (samme 90 m-DEM som forecast-API'et nedskalerer
temperature_2m til) med `termik/tools/fetch_elevations.py`. Flyvepladserne
har værdien hardcodet i `locations.AIRFIELDS`, griddet læser
`termik/grid_elevations.json`. Ingen ekstra API-kald i produktion.
Påvirker termiktop og kommentarer; scoren rykker sig næsten ikke
(Christianshede 4/10 kl. 14 går fra "inversion" til LCL-begrænset med
TI-nul ~950 m).

**Fix 2: sæsonskaleret stråling (kun v2).** Faktor =
sin(middagssolhøjde i dag) / sin(middagssolhøjde 8/8), klampet til
[0.5, 1.0]. Ganges på strålings-gaten (400/250/100), varmehukommelsens gulv
(bundet til gatens nederste tier), solscorens 600/800 W/m² og basehøjde-
cappets SW >= 400. Datoen læses fra timens tidsstempel. v1 er urørt.
Faktor 4/10: 0.63.

**Fix 3: blandingslagets lapse (kun v2).** Lapse 2 m -> 925 hPa
(terrænhøjden trukket fra, mindst 300 m lag). Er den >= 0.95 OG
boundary_layer_height >= 900 m, scores og cappes på den største af
850- og 925-lapse; ellers står 850-målet. Dybdekravet er BL-gatens 900 m,
så en overophedet morgenbund ikke tæller. 850-lapse publiceres stadig som
`lapse_rate_850` (revisionsspor); `lapse_rate` er nu den scorede værdi,
så kommentarens stabilitetslinje og popup'ens lapse-måler følger scoren.
Søbrise 5b bruger fortsat 850 hPa-temperaturen direkte.

## Validering

Samme cachede modeldata (forecast-endpoint, past_days) for sommerens
facit-dage 11/7-23/8 (58 plads-dage, Hammer og tynd udeladt) og weekendens
24. Metrik: gennemsnit af dagens 3 bedste timer kl. 11-18, afvigelse fra
facit-båndet. Adskillelse = gennemsnit for fløjne dage (mulig/god/staerk)
minus gennemsnit for svage dage.

| | Sommer i bånd | Sommer afv. | Sommer adskillelse | Okt i bånd | Okt afv. | Okt største fejl | Okt adskillelse |
|---|---|---|---|---|---|---|---|
| Før | 37/58 | 85.3 | 2.07 | 14/24 | 23.1 | 4.3 | 0.36 |
| Fix 1+2 | 36/58 | 85.2 | 2.08 | 11/24 | 24.0 | 4.1 | 0.14 |
| **Fix 1+2+3** | 37/58 | 86.1 | **2.30** | 12/24 | **14.1** | **2.4** | **1.07** |

**Fix 2 alene er ikke en forbedring.** Søndagens stærke pladser løftes kun
0.1-0.7 fordi 850-lapse holder dem nede, mens lørdagens svage løftes mere
(Frederikssund 5.0 -> 7.1), så adskillelsen falder til 0.14. Fix 2 og 3
skal derfor følges ad. Enkelt-time-test: Slaglille søndag kl. 14 er <= 5
med kun den ene af de to, 6.0 med begge.

Med alle tre: søndagens Sjælland lander på 6.8-7.6 (Slaglille 4.9 -> 7.1,
Gørløse 5.0 -> 7.6, Kalundborg 4.8 -> 6.8), Christianshede/Bolhede 3.2-3.5
-> 5.1-5.7.

Følsomhed: lapse-grænse 0.90-0.95 og dybde 700-900 m giver identiske tal;
1.00 forværrer oktober (15.8), 1100 m bytter oktober (16.3) for sommer
(85.2). Valget 0.95/900 er fysisk begrundet (lige under tør-adiabatisk,
samme dybde som BL-gaten), ikke tilpasset.

Sommerens bytte (afvigelse +0.8 i alt, i-bånd uændret):

- Vundet: Christianshede 15/8 (god, 100 min) 3.7 -> 9.1, fejl 2.8 -> 0;
  Kalundborg 16/8 (staerk, 315 min) 5.8 -> 7.2, fejl 1.7 -> 0.3.
- Tabt: de kendte overcalls bliver ~1 point værre: 22/8 Slaglille,
  Kongsted og Christianshede, 2/8 Gesten og Aars, 23/8 Sæby (alle svag).
  Det er dage hvor scoren allerede var 7-8 af andre grunde
  (pålandsvind/søbrise, se sæson-referatet); lapse var ikke årsagen.

Tilbageværende oktober-fejl: lørdagens Frederikssund, Gesten og
Skinderholm scores 7.4-8.4 mod facit svag, og søndagens Frederikssund 8.2.
De har tyndt facit (se forbehold). Slaglille søndag holdes desuden 1.8
nede af søbrise-straffen i vestenvind 33 km inde.

## Forbehold

- 2 dage, 24 plads-dage med facit. Nogle "svag" er tyndt facit:
  Frederikssund fløj søndag mest korte spilstarter, mens Gørløse 15 km
  væk fløj 193 min. Klubaktivitet er ikke det samme som vejret.
- Replay bruger modellens nuværende version af dagen; den afviger lidt fra
  det publicerede (fx Slaglille søndag 46-60 % sky i replay mod 63-88 %
  publiceret).

## Åbne punkter, prioriteret

1. Gentag valideringen på flere efterårsdage (og foråret, hvor
   sæsonfaktoren også er under 1) før yderligere kalibrering.
2. Søbrise-straffen: løst samme dag, se de to sidste afsnit.
3. Hent `temperature_1000hPa` og lavniveau-profil/heat flux fra
   `icon_seamless` eller `dmi_seamless` i stedet for ECMWF-niveauerne.
4. På sigt: RASP-agtig W* (termikstyrke fra varmestrøm og BL-dybde) som
   kerneinput i stedet for lappeværket af absolutte caps; den håndterer
   årstiden af sig selv.

## Opfølgning samme dag: søbrise og havtemperatur

Slaglille søndag blev holdt 1.8 nede af søbrise-straffen, i vestenvind
33 km inde. Punkt 5b (pålandsvind >= 8 kt over stabil havluft giver fuld
søbrise) fyrede fordi havtemp minus 850-temp var 12 - 5.1 = 6.9, under
tærsklen 7. De 12 grader er `SEA_TEMP_BY_MONTH[10]`, en fast månedsværdi.

**Månedstabellen var forkert.** Open-Meteos marine-API ved pladsernes
havpunkter:

- 3.-4. oktober målte 14.5-16.4 grader (Storebælt 15.9), ikke 12.
- Tabellen er en trappe: natten til 1/10 falder det antagne hav 4 grader
  (16 -> 12), mens det målte gik 15.1 -> 15.0.
- Målt minus tabel, middel 2024-2026: maj +2.9, juni +2.4, juli +1.9,
  august +0.9, september +1.2, oktober +1.1.

Med de målte 15.9 er land/hav-forskellen ~0 og 5b fyrer ikke: straffen
bliver 0, ikke 1.8.

**Tærsklen 7 holder.** Pålandsstudiet (2026-08-25) gentaget med målt
havtemperatur på samme 26 pålandsdage (v2 >= 6.5, aktive): tabel og målt
fejlklassificerer begge 5 dage ved tærskel 7 (tabel: 3 falske straffe og 2
manglende; målt: 0 falske og 5 manglende), og ingen anden tærskel er
bedre. Gevinsten ligger i havtemperaturen, ikke i at flytte tærsklen.

### Implementeret

- `termik/tools/fetch_sea_points.py` vælger én gang en havcelle pr.
  kystnært punkt (ud langs kystretningen til marine-API'et svarer med en
  havtemperatur), afrundet til 0.1 grad og delt: 158 celler for 255
  punkter i `termik/sea_points.json`. Svævethy og seks indre
  Limfjords-gitterpunkter får ingen celle (fjorden er ikke i
  marine-modellen) og bruger klimatologien.
- `fetch_weather.fetch_sea_temps` henter den aktuelle havtemperatur for
  alle celler én gang pr. kørsel (2 lette kald) og sætter `sea_temp_c` på
  punkterne. Fejler kaldet, kører prognosen videre på klimatologien.
- Fallback: `SEA_TEMP_CLIMATOLOGY`, målt månedsmiddel 2024-2026,
  interpoleret pr. dag (ingen trapper). Månedstabellen bruges kun af v1 og
  direkte kald.
- Data-blokken viser `sea_temp` og `sea_temp_source` (measured /
  climatology). `replay_day` bruger den målte havtemperatur for den
  genafspillede dag, så kalibrering ser det samme som produktionen.

### Validering

Samme sæt som ovenfor, med produktionens havceller og målt historik.

| | Sommer i bånd | Sommer afv. | Sommer adskillelse | Okt i bånd | Okt afv. | Okt adskillelse |
|---|---|---|---|---|---|---|
| Før alle rettelser | 37/58 | 85.3 | 2.07 | 14/24 | 23.1 | 0.36 |
| Fix 1-3 | 37/58 | 86.1 | 2.30 | 12/24 | 14.1 | 1.07 |
| **+ målt havtemp** | **38/58** | **85.4** | **2.38** | **16/24** | 13.2 | **1.59** |
| (+ kun klimatologi) | 38/58 | 86.9 | 2.32 | 16/24 | 12.7 | 1.59 |

Søndagens stærke pladser når nu båndet: Slaglille 7.1 -> 8.5, Kalundborg
6.8 -> 8.4, Gørløse 7.6 -> 8.5 (før alle rettelser 4.8-5.0). Replay af
Slaglille 4/10 giver 7.7-8.6 kl. 12-15. Om sommeren flytter kun to rækker
sig mærkbart: Kalundborg 2/8 (god, 208 min) 8.2 -> 9.1 og Sæby 23/8
(svag) 7.0 -> 6.6, begge i den rigtige retning.

Målt og klimatologi er næsten lige gode på dette materiale; målt er valgt
fordi årene afviger (4/10-2026 lå 0.8 over klimatologien) og fordi lokal
opvælling ikke kan ligge i en tabel (Køge Bugt 15 grader 8/8-2026 mod
19 i resten af farvandet).

## Opfølgning: 5b's stabilitetstest i det nedre lag

5b kaldte havluften stabil når hav -> 850 hPa var under 7 K. Det er samme
inversionsproblem som lapse rate: ligger et låg mellem 925 og 850 hPa,
ser et ustabilt nedre lag stabilt ud.

**Ny dataindsamling.** 925 og 850 hPa (historical-forecast, samme kilde
som studiet) for pålandsstudiets 8 pladser, maj-september 2024-2026, plus
målt havtemperatur ved produktionens havceller. Stabilitet i det nedre lag
= (hav - T925) / (z925 / 100), kl. 12-16.

**Fundet.** Mekanismen findes: Slaglille 15/8-2026 faldt 925 hPa fra 18.7
til 12.9 grader mens 850 lå på 13-15, så hav -> 850 sagde 5.9-6.8
("stabil") og hav -> 925 0.76-0.91 grader/100 m (ustabilt). Der blev
fløjet 158 min; det er den ene dag i studiet som 5b fejlagtigt straffer.
På timeniveau gjaldt det samme 37 af 420 timer hvor 5b fyrede juli-oktober
2026 (9 %).

**Tærskel uden tilpasning.** 5b's egen grænse pr. 100 m: 7 K over 15 hm =
0.47 grader/100 m. Havluften er nu kun stabil når BÅDE hav -> 850 og hav
-> 925 er under grænsen. På de 48 aktive pålandsdage:

| Regel | Stabil, fløj | Konvektiv, fløj | Fejlklassificeret |
|---|---|---|---|
| Kun hav -> 850 (før) | 1/7 | 27/41 | 15 |
| Kun hav -> 925 (0.7-1.0) | 8/18 til 18/36 | | 18-22 |
| **Begge under 0.47 (nu)** | 0/6 | 28/42 | **14** |

De seks dage hvor begge lag var stabile (nedre lag 0.02-0.11) døde alle.
Det nedre lag alene er en dårligere test end 850-målet; det virker kun som
supplement.

**Effekt på scoren: ingen målbar.** Sommerens 58 og oktobers 24 plads-dage
er uændrede (ingen af dem har timer hvor kun det nedre lag var ustabilt).
På Slaglille 15/8 falder søbrise-straffen 1.8 -> 0.9 kl. 14-17, men scoren
bliver 2-3, for cirrus-skjoldet (81-95 % høj sky) capper på 3, og
morgenens 850-lapse og et lavt grænselag holder resten nede. Rettelsen er
en konsistens- og robusthedsrettelse, ikke en kalibrering.

Slaglille 15/8 blev fløjet 158 min under 81-95 % cirrus, som skjoldet
dømmer til max 3; undersøgt i næste afsnit.

## Opfølgning: cirrus-skjoldet mod flyvninger time for time

Spørgsmål: er skjoldet (høj sky >= 85 % inden for 3 timer og >= 50 % nu,
cap 3) for hårdt, når Slaglille 15/8 fløj 158 min under det?

**Data.** Startlister for alle 18 sæsondage plus weekenden (5467
flyvninger med start- og landingstid) og fulde timedata fra
historical-forecast-endpointet for 17 pladser (Hammer udeladt). For hver
time kl. 11-17 med signalflyvninger i luften: "bar" = en flyvning på
>= 60 min var i luften i timen, "kort" = alle flyvninger i timen < 30 min.
986 aktive timer, 873 med entydigt facit.

**Skjoldet har reelt signal:**

| Timer | Bar |
|---|---|
| Uden skjold, høj sky < 40 % | 71 % |
| Uden skjold, høj sky 40-85 % | ~55 % |
| **Skjold aktivt (score 2-3)** | **41 % (61/148)** |
| Skjold, direkte sol < 100 W/m² (sæsonskaleret) | 17 % |
| Skjold, direkte sol >= 100 W/m² | 35-61 % |

**Ingen variant slår det nuværende skjold.** Afprøvet: cap 3 kun for tyk
cirrus (direkte < 100 W/m² eller direkte-andel < 0.3) og ellers cap 5
eller intet cap, samt helt uden skjold:

| Variant | Skjold-timer: score bar / kort | Alle timer: adskillelse | Træfsikkerhed (score >= 5 = bar) |
|---|---|---|---|
| **Nuværende (cap 3)** | 2.41 / 2.41 | **2.68** | **0.691** |
| Tyk -> 3, tynd -> intet cap | 3.88 / 3.53 | 2.53 | 0.686 |
| Tyk -> 3, tynd -> 5 | 3.17 / 3.12 | 2.57 | 0.686 |
| Uden skjold | 3.88 / 3.58 | 2.52 | 0.685 |

Inden for skjold-timerne kan scoren ikke skelne bar fra kort, hverken med
eller uden skjold: modellens høj-sky-andel og stråling indeholder ikke
oplysningen om, hvorvidt cirrussen i virkeligheden var tynd eller tyk.
Direkte stråling udpeger kun de klart døde timer (< 100 W/m²), og dem
capper strålings-gaten i forvejen for de flestes vedkommende.

**Konklusion: skjoldet ændres ikke.** Slaglille 15/8 er en reel miss, men
i en gruppe hvor 41 % af timerne kunne flyves; det er en grænse for
prognosen, ikke en forkert tærskel. Skjoldet er netto den bedste af de
afprøvede regler.

Timer uden skjold med score 0-3 bar i 49 % af tilfældene (89/181), mod
31 % ved score 3-5; undersøgt i næste afsnit.

## Opfølgning: hvorfor lave scores flyves, og overskyet-cappet

Samme 873 timer. Hver times kald til `apply_dealbreakers_v2` blev
opfanget, og hvert caps betingelse genberegnet, så det kunne ses hvilket
cap der satte den endelige score.

**Hvilke caps binder, og hvor ofte blev der alligevel fløjet:**

| Cap | Timer hvor det binder | Bar |
|---|---|---|
| **Skydække >= 87 % (cap 2)** | **238** | **47 %** |
| Mellemhøjt dække | 59 | 30 % |
| Cirrus-skjold | 63 | 41 % |
| Grænselag < 900 m (cap 5) | 42 | 59 % |
| Lapse < 0.65 / < 0.70 / < 0.50 | 20 / 11 / 4 | 25 / 27 / 25 % |
| Nedbør | 9 | 33 % |
| (alle timer) | 873 | 64 % |

Af de 202 timer med score 0-3 uden skjold stod skydække-cappet alene for
128 (54 % bar). Lapse-, dække- og nedbørs-caps er velkalibrerede.

**Den ucappede score rangerede stadig:** i timerne hvor skydække-cappet
bandt, bar 62 % ved ucappet score 7-10, 42 % ved 5.5-7, 18 % ved 4-5.5 og
0 % under 4. Cap 2 fladede det ud. Hverken direkte sol, lav sky eller
lagvægtet dække skilte bar fra kort.

**Afprøvede varianter:**

| Variant | Træfsikkerhed | Bar pr. scorebånd 0-3 / 3-5 / 5-6.5 / 6.5-8 / 8+ | Dage sommer / okt |
|---|---|---|---|
| Cap 2 (før) | 0.691 | 46 / 37 / 55 / 73 / 85 % | 85.4 / 13.2 |
| Cap 4 | 0.691 | 28 / 47 / 55 / 73 / 85 % | 85.5 / 12.6 |
| Cap 5 | 0.721 | 28 / 40 / 59 / 73 / 85 % | 85.6 / 12.0 |
| -2 point | 0.726 | 24 / 43 / 59 / 75 / 85 % | 85.7 / 12.5 |
| **-2 point, loft 5 (valgt)** | **0.726** | **24 / 43 / 62 / 73 / 85 %** | 85.6 / 12.5 |

**Implementeret:** `OVERCAST_COVER = 87`, `OVERCAST_PENALTY = 2.0`,
`OVERCAST_MAX_SCORE = 5` i v2 (v1 er urørt). Kalibreringen bliver
monoton (højere score betyder altid større chance), træfsikkerheden stiger
3.5 procentpoint, dagsvalideringen er uændret, og referencedagene 8/8 og
9/8 består. Loftet 5 betyder at en næsten overskyet time aldrig viser
"God termik".

Forbehold: timedata fra historical-forecast (ikke præcis det publicerede),
og "bar" tæller enhver time en flyvning på 60+ min rører.

---

## Opfølgning: begrænsende faktor i popup'en (punkt 9)

**Målt først.** 986 timer kl. 11-17 på 19 startlist-dage, nuværende kode,
[`limit9.py`](2026-10-05-analyse/limit9.py). `caps.py` var forældet: den
manglede lapse 2-180 m og CAPE og havde overskyet som cap 2.

Et loft satte scoren i 451 timer (46 %), og i 447 af de 518 timer under 6.5:

| Loft der satte scoren | Timer | Bar / kort |
|---|---|---|
| Cirrus-skjold (3) | 131 | 54 / 56 |
| Mellemhøj sky (2) | 70 | 18 / 38 |
| Overskyet (5) | 59 | 33 / 14 |
| Stråling | 39 | 16 / 21 |
| Grænselag < 900 m | 38 | 22 / 11 |
| Stråling + overskyet | 27 | 17 / 9 |
| Stabil luft | 27 | 2 / 20 |
| Vind/stød | 20 | 9 / 11 |
| Resten (termiktop, regn, CAPE, kombinationer) | 40 | |

50 timer har to eller tre lige lofter. De 71 lave timer uden loft skyldes den
vægtede sum (svag sol 41, svag lapse 30); efter aftale vises kun lofter.

**Implementeret.** `dealbreaker_caps_v2` (alle lofter som kode og værdi) og
`dealbreakers_v2` (score plus de bindende koder); `apply_dealbreakers_v2`
er nu en tynd indpakning med uændret returværdi. `compute_thermal_score_v2`
giver `limited_by`, publiceret som `data.limited_by` for flyvepladserne.
Popup'en viser en gul linje under kommentaren: "Holdes nede af for meget
vind eller stød (højst 4)."

**Kontrol.** Ingen score flyttet: 35 parametriserede tests sammenligner
med den gamle funktion, og produktionsstien gav samme score og samme koder
som analysen i alle 986 timer. `airfields.json` vokser 1 % gzippet (401 ->
406 KB); gitterpunkterne er uændrede (eksisterende test låser deres nøgler).

**Bemærket undervejs.** Mellemhøj sky-cappet (2) har den dårligste
træfsikkerhed af de hyppige lofter: 18 af 56 timer med facit bar alligevel.
Kandidat til samme time-for-time-forsøg som cirrus-skjoldet.

---

## Opfølgning: tæller `score_solar` dagens egne cumulus som dæmpning? (punkt 1)

Åbent punkt 2 i [2026-08-12-straale-gate.md](2026-08-12-straale-gate.md).
Samme 873 timer med facit, [`solar1.py`](2026-10-05-analyse/solar1.py) og
[`solarvar.py`](2026-10-05-analyse/solarvar.py).

**v2 har allerede taget det meste.** Den oprindelige sag, 8/8 kl. 19 (v1:
5.9 fordi 88,6 % vægtet dække var dagens egne cumulus), består i v2, fordi
`CU_ALLOWANCE = 40` gør de første 40 procentpoint lav sky gratis.

**Hvad lav sky ud over 40 % koster, og om det er fortjent.** I
cumulus-regimet (mellemsky < 30 %, høj sky < 50 %, 477 timer) falder
solscoren fra 7.8 til 4.4 når lav sky går fra 0 til 85 %+, og andelen bar fra
79 % til 50-63 %. Men direkte stråling sorterer langt bedre alene (0-150
W/m²: 48 % bar, 550-700: 89 %), og holdt fast inden for samme
strålingsbånd giver lav sky intet entydigt signal:

| Direkte stråling | Lav sky < 40 %: n, bar, solscore | Lav sky >= 40 %: n, bar, solscore |
|---|---|---|
| 0-150 | 58, 48 %, 4.5 | 29, 48 %, 3.2 |
| 150-250 | 65, 60 %, 6.0 | 25, 44 %, 4.5 |
| 250-350 | 49, 80 %, 6.9 | 24, 62 %, 5.4 |
| 350-450 | 72, 82 %, 7.6 | 16, 94 %, 6.6 |
| 450+ | 114, 87 %, 9.1 | 25, 68 %, 7.5 |

Skydækleddet tæller altså de samme cumulus som strålingsleddet allerede
har set, men forskellen er 1-1.5 point i solscoren, ~0.3 i slutscoren, og
lofterne sætter alligevel scoren i 46 % af timerne.

**Varianter** (time: adskillelse bar/kort og træfsikkerhed ved score >= 5;
dage: samlet afvigelse fra facit-båndet og antal i bånd):

| Variant | Sep | Træf | Sommer afv / i bånd | Okt afv / i bånd |
|---|---|---|---|---|
| **Nu (40 % gratis)** | **2.63** | **0.726** | **85.6 / 38 af 58** | **12.5 / 16 af 24** |
| 60 % gratis | 2.64 | 0.726 | 86.1 / 38 | 12.2 / 16 |
| 80 % gratis | 2.64 | 0.725 | 86.4 / 38 | 12.0 / 16 |
| Lav sky tæller ikke | 2.64 | 0.726 | 86.5 / 38 | 12.0 / 16 |
| Lav sky halv vægt | 2.64 | 0.726 | 86.1 / 38 | 12.2 / 16 |
| Kun direkte sol | 2.60 | 0.721 | 85.6 / 36 | 10.0 / 16 |

Referencedagene 8/8 og 9/8 og sæsonscenarierne består under alle varianter.

**Konklusion: uændret.** Ingen variant flytter timeniveauet ud over støjen,
og sommer og oktober trækker i hver sin retning med under 1 point. "Kun
direkte sol" er den eneste med en tydelig oktober-gevinst, men koster to
sommerdage i bånd og træfsikkerhed. Punktet kan lukkes; genåbnes hvis
efterårs- og forårsdagene (punkt 8) viser et mønster.

---

## Opfølgning: bedre lavniveaudata fra icon_seamless / dmi_seamless (punkt 7)

Hentet fra historical-forecast for de 18 pladser og 19 dage
([`pull_models.py`](2026-10-05-analyse/pull_models.py), 108 kald) og målt mod
de 873 timer med facit ([`lowlevel7.py`](2026-10-05-analyse/lowlevel7.py)).
AUC = sandsynligheden for at en bar time rangerer over en kort; 0.5 er
ingen information. "Inden for scorebånd" sammenligner kun timer i samme
produktionsscore-bånd, altså om feltet tilføjer noget scoren ikke har.

| Felt | AUC alene | Inden for scorebånd | Inden for score x termiktop |
|---|---|---|---|
| Produktionens score | 0.769 | | |
| Produktionens lapse_rate | 0.771 | 0.705 | 0.631 |
| Produktionens termiktop | 0.798 | 0.733 | 0.633 |
| icon termiktop (950/925/900/850) | 0.805 | 0.738 | 0.663 |
| icon lapse 2 m -> 900 hPa | 0.751 | 0.685 | 0.609 |
| icon laveste lags-lapse < 1.5 km | 0.700 | 0.670 | 0.598 |
| icon sensibel varmestrøm | 0.705 | 0.633 | 0.553 |
| dmi lapse 2-180 m | 0.676 | 0.607 | 0.541 |

**Fund.**
- best_match leverer allerede `temperature_1000hPa`; det er 950/900 hPa og
  80/120/180 m-temperaturen der mangler. Derfor har **lapse 2-180 m-cappet
  (1/2) data i kun 168 af 5040 flyvepladstimer** i produktionen. Med DMI's
  180 m ville det ramme 7 af 873 timer, alle korte og allerede scoret ~3;
  med ICON's ingen. Det er ikke værd at genoplive.
- Kun ICON's termiktop tilføjer en smule ud over produktionens (0.663 mod
  0.633 i den hårdeste kontrol). Varmestrøm og ICON-lapse tilføjer mindre end
  det produktionen allerede har. best_match 925 hPa afviger under 1 K fra
  ICON i 91 % af timerne.
- ICON kan ikke hentes i samme kald uden at fordoble alle variable, så det
  koster et ekstra kald pr. batch (27 -> 54) netop hvor GitHub-runnerne
  drosles.

**Konklusion: ikke implementeret.** Det egentlige fund er at produktionens
egen lapse_rate og termiktop stadig sorterer bar fra kort inden for
scorebåndene (0.705 / 0.733): scoren udnytter information den allerede har
for dårligt. Det peger på åbent punkt 3 (lapse-vægten) og termiktoppens
vægt, som kan afprøves uden nye API-kald.
