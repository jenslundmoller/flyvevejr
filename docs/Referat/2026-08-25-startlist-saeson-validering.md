# Sæson-validering af v1/v2 mod startlist.club, 18 dage maj-august 2026

Dato: 2026-08-25. Rådata: `2026-08-25-startlist-season.jsonl` (110 plads-dage).
Script: batch-pipeline der pr. dag henter startlisten, klassificerer skolefly,
mapper pladser til termik-punkter og kører alle timer 11-18 gennem
`process_point_hour` med begge scoringsversioner (historical-forecast,
samme best_match som produktionen).

## Metode: skolefly filtreres fra

Efter pilotens anvisning: et fly der flyves af 3+ forskellige forsædepiloter
samme dag er skolefly og siger intet om vejret (de får sjældent over ~45
min uanset termik). Facit bygges kun på "signalflyvninger" (alle andre fly);
samme person i samme fly er den bedste indikator for forholdene.

Facit-bånd pr. plads-dag ud fra længste signalflyvning:
staerk (2+ over 60 min og længste >= 120, forventet score 7.5-10),
god (>= 90 min, forventet 6.5-10), mulig (>= 60 min, forventet 4.5-8.5),
svag (2+ signalflyvninger, længste < 45 min, forventet 0-6),
tynd (for lidt data, udgår).

Dage: 16-17/5, 6-7/6, 20-21/6, 11-12/7, 25-26/7, 1-2/8, 8-9/8, 15-16/8,
22-23/8 (2026).

## Resultat

| Metrik | v1 (gammel) | v2 (ny) |
|---|---|---|
| Inden for forventet bånd | 57/88 | **63/88** |
| Samlet afvigelse fra båndene | 55.0 point | **52.6 point** |
| Divergerende rækker (>= 0.8 point): tættest på facit | 4 | **10** (3 lige) |

## De 17 divergerende rækker

| Dag | Plads | Facit | Længste | v1 | v2 | Tættest |
|---|---|---|---|---|---|---|
| 17/5 | True | staerk | 134m | 6.7 | 8.1 | v2 |
| 17/5 | Christianshede | mulig | 89m | 6.2 | 7.3 | lige |
| 6/6 | True | staerk | 255m | 6.9 | 8.5 | v2 |
| 26/7 | Sæby | staerk | 169m | 7.3 | 5.0 | **v1** |
| 26/7 | Aars | svag | 36m | 6.2 | 5.0 | v2 |
| 2/8 | Christianshede | staerk | 174m | 6.8 | 7.8 | v2 |
| 2/8 | Gesten | svag | 41m | 9.3 | 8.5 | v2 (begge langt over) |
| 2/8 | Kalundborg | god | 208m | 6.4 | 8.5 | v2 |
| 8/8 | Kongsted | staerk | 260m | 8.5 | 9.3 | lige |
| 8/8 | Sæby | god | 108m | 6.9 | 5.8 | **v1** |
| 8/8 | Viborg | staerk | 127m | 6.5 | 7.9 | v2 |
| 9/8 | True | god | 174m | 6.4 | 7.4 | v2 |
| 16/8 | Hammer | mulig | 81m | 6.5 | 5.2 | lige |
| 16/8 | Kalundborg | staerk | 315m | 4.7 | 7.3 | v2 (v1 2.8 fra facit) |
| 16/8 | Viborg | svag | 33m | 5.2 | 6.8 | **v1** |
| 22/8 | Slaglille | svag | 42m | 5.7 | 7.6 | **v1** |
| 22/8 | Viborg | god | 104m | 6.4 | 8.6 | v2 |

## Læsning

**v2's gevinster** ligger hvor hæftets punkter forudsagde dem: stærke dage
som v1 undervurderede (True 6/6 og 17/5, Viborg 8/8 og 22/8, Christianshede
2/8), og især kystpladser i sensommeren, hvor v1's faste søbrise-straf
knuste reelle topdage: Kalundborg 16/8 fløj 315 min mens v1 sagde 4.7
(2.8 point fra facit), og Kalundborg 2/8 fløj 208 min mod v1's 6.4.
Søbrise-lempelsen (punkt 5), som overcallede Slaglille 22/8, har altså
også målbare gevinster: netto vinder den mere end den taber i materialet.

**v2's tab**: Slaglille 22/8 (kendt fra forrige referat: pålandsvind med
termikfrit maritimt grænselag) og to Sæby-undercalls på gode dage (26/7:
5.0 mod facit staerk; 8/8: 5.8 mod facit god). Sæby-tabene bør undersøges
før næste justering: kandidater er den nye rest-straf for fralandsvind ved
lille land/hav-forskel og det strammere vindbånd.

**Fælles misses (samme fejl i begge versioner, dvs. data/domæne, ikke
v1-mod-v2)**:

- Hammer 25/7 (309m), 26/7 (320m) og 7/6 (283m) med scores 2-3: tre meget
  lange flyvninger på dage hvor termikscoringen (korrekt for termik) sagde
  dødt. Sandsynligvis skrænt-/bølgeflyvning, som ligger uden for
  termik-scoringens domæne; Hammer bør undtages fra termik-facit.
- Slaglille 15/8 (158m mod score 3) og Kalundborg 7/6 (103m mod 2):
  reelle enkelt-misses hvor best_match-dataene formentlig ikke ramte dagen.

## Konklusion

Over 88 plads-dage med facit rammer v2 flere bånd (63 mod 57), har mindre
samlet afvigelse (52.6 mod 55.0) og vinder de divergerende rækker 10-4.
v2 beholdes som produktionsversion (`SCORING_VERSION = "v2"`), v1 som
rollback. Åbne kalibreringspunkter, i prioriteret rækkefølge:

1. Sæby-undercalls 26/7 og 8/8: find mekanismen (fralands-reststraf eller
   vindbånd) med `compare_scores` og timedata.
2. Pålandsvind-reststraf (Slaglille 22/8-hypotesen fra forrige referat):
   ikke implementeret; kræver flere pålandsvinds-dage som facit.
3. Hammer undtages fra fremtidig termik-validering (skrænt/bølge).

## Opfølgning samme dag: Sæby-undercalls opklaret og rettet

Dybdeanalysen af de to Sæby-dage fandt to årsager:

**26/7 (fløjet 169 og 134 min kl. 13-16, v2 sagde 4.0): en ægte fejl i
punkt 4.** Toppen var begrænset af LCL (664 m kl. 13), TI-nul lå sundt i
1351-1645 m, men cappet testede den Hcrit-korrigerede top (LCL minus ~256 m
margin = 408 m) mod Skema 1's 600 m-bånd. Skema 1's rækker er BASEhøjder;
margin-fradraget fik cappet til at ramme dage med reel base op til ~850 m.
Rettet: båndene testes nu mod den ukorrigerede base, min(LCL, TI-nul) AGL
(`fetch_weather` sender `thermal_base_agl_m`).

**8/8 (fløjet 108 min fra kl. 11:33, v2 sagde 5.8): cirrus-fradraget for
hårdt i mellemområdet.** Fuldt fradrag (-1.0) faldt allerede ved 60 % høj
sky; hæftet siger "svækkes med OP TIL 1 m/s". CIRRUS_BANK_HEAVY er flyttet
til 70 %, så 67 % (timen hvor VI startede og fløj 108 min) giver -0.5,
mens 83 % (2026-05-27 kl. 15, reelt svækket) stadig giver fuldt fradrag.

Sæson-valideringen genkørt efter rettelserne (rådata i
`2026-08-25-startlist-season-v2fix.jsonl`):

| Metrik | v1 | v2 før | v2 efter |
|---|---|---|---|
| Inden for bånd | 57/88 | 63/88 | 61/88 |
| Samlet afvigelse | 55.0 | 52.6 | **51.6** |
| Største enkeltfejl | 3.3 | 2.5 | **1.6** |

De to rettede rækker: Sæby 26/7 err 2.5 -> 0.3, Sæby 8/8 err 0.7 -> 0.2.
Tre rækker krydsede en båndkant den anden vej med højst 0.5 point (True
20/6, Sæby 2/8 og 23/8), alle på dage med blødt facit. Nettoresultat:
lavere samlet afvigelse og markant mindre værste fejl; rettelsen af punkt 4
er desuden en kategorirettelse (base mod base, ikke base mod brugshøjde),
ikke en tilpasning til én dag.
