# Overdragelse 2026-10-06: Jylland, termiktoppen mod flyvninger, QNH/QFE

Fortsættelse af [2026-10-05-overdragelse-2.md](2026-10-05-overdragelse-2.md)
(den forrige aktuelle overdragelse) og
[2026-10-05-overdragelse.md](2026-10-05-overdragelse.md) (den fulde liste
over åbne punkter). Tal og begrundelser står i
[2026-10-05-startlist-weekend-oktober.md](2026-10-05-startlist-weekend-oktober.md)
(sidste afsnit, Jylland og 18/7) og
[2026-10-06-termiktop-mod-flightradar.md](2026-10-06-termiktop-mod-flightradar.md).
Analysescripts i [2026-10-05-analyse/](2026-10-05-analyse/README.md)
(`jy_*.py`) og [2026-10-06-analyse/](2026-10-06-analyse/README.md).
Prompt til at fortsætte står nederst.

## Kort fortalt

| Emne | Resultat | Scores ændret? |
|---|---|---|
| TopMeteo 4/10 | Samme regionale billede og tidsforløb som vores, men vores termiktop lå på ca. halvdelen af TopMeteos (og sondens) højde | Nej (analyse) |
| Jylland juli-september | 113 plads-dage: 69 % i bånd, men 61 % og adskillelse 1.8 på dage v2 ikke er kalibreret på. Scoren skelner dage bedre end pladser | Nej (analyse) |
| 18/7 overcall | Punkt 9 (blandingslagets lapse) over en inversion lige over 925 hPa. Kandidatregel fundet, ikke implementeret (åbent punkt 18) | Nej |
| Termiktoppen mod FlightRadar | 27.500 termikbobler: toppen lå 150 m for lavt over sæsonen, 380 m i september-oktober | |
| Årsagen | Schleswig-sonden: modellens LCL er op til 150 m for høj i stærk sol. Det gamle fradrag (200-500 m) gik den forkerte vej | |
| Nyt fradrag (v2) | 0.4 m pr. W/m² over 400 W/m², intet under. Fejl 232 -> 170 m, efterår 368 -> 135 m | Nej (43.680 timer) |
| Basehøjde-båndene | Testet mod rettet base på 218 plads-dage: ingen gevinst | Nej |
| Højdedatum | FlightRadar er GPS-højde over havet. Popup'en siger nu "Termiktop QNH" og "Skybase QFE" | Nej |

Ingen scoringsregel er ændret. Kun den viste termiktop, kommentarteksten
og etiketterne er ændret.

## Commits (alle pushet til main)

| Commit | Indhold |
|---|---|
| `15c5753` | Jylland mod startlist juli-september og 18/7 i startlist-referatet; `jy_*.py`; åbent punkt 18 |
| `8348286` | Referat 2026-10-06 (termiktoppen mod FlightRadar) og `2026-10-06-analyse/` |
| `e8585e2` | Første fradrag: 100-300 m, fuld sol sæsonskaleret. **Erstattet af `60b5575` samme dag** |
| `60b5575` | Fradraget følger strålingen: `hcrit_margin_v2(SW)`, `HCRIT_V2_SW_FREE_W_M2 = 400`, `HCRIT_V2_M_PER_W_M2 = 0.4`; `compute_thermal_top(..., margin_m=)`; sondescripts |
| `838b92e` | Etiketter "o.h."/"o.j." (afløst af næste) |
| `b8d0af4` | Etiketter "Termiktop QNH" og "Skybase QFE", "m QNH" i kommentar og kortlag, cache `termik-v23` |

En anden session arbejdede i samme mappe samtidig (OMV-drift, aftenkørsel
20:15 UTC, ny termiktop-palet `2739ede`/`e44f65f`/`f902580`). Dens commits
ligger flettet ind imellem; ingen konflikter.

## 1. TopMeteo 4/10

Ni skærmbilleder (kl. 09-16, timerne er UTC: termik med cumulus allerede
kl. 09 og alt gråt kl. 16 passer kun med UTC). Tallene er flyvbar højde i
hundreder af meter (10 = ~1000 m); TopMeteos forklaring siger hecto-feet,
men læst sådan ville 10 være ~3000 m, umuligt under sondens inversion ved
1500 m. Det er en antagelse.

- **Enige:** Sjælland og Sønderjylland holdt hele eftermiddagen,
  Nordjylland døde først; dagen sluttede samtidig.
- **Uenige:** TopMeteo startede termikken ~1 time før os og så Jylland
  lige så højt som Sjælland. Facit (startlist) gav os ret i rangeringen,
  men vores Jylland var for lavt på Christianshede og Bolhede.
- **Højden:** TopMeteo 1000-1200 m passede med sonden; vores top 450-650 m
  var for lav. Det førte til FlightRadar-analysen (afsnit 4).

## 2. Jylland juli-september mod startlist

Alle weekenddage 4/7-27/9, 11 jyske pladser (Hammer udeladt), samme
metode og bånd som oktober-referatet.

| | Plads-dage | I bånd | Adskillelse |
|---|---|---|---|
| Kalibreringsdagene 11/7-23/8 | 69 | 74 % | 3.5 |
| **Dage v2 ikke har set** | 44 | **61 %** | **1.8** |
| 3.-4. oktober (til sammenligning) | 14 | 64 % | |

Inden for samme dag adskiller scoren svage fra fløjne pladser med kun 1.6,
og 4 af 16 dage står forkert. Undercalls fordeler sig på cirrus, vind,
stråling og overskyet uden et dominerende loft. Overcalls er mest
enkeltpladser på dage hvor andre fløj godt (klubaktivitet), undtagen 18/7.

## 3. 18/7: punkt 9 over et låg

Fem jyske pladser scorede 7.5-8.9; der blev fløjet mange korte ture
(15-45 min). Lapse 2 m -> 925 hPa var 1.3-1.7 (overadiabatisk over 700 m)
med en inversion lige over 925 hPa. Uden punkt 9 falder de til 3.0-5.6.
Sonden viste mættet luft fra ~950 m helt op til inversionen ved 1230 m:
et stratocumulus-lag. Kandidatreglen "punkt 9 kun når 925 -> 850 >= 0"
giver 156/218 mod 154 i bånd og rører ikke oktober, men flytter kun 11
plads-dage på tre dage og har et modeksempel (Kalundborg 15/8). Ikke
implementeret.

## 4. Termiktoppen mod FlightRadar

- **Data:** FlightRadars `thermals`-tabel (read-only kopi af prod-DB'en på
  OMV), 19/5-4/10, 27.506 bobler. Hver boble til nærmeste flyveplads
  (<= 20 km) og time; timer med >= 3 bobler fra >= 2 flyvninger: 1.612
  plads-timer på 89 dage. Observeret top = 90 %-fraktilen af `end_alt`.
- **Luftrumslofter:** Sjælland stopper ved ~750 og ~1400 m QNH (oplyst af
  brugeren; synligt som top og knæk i højdefordelingen). 128 sjællandske
  timer ved loftet er censurerede. Jylland og Fyn er referencen.
- **Resultat før:** korrelation 0.70; toppen 150 m for lavt i Jylland, 380 m
  i september-oktober.

## 5. Årsagen og det nye fradrag

Schleswig-sonden kl. 12 UTC på alle 89 dage mod modellen i samme punkt:
i stærk sol er modellens 2 m-luft for varm (+0.9) og tør (-0.7), så LCL
ligger for højt i forhold til blandingslagets LCL i sonden:

| Modellens SW | Model-LCL minus sondens |
|---|---|
| 0-200 W/m² | -54 m |
| 200-400 W/m² | +31 m |
| 400-600 W/m² | +80 m |
| over 600 W/m² | +151 m |

Det sommerkalibrerede fradrag rettede altså en modelfejl og ramte for lavt
om efteråret. Det nye fradrag er tilpasset på maj-august og testet på
september-oktober:

| Jylland+Fyn, afvigelse / fejl | Maj-aug | Sep-okt (ikke set) | Hele sæsonen |
|---|---|---|---|
| v1 (200-500 m) | -126 / 219 | -378 / 368 | -152 / 232 |
| `e8585e2` (100-300 m) | -19 / 189 | -211 / 209 | -43 / 191 |
| **`60b5575`: 0.4 x (SW - 400), mindst 0** | **-1 / 173** | **-107 / 135** | **-16 / 170** |

Kontrol: scoren uændret i alle 43.680 dagtimer (26 pladser, 18/5-4/10).
30 overskyede timer med base under 100 m AGL skifter label fra
`margin_collapse` til `weak_solar`; ingen påvirker scoren. v1 er urørt.

## 6. Dagsscoren

Ændringerne flytter ikke scoren, fordi v2 scorer på den rå base. At
teste basehøjde-båndene (punkt 4) mod den rettede base gav ingen gevinst
(153 mod 154 i bånd på 218 plads-dage). Ikke ændret.

## 7. Højdedatum og etiketter

- FlightRadar gemmer OGN's `/A=`-højde. På 13.758 starter er den feltets
  højde ±1 m og følger ikke lufttrykket: GPS-højde over havet (eller QNH;
  ens på jorden). Knækket ved 1450-1500 m på Sjælland (loftet 1400 m QNH)
  peger på GPS. Modellen er geometrisk over havet: samme datum.
- Popup: **"Termiktop QNH"** (over havet) og **"Skybase QFE"** (spread x
  125 m over terræn). Brugeren bad om "QNE" for skybasen; QNE er
  trykhøjde på 1013.25 hPa, hvilket ingen af værdierne er, så QFE blev
  brugt og forklaret.

## Data og værktøjer

- **FlightRadar prod-DB:** kun via SSH med password (ingen nøgle til
  `omvadmin@10.71.21.238`). Brugeren kører de tre trin i
  `2026-10-06-analyse/README.md` i en rigtig terminal; `!` i Claude Code
  har ingen tty, så password-prompten fejler. Kopien er ~260 MB.
- **Radiosonder:** `https://weather.uwyo.edu/wsgi/sounding?datetime=YYYY-MM-DD%2012:00:00&id=10035&type=TEXT:LIST&src=UNKNOWN`
  (den gamle `cgi-bin`-URL giver 404). 89 dage tager ~15 min.
- **Vejrdata:** historical-forecast for hele sæsonen er ét kald pr. punkt
  (26 for flyvepladserne). Forecast-endpointet når kun 92 dage tilbage.

## Faldgruber fra i dag

- **To sessioner i samme mappe** igen: overdragelsen 2026-10-05 blev ændret
  på disken midt i sessionen. Tjek `git show` på egne commits, før de
  pushes; `git push` sender også den anden sessions commits.
- **Kalibreringsdage flatterer.** Valider altid på dage reglen ikke er
  tilpasset på (Jylland: 74 % mod 61 %).
- **Et fradrag kan skjule en modelfejl.** Det sommerkalibrerede fradrag så
  fint ud, indtil efteråret viste at det rettede modellens solfejl.
  Sammenlign med en uafhængig kilde (sonden) før en rettelse låses.
- **Sjællands højder er censurerede** af luftrumslofter og kan ikke bruges
  til at kalibrere toppen uden dagens loft.

## Åbne punkter

Videreført (numrene er bevaret): 2, 3, 4, 8, 10, 11, 12, 14, 15, 16, 17
fra [2026-10-05-overdragelse.md](2026-10-05-overdragelse.md) og 19, 20,
21, 23, 24 fra [2026-10-05-overdragelse-2.md](2026-10-05-overdragelse-2.md).

Ændret status:

5. ~~Hcrit-margin fra solindstråling~~ Fradraget er nu en målt rettelse
   af modellens LCL (0.4 x (SW - 400)), ikke en sikkerhedsmargin.
6. Termiktoppen stopper ved LCL: FlightRadar viser at den fløjne top
   følger basen (korrelation 0.70) og kun ligger over den om efteråret
   (punkt 25). Ikke længere en selvstændig fejl.
18. Punkt 9 over et låg: uændret, venter på flere dage med profilen. Den
    planlagte genkørsel efter weekenden 10.-11. oktober står ved magt.

Nye (25 er omnummereret fra "19" i den første overdragelse 5/10, som
kolliderede med overdragelsen (2)):

25. **De sidste ~100 m om efteråret:** piloterne kommer ~100 m over
    modellens base i september-oktober, selv om model og sonde er enige.
    Måske stiger basen over eftermiddagen (sonden er kl. 14 lokal). Hviler
    på 8-10 dage; saml flere.
26. **Den falske "inversion"-dom:** 25 timer (11 dage) viser top 0 m, men
    der blev fløjet til median 644 m AGL. Se på de grove trykniveauer og
    blandingslaget (samme mekanisme som punkt 9).
27. **Sjællands luftrumslofter:** registreres dagens loft (FlightRadar
    eller klubberne), kan Sjælland bruges som censurerede data.
28. **FlightRadar som facit for scoren:** `thermals.avg_climb_ms` måler
    termikstyrken direkte, også på hverdage. Gennemsnitlig stigning pr.
    plads og time mod scoren er et skarpere facit end startlistens
    flyvetid. Anbefalet næste skridt; brug det derefter til 3 (lapse-
    vægten), 18 og 21.
29. **Popup'ens højdeakse blander datum:** `buildAltAxis` i `app.js`
    tegner termiktoppen og LCL (over havet) på samme akse som
    blandingslaget (over terræn) og skybasen (spread x 125, over terræn,
    fallback når LCL mangler). Forskellen er terrænhøjden (op til ~170 m).
    Vælg ét datum for aksen.

Forslag til næste session: **28**, derefter **3 + 5 fra overdragelsen (2)
med FlightRadar-facit**, og **18** når weekendens data er inde.

## Prompt til at fortsætte

```
Continue the Flyvevejr work from docs/Referat/2026-10-06-overdragelse.md.
Read it first, then docs/Referat/2026-10-06-termiktop-mod-flightradar.md
and the two 2026-10-05 handovers it links to for the full open-point list.
Analysis scripts are in docs/Referat/2026-10-06-analyse/ and
docs/Referat/2026-10-05-analyse/ (see their READMEs).

Work through these one at a time. For each, show me the findings before
changing production code, validate any scoring change on days the rule was
not fitted on, write tests first, update the referat and
PROJEKT-DOKUMENTATION, and commit. Ask before pushing. Another session may
be working in the same folder: check what your commits contain before
pushing. Open-Meteo's free quota is shared with the OMV production runner.

28. FlightRadar as the answer key for the score. I will copy the production
    database for you (three steps in 2026-10-06-analyse/README.md; it needs
    my password). Match thermals to airfields and hours as compare.py does,
    then compare average climb (avg_climb_ms) and thermal count per site-hour
    with the v2 score, by score band, month and region. Keep Sjaelland's
    ceilings in mind (~750 and ~1400 m QNH).

3+5. With that answer key, test reweighting the lapse rate (the largest
    weight, never tested against data) and a thermal-top term in the score.

18. Fix 3 over a lid: once the 10-11 Oct weekend data is in, re-check the
    candidate rule (fix 3 only when 925 -> 850 >= 0) on the new days.
```
