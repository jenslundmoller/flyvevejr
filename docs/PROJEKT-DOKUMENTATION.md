# Termik-forecast Danmark — Projektdokumentation

## Oversigt

Automatisk termik-vurdering for danske svæveflyvere. Systemet henter vejrdata fra Open-Meteo API, beregner for 262 punkter over hele Danmark:

1. **Termik-score (0-10)** — samlet vurdering af flyveforhold
2. **Termik-tophøjde (m)** — maks. brugbar termikhøjde via parcel-teori (jf. [Referat 2026-05-28](Referat/2026-05-28-termik-top.md))

Resultaterne vises som to skifteligbare interaktive kortlag på **https://flyvevejr.dk**. Data opdateres automatisk hver 3. time kl. 05-17 UTC via GitHub Actions på en selvhostet runner (OMV-maskinen derhjemme).

---

## Baggrund

Projektet er baseret på en grundig analyse af Meteorologi SPL-teori kompendiet (EASA/ICAO pensum for svæveflyvere). Alle faktorer der påvirker termik — positivt og negativt — er identificeret fra kompendiet og omsat til en kvantitativ scoringsmodel.

### Faktorer der fremmer termik

| Faktor | Forklaring | Målbar parameter |
|--------|------------|-----------------|
| Labil atmosfære | Lagdelingsgradient >1°C/100m — luften stiger frit | Lapse rate fra overfladetemperatur og temp i 850 hPa |
| Stærk solindstråling | Jordoverfladen opvarmer luften. Kræver solvinkel >45° | Skydække + shortwave radiation |
| Sæson | Maj, juni, juli er bedst i DK (høj sol, koldere luftmasser) | Dato |
| Tidspunkt | Stærkest kl. 14-15 | Klokkeslæt |
| Kold luftmasse | Luft koldere end jorden skaber instabilitet | Vindretning, temperatur |
| Koldluftsadvektion | Kold luft i højden labiliserer atmosfæren | Temperaturtrend i 850 hPa |
| Bagsidevejr efter koldfront | Klar luft, god sigt, cumulus-skyer | Stigende lufttryk |
| Stor dugpunktsspredning | 8-15°C spread giver høj skybase uden udkagning | Temperatur minus dugpunkt |
| Moderat vind (5-15 kt) | Udløser termikbobler, muliggør skygader | Vindstyrke |
| Fralandsvind | Holder søbrisen væk | Vindretning ift. kystlinje |
| Tør, mørk jord | Sand, hede, kornmarker, byer opvarmes hurtigt | Nedbør seneste dage |
| Nordøstlige vinde (sommer) | Tør, ustabil polarluft med god sigtbarhed | Vindretning + temperatur |

### Faktorer der hæmmer termik

| Faktor | Forklaring | Målbar parameter |
|--------|------------|-----------------|
| Stabil atmosfære / inversion | Opstigende luft presses ned igen | Lapse rate <0.65°C/100m |
| Søbrise | Kølig havluft ødelægger termikken. Særligt vigtigt i DK | Kystafstand, vindretning, land/hav temp-forskel |
| Varm luftmasse | Varmere end jorden → inversionslag → stabilitet | Luftmassetype |
| Varmefront | Tiltagende skydække, sol forsvinder | Faldende lufttryk, skytype |
| Høj luftfugtighed / lav spread | Lav skybase → udkagning (skyer blokerer sol) | Dugpunktsspredning |
| Overskyet (>5/8) | Blokerer solindstråling | Skydække |
| For kraftig vind (>25 kt) | Termikbobler forrevet, turbulent | Vindstyrke |
| Vindstille | Ingen dynamisk udløsning af termikbobler | Vindstyrke = 0 |
| Våd jord / vandområder | Dårlig opvarmning, energi bruges til fordampning | Nedbør seneste dage |
| Overudvikling (Cb) | Cumulus → cumulonimbus → byger/torden | CAPE >1000 J/kg |
| Continental tropisk luft | Sahara-vinde: stabilt nær jorden trods varme | Sydlig vind + høj temp i højden |
| Nedbør | Afkøler jordoverfladen | Nedbørsmængde |

---

## Arkitektur

```
Open-Meteo API (gratis, ingen nøgle)
       │
       ▼
┌──────────────────┐     ┌────────────────┐     ┌─────────────────────┐
│ Python-script    │────▶│ JSON-datafiler │────▶│ Statisk HTML/JS     │
│ (Actions på OMV, │     │ current.json   │     │ Leaflet.js heatmap  │
│  05-17 UTC /3 t) │     │ airfields.json │     │ flyvevejr.dk        │
└──────────────────┘     │ meta.json      │     └─────────────────────┘
                         └────────────────┘
```

### Dataflow

1. GitHub Actions kører `python -m termik` kl. 05:15, 08:15, 11:15, 14:15 og 17:15 UTC på den selvhostede runner på OMV (reserve: GitHubs egne runnere, se GitHub Actions nedenfor)
2. Scriptet henter først den målte havtemperatur for 158 havceller fra
   Open-Meteos marine-API (2 lette kald; fejler de, bruges klimatologien),
   derefter vejrdata fra Open-Meteo for 262 punkter, 30 flyvepladser
   og 232 gitterpunkter, i 27 batch-kald a 10 punkter
3. For hvert punkt beregnes termik-score for hver time, 7 dage frem
4. Resultatet skrives som JSON-filer
5. GitHub Actions committer de opdaterede JSON-filer og pusher
6. Kørslen starter GitHub Pages-deploy via REST-API'et (`termik/tools/dispatch_workflow.py`)
7. https://flyvevejr.dk viser den opdaterede side

### Hosting

| Komponent | Tjeneste |
|-----------|----------|
| Kode + data | GitHub repo `jenslundmoller/flyvevejr` |
| Automatisering | GitHub Actions; forecast-jobbet på en selvhostet runner på OMV, øvrige jobs på GitHubs runnere (gratis for public repos) |
| Webhosting | GitHub Pages |
| Domæne | flyvevejr.dk |
| DNS | Cloudflare (CNAME → jenslundmoller.github.io, proxy fra) |
| SSL | GitHub Pages (Let's Encrypt) |
| Vejrdata | Open-Meteo forecast- og marine-API (gratis, ingen nøgle) |

---

## Geografi

### Svæveflyvepladser (30 stk)

Baseret på listen fra [Svæveflyveklubber i Danmark (Wikipedia)](https://da.wikipedia.org/wiki/Sv%C3%A6veflyveklubber_i_Danmark).

**Nordjylland:** Aars (Aviator Aalborg), Sæby/Ottestrup (Nordjysk), Vinkel/Skive, Svævethy/Mors, Viborg

**Midtjylland:** True/Aarhus, Arnborg (DSvU), Chr. Hede/Silkeborg, Skinderholm/Herning, Lemvig, Nr. Felding/Holstebro, Videbæk

**Sydjylland:** Billund, Skrydstrup, Gesten/Kolding, Rødekro, Tønder, Vejle, Bolhede

**Fyn:** Broby

**Sjælland:** Gørløse, Frederikssund, Kalundborg, Kongsted, Ringsted/Midtsjælland, Tølløse, Lolland-Falster

**Bornholm:** Rønne

### Grid-punkter (232 stk)

Et 0.2° × 0.2° grid over Danmark (54.5°N-57.8°N, 8.0°E-15.2°E). Punkter i havet er filtreret fra med en polygon-baseret landmassedetektering for Jylland, Fyn, Sjælland, Lolland-Falster og Bornholm.

**Total: 262 punkter** (232 grid + 30 svæveflyvepladser) med vejrdata for hver time i 7 dage.

---

## Scoringsmodel

Produktionen kører **scoring v2** (`termik/scoring_v2.py`), som implementerer
justeringer fra DSvU-hæftet "Svæveflyvningen og vejret" oven på den
oprindelige model. Den gamle score (`termik/scoring.py`) er urørt og er
rollback-stien: sæt `SCORING_VERSION = "v1"` i `termik/config.py`. Hver
publiceret time bærer `scoring_version` som revisionsspor. Se
[plan](plans/2026-08-25-scoring-v2-dsvu-haefte.md) og referaterne fra
2026-08-25 for kalibrering og validering.

### v2's justeringer fra hæftet

1. **Vind**: 5-10 kt er ideal (før 5-15); 15-25 kt mildnes ved koldluftsadvektion (skygader).
2. **Cu-allowance**: de første 40 procentpoint lav sky er gratis i solscoren (Skema 1: 1-4/8 cumulus er det optimale skybillede).
3. **Cirrus-fradrag**: -0.5 ved ≥40 % høj sky, -1.0 ved ≥70 % (fuldt fradrag kræver næsten tæt lag).
4. **Basehøjde-kobling**: cap 4 ved base under 600 m AGL (kun i sol, SW ≥400, og kun ved positiv lcl/ti_zero-dom), +0.5 bonus over 1200 m. Båndene testes mod den ukorrigerede base, min(LCL, TI-nul).
5. **Søbrise skalerer med land/hav-forskellen** i stedet for v1's faste pålandsstraf; **5b**: pålandsvind ≥8 kt med stabil havluft (havtemp minus 850-temp under 7) løfter drivkraften til maksimum.
6. **Varmehukommelsen forlænges** ved koldluftsadvektion (faktor 0.65 → 0.75); ingen spejlvendt varme-malus (modbevist på referencedagen 8/8).
7. **Temperaturvægt sænket** (kold luftmasse behøver ikke høje temperaturer).

Tilføjet 2026-10-05 efter startlist-weekenden 3.-4. oktober (se [Referat 2026-10-05](Referat/2026-10-05-startlist-weekend-oktober.md)):

8. **Sæsonskaleret stråling**: alle absolutte W/m²-tærskler (strålings-gaten, varmehukommelsens gulv, solscorens 600 W/m² og basehøjde-cappets SW-krav) ganges med sin(middagssol i dag) / sin(middagssol 8/8), klampet til [0.5, 1.0]. Maj-juli er uændret; 4/10 er faktoren 0.63.
9. **Blandingslagets lapse**: er 2 m -> 925 hPa >= 0.95 og grænselaget >= 900 m, scores og cappes på den største af 850- og 925-lapse. Fanger dage hvor inversionen ligger under 850 hPa over et fuldt blandet lag. `lapse_rate` er den scorede værdi, `lapse_rate_850` revisionssporet.
10. **Terrænhøjde**: alle punkter har `elevation_m` (hardcodet for flyvepladser, `termik/grid_elevations.json` for griddet, hentet én gang med `termik/tools/fetch_elevations.py`), så parcel-beregningen starter i den rigtige højde.
11. **Målt havtemperatur i søbrisen**: én gang pr. kørsel hentes havoverfladetemperaturen for en fast havcelle pr. kystnært punkt (`termik/sea_points.json`, valgt med `termik/tools/fetch_sea_points.py`) fra Open-Meteos marine-API. Fallback er en målt klimatologi interpoleret pr. dag. Den gamle månedstabel lå 1-3 grader for koldt og faldt 4 grader natten til 1/10.
12. **5b ser også det nedre lag**: havluften kaldes kun stabil når både hav -> 850 hPa (< 7 K) og hav -> 925 hPa (< 0.47 grader/100 m, samme grænse pr. 100 m) er stabile, så et låg mellem 925 og 850 hPa ikke skjuler ustabil havluft.
13. **Overskyet er en straf, ikke et cap 2**: rå skydække ≥ 87 % giver -2 point og loft 5. Cap 2 kastede en rangering væk der stadig virkede (piloterne holdt sig oppe i 47 % af de cappede timer).

Tilføjet 2026-10-06 efter sammenligning med FlightRadars termikbobler (se [Referat 2026-10-06](Referat/2026-10-06-termiktop-mod-flightradar.md)):

14. **Mindre, sæsonskaleret fradrag på termiktoppen**: den viste top er den rå base minus 100 m i fuld sol til 300 m uden sol (v1: 200-500 m), og "fuld sol" er 600 W/m² gange strålingens sæsonfaktor. Mod 27.500 bobler i Jylland og på Fyn lå toppen 150 m for lavt over sæsonen og 380 m i september-oktober; nu 43 og 210 m. Scoren er uændret (den bruger den rå base).

### Basis-scorer (vægtet sum, v2)

| Faktor | Vægt | Score 10 | Score 0 |
|--------|------|----------|---------|
| Lapse rate (stabilitet) | 30% | ≥1.2°C/100m (meget labil) | <0.65°C/100m (stabil) |
| Solindstråling | 24% | Stærk **direkte** stråling; første 40 pp lav sky gratis | Overskyet + ingen stråling |
| Spread (dugpunktsspredning) | 15% | 8-15°C (optimal skybase) | <3°C (tåge-risiko) |
| Vindstyrke | 10% | 5-10 kt (optimal udløsning) | >35 kt |
| Vindstød | 10% | Effektiv vind ≤20 kt | Stød ≥35 kt |
| Temperatur | 4% | Høj overfladetemperatur | <5°C |
| Nedbør | 7% | Tørt, ingen nedbør seneste 6t | Aktiv nedbør |

### Modifikatorer (justerer basis-scoren)

| Modifier | Effekt | Betingelse |
|----------|--------|-----------|
| CAPE-bonus | +0.5 / +1.0 | CAPE >300 / >700 J/kg |
| Tryktendens | +0.5 / -0.5 | Stigende / faldende >1.5 hPa/3t |
| Koldluftsadvektion | +0.5 | Faldende temp i 850 hPa |
| Søbrise-penalty | -1 til -3 | Kystpunkter med pålandsvind |

### Dealbreakers (hårdt loft for scoren)

| Betingelse | Max score | Kode (`limited_by`) | Begrundelse |
|-----------|-----------|------|------------|
| Lapse rate <0.50 / <0.65 / <0.70 | 1 / 3 / 5 | `stable` | Inversion eller stabil atmosfære: meget begrænset termik |
| Lapse 2-180 m <0.3 / <0.5 | 1 / 2 | `surface_stable` | Stabilt lag ved jorden |
| Skydække ≥87% | v1: 2. v2: -2 point og loft 5 | `overcast` | Sol blokeret. Læser den **rå** total, ikke lagvægtet, se nedenfor. v2 bevarer rangeringen (Referat 2026-10-05) |
| Effektiv stråling <400 / <250 / <100 W/m² (v2: sæsonskaleret) | 5 / 3 / 1 | `radiation` | For lidt opvarmning til konvektion |
| Grænselagshøjde <900 m | 5 | `shallow_bl` | For tyndt arbejdslag til at blive oppe i |
| Høj sky ≥85% nu og i de sidste 3 timer | 3 | `cirrus` | Optisk tykt cirrus-skjold lukker jorden ned |
| Mellemhøj sky ≥85% | 2 | `mid_cloud` | Solidt altostratus-dække |
| Aktiv nedbør | 1 | `rain` | Jorden afkøles |
| Vind >35 kt, stød ≥30/≥35 kt, effektiv vind (vind + stød/2) >25/>30/>35 kt | 2; 2/1; 4/2/1 | `wind` | For turbulent til brugbar termik |
| Temperatur <5°C | 3 | `cold` | For koldt til konvektion |
| CAPE >1000 / >1500 J/kg | 7 / 5 | `cape` | Byge- og tordenrisiko |
| Base under 600 m over terræn trods god sol (v2 punkt 4) | 4 | `low_top` | For lidt højde at arbejde i |

**Begrænsende faktor (siden 2026-10-05).** `scoring_v2.dealbreaker_caps_v2` giver alle lofter der rammer timen, og `dealbreakers_v2` giver scoren plus koderne for de lofter der satte den: det laveste loft, når det ligger under scoren efter overskyet-straffen, og alle ved lige lofter. Overskyet-straffen alene er ikke et loft. Koderne publiceres pr. time som `data.limited_by` for flyvepladserne (tom liste når intet loft bandt, og altid i v1); gitterpunkterne får dem ikke. Målt på 986 timer kl. 11-17 med startlist-facit binder et loft i 46 %, oftest cirrus-skjoldet (131), mellemhøj sky (70) og overskyet (59). Se [Referat 2026-10-05](Referat/2026-10-05-startlist-weekend-oktober.md).

Lapse rate-dealbreakeren er den vigtigste: **uden atmosfærisk instabilitet kan der ikke være termik**, uanset hvor godt de andre faktorer ser ud. Dette fanger f.eks. "Sahara-dage" med 30°C og blå himmel men stabil luft i højden.

Strålings-, grænselags-, cirrus- og mellemsky-cappene kom til i august 2026, kalibreret mod to pilot-verificerede dage. Se [Referat 2026-08-12](Referat/2026-08-12-straale-gate.md). To ting er værd at kende:

- **Effektiv stråling** er ikke øjebliksstrålingen. Grænselaget holder på varmen en time eller to efter solen er begyndt at falde, så gaten krediterer en andel af de sidste tre timers højeste værdi. Den kredit bortfalder når skydækket er steget væsentligt hen over vinduet, for så blev opvarmningen skåret over af en front og ikke af solnedgang.
- **Caps læser den rå `cloud_cover`-total, ikke lagvægtet dække**, modsat `score_solar`. Det er afprøvet og rullet tilbage: i `best_match` modsiger totalen og lagene hinanden i begge retninger, og lagvægtning læser en god dags egne termikcumulus som overtrukket. Cirrus når caps gennem de to lagspecifikke skjolde i stedet.

### Solindstråling — håndtering af cirrus-skyer

`score_solar` bruger to forfinelser, så cirrus straffes korrekt (jf. [Referat 2026-05-24](Referat/2026-05-24-cirrus-direct-radiation.md)):

- **Vægtet skydække:** `effective_cloud = cc_low*1.0 + cc_mid*0.7 + cc_high*0.5`. Cirrus dæmper ca. halvt så meget som lav stratus per % skydække.
- **Direkte stråling (ikke total SW):** `direct_radiation / 600 W/m²` for fuld score. Cirrus dæmper total SW kun lidt, men halverer ofte direkte stråling og fordobler diffus-andelen, det er den direkte-andel, der driver differentiel jordopvarmning og dermed termik-trigger.

### Score-labels

| Score | Label | Farve |
|-------|-------|-------|
| 9-10 | Fremragende termik | Rød |
| 7-8 | God termik | Orange |
| 5-6 | Moderat termik | Gul |
| 3-4 | Svag termik | Lyseblå |
| 0-2 | Ingen brugbar termik | Mørkeblå |

### Søbrise-model (v2, punkt 5 og 5b)

Danmark er meget kystnært, og søbrisen er en af de vigtigste termik-dræbere. For hvert punkt beregnes:

1. **Kystafstand** (forudberegnet, statisk); straffen skaleres med afstanden, max effekt inden for 80 km
2. **Vindretning vs. kystretning** — er vinden fralands eller pålands?
3. **Land/hav-temperaturforskel** (havet målt, se punkt 11 ovenfor) driver risikoen; er forskellen ≤2 grader, er der ingen straf (kryds-plads-studiet 2026-08-25: 8/8 pålandsdage med lille forskel bar, median 174 min)
4. **Havluftens instabilitet (5b)**: pålandsvind ≥8 kt med stabil havluft (havtemp minus 850 hPa-temp under 7, og hav -> 925 hPa under 0.47 grader/100 m) løfter drivkraften til maksimum uanset land/hav-forskellen. Konvektiv havluft (kold luftmasse over varmt sensommerhav) bærer derimod termik med ind over land.

### Validering

Ud over de syntetiske scenarier ([scoring-scenarios.md](scoring-scenarios.md), v1-reference) er v2 valideret mod **virkelige flyvninger fra startlist.club**: 18 dage maj-august 2026, 88 plads-dage med facit (skolefly frafiltreret: samme fly med 3+ forskellige forsædepiloter samme dag tæller ikke). Resultat: v2 rammer 61/88 forventede bånd mod v1's 57/88, samlet afvigelse 51.6 mod 55.0, største enkeltfejl 1.6 mod 3.3. Se [sæson-valideringen](Referat/2026-08-25-startlist-saeson-validering.md) og [pålandsvinds-studiet](Referat/2026-08-25-paalandsvind-studie.md) (4180 plads-dage scannet).

Efterårsvalidering 2026-10-05 (3.-4. oktober, 24 plads-dage, plus regression mod sommerens 58): punkt 8-13 tager oktobers afvigelse fra 23.1 til 12.5 og bånd-træf fra 14/24 til 16/24, mens sommeren er uændret (38/58, afvigelse 85.3 -> 85.6). Samme dag blev der indført **validering time for time**: 873 timer med flyvninger på 18 sæsondage + 3.-4. oktober, hvor en time "bar" hvis en flyvning på 60+ min var i luften. Efter punkt 13 bar 24 / 43 / 62 / 73 / 85 % af timerne i scorebåndene 0-3 / 3-5 / 5-6.5 / 6.5-8 / 8+. Se [Referat 2026-10-05](Referat/2026-10-05-startlist-weekend-oktober.md) og [overdragelsen](Referat/2026-10-05-overdragelse.md); analysescripts i `docs/Referat/2026-10-05-analyse/`.

### Kommentargenerering

`termik/comments.py` genererer en kort dansk kommentar (2-3 sætninger). Struktur (siden popup-redesignet 2026-08-26): tal der står i popup'ens felter og grafik gentages ikke; sætningerne har faste roller:

- **Bindende faktor** (leder, når dagen er brugbar): "Toppen begrænses af skybasen, regn med ca. 1100 m." Styret af `thermal_top_limited_by`; "inversion"- og "saturated"-domme oversættes bevidst ikke ved brugbar score (de kan være falske hen over et superadiabatisk overfladelag): der falder teksten tilbage på stabilitetslinjen fra målt lapse rate. Siden 2026-10-05 er `lapse_rate` den scorede værdi (blandingslagets lapse når det gælder), så teksten og popup'ens lapse-måler følger scoren; 850 hPa-værdien står i `lapse_rate_850`.
- **Advarsler/observationer** (op til 2, prioriteret): cirrus-banker, søbrise, vindstød/effektiv vind, vind der øger i højden, Cb-risiko, bagsidevejr, tørtermik.
- **Termikvinduet** ("Termik ca. 11 til 19") genereres i frontenden af dagsforløbet og hører ikke til her.

---

## Open-Meteo API

### Endpoint

```
https://api.open-meteo.com/v1/forecast
```

Gratis, ingen API-nøgle. Understøtter multi-location i ét kald (kommaseparerede koordinater).

### Parametre der hentes

**Hourly (overflade):**
temperature_2m, dewpoint_2m, relative_humidity_2m, wind_speed_10m, wind_direction_10m, wind_gusts_10m, cloud_cover, cloud_cover_low, cloud_cover_mid, cloud_cover_high, precipitation, shortwave_radiation, direct_radiation, cape, surface_pressure, boundary_layer_height

**Højdelag (80/120/180 m):**
wind_speed/direction_80m/120m/180m

**Pressure levels — temperaturer:**
temperature_925hPa, temperature_850hPa, temperature_700hPa, temperature_600hPa

**Pressure levels — geopotential heights (til parcel-teori for termik-tophøjde):**
geopotential_height_925hPa, _850hPa, _700hPa, _600hPa

I alt 32 variable (2026-10-05). Open-Meteo tæller hver påbegyndte 10 variable som ét kald pr. punkt, så en kørsel koster ~1.000 af de 10.000 gratis kald i døgnet (262 punkter x 3,2 plus havtemperaturen).

**Pressure levels — vind:**
wind_speed_850hPa, wind_direction_850hPa

**Bemærk (målt 2026-10-05):** best_match henter trykniveauerne for Danmark
fra en model der kun har 1000/925/850 hPa i de nederste 1.6 km. 950, 900 og
800 hPa samt 80/120/180 m-temperaturen kom tomme tilbage for 252 af 262
punkter og hentes derfor ikke længere; kun Lolland og gitteret ved 54.5-54.7 N
fik dem. Fjernelsen flyttede 6 af 700 dagtimer på de 10 punkter (alle op til
3, via lapse 2-180 m-cappet) og termiktoppen dér med -45 m i middel, som nu
regnes som i resten af landet. Koden læser felterne stadig, hvis de findes. Parcel-beregningen og blandingslagets lapse
bygger reelt på 925 og 850 hPa; overflade-lapse-checket (2 m -> 180 m) kører
aldrig. `icon_seamless` og `dmi_seamless` leverer flere lavniveau-felter (se
åbent punkt 7 i [overdragelsen](Referat/2026-10-05-overdragelse.md)).

### Andre Open-Meteo-endpoints

| Endpoint | Brug | Hvornår |
|---|---|---|
| `marine-api.open-meteo.com/v1/marine` | `current=sea_surface_temperature` for havcellerne i `termik/sea_points.json` | Hver kørsel (2 kald) |
| `api.open-meteo.com/v1/elevation` | Terrænhøjde til `elevation_m` | Én gang, med `termik/tools/fetch_elevations.py` |
| `marine-api` (current) | Valg af havcelle pr. kystnært punkt | Én gang, med `termik/tools/fetch_sea_points.py` |
| `historical-forecast-api.open-meteo.com` | Kalibrering af dage ældre end 92 dage | Kun værktøjer (`compare_scores`, analyser) |

### Afledte beregninger

| Beregning | Formel |
|-----------|--------|
| Spread | temperature_2m - dewpoint_2m |
| Skybase (m) | spread × 125 |
| Skybase (ft) | spread × 400 |
| Lapse rate | (temperature_2m - temperature_850hPa) / 15; i v2 erstattet af 2 m -> 925 hPa når det lag er konvektivt (>= 0.95) og grænselaget >= 900 m |
| Tryktendens | Delta surface_pressure over 3 timer |
| Nedbør seneste 6t | Sum af precipitation for foregående 6 timer |
| Termik-tophøjde | TI=0 via tør-adiabatisk parcel-løft på multilevel-sondering (DALR = 9.8 K/km), cap'd med LCL (Bolton 1980 eq. 22), minus Hcrit-margin (v2: 100-300 m, lineært skaleret med shortwave_radiation, fuld sol sæsonskaleret; v1: 200-500 m). Se Referat 2026-05-28 og 2026-10-06. |

---

## Filstruktur

```
flyvevejr/
├── .github/
│   └── workflows/
│       ├── update-forecast.yml    # Henter vejrdata hver 3. time kl. 05-17 UTC
│       ├── rerun-failed-forecast.yml # Genstarter en fejlet forecast-kørsel
│       ├── forecast-fallback.yml  # Flytter kørslen til GitHub hvis runneren derhjemme er nede
│       └── deploy-pages.yml       # Deployer til GitHub Pages
├── .gitignore
├── docs/
│   ├── PROJEKT-DOKUMENTATION.md   # Dette dokument
│   └── plans/
│       ├── 2026-03-27-termik-forecast-design.md
│       └── 2026-03-27-termik-forecast-implementation.md
├── termik/
│   ├── __init__.py
│   ├── __main__.py                # Entry point: python -m termik
│   ├── config.py                  # Konfiguration (API, vægte, tærskler)
│   ├── locations.py               # 30 svæveflyvepladser + 232 grid-punkter
│   ├── grid_elevations.json       # Terrænhøjde pr. gitterpunkt (fetch_elevations)
│   ├── sea_points.json            # Havcelle pr. kystnært punkt (fetch_sea_points)
│   ├── scoring.py                 # Scoringsmodel v1 (rollback)
│   ├── scoring_v2.py              # Scoringsmodel v2 (produktion)
│   ├── comments.py                # Kommentargenerering på dansk
│   ├── fetch_weather.py           # Open-Meteo API + databehandling
│   ├── tools/                     # Håndværktøjer: replay_day, compare_scores,
│   │                              #   fetch_reference_day, fetch_elevations,
│   │                              #   fetch_sea_points, forecast_watchdog,
│   │                              #   dispatch_workflow
│   ├── cron_setup.sh              # Hjælpescript til lokal cron
│   ├── requirements.txt           # Python: requests, pytest
│   ├── output/
│   │   ├── index.html             # Hovedside
│   │   ├── style.css              # Styling (responsivt)
│   │   ├── app.js                 # Leaflet.js kort + interaktion
│   │   ├── CNAME                  # Custom domain: flyvevejr.dk
│   │   └── data/
│   │       ├── current.json       # Alle punkter, alle timer, 3 dage
│   │       ├── airfields.json     # Kun svæveflyvepladser
│   │       └── meta.json          # Tidsstempel, antal punkter
│   └── tests/                     # 504 tests (2026-10-06)
│       ├── conftest.py            # Stubber marine-kaldet; tests rammer aldrig nettet
│       ├── test_locations.py
│       ├── test_scoring.py        # v1 + termiktop
│       ├── test_scoring_v2.py     # v2-punkterne inkl. 2026-10-05-rettelserne
│       ├── test_reference_days.py # 8/8 og 9/8 med bagte timedata
│       ├── test_comments.py
│       ├── test_fetch_weather.py
│       ├── test_forecast_watchdog.py # Hvornår en kørsel flyttes til GitHub
│       ├── test_dispatch_workflow.py # Deploy-trigger uden gh
│       └── test_workflow_schedule.py # Kørselsplanen (dagtimer, frisk morgen)
```

---

## Frontend

### Kort (Leaflet.js)

- Centreret på Danmark (56.2°N, 10.5°E), zoom 7
- OpenStreetMap-basekort
- **Heatmap-lag** (leaflet-heat): Grid-punkternes termik-score som farve-overlay
- **Svæveflyveplads-markører**: Farvekodede cirkler der kan klikkes

### Farverampe

Mørkeblå (0) → Lyseblå (3) → Gul (5) → Orange (7) → Rød (10)

### Kontroller

- **Dagvælger**: 7 knapper (I dag, I morgen, Overmorgen, +3 til +6 dage)
- **Timeslider**: Kl. 06-21, opdaterer heatmap og markører i realtid
- **Favorit-plads**: vælg én flyveplads og se hele dagens forløb i sidepanelet
- **Kortlag**: vælg mellem to lag — Flyveforhold (score-heatmap) eller Termik-tophøjde (glat interpoleret, med højde-labels per celle ved zoom ≥ 9). Valget huskes i localStorage.
- **Opdater-knap**: ved siden af "Opdateret:"-teksten; henter nyeste data med `cache: no-cache` og genbygger markører, dagknapper og lag. Derudover genhenter appen automatisk ved `visibilitychange`, når den kommer i forgrunden og sidste hentning er over 30 min gammel (PWA'en genoptages ellers fra hukommelsen på mobil med timegamle data).
- **Vejr-widget**: lille kort i kortets venstre top (under zoom-knapperne) der viser vejret lige nu for favorit-pladsen. Se eget afsnit nedenfor.

### Kortlag — termik-tophøjde

Lag baseret på `compute_thermal_top()`-resultatet per grid-celle, renderet med samme glatte browser-interpolation og kystklipning som score-laget (siden 2026-08-25; null-celler udfyldes med nærmeste reelle værdi før interpolationen). Distinkt viridis-lignende palet (lilla → orange) for at undgå forveksling med score-laget. Værdier <500 m vises lilla, ~1500 m grøn (god dansk dag), 2500 m+ orange-rød (sjælden i DK). Højde-labels tegnes ovenpå ved zoom ≥ 9.

### Vejr-widget — vejret lige nu på favorit-pladsen

Et lille kort placeret som et Leaflet-kontrol i `topleft`, så det stables under
zoom-knapperne. Viser de aktuelle forhold for den valgte favorit-plads (jf.
[Referat 2026-05-29](Referat/2026-05-29-vejr-widget.md)).

- **Datakilde**: ingen ny API-kald. Widgeten læser den aktuelle lokale time for
  favorit-pladsen direkte fra `current.json` via `getPointAtTime(plads, 0, time)`.
  Data fornyes hver 3. time i dagtimerne via GitHub Actions, så "caching" sker
  gratis på data-laget. Opdateres ved page-load, ved favorit-skift, og hvert
  minut (følger uret uden reload).
- **Indhold**: stort temperaturtal + pladsnavn, dynamisk vejr-ikon (inline-SVG
  valgt ud fra `cloud_cover` + `precipitation`: klart / sol+sky / overskyet /
  regn), og en farvet bund-bjælke med termik-label farvet via `scoreToColor`.
- **Detalje-række** (folder ud ved hover på desktop): luftfugtighed, vind (kt +
  retningspil), Real Feel (Australian Apparent Temperature beregnet fra temp,
  fugtighed og vind), og lufttryk (hPa).
- **Synlighed**: skjult når ingen favorit-plads er valgt, og skjult helt på
  mobil (`<768px`) via media query.

### Popup ved klik på svæveflyveplads

Redesignet 2026-08-26 med prioriteret hierarki (design-forløbet ligger i sessionsrapporten, se [Referat 2026-08-26](Referat/2026-08-26-sessionsrapport.md)):

1. **Score-ring** med dagens gennemsnit kl. 10-18 (samme tal som favorit-panelet) og **termikvinduet** ("Termik ca. 11 til 19, bedst 13 til 15"), beregnet i frontenden af dagsforløbet (timer ≥5 hhv. ≥8.5).
2. **Kommentar** (bindende faktor + advarsler, se Kommentargenerering), og under den, når et loft satte timens score, en gul linje på almindeligt dansk: "Holdes nede af cirrusslør der skærmer for solen (højst 3)." Teksterne står i `LIMIT_TEXT` i `app.js`; ukendte koder springes over.
3. **Dagsforløb** (mini-søjlediagram).
4. **Tre heltetal**: Termiktop (med begrænsnings-årsag), Skybase (m + ft), Vind (retningspil + kt + stød).
5. **Termik**: højdeakse med termiksøjle, base- og blandingslag-linjer og cirrusbånd, plus lapse-måler med scoringens zonegrænser.
6. **Temperatur (°C)**: spread-termometer fra dugpunkt til temperatur på 0-30°-skala.
7. **Vind (knob)**: kompas med drejningsvifte (10/80/180 m, pilene peger med vinden) og styrkesøjler pr. højde med stødmærke.
8. **Himmel og sol**: skylag-bjælker (høj/mellem/lav), direkte sol; CAPE og nedbør kun når de er informative.

Popup-højden følger skærmen (vindueshøjde minus 150 px, min. 420): desktop viser det hele, mobil scroller i popup'en. Alle multi-level-felter kan mangle uden at vælte layoutet.

### Responsivt

Desktop: sidepanel til højre. Mobil (<768px): sidepanel som bund-panel.

---

## GitHub Actions

### update-forecast.yml

- **Trigger**: Cron `15 5-17/3 * * *` (05:15, 08:15, 11:15, 14:15, 17:15 UTC; ingen kørsler om natten, frisk prognose om morgenen; besluttet 2026-10-05) + manuel dispatch (valg af runner). 5 kørsler x ~1.000 = ~5.000 Open-Meteo-kald i døgnet.
- **Runner** (siden 2026-10-05): selvhostet på OMV-maskinen derhjemme (Debian 13, labels `self-hosted`, `flyvevejr`, i `/opt/gh-runner` som systembrugeren `gh-runner`, hærdet med en systemd-drop-in; se OMV-webhosting-referencen). Open-Meteo drosler GitHub-runnerne: halvdelen af kaldene hang 30 s derfra, hjemmefra intet ([Referat 2026-09-02, opfølgning 5/10](Referat/2026-09-02-api-robusthed.md)). Manuel dispatch med `runner=ubuntu-latest` kører på GitHub som reserve.
- **Kører**: Python (OMV: maskinens 3.13 i en venv; GitHub: setup-python 3.12; testsuiten består på begge), installerer requests, kører `python -m termik`. Deploy startes med `termik/tools/dispatch_workflow.py` (REST-API via requests), fordi OMV ikke har gh.
- **Committer**: Opdaterede JSON-filer til repo'et med bot-bruger
- **Push med rebase-retry** (siden 2026-08-26): kørslen tager ~20 min fra checkout til push, så et kode-push i det vindue flyttede main og fik datapushet afvist. Push-trinnet prøver nu op til 3 gange med `git pull --rebase` imellem; datacommits rører kun `termik/output/data/`, så rebasen er altid ren.

### rerun-failed-forecast.yml

Vagthund: trigges når en forecast-kørsel slutter. Fejlede den (og attempt < 3), ventes 60 s og de fejlede jobs genstartes. Bemærk to ting: listen i Actions viser én (oftest "skipped") kørsel pr. datakørsel, det er GitHubs workflow_run-mekanik og harmløst; og en genstart kører på det oprindelige commit-SHA, så den kan aldrig reparere en push-race (det gør rebase-retry ovenfor), kun transiente fejl som API-nedetid og runner-nedbrud.

### forecast-fallback.yml

Vagthund for den selvhostede runner, kører på GitHub hver halve time kl. 05-18 UTC (`5,35 5-18 * * *`). Har en forecast-kørsel stået i kø i mindst 15 min (en online runner tager den på sekunder), aflyses den og erstattes af én kørsel på `ubuntu-latest`. Reservekørsler (titel "(ubuntu-latest)") aflyses aldrig. Logikken er `termik/tools/forecast_watchdog.py` med tests. En aflyst kørsel trigger ikke rerun-workflowet, som kun reagerer på `failure`.

### Sikkerhed for den selvhostede runner (repoet er offentligt)

Besluttet 2026-10-05: repoet forbliver offentligt, fordi GitHub Pages fra et privat repo kræver en betalt plan. Til gengæld:

- **Ingen workflow må få en `pull_request`-trigger.** En fork kunne ellers køre kode på OMV.
- **Godkendelse af fork-workflows** er sat til "alle eksterne bidragydere" (Settings → Actions → General).
- **Kun GitHubs egne actions** (`actions/*`, `github/*`) må køres; alle workflows bruger kun dem.
- **Runneren er hærdet** på OMV: egen systembruger, `ProtectSystem=strict`, `ProtectHome=true`, og `/srv`, FlightRadar, hue-poller og cloudflared skjult med `InaccessiblePaths=`.

**Overvej i fremtiden** at gøre repoet privat og flytte siden væk fra GitHub Pages (Cloudflare Pages, eller OMV via den eksisterende Cloudflare Tunnel), så den selvhostede runner ikke hænger på et offentligt repo. Repoet er desuden ~920 MB, fordi hver kørsel committer ~14 MB JSON; en flytning er en naturlig anledning til at stoppe med at committe data. Se åbent punkt 20 og 19 i [overdragelsen 2026-10-05 (2)](Referat/2026-10-05-overdragelse-2.md).

### deploy-pages.yml

- **Trigger**: Push til main der ændrer `termik/output/**` + manuel dispatch
- **Kører**: Upload `termik/output/` som GitHub Pages artifact og deployer

---

## DNS-opsætning (Cloudflare)

| Type | Name | Content | Proxy |
|------|------|---------|-------|
| CNAME | @ | jenslundmoller.github.io | DNS only (grå sky) |
| CNAME | www | jenslundmoller.github.io | DNS only (grå sky) |

Cloudflare-proxy er slået fra for at undgå konflikt med GitHub Pages' eget SSL (Let's Encrypt).

---

## Test

269 automatiserede tests fordelt på 6 moduler (268 beståede, 1 `xfail`):

| Modul | Tests | Dækker |
|-------|-------|--------|
| test_locations.py | 8 | Datastruktur, koordinatvalidering, grid-dækning |
| test_scoring.py | 180 | Score-funktioner, dealbreakers, modifikatorer, scenario-tests, parcel-teori for termik-tophøjde |
| test_scenarios_multilevel.py | 24 | Multilevel-data scenarier (vindshear, BL-mixing) |
| test_comments.py | 17 | Kommentargenerering for alle vejrsituationer |
| test_fetch_weather.py | 30 | URL-bygning, response-parsing, trendberegninger, thermal_top-integration |
| test_reference_days.py | 10 | De to pilot-verificerede dage, med timedata bagt ind så de kører offline |

`xfail`'en er acceptkriterium 1 kl. 19 på 2026-08-08, bevidst efterladt åbent og markeret `strict=True`, så den siger til hvis den nogensinde begynder at bestå. Se [Referat 2026-08-12](Referat/2026-08-12-straale-gate.md).

Kør alle tests:
```bash
source termik/.venv/bin/activate
python -m pytest termik/tests/ -v
```

---

## Drift og vedligeholdelse

### Automatisk drift

Systemet kører fuldautomatisk via GitHub Actions. Forecast-jobbet kører siden 2026-10-05 på en selvhostet runner på OMV-maskinen derhjemme (`/opt/gh-runner`, systemd-unit `actions.runner.jenslundmoller-flyvevejr.omv.service`); opsætning, hærdning og fejlsøgning står i OMV-webhosting-referencen rev. 5. Er OMV nede, flytter `forecast-fallback.yml` kørslen til GitHubs runnere efter 15 min, så siden aldrig mangler data, men kørslen tager så 12-43 min på grund af Open-Meteos drosling. Hjemme-IP'en deler Open-Meteos gratis kvote (10.000 kald/døgn) med alt andet derhjemme, inklusive analysekald; produktionen bruger ~5.000.

### Manuel kørsel

```bash
cd /home/jens/AI/Flyvevejr
source termik/.venv/bin/activate
python -m termik
```

### Manuel trigger via GitHub

1. Gå til Actions-fanen på GitHub
2. Vælg "Update Termik Forecast"
3. Klik "Run workflow" og vælg runner (`self-hosted` = OMV, `ubuntu-latest` = GitHubs reserve)

Eller fra kommandolinjen: `gh workflow run update-forecast.yml -f runner=self-hosted`.

### Lokal udvikling med preview

```bash
source termik/.venv/bin/activate
python -m termik
cd termik/output && python3 -m http.server 8090
# Åbn http://localhost:8090
```

### Tilføj ny svæveflyveplads

Rediger `termik/locations.py` → AIRFIELDS listen. Tilføj en dict med:
```python
{"id": "ny_plads", "name": "Ny Plads", "lat": 55.50, "lon": 10.00,
 "region": "Region", "coast_distance_km": 30, "coast_direction_deg": 270}
```

### Juster scoringsmodel

Alle vægte og tærskler er i `termik/config.py`. Score-funktionerne er i `termik/scoring.py`. Kør tests efter ændringer for at verificere at scenarierne stadig giver forventede resultater.

---

## Teknologivalg

| Valg | Begrundelse |
|------|-------------|
| **Python** | Simpelt, godt til databehandling, nemt at køre i CI |
| **Open-Meteo** | Gratis, ingen nøgle, alle parametre inkl. pressure levels og CAPE |
| **Statisk HTML/JS** | Ingen server nødvendig, kan hostes gratis på GitHub Pages |
| **Leaflet.js** | Open source, let, god heatmap-plugin |
| **GitHub Actions** | Gratis CI/CD for public repos, cron-scheduling; selvhostet runner på OMV fordi Open-Meteo drosler GitHubs runnere |
| **GitHub Pages** | Gratis hosting, custom domain-support, automatisk SSL |

---

## Kilder

- **Meteorologi SPL-teori kompendium** (EASA/ICAO pensum) — primær kilde for termik-faktorer
- **Open-Meteo API dokumentation** — https://open-meteo.com/en/docs
- **Wikipedia: Svæveflyveklubber i Danmark** — https://da.wikipedia.org/wiki/Svæveflyveklubber_i_Danmark
