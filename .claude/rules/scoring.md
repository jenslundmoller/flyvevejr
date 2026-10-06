---
description: Hvordan scoringen og termiktoppen ændres og valideres
paths:
  - "termik/scoring_v2.py"
  - "termik/scoring.py"
  - "termik/config.py"
  - "termik/fetch_weather.py"
  - "termik/comments.py"
  - "docs/Referat/**/*.py"
---

# Scoring og kalibrering

Scoren er kalibreret mod virkelige flyvninger. En regel der ser fornuftig ud
i teorien, men ikke er målt, kommer ikke i produktion.

## Facit

| Kilde | Hvad den måler | Faldgruber |
|---|---|---|
| startlist.club | Flyvetid pr. plads og dag/time | Kun weekender og klubdage. Frafiltrér skoleflyvning (samme fly, 3+ forsædepiloter samme dag). En time "bar" hvis en flyvning på 60+ min var i luften |
| FlightRadar `thermals` | Termikbobler: `end_alt` (GPS m over havet), `avg_climb_ms` | Kopi af prod-DB'en via SSH (se `docs/Referat/2026-10-06-analyse/README.md`). **Sjælland stopper ved luftrumslofter (~750 og ~1400 m QNH)** og kan ikke kalibrere toppen |
| Schleswig-sonden (10035) | Den rigtige profil kl. 12 UTC | Wyoming-URL'en `weather.uwyo.edu/wsgi/sounding?...`; den gamle `cgi-bin` giver 404 |
| historical-forecast-API | Modellens data for gamle dage | Forecast-endpointet når kun 92 dage tilbage |

## Sådan ændres en regel

1. **Find mekanismen i data**, ikke kun i et gennemsnit. Én dag med en
   forklaring er en hypotese, ikke en regel.
2. **Valider på dage reglen ikke er tilpasset på.** Kalibreringsdage
   flatterer (Jylland 2026-10-06: 74 % i bånd på kalibreringsdagene, 61 % på
   de andre). Rapportér begge tal.
3. **Mål både dag for dag og time for time**, og mod sommeren som
   regression når en efterårsregel indføres.
4. **Sammenlign med en uafhængig kilde før en rettelse låses.** Det
   sommerkalibrerede termiktop-fradrag skjulte en modelfejl, som først
   sonden afslørede.
5. **Vis brugeren tallene og vent på et ja.** Skriv derefter tests, så
   koden.
6. **Kontrollér at intet andet flytter sig:** kør scoren for alle dagtimer
   før og efter og tæl ændrede timer (2026-10-06: 0 af 43.680).

## Kode

- Nye konstanter i `config.py` med enhed i navnet (`_W_M2`, `_M`, `_KT`) og
  en kommentar med kilde (referat og dato).
- **v1 (`scoring.py`) er rollback-stien og ændres ikke.** Ny adfærd går i
  `scoring_v2.py`. Hver publiceret time bærer `scoring_version`.
- Et nyt loft får en `limited_by`-kode og en tekst i `LIMIT_TEXT` i `app.js`.
- Caps læser den rå `cloud_cover`-total, ikke lagvægtet dække (afprøvet og
  rullet tilbage, se PROJEKT-DOKUMENTATION).
- `best_match` har kun 1000/925/850 hPa i de nederste 1.6 km for Danmark.
  Felter der kom tomme tilbage (950, 900, 800 hPa, 180 m) hentes ikke.
- Hver påbegyndt 10. variabel koster et ekstra kald pr. punkt. En ny
  variabel kan koste 262 kald pr. kørsel.

## Analysescripts

Lægges i `docs/Referat/YYYY-MM-DD-analyse/` med en README der siger hvad
hvert script gør, hvilke data det kræver og hvor mange API-kald det koster.
Rådata (`*.pkl`, DB-kopier) committes ikke. Hold historiske hentninger små;
kvoten deles med produktionen.
