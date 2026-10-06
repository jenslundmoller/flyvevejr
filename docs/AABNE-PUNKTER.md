# Åbne punkter

Samlet liste over alt der er åbent i projektet. **Numrene er faste**: et
punkt beholder sit nummer, også når det løses, og et nyt punkt får det
næste ledige nummer (næste: **31**). Løste punkter streges over med dato og
henvisning, og ryddes ud når de er over en måned gamle.

Samlet 2026-10-06 fra [overdragelsen 2026-10-05](Referat/2026-10-05-overdragelse.md),
[overdragelsen 2026-10-05 (2)](Referat/2026-10-05-overdragelse-2.md),
[overdragelsen 2026-10-06](Referat/2026-10-06-overdragelse.md) og
[termikfarve-overdragelsen](Referat/2026-10-06-overdragelse-termikfarver.md).
Fra nu af opdateres denne fil, og overdragelserne henviser hertil.

**Forslag til næste session:** 28, derefter 3 + 5 med FlightRadar-facit,
og 18 når weekendens data (10.-11. oktober) er inde.

## Scoring og termiktop

2. Vindretning og luftmasse scores ikke (pilotregel: højtryk NV for
   Danmark giver god termik).
3. **Lapse-vægten** (0.30, den største) er aldrig efterprøvet mod data.
   Lapse og termiktop sorterer stadig bar fra kort inden for scorebåndene
   (AUC 0.705 / 0.733), så scoren udnytter dem for dårligt. Testes sammen
   med 5 mod FlightRadar-facit (28).
4. Strålingsfeltet reagerer knap på modellens cirrus; kun høj-sky-andelen
   ved det. Ingen brugbar skelnen fundet 5/10.
5. Et termiktop-led i scoren. Fradraget er siden 6/10 en målt rettelse af
   modellens LCL (0.4 x (SW - 400)), ikke en sikkerhedsmargin; tilbage er
   at teste om toppen skal vægte i scoren (sammen med 3).
6. Termiktoppen stopper ved LCL. FlightRadar viser at den fløjne top følger
   basen (korrelation 0.70) og kun ligger over den om efteråret (25). Ikke
   længere en selvstændig fejl; lukkes hvis 25 forklarer resten.
18. **Punkt 9 (blandingslagets lapse) over et låg.** 18/7 scorede fem jyske
    pladser 7.5-8.9 på svage dage under en inversion lige over 925 hPa.
    Kandidat: punkt 9 kun når 925 -> 850 >= 0 (218 plads-dage: 154 -> 156
    i bånd, oktober uændret), men den hviler på én dag og har et
    modeksempel (Kalundborg 15/8). Genkøres på weekenden 10.-11. oktober.
21. **Mellemhøj sky-cappet (2)**: 18 af 56 facit-timer bar alligevel.
    Testes time for time som cirrus-skjoldet.
23. `surface_stable`-cappet er reelt død kode (`temperature_180m` hentes
    ikke). Fjern det eller dokumentér det som inaktivt.
25. **De sidste ~100 m om efteråret:** piloterne kommer ~100 m over
    modellens base i september-oktober, selv om model og sonde er enige.
    Måske stiger basen over eftermiddagen. Hviler på 8-10 dage.
26. **Den falske "inversion"-dom:** 25 timer (11 dage) viser top 0 m, men
    der blev fløjet til median 644 m AGL. Samme mekanisme som 18.
27. **Sjællands luftrumslofter** (~750 og ~1400 m QNH): registreres dagens
    loft, kan Sjælland bruges som censurerede data.
28. **FlightRadar som facit for scoren:** `thermals.avg_climb_ms` måler
    termikstyrken direkte, også på hverdage. Gennemsnitlig stigning pr.
    plads og time mod scoren, pr. scorebånd, måned og region. Anbefalet
    næste skridt; brug det derefter til 3, 18 og 21.

## Data og validering

8. Gentag startlist-valideringen på flere efterårsdage og i foråret (hvor
   sæsonfaktoren også er under 1), især fugtige dage med lav base.

## UI

10. Vis cirrus særskilt i popup'en ("Skydække 50 %, heraf cirrus 80 %").
11. Felt for dagens maksimale termiktop.
12. Vejr-widget: brug Open-Meteos `apparent_temperature` og `weathercode`.
29. **Popup'ens højdeakse blander datum:** `buildAltAxis` i `app.js`
    tegner termiktop og LCL (over havet) på samme akse som blandingslaget
    og skybasen (over terræn). Forskellen er terrænhøjden (op til ~170 m).
30. **Termiktop-paletten** (6/10): tjek på en dag med toppe over 1500 m at
    gul/grøn læses godt over OSM-kortet, og eventuelt for deuteranopi.

## Drift

14. Redningsrunden for fejlede batches og dækningsbanneret er ikke set i
    produktion.
19. **Repoets størrelse: ~920 MB.** Hver kørsel committer ~14 MB JSON.
    Publicér data uden at committe dem, eller ryd historikken.
20. Gør repoet privat og flyt siden fra GitHub Pages (Cloudflare Pages
    eller OMV via Cloudflare Tunnel), så den selvhostede runner ikke hænger
    på et offentligt repo. Hænger sammen med 19. Besluttet 5/10 at vente.
24. Fallback til `ubuntu-latest` er ikke set i produktion. Test ved at
    stoppe runneren på OMV et kvarter før en planlagt kørsel.

## Sikkerhed og oprydning

15. Self-host Leaflet (fjern unpkg.com fra CSP).
16. Escape alle JSON-felter i popup'en (navn og kommentar er escapet).
17. Fjern det ubrugte `_is_land()` i `locations.py`; tilføj manglende
    småøer til kortets omrids.

## Løst

1. ~~`score_solar` tæller en god dags egne cumulus som dæmpning~~
   Undersøgt 5/10, uændret.
7. ~~Lavniveaudata fra `icon_seamless`/`dmi_seamless`~~ Målt 5/10, ikke
   implementeret.
9. ~~Vis den begrænsende faktor~~ Løst 5/10 (`data.limited_by`).
13. ~~Actions-timinger~~ Løst 5/10: forecast-jobbet kører på OMV.
22. ~~Probe-workflowet~~ Slettet 6/10 (koden i `9fa8a98`).
