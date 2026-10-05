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

**Nyt åbent punkt:** Slaglille 15/8 blev fløjet 158 min under 81-95 %
cirrus, som skjoldet dømmer til max 3. Værd at tjekke mod andre
cirrus-dage før skjoldet ændres; det står også som fælles miss i
sæson-referatet.
