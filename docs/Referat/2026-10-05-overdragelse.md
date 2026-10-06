# Overdragelse 2026-10-05: kalibrering efter startlist-weekenden

> **Fortsat samme dag:** punkt 13, 9, 1 og 7 er afsluttet, og driften er
> flyttet til OMV. Se [2026-10-05-overdragelse-2.md](2026-10-05-overdragelse-2.md),
> som er den aktuelle overdragelse.

Samlet status efter sessionen 5. oktober 2026, så arbejdet kan fortsætte i
en ny session. Detaljer, tal og begrundelser står i
[2026-10-05-startlist-weekend-oktober.md](2026-10-05-startlist-weekend-oktober.md);
analysescripts i [2026-10-05-analyse/](2026-10-05-analyse/README.md).
Prompt til at fortsætte står nederst.

## Udgangspunkt

Piloterne oplevede at Flyvevejr ramte nogenlunde lørdag 3/10, men tog fejl
søndag 4/10, især på Sjælland. Det holdt: søndag fløj Slaglille 10
flyvninger over 2 timer, Kalundborg 326/285 min og Gørløse 193 min, mens
den publicerede score lå på 3.1-3.6 (aldrig over 5). Lørdag var Sjælland
svag og scoret svag.

Rodårsagen var ikke vejrmodellen. Radiosonde Schleswig og modellen var
enige: tør-adiabatisk lag fra jorden til ~1000 m, cumulus 1000-1250 m,
inversion 1500-1750 m. Scoringen læste det forkert.

## Hvad der er ændret og pushet (alle på main, v2; v1 er urørt rollback)

| Commit | Ændring | Effekt |
|---|---|---|
| `b6cc1e7` | `elevation_m` på alle 262 punkter (hardcodet for flyvepladser, `termik/grid_elevations.json` for griddet, værktøj `termik/tools/fetch_elevations.py`) | Parcel-beregningen starter i rigtig højde; Christianshede (98 m) er ikke længere "inversion" hele dagen |
| `f4013ec` | Sæsonskalerede strålingstærskler (faktor sin(middagssol)/sin(middagssol 8/8), [0.5, 1.0]) og blandingslagets lapse (2 m -> 925 hPa når >= 0.95 og grænselag >= 900 m) | Oktobersol capper ikke længere alt på 5; inversion under 850 hPa læses ikke som stabilt. `lapse_rate_850` er revisionsspor |
| `46390c2` | Målt havtemperatur til søbrisen (`fetch_sea_temps`, 158 havceller i `termik/sea_points.json`, 2 lette marine-kald pr. kørsel), fallback `SEA_TEMP_CLIMATOLOGY` interpoleret pr. dag | Månedstabellens trin på 4 grader 1/10 er væk; Slaglilles 1.8 i søbrise-straf søndag forsvandt |
| `7ef0a38` | 5b kalder kun havluften stabil når også hav -> 925 hPa er under 0.47 grader/100 m | Konsistensrettelse, ingen målbar score-effekt |
| `34514f1` | Cirrus-skjoldet testet time for time; uændret (dokumentation) | Skjoldet er netto bedst af de afprøvede regler |
| `abc8d21` | Overskyet (rå skydække >= 87 %): -2 point og loft 5 i stedet for cap 2 | Kalibreringen monoton, træfsikkerhed 0.691 -> 0.726 |

Nye datafelter pr. time i `airfields.json`: `lapse_rate_850`, `sea_temp`,
`sea_temp_source`. `lapse_rate` er nu den scorede værdi.

Tests: 430 grønne. `termik/tests/conftest.py` stubber marine-kaldet, så
tests aldrig rammer nettet (markør `real_sea_fetch` slår det fra).

## Resultater

Dagsvalidering (gennemsnit af dagens 3 bedste timer kl. 11-18 mod
facit-bånd; sommer = 58 plads-dage 11/7-23/8, oktober = 24 plads-dage 3-4/10):

| | Sommer i bånd | Sommer afvigelse | Okt i bånd | Okt afvigelse | Okt adskillelse fløjet/svag |
|---|---|---|---|---|---|
| Før | 37/58 | 85.3 | 14/24 | 23.1 | 0.36 |
| Efter alt | 38/58 | 85.6 | 16/24 | 12.5 | 1.59 (målt før overskyet-ændringen) |

Søndagens Sjælland: Slaglille 4.9 -> ~8.5, Kalundborg 4.8 -> ~8.4,
Gørløse 5.0 -> ~8.5 (replay af Slaglille 4/10: 7.7-8.6 kl. 12-15), målt
før overskyet-ændringen, som kun kan sænke timer med >= 87 % skydække.

Timevalidering (873 timer med flyvninger, 18 sæsondage + 3-4/10):
andel timer med 60+ min i luften pr. scorebånd 0-3 / 3-5 / 5-6.5 / 6.5-8 /
8+ er nu 24 / 43 / 62 / 73 / 85 % (før 46 / 37 / 55 / 73 / 85 %).

## Metoden (genbrugelig)

- **Facit**: startlist.club/YYYY-MM-DD. Skolefly frasorteres: et fly med
  3+ forskellige forsædepiloter samme dag (typisk ASK 21). Hammer udelades
  (skrænt/bølge). Bånd: staerk (2+ over 60 min og længste >= 120,
  forventet 7.5-10), god (>= 90, 6.5-10), mulig (>= 60, 4.5-8.5), svag (2+
  flyvninger, længste < 45, 0-6), tynd udgår.
- **Time-facit**: "bar" = en signalflyvning på >= 60 min var i luften i
  timen; "kort" = alle flyvninger i timen < 30 min.
- **Publiceret score**: `git show <commit>:termik/output/data/airfields.json`
  for datakørslen fra morgenen samme dag.
- **Replay**: `python3 -m termik.tools.replay_day <id> <dato>` (forecast-
  endpoint, <= 92 dage tilbage, bruger nu målt havtemperatur for dagen).
  Ældre dage: historical-forecast-endpointet (ikke helt det publicerede).
- **Hvilket cap binder**: opfang `apply_dealbreakers_v2` og genberegn hvert
  caps betingelse (`2026-10-05-analyse/caps.py`).
- **Variantforsøg**: byt én regel ud i en kopi af funktionen og kør time-
  og dagsvalidering (`ccvar.py`).
- **Radiosonder**: `https://weather.uwyo.edu/wsgi/sounding?datetime=YYYY-MM-DD%2012:00:00&id=10035&src=UNKNOWN&type=TEXT:LIST`
  (Schleswig virker; København 06181 havde ingen data).
- **Faldgruber**: Open-Meteo minut-grænse (vent 65 s); best_match har kun
  1000/925/850 hPa under 1.6 km (950/900/800 og 80/120/180 m-temperatur er
  tomme); sommerens to studier har kun n = 26-48 pålandsdage.

## Live-tjek planlagt

Første live-test af ændringerne er weekenden 10.-11. oktober. En cloud-
rutine ("Flyvevejr: compare weekend 10-11 Oct forecast with startlist",
https://claude.ai/code/routines/trig_0169kVTawZuW676BAxeapHfV) kører én gang
mandag 12. oktober kl. 09:00 dansk tid. Den sammenligner startlisterne for
10. og 11. oktober (og tirsdag 6/10, hvis der blev fløjet) med den
publicerede prognose på dags- og timeniveau, tjekker de to kendte risici
(timer med 8.5+ under en vist top på kun ~500-650 m; fugtige dage med lav
base som lørdag 3/10) og lægger resultatet som
`docs/Referat/2026-10-12-startlist-weekend.md` i en PR fra grenen
`claude/startlist-2026-10-10-11`. Den ændrer ikke scoring og pusher aldrig
til main. Læs PR'en før næste kalibrering.

Bemærk: prognosen 5/10 kl. 12:59 UTC gav tirsdag 6/10 kl. 13-16 score
7.7-9.4 på Slaglille, Kalundborg og Christianshede med en vist top på kun
516-631 m; det er netop risiko (a).

## Undersøgt og bevidst ikke ændret

- **Cirrus-skjoldet** (cap 3 ved høj sky >= 85 %): skjold-timer bar 41 %
  mod 68 % uden, så det har signal. At lempe for "tynd" cirrus (direkte sol
  >= 100 W/m²), loft 5 eller intet skjold sænkede alle adskillelsen.
  Modellens data kan ikke skelne tynd fra tyk cirrus. Slaglille 15/8 (158
  min under skjoldet) er en reel, men accepteret miss.

## Åbne punkter (hele projektet)

Prioriteret forslag til næste session: **13, 9, 1, 7** (prompt nedenfor).

Scoring:

1. ~~**`score_solar` tæller en god dags egne cumulus som dæmpning**~~
   Undersøgt 5/10, uændret: v2's `CU_ALLOWANCE` har allerede løst 8/8 kl. 19,
   og ingen variant slår støjen (startlist-referatet, punkt 1-afsnittet).
2. Vindretning og luftmasse scores ikke (pilotregel: højtryk NV for
   Danmark giver god termik).
3. Lapse-vægten (0.30, den største) er aldrig efterprøvet mod data. 5/10:
   lapse og termiktop sorterer stadig bar fra kort inden for scorebåndene
   (AUC 0.705 / 0.733), så scoren udnytter dem for dårligt. Næste kandidat.
4. Strålingsfeltet reagerer knap på modellens cirrus; kun høj-sky-andelen
   ved det. Bekræftet i dag: ingen brugbar skelnen.
5. Hcrit-margin fra solindstråling i stedet for modellens varmestrøm
   (±100-200 m på termiktoppen); hænger sammen med RASP-agtig W*.
6. Termiktoppen stopper ved LCL; cumulus kan række 200-500 m højere.
18. Fix 3 (blandingslagets lapse) over et låg: 18/7 scorede fem jyske
    pladser 7.5-8.9 på svage dage, fordi 2 m -> 925 hPa var 1.3-1.7 under
    en inversion lige over 925 hPa. Kandidat: fix 3 kun når 925 -> 850 >= 0
    (218 plads-dage: i bånd 154 -> 156, adskillelse 2.88 -> 3.03, oktober
    uændret), men den hviler på én dag og har et modeksempel (Kalundborg
    15/8). Ikke implementeret; saml flere dage med profilen. Jylland juli-
    september: 61 % i bånd på dage uden for kalibreringen. Se
    startlist-referatet, sidste afsnit.
19. Termiktoppen mod FlightRadar (Referat 2026-10-06): fradraget følger nu
    strålingen (modellens LCL er for høj i stærk sol). Tilbage: ~100 m for
    lavt om efteråret, og "inversion"-dommen viser 0 m i 25 timer hvor der
    blev fløjet til ~640 m AGL. Sjælland kan ikke kalibrere toppen uden
    dagens luftrumsloft (~750 / ~1400 m).

Data:

7. ~~**Hent lavniveaudata fra `icon_seamless`/`dmi_seamless`**~~ Målt 5/10,
   ikke implementeret: kun ICON's termiktop tilføjer en smule, mod et ekstra
   kald pr. batch. Lapse 2-180 m-cappet har næsten aldrig data i
   produktionen (best_match mangler 180 m). Se startlist-referatet, punkt 7.
8. Gentag startlist-valideringen på flere efterårsdage og i foråret (hvor
   sæsonfaktoren også er under 1). Næste weekend er et godt live-tjek,
   især fugtige dage med lav base som lørdag 3/10, hvor de nye regler mest
   sandsynligt overcaller.

UI:

9. ~~**Vis den begrænsende faktor** i popup'en.~~ Løst 5/10: `data.limited_by`
   og en linje i popup'en (startlist-referatet, sidste afsnit).
10. Vis cirrus særskilt i popup'en ("Skydække 50 %, heraf cirrus 80 %").
11. Felt for dagens maksimale termiktop.
12. Vejr-widget: brug Open-Meteos `apparent_temperature` og `weathercode`.

Drift:

13. ~~**Læs `Batch n/27 ok in X s`-linjerne i GitHub Actions-loggene**~~
    Løst 5/10: kaldene hang (ikke langsomme), proben fandt ingen pause der
    virker, og forecast-jobbet kører nu på en selvhostet runner på OMV
    (2.5 min, 0 timeouts). Se `2026-09-02-api-robusthed.md`, opfølgning 5/10,
    og [overdragelsen 2026-10-05 (2)](2026-10-05-overdragelse-2.md).
14. Redningsrunden for fejlede batches og dækningsbanneret er ikke set i
    produktion.

Sikkerhed og oprydning:

15. Self-host Leaflet (fjern unpkg.com fra CSP).
16. Escape alle JSON-felter i popup'en (navn og kommentar er escapet).
17. Fjern det ubrugte `_is_land()` i `locations.py`; tilføj manglende
    småøer til kortets omrids.

## Prompt til at fortsætte

```
Continue the Flyvevejr work from docs/Referat/2026-10-05-overdragelse.md.
Read that handover first, then docs/Referat/2026-10-05-startlist-weekend-oktober.md
for the numbers behind it. Reusable analysis scripts are in
docs/Referat/2026-10-05-analyse/ (see its README).

Work through these four open items in order, one at a time. For each, show me
the findings before changing production code, validate any scoring change
against the startlist facit (day level and hour level, as in the referat),
write tests first, update the referat/PROJEKT-DOKUMENTATION, and commit.
Ask before pushing.

13. GitHub Actions timings: use gh to read the "Batch n/27 ok in X s" and
    timeout lines from the update-forecast runs since 2026-10-01. Tell me
    whether successful calls cluster near the 30 s timeout (raise it) or hang
    (move off GitHub-hosted runners), with the numbers.

9.  Limiting factor in the UI: make apply_dealbreakers_v2 report which cap set
    the score (the analysis in caps.py shows how), publish it per hour, and
    show it in the airfield popup in plain Danish. Keep the payload small for
    grid points.

1.  score_solar treats a good day's own cumulus as shading
    (docs/Referat/2026-08-12-straale-gate.md, open item 2). Measure it hour by
    hour against the startlists before proposing a change; the overcast cap
    finding from 2026-10-05 is the closest precedent.

7.  Better low-level data: evaluate adding temperature_1000hPa and the
    low-level profile/heat flux from icon_seamless or dmi_seamless. Weigh the
    extra API calls (production already runs 27 batches plus 2 marine calls)
    against the measured gain before implementing.
```
