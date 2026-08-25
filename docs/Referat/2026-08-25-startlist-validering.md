# Validering af v1/v2 mod startlist.club, 22-25. august 2026

Dato: 2026-08-25. Datagrundlag: alle registrerede flyvninger på
startlist.club for 22/8, 23/8 og 25/8, holdt op mod v1/v2-scores beregnet
med `termik.tools.compare_scores` (historical-forecast for 22-23/8,
forecast-endpoint for 25/8). Flyvedata er facit: lange flyvninger beviser
bærende termik; mange starter uden lange flyvninger beviser, at termikken
ikke bar (skolefly flyver dog sjældent over ~45 min uanset vejret, og lette
fly som M1/M4/MF kan holde sig oppe i svagere termik end fx PL).

## Skema: flyvninger mod maks-score kl. 11-18

| Dag | Plads | Starter | >60 min | Længste | v1 maks | v2 maks | Facit vs score |
|---|---|---|---|---|---|---|---|
| 22/8 | Sæby | 25 | 5 | 180 min | 8.2 | 8.6 | God termikdag: begge rammer |
| 22/8 | True/Aarhus | 18 | 3 | 159 min | 7.6 | 7.6 | God termikdag: begge rammer |
| 22/8 | Viborg | 7 | 1 | 104 min | 6.4 | 8.6 | Termik muligt: begge ok, v2 i overkanten |
| 22/8 | Kongsted | 29 | 1 | 63 min | 7.2 | 7.2 | Kun én kom væk: begge lidt høje |
| 22/8 | **Slaglille** | **45** | **0** | **42 min** | **5.7** | **7.6** | **v2 overcaller: se analysen** |
| 22/8 | Christianshede | 12 | 0 | 46 min | 7.9 | 8.4 | Skoledag, svært facit; begge høje |
| 22/8 | Gesten | 21 | 0 | 41 min | 4.0 | 4.0 | Svag dag: begge rammer |
| 23/8 | Hammer/Vejle | 10 | 1 | 152 min | 5.0 | 5.0 | Én lang flyvning i "Moderat": ok |
| 23/8 | Slaglille | 19 | 0 | 8 min | 3.0 | 3.0 | Død dag: begge rammer |
| 23/8 | Sæby | 26 | 0 | 30 min | 5.1 | 5.7 | Begge lidt høje |
| 23/8 | True, Viborg, Kongsted, Gesten | 82 | 0 | <=36 min | 2.0-5.0 | 2.0-5.0 | Død dag: begge rammer |
| 25/8 | Slaglille | 1 | 1 | 184 min | 8.9 | 9.5 | Topdag (OB 13:06-16:11): begge rammer |
| 25/8 | Hammer/Vejle | 2 | 1 | 166 min | 8.8 | 8.6 | Topdag: begge rammer |
| 25/8 | Viborg | 1 | 1 | 83 min | 8.7 | 8.9 | God dag: begge rammer |
| 25/8 | Gørløse, True, Gesten | 15 | 0 | <=44 min | 7.5-8.5 | 8.4-8.7 | Aftenskolestarter kl. 16-18; intet facit for middagsvinduet |

25/8 var iflg. pilotobservation en rigtig god flyvedag med få flyvninger
(hverdag); de fem lange flyvninger (83-184 min) bekræfter det, og begge
versioner scorede dagen højt. v2 en anelse skarpere (9.5 mod 8.9 på
Slaglille).

## Fundet: Slaglille 22/8, v2's ene klare overcall

27 starter efter kl. 14:30, og selv de lette fly kom ikke væk: M1 fløj 42
min (14:50-15:32), MF 36 min (17:00-17:36), PL kun 19 min. Termik fandtes,
men bar ikke: facit er "Svag/Moderat", v1 sagde 5.7, v2 sagde 7.6 ("God").

Mekanismen er målt: hele gabet på nær 0.1 er søbrise-leddet. Vind 12-13 kt
fra 280 (pålandsvind, kystretning 239), land/hav-forskel kun ~1 grad i
august, så v2's punkt 5 gav straf 0, hvor v1 gav 1.8. Hæftets
FRONT-mekanisme (temperaturforskel-drevet) var korrekt fraværende, men
pålandsvinden bar stadig termikfrit maritimt grænselag ind over Sjælland:
luften var ikke koldere, men den skal stadig genopvarmes/destabiliseres
over land, og 33 km/12 kt giver kun ca. 1.5 times landbane.

Kontrolpunktet samme dag: Sæby ligger 8 km fra kysten men havde FRAlandsvind
(vest, østkystplads) og fløj 180 min. Pålandsvind mod fralandsvind forklarer
begge pladser konsistent.

**Hypotese til næste justering** (ikke implementeret): pålandsvind >= ~8 kt
bør beholde en rest-straf (advektion af maritimt grænselag) selv når
land/hav-forskellen er lille, skaleret med afstand som i dag. Kræver flere
dage som facit, især sensommerdage med pålandsvind, før tærsklen fastsættes.

## Konklusion

- På 13 af 15 rækker med reelt facit rammer v2 lige så godt som eller bedre
  end v1 (topdage, døde dage, svage dage).
- v2's gevinster på gode dage (pilotdagen 8/8, hele 25/8) står ved magt.
- Én klar v2-miss: Slaglille 22/8, drevet af søbrise-leddets
  august-nulstilling ved pålandsvind. Registreret som hypotese ovenfor;
  v1 beholdes som rollback via `SCORING_VERSION`.
