# Stråle-gate og cirrus i hard caps — implementeringsplan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Ret stråle-gaten så den ikke længere klipper gode eftermiddagstimer af, og lad de hårde caps bruge den samme cirrus-vægtede sky- og strålingsforståelse som `score_solar` allerede har.

**Architecture:** Tre lag, i rækkefølge. Først persisteres de strålings- og skylagsfelter der allerede beregnes men smides væk, så alt det følgende kan måles. Derefter får stråle-gaten en hukommelse om dagens ophobede opvarmning i stedet for at teste øjebliksstråling. Til sidst får `apply_dealbreakers` de samme cirrus-vægtede input som `score_solar`, med en separat cap for tykke cirrus-skjolde.

**Tech Stack:** Python 3.12, pytest, Open-Meteo API, GitHub Actions, vanilla JS frontend.

---

## Baggrund

To piloter fra Midtsjællands Svæveflyveklub har nu rapporteret det samme mønster, med tre måneders mellemrum:

- **2026-05-23** (dokumenteret i `docs/Referat/2026-05-24-cirrus-direct-radiation.md`): cirrus ødelagde termikken, forecasten lovede 5.9. Førte til cirrus-vægtning i `score_solar`.
- **2026-08-08 og 2026-08-09**: lørdag var fremragende til kl. 19, søndag var umulig. Systemet gav lørdag 7.1 i top og klemte 18:00 og 19:00 til præcis 5.0, mens søndag fik 7.4 som bedste time.

### Måling: stråle-gaten klemmer systematisk

Gennemgang af sidste run pr. dag 2026-04-01 til 2026-08-11, 30 flyvepladser, 2076 plads-timer pr. klokketime. Alle øvrige caps er genberegnet fra de gemte felter. Hvor scoren rammer præcis en gate-tærskel og alle andre caps tillod mere, er stråle-gaten bindende.

| kl | klemt til 5 | klemt til 3 |
|---|---|---|
| 08 | 5 | 127 |
| 09 | 134 | 92 |
| 17 | 88 | 40 |
| 18 | 188 | 39 |
| 19 | **493** | 155 |
| 20 | 33 | **578** |

Ved 19:00 lander 517 af 2076 plads-timer på præcis 5.0, mod 65 på præcis 4.0 og 7 på præcis 6.0. Det er en klemme, ikke en fordeling. I alt cirka 2800 plads-timer hen over sæsonen hvor alle øvrige forhold tillod 7 eller bedre.

**Årsag:** `apply_dealbreakers` (`scoring.py:451`) tester *øjebliks*-stråling. Konvektionen henfalder med forsinkelse efter maksimal opvarmning, fordi grænselaget bliver ved med at være blandet på oplagret varme. En gate uden hukommelse om dagens ophobede opvarmning vil altid lukke aftenen for tidligt.

### Måling: cirrus-fixet nåede kun halvvejs

Maj-fixet ramte `score_solar`, som vejer 20 % (`config.py:63`). Ved kaldestedet (`scoring.py:608-614`) får `apply_dealbreakers` stadig rå `cloud_cover` og rå `shortwave_radiation`, mens `score_solar` får lagopdelingen og `direct_radiation`. De to halvdele af scoringen er altså uenige om hvad "sky" og "stråling" betyder, og cap'en, der dominerer resultatet, behandler stadig 90 % cirrus som 90 % stratus.

### Måling: lapse rate skelnede ikke de to dage

Ringsted, hindcast-runs, kl. 11 til 16:

| dag | lapse_rate |
|---|---|
| lørdag 2026-08-08 | 0.90, 0.98, 1.05, 1.12, 1.16, 1.11 |
| søndag 2026-08-09 | 0.89, 0.96, 0.99, 0.99, 0.97, 0.96 |

Næsten identiske. Den tungest vægtede variabel (0.30) adskilte ikke en dag med massiv termik fra en dag uden. Vindretning bruges kun i `calculate_seabreeze_penalty` (`scoring.py:353-372`) og aldrig til at karakterisere luftmassen.

### Acceptkriterier for hele planen

Disse sager er sandheden vi kalibrerer mod. Alle tre skal holde til sidst:

1. **Ringsted 2026-08-08 kl. 18:00 og 19:00** skal score over 6.5 (var 5.0). Piloten fløj god termik til 19.
2. **Ringsted 2026-08-09 kl. 10:00 til 14:00** skal blive på 3.0 eller derunder (var 2.0 i morgen-run, 6.2 i hindcast). Det var umuligt at finde noget.
3. **Ringsted 2026-08-09 kl. 18:00** skal ned på 5.0 eller derunder (var 7.4, "God termik"). Tilføjet efter Task 2. Det var dagens værste forudsigelse, og hverken Task 3 eller Task 5 rører den: himlen var klaret op (total 15, cirrus 0) og strålingen var 429 W/m², over gate-tærsklen. Kun grænselagshøjden skiller timen (780 m mod lørdagens 1250 m). Det er hele grunden til at Task 6 findes.

Kriterium 2 er den farlige: Task 5 gør cirrus-cap'en mildere, og hvis den bliver for mild, ryger søndag op i det grønne igen. Kriterium 3 trækker den anden vej og må ikke løses ved at trække lørdag ned med sig, så kriterium 1 er samtidig værn mod overfitting.

### Målt sandhed fra Task 2

Fuld tabel for begge dage ligger i `docs/Referat/2026-08-12-straale-gate.md`. Det der styrer resten af planen:

**Kalibrér altid mod forecast-endpointet, aldrig mod `archive-api`.** ERA5 dækker ikke dagene endnu, så arkivet falder stille tilbage på `ecmwf_ifs`, en anden model end den `best_match`-blanding produktionen kører på. De er uenige med op til 253 W/m². Afgjort på beviser: produktionen udgav præcis 5.0, 5.0, 3.0 kl. 18/19/20, forecast-værdierne (398, 274, 139) reproducerer det, arkivets (298, 186, 92) ville give 5, 3, 1. Kalibrering mod arkivet ville have tvunget `RADIATION_MEMORY_FACTOR` op på 0.83.

**Lørdag 2026-08-08, stråling:** peak er 736 kl. 13 (planens antagelse om ~640 var forkert, men med et 3-timers vindue er peaken ikke det bindende). SW kl. 16 til 20: 657, 523, 398, 274, 139.

**Søndag 2026-08-09, skylag kl. 10 til 14:** total 74/79/55/64/75, lav **0/0/0/0/0**, mellem 0/0/0/0/0, høj **99/81/59/84/100**. Lavt skydække var 0 hele dagen. Præmissen for Task 5 er bekræftet.

**Grænselagshøjde skiller dagene langt bedre end lapse rate:**

| kl | lør | søn | forhold |
|---|---|---|---|
| 09 | 1085 | 315 | 3.4 |
| 10 | 1155 | 410 | 2.8 |
| 11 | 1270 | 1210 | 1.05 |
| 13 | 1600 | 1295 | 1.24 |
| 17 | 1685 | 980 | 1.7 |
| 18 | 1250 | 780 | 1.6 |
| 19 | 1000 | 355 | 2.8 |

Forbeholdet er kl. 11 til 13, hvor dagene er næsten ens. Grænselagshøjden kan altså ikke bære kriterium 2 alene, kun kriterium 3.

**`cloud_cover` modsiger sine egne lag i `best_match`.** Søndag kl. 10: total 74 med høj 99. Lørdag kl. 13: total 67 med lav 95. Begge fysisk umulige, så total og lag kommer fra forskellige modeller i blandingen. Beslutning: **caps holder op med at læse totalfeltet og udleder skydække fra lagene**, som er indbyrdes konsistente og er det cirrus-researchen bygger på. Det ændrer adfærd på alle dage, ikke kun de to, så sæsonkørslen i Task 4 er værnet mod regressioner.

---

## Task 1: Persister strålings- og skylagsfelter til output

Uden dette kan intet af det følgende revideres bagefter. Felterne hentes og bruges allerede i scoringen, de skrives bare ikke til `current.json`. Det er stadig et åbent punkt fra maj-referatet.

Grid-punkter strippes allerede til `time` + `score` + `thermal_top_m` (`fetch_weather.py:354-361`), så det her rammer kun de 30 flyvepladser: cirka 5040 timer, anslået +550 KB på en 6 MB fil.

**Files:**
- Modify: `termik/fetch_weather.py:281-317` (returdictens `data`-blok)
- Test: `termik/tests/test_fetch_weather.py`

**Step 1: Skriv den fejlende test**

Tilføj nederst i `termik/tests/test_fetch_weather.py`. Genbrug mønstret fra `test_process_point_hour_passes_multilevel_data` (linje 101) til at bygge `hourly_data`.

```python
def test_process_point_hour_persists_radiation_and_cloud_layers():
    """Revisionsfelter: uden dem kan gate og cirrus-caps ikke efterprøves."""
    point = {"id": "test", "name": "Test", "lat": 55.9, "lon": 9.1,
             "coast_distance_km": 40, "coast_direction_deg": 90}
    hourly_data = _minimal_hourly_data(
        shortwave_radiation=[520.0] * 4,
        direct_radiation=[380.0] * 4,
        cloud_cover=[60] * 4,
        cloud_cover_low=[5] * 4,
        cloud_cover_mid=[10] * 4,
        cloud_cover_high=[85] * 4,
    )
    result = process_point_hour(point, hourly_data, 3, month=8)
    d = result["data"]
    assert d["shortwave_radiation"] == 520.0
    assert d["direct_radiation"] == 380.0
    assert d["cloud_cover_low"] == 5
    assert d["cloud_cover_mid"] == 10
    assert d["cloud_cover_high"] == 85
```

Hvis der ikke allerede findes en `_minimal_hourly_data`-helper i testfilen, så skriv den først som en lille factory der fylder alle nøgler i `HOURLY_PARAMS` med neutrale værdier og lader kwargs overskrive. Det holder de følgende tasks korte.

**Step 2: Kør testen og se den fejle**

Kør: `python3 -m pytest termik/tests/test_fetch_weather.py::test_process_point_hour_persists_radiation_and_cloud_layers -v`
Forventet: FAIL med `KeyError: 'shortwave_radiation'`

**Step 3: Tilføj felterne til returdicten**

I `termik/fetch_weather.py`, i `data`-blokken lige efter `"cloud_cover": cloud_cover,`:

```python
            "cloud_cover_low": cloud_cover_low,
            "cloud_cover_mid": cloud_cover_mid,
            "cloud_cover_high": cloud_cover_high,
            "shortwave_radiation": shortwave,
            "direct_radiation": direct_radiation,
```

Variablerne findes allerede i scope (`fetch_weather.py:120-124`). Bemærk at `shortwave` får fallback til 0 på linje 215, så det er den efter-fallback-værdi der gemmes. Det er med vilje: det er den værdi scoringen faktisk brugte.

**Step 4: Kør testen og se den bestå**

Kør: `python3 -m pytest termik/tests/test_fetch_weather.py -v`
Forventet: PASS, ingen andre tests knækker.

**Step 5: Kør hele suiten**

Kør: `python3 -m pytest termik/tests -q`
Forventet: 175 passed (174 i dag plus den nye).

**Step 6: Commit**

```bash
git add termik/fetch_weather.py termik/tests/test_fetch_weather.py
git commit -m "data: persister stråling og skylag til airfield-payload"
```

---

## Task 2: Hent sandheden for de to referencedage

Vi kan ikke kalibrere på arkivet, fordi felterne først findes fra Task 1 og frem. Maj-referatet løste det samme problem ved at hente historik fra Open-Meteo. Gør det igen for 2026-08-08 og 2026-08-09.

ERA5-arkivet har typisk 5 dages forsinkelse, så brug `past_days` på det almindelige forecast-endpoint først. Falder det igennem, så prøv `https://archive-api.open-meteo.com/v1/archive`.

**Files:**
- Create: `termik/tools/fetch_reference_day.py`

**Step 1: Skriv scriptet**

```python
#!/usr/bin/env python3
"""Hent faktiske strålings- og skyværdier for en referencedag.

Bruges til kalibrering af stråle-gaten og cirrus-caps. Ikke en del af
produktions-pipelinen; kaldes manuelt.

Brug: python3 -m termik.tools.fetch_reference_day 55.451748 11.642456 2026-08-08
"""
import sys
import requests

lat, lon, day = sys.argv[1], sys.argv[2], sys.argv[3]
params = (
    "shortwave_radiation,direct_radiation,cloud_cover,"
    "cloud_cover_low,cloud_cover_mid,cloud_cover_high,"
    "temperature_2m,boundary_layer_height,wind_direction_10m,surface_pressure"
)
url = (
    f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}"
    f"&hourly={params}&timezone=Europe/Berlin&past_days=14&forecast_days=1"
)
h = requests.get(url, timeout=60).json()["hourly"]

print(f"{'kl':>5} {'SW':>6} {'direct':>7} {'cc':>4} {'low':>4} {'mid':>4} {'high':>5} {'BL_m':>7}")
for i, t in enumerate(h["time"]):
    if not t.startswith(day):
        continue
    if not 6 <= int(t[11:13]) <= 21:
        continue
    print(f"{t[11:16]:>5} {h['shortwave_radiation'][i]:>6} {h['direct_radiation'][i]:>7} "
          f"{h['cloud_cover'][i]:>4} {h['cloud_cover_low'][i]:>4} {h['cloud_cover_mid'][i]:>4} "
          f"{h['cloud_cover_high'][i]:>5} {h['boundary_layer_height'][i]:>7}")
```

**Step 2: Kør for begge dage på Ringsted**

```bash
python3 -m termik.tools.fetch_reference_day 55.451748 11.642456 2026-08-08
python3 -m termik.tools.fetch_reference_day 55.451748 11.642456 2026-08-09
```

**Step 3: Skriv tallene ned**

Læg output i `docs/Referat/2026-08-12-straale-gate.md` under en overskrift "Referencedage". De konkrete SW-værdier kl. 17 til 19 lørdag og cirrus-fraktionen kl. 10 til 14 søndag er det Task 3 og Task 5 kalibreres mod.

**Vigtigt:** hvis søndagens skydække kl. 10 til 14 viser sig at være overvejende *lavt* skydække og ikke cirrus, så er præmissen for Task 5 forkert. Stop og sig det, i stedet for at implementere en cirrus-cap der ikke havde noget at gøre med sagen.

**Step 4: Commit**

```bash
git add termik/tools/fetch_reference_day.py docs/Referat/2026-08-12-straale-gate.md
git commit -m "tools: hent referencedage til kalibrering af stråle-gate"
```

---

## Task 3: Giv stråle-gaten hukommelse

Fysikken: konvektion henfalder ikke i takt med solindstrålingen, den henfalder bagefter, fordi grænselaget allerede er blandet. Gaten skal derfor se på det højeste den har set inden for de seneste timer, ikke kun på nu.

Tærsklerne flyttes samtidig til `config.py`, så kalibrering i Task 4 er en konstant-ændring og ikke en kode-ændring.

**Files:**
- Modify: `termik/config.py` (nye konstanter)
- Modify: `termik/scoring.py:451` (`apply_dealbreakers`)
- Modify: `termik/scoring.py:608-614` (kaldestedet)
- Modify: `termik/fetch_weather.py:109` (`process_point_hour` skal sende serien med)
- Test: `termik/tests/test_scoring.py`

**Step 1: Skriv de fejlende tests**

```python
def test_effective_radiation_remembers_recent_peak():
    # Kl. 19 i august: SW er faldet til 220, men kl. 16 var den 640.
    # Grænselaget er stadig blandet, termikken lever.
    eff = effective_radiation(current=220.0, trailing=[640.0, 480.0, 330.0])
    assert eff > 400

def test_effective_radiation_no_credit_on_a_dead_day():
    # Overskyet hele dagen: intet at huske.
    eff = effective_radiation(current=180.0, trailing=[260.0, 240.0, 210.0])
    assert eff < 250

def test_effective_radiation_never_below_current():
    eff = effective_radiation(current=700.0, trailing=[100.0, 120.0, 140.0])
    assert eff == 700.0
```

**Step 2: Kør og se dem fejle**

Kør: `python3 -m pytest termik/tests/test_scoring.py -k effective_radiation -v`
Forventet: FAIL med `NameError: name 'effective_radiation' is not defined`

**Step 3: Tilføj konstanter i `termik/config.py`**

Efter `WEIGHTS`:

```python
# Stråle-gate: (tærskel W/m², max score under tærsklen).
# Testes mod effektiv stråling, ikke øjebliksstråling, se
# scoring.effective_radiation.
RADIATION_GATE = [(400, 5), (250, 3), (100, 1)]

# Hvor meget af de seneste timers højeste stråling der stadig tæller.
# 0.65 er målt mod 2026-08-08: den bindende time er kl. 19, hvor de
# foregående tre timers maksimum er 657 W/m². Mindste brugbare faktor er
# 400/657 = 0.609, så 0.65 klarer kriterium 1 med cirka 7 % margin.
RADIATION_MEMORY_FACTOR = 0.65
RADIATION_MEMORY_HOURS = 3

# Hukommelsen må ikke redde en time hvis egen stråling er under bunden.
# Uden dette løftes kl. 21 med 30 W/m² fra cap 1 til cap 5, efter solnedgang.
RADIATION_MEMORY_FLOOR = 100
```

**Step 4: Implementer `effective_radiation` i `termik/scoring.py`**

Lige før `apply_dealbreakers`:

```python
def effective_radiation(current: float, trailing: list[float] | None = None) -> float:
    """Stråling korrigeret for grænselagets varmehukommelse.

    Konvektionen dør ikke samtidig med indstrålingen: grænselaget er
    allerede blandet og holder termikken gående en time eller to efter
    maksimal opvarmning. Vi krediterer derfor en brøkdel af de seneste
    timers højeste stråling, aldrig mindre end den aktuelle.

    trailing er de foregående RADIATION_MEMORY_HOURS timers stråling.

    Hukommelsen gælder kun mens der stadig er lys nok til at der er noget
    at huske: under RADIATION_MEMORY_FLOOR er solen reelt væk, og en høj
    eftermiddagspeak må ikke kunne løfte en time efter solnedgang.
    """
    if not trailing or current < RADIATION_MEMORY_FLOOR:
        return current
    return max(current, RADIATION_MEMORY_FACTOR * max(trailing))
```

Tre tests mere, ud over de tre nedenfor, til gulvet:

```python
def test_effective_radiation_no_memory_after_sunset():
    # 2026-08-08 kl. 21: 30 W/m², men kl. 18 var der 398.
    # Uden gulv ville hukommelsen løfte cap 1 til cap 5 efter solnedgang.
    eff = effective_radiation(current=30.0, trailing=[523.0, 398.0, 274.0])
    assert eff == 30.0
```

Husk `from termik.config import RADIATION_GATE, RADIATION_MEMORY_FACTOR` i importblokken (`scoring.py:9`).

**Step 5: Kør testene og se dem bestå**

Kør: `python3 -m pytest termik/tests/test_scoring.py -k effective_radiation -v`
Forventet: PASS, 3 tests.

**Step 6: Commit**

```bash
git add termik/config.py termik/scoring.py termik/tests/test_scoring.py
git commit -m "scoring: tilføj effective_radiation med grænselags-hukommelse"
```

**Step 7: Skriv den fejlende test for selve gaten**

```python
def test_dealbreaker_gate_uses_effective_radiation():
    # God aften: alt andet tillader 8+, øjebliksstråling er 220 men
    # peak for en time siden var 640. Må ikke klemmes til 5.
    score = apply_dealbreakers(
        8.2, lapse_rate=1.05, cloud_cover=35, precipitation=0,
        wind_kt=8.0, wind_gusts_kt=16.0, temp=21.5,
        shortwave_radiation=220.0,
        trailing_radiation=[640.0, 480.0, 330.0],
    )
    assert score > 6.5

def test_dealbreaker_gate_still_kills_a_genuinely_dark_hour():
    score = apply_dealbreakers(
        8.2, lapse_rate=1.05, cloud_cover=35, precipitation=0,
        wind_kt=8.0, wind_gusts_kt=16.0, temp=21.5,
        shortwave_radiation=60.0,
        trailing_radiation=[90.0, 80.0, 70.0],
    )
    assert score <= 1
```

**Step 8: Kør og se dem fejle**

Kør: `python3 -m pytest termik/tests/test_scoring.py -k dealbreaker_gate -v`
Forventet: FAIL, `apply_dealbreakers() got an unexpected keyword argument 'trailing_radiation'`

**Step 9: Ret `apply_dealbreakers`**

Tilføj parameteren i signaturen (`scoring.py:451`):

```python
    trailing_radiation: list[float] | None = None,
```

Erstat den hårdkodede gate-blok (`scoring.py:467-474`) med:

```python
    if shortwave_radiation is not None:
        eff = effective_radiation(shortwave_radiation, trailing_radiation)
        for threshold, cap in RADIATION_GATE:
            if eff < threshold:
                max_score = min(max_score, cap)
```

Bemærk at løkken skal ramme *alle* tærskler den er under, ikke kun den første, så en time med 50 W/m² også får cap 1. `RADIATION_GATE` er sorteret faldende, så det falder ud af sig selv.

**Step 10: Kør og se dem bestå**

Kør: `python3 -m pytest termik/tests/test_scoring.py -v`
Forventet: PASS. Eksisterende gate-tests skal stadig bestå, fordi `trailing_radiation=None` giver præcis den gamle opførsel.

**Step 11: Før serien igennem fra fetch-laget**

I `termik/fetch_weather.py:109`, `process_point_hour`, udtræk de foregående timers stråling:

```python
    trailing_start = max(0, hour_index - RADIATION_MEMORY_HOURS)
    trailing_radiation = [
        v for v in hourly_data["shortwave_radiation"][trailing_start:hour_index]
        if v is not None
    ]
```

Send den videre til `compute_thermal_score`, som sender den videre til `apply_dealbreakers`. Det kræver en gennemgående parameter i `compute_thermal_score` (`scoring.py:514`) og i kaldet på `scoring.py:608-614`.

**Step 12: Kør hele suiten**

Kør: `python3 -m pytest termik/tests -q`
Forventet: alle består.

**Step 13: Commit**

```bash
git add termik/scoring.py termik/fetch_weather.py termik/tests/test_scoring.py
git commit -m "scoring: stråle-gate bruger effektiv stråling med hukommelse"
```

---

## Task 4: Kalibrer mod referencedagene

**Files:**
- Create: `termik/tools/replay_day.py`
- Modify: `termik/config.py` (kun konstanter, hvis kalibreringen kræver det)

**Step 1: Skriv replay-scriptet**

Scriptet skal hente rå timedata for en plads og dag via samme kald som Task 2, køre `compute_thermal_score` på hver time, og printe score pr. time. Så kan gate-ændringen måles direkte mod de to sager uden at vente på et produktions-run.

**Step 2: Kør mod lørdag**

```bash
python3 -m termik.tools.replay_day ringsted 2026-08-08
```

Acceptkriterium 1: kl. 18:00 og 19:00 skal score over 6.5.

**Step 3: Kør mod søndag**

```bash
python3 -m termik.tools.replay_day ringsted 2026-08-09
```

Acceptkriterium 2: kl. 10:00 til 14:00 skal blive på 3.0 eller derunder.

**Step 4: Juster om nødvendigt**

Kun `RADIATION_MEMORY_FACTOR` og `RADIATION_GATE` må røres her. Rammer man ikke begge kriterier med én indstilling, så noter det og gå videre: Task 5 kan flytte søndag, og kriterie 2 revurderes til sidst i Task 6.

**Step 5: Kør sæsonanalysen igen**

Genbrug `gate_season.py` fra undersøgelsen (ligger i scratchpad, kopiér den ind i `termik/tools/`). Målet er ikke nul klemte timer, det er at 19:00-spidsen på præcis 5.0 forsvinder. Forvent stadig klemning kl. 20 og 21, det er korrekt.

**Step 6: Commit**

```bash
git add termik/tools/ termik/config.py
git commit -m "tools: replay og sæsonanalyse til gate-kalibrering"
```

---

## Task 5: Lad caps se cirrus som `score_solar` gør

To ting er uenige i dag, og de skal bringes på linje uden at miste den blunte cloud-cap der faktisk fangede søndag rigtigt.

**Files:**
- Modify: `termik/scoring.py:219-258` (træk `effective_cloud` ud i egen funktion)
- Modify: `termik/scoring.py:451` (`apply_dealbreakers`)
- Modify: `termik/config.py`
- Test: `termik/tests/test_scoring.py`

**Step 1: Skriv den fejlende test for udtrækket**

```python
def test_effective_cloud_cover_weights_cirrus_lighter():
    assert effective_cloud_cover(90, 0, 0, 90) == 45.0
    assert effective_cloud_cover(90, 90, 0, 0) == 90.0

def test_effective_cloud_cover_falls_back_to_total():
    assert effective_cloud_cover(75, None, None, None) == 75
```

**Step 2: Kør og se den fejle**

Kør: `python3 -m pytest termik/tests/test_scoring.py -k effective_cloud -v`
Forventet: FAIL, `NameError`

**Step 3: Træk funktionen ud**

Flyt beregningen fra `score_solar` (`scoring.py:238-250`) til:

```python
def effective_cloud_cover(
    cloud_cover: float,
    cloud_cover_low: float | None = None,
    cloud_cover_mid: float | None = None,
    cloud_cover_high: float | None = None,
) -> float:
    """Skydække vægtet efter lag. Cirrus dæmper mindre pr. procent end stratus."""
    if cloud_cover_low is None or cloud_cover_mid is None or cloud_cover_high is None:
        return cloud_cover
    return min(
        100.0,
        cloud_cover_low * 1.0 + cloud_cover_mid * 0.7 + cloud_cover_high * 0.5,
    )
```

Lad `score_solar` kalde den. Ingen adfærdsændring der, så de tre cirrus-tests fra maj skal stadig bestå uændret.

**Step 4: Kør og se alt bestå**

Kør: `python3 -m pytest termik/tests/test_scoring.py -q`
Forventet: alle består, inklusive `test_solar_cirrus_shield_penalised_when_total_cloud_low`.

**Step 5: Commit**

```bash
git add termik/scoring.py termik/tests/test_scoring.py
git commit -m "refactor: træk effective_cloud_cover ud af score_solar"
```

**Step 6: Skriv de fejlende tests for cap-siden**

Her er den vigtige afvejning. Den nuværende cap `cloud_cover >= 87 → max 2` fangede søndag rigtigt. Hvis vi bare skifter til effektivt skydække, bliver 90 % cirrus til 45 og cap'en forsvinder. Derfor: brug effektivt skydække til den generelle cap, men tilføj en separat cap for tykke cirrus-skjolde.

```python
def test_thick_cirrus_shield_caps_score():
    # Søndag 2026-08-09: næsten total cirrus, alt andet så fint ud.
    score = apply_dealbreakers(
        7.5, lapse_rate=0.99, cloud_cover=92, precipitation=0,
        wind_kt=9.5, wind_gusts_kt=19.0, temp=24.6,
        shortwave_radiation=420.0,
        cloud_cover_low=2, cloud_cover_mid=8, cloud_cover_high=92,
    )
    assert score <= 3

def test_thin_cirrus_does_not_cap():
    # 55 % cirrus, ellers klart: må ikke rammes af cirrus-cap'en.
    score = apply_dealbreakers(
        7.5, lapse_rate=0.99, cloud_cover=55, precipitation=0,
        wind_kt=8.0, wind_gusts_kt=15.0, temp=22.0,
        shortwave_radiation=600.0,
        cloud_cover_low=0, cloud_cover_mid=5, cloud_cover_high=55,
    )
    assert score > 6

def test_low_stratus_still_capped_hard():
    score = apply_dealbreakers(
        7.5, lapse_rate=0.99, cloud_cover=90, precipitation=0,
        wind_kt=8.0, wind_gusts_kt=15.0, temp=18.0,
        shortwave_radiation=150.0,
        cloud_cover_low=90, cloud_cover_mid=0, cloud_cover_high=0,
    )
    assert score <= 2
```

**Step 7: Kør og se dem fejle**

Kør: `python3 -m pytest termik/tests/test_scoring.py -k cirrus -v`
Forventet: FAIL på uventede keyword-argumenter.

**Step 8: Tilføj konstant i `termik/config.py`**

```python
# Tykt cirrus-skjold: kalibreret mod 2026-08-09, hvor næsten total cirrus
# gav ubrugelig termik selvom lapse rate og vind så fine ud. Maj-referatets
# research: cirrostratus med optisk dybde > 1.5 er ødelæggende, mens tynd
# cirrus er ubetydelig. Den lineære 0.5-vægt fanger ikke den øvre ende.
#
# Testes mod de seneste timers HØJESTE cirrus, ikke mod øjebliksværdien.
# Målt 2026-08-09 kl. 10 til 14: 99, 81, 59, 84, 100. En øjeblikstest ved
# 85 fanger kun kl. 10 og 14 og dumper kriterium 2. Et skjold der har stået
# siden kl. 06 har allerede lukket jorden ned, uanset et enkelt hul kl. 12,
# så trailing-maksimum giver 99, 99, 99, 99, 100 og fanger hele blokken.
# Lørdag rammes ikke: cirrus toppede på 57 kl. 07 og lå så på 0 til 23.
CIRRUS_SHIELD_THRESHOLD = 85
CIRRUS_SHIELD_MAX_SCORE = 3
CIRRUS_SHIELD_MEMORY_HOURS = 3
```

**Step 9: Ret `apply_dealbreakers`**

Tilføj `cloud_cover_low`, `cloud_cover_mid`, `cloud_cover_high` som keyword-parametre med default `None`. Erstat cloud-cap'en:

```python
    eff_cloud = effective_cloud_cover(
        cloud_cover, cloud_cover_low, cloud_cover_mid, cloud_cover_high
    )
    if eff_cloud >= 87:
        max_score = min(max_score, 2)
    shield = max([cloud_cover_high] + (trailing_cirrus or [])) \
        if cloud_cover_high is not None else None
    if shield is not None and shield >= CIRRUS_SHIELD_THRESHOLD:
        max_score = min(max_score, CIRRUS_SHIELD_MAX_SCORE)
```

Opdater kaldestedet (`scoring.py:608-614`) så lagene sendes med. De findes allerede i `compute_thermal_score`s signatur fra maj-fixet. `trailing_cirrus` føres igennem fra `process_point_hour` på samme måde som `trailing_radiation` i Task 3, med `CIRRUS_SHIELD_MEMORY_HOURS` som vindue.

**ADVARSEL, fundet i code review af Task 3: cap-ombytningen åbner et nyt hul.** Den rå `cloud_cover >= 87`-cap er i dag det eneste der fanger et tykt mellemhøjt dække. Måler man et altostratus-dække med rå dækning 90, alt sammen mellemhøjt:

| | score |
|---|---|
| i dag (rå 90 rammer cap'en) | 2.0, "Ingen brugbar termik" |
| efter Task 5 (effektiv 63, cap'en rammer ikke) | **8.9, "God termik"** |

Cirrus-skjoldet redder det ikke, det kræver høj ≥ 85. Det er samme fejltype som C1, ad en anden vej. **Task 5 må ikke shippe cap-ombytningen uden en mellemhøj pendant til cirrus-skjoldet.** Kalibrér den mod casen ovenfor, og husk at Task 6's frontscenarie-test ved rå dækning 90 er tænkt som netop denne interaktionstest.

**Bemærk hvad der ikke længere sker:** efter denne ændring læser caps ikke `cloud_cover`-totalen når lagene findes. Det er bevidst, jf. beslutningen i "Målt sandhed fra Task 2": totalen modsiger sine egne lag i `best_match`. `effective_cloud_cover` falder kun tilbage på totalen når lagene mangler helt (ældre fetches). Konsekvensen er at den gamle `cloud_cover >= 87`-cap, der tilfældigvis fangede søndag rigtigt i morgen-runnet, ikke længere fyrer på de data: søndagens totaler var 55 til 79. Det er cirrus-skjoldet der skal fange dagen nu, og kriterium 2 er testen på om det virker.

**Step 10: Kør hele suiten**

Kør: `python3 -m pytest termik/tests -q`
Forventet: alle består.

**Step 11: Kør replay igen mod begge referencedage**

```bash
python3 -m termik.tools.replay_day ringsted 2026-08-08
python3 -m termik.tools.replay_day ringsted 2026-08-09
```

Begge acceptkriterier skal nu holde samtidig. Gør de ikke det, så juster `CIRRUS_SHIELD_THRESHOLD` og `RADIATION_MEMORY_FACTOR`, ikke testene.

**Step 12: Commit**

```bash
git add termik/scoring.py termik/config.py termik/tests/test_scoring.py
git commit -m "scoring: caps bruger cirrus-vægtet skydække plus cirrus-skjold-cap"
```

---

## Task 6: Grænselagshøjde som scoringsinput

> **Rykket frem foran Task 4 efter code review af Task 3.** Se "C1" nedenfor: hukommelsen i Task 3 kan ikke skelne solnedgang fra et skydække der trækker ind, og grænselagshøjden er den fysisk rigtige måde at lukke det hul. Task 6 skal derfor både løse kriterium 3 og levere værnet til Task 3, før der kalibreres i Task 4.

### C1: hukommelsen kan ikke se forskel på solnedgang og en front

`effective_radiation` ser kun på størrelsen af strålingen, aldrig på **hvorfor** den er faldet. Et mellemhøjt skydække der trækker ind midt på eftermiddagen giver præcis samme signatur som solnedgang, og får samme redning. Målt ende til ende gennem `compute_thermal_score` på en ellers god augustdag (23 °C, lapse 1.0, dække 85 % hvoraf 75 % mellemhøjt, direkte 60 W/m², SW knust fra 720 til 150):

| | score |
|---|---|
| uden hukommelse (før Task 3) | 3.0, "Svag termik" |
| med hukommelse (efter Task 3) | **8.8, "God termik"** |

Det er nøjagtig den fejltype hele planen findes for at rette, nået ad en ny vej.

**Task 5 lukker det ikke.** Det var den oprindelige antagelse i reviewet, men regnestykket holder ikke: med lav 10, mellem 75, høj 0 giver `effective_cloud_cover` 62.5, altså under 87-cap'en, og cirrus-skjoldet kræver høj ≥ 85. Ingen af Task 5's to mekanismer fyrer på et mellemhøjt frontdække.

**Frontcasens input, rettet.** Den første måling brugte `temp_180m=19.5`, hvilket giver en overadiabatisk overflade-lapse på 1.97 og er fysisk uforeneligt med 150 W/m². Genkørt over realistiske værdier holder fundet: scoren bliver på 8.8 helt ned til en overflade-lapse på 0.56, som er rimelig for et dække der lige er trukket ind. Brug 0.84 eller 0.56 som reference, ikke 1.97.

**Grænselagshøjden lukker det ikke alene.** Tre indvendinger fra code review, hvoraf den første er strukturel:

1. **Residuallaget.** En profilbaseret grænselagsdiagnose måler det *velblandede* lag, ikke det *aktivt konvekterende*. Når overfladefluxen skæres væk, forsvinder blandingslaget ikke, det bliver et residuallag med stort set uændret profil, og diagnosen rapporterer videre den gamle dybde. Den kan altså ikke skelne "konvekterer i 1200 m" fra "kører på frihjul i 1200 m", præcis den skelnen strålingshukommelsen allerede fejler på. Værnet ville arve den fejl det skulle krydstjekke.
2. **Solnedgangskollapset drives af en mekanisme dagdækket undertrykker.** Kollapset fra 1000 til 225 m skyldes radiativ afkøling, overfladeinversion og et Ri-spring. Et dække midt på dagen gør det modsatte: det reducerer langbølget tab, så ingen inversion dannes og dybden holder sig høj. Signalet er altså stærkest hvor hukommelsen i forvejen var sikker.
3. **Post-frontal koldluftadvektion med stratocumulus**, som er almindelig i Danmark: overfladefluxen forbliver positiv, blandingslaget er dybt, og strålingen er alligevel knust.

**Overflade-lapse kan ikke kalibreres.** Det var det foreslåede alternativ, og fysisk er det det rigtigere signal, fordi det følger fluxen og ikke den ophobede profil. Men `temperature_180m` er `None` for **alle 360 historiske timer** i API-svaret, så `surface_lapse_rate` kan ikke beregnes for nogen af referencedagene. Feltet findes kun for forecast-timer. Det udelukker både kalibrering og offline regressionstests for de to dage, og derfor er det fravalgt.

### Beslutning: to værn med hver sit job

- **Skydække-delta lukker C1.** Faldt strålingen fordi skyer trak ind, eller fordi solen gik ned? Lørdag aften faldt skydækket (57, 61, 48, 32, 31, 26), et dække der trækker ind får det til at stige. Data findes historisk, så det kan kalibreres. Hukommelsen blokeres når skydækket er steget væsentligt hen over vinduet.
- **Grænselagshøjde løser kriterium 3.** Søndag kl. 18 med 780 m mod lørdagens 1250 m ved samme klokkeslæt. Det er det den blev godkendt til, og her er signalet gyldigt.

Hver mekanisme bruges kun hvor dens signal faktisk holder. De målte tal fra Task 2:

| | lør 08-08 | søn 08-09 |
|---|---|---|
| 17:00 | 1685 | 980 |
| 18:00 | 1250 | 780 |
| 19:00 | **1000** | 355 |
| 20:00 | **225** | 165 |
| 21:00 | 90 | 110 |

Grænselagshøjden skiller kriterium 3 rent: søndag kl. 18 har 780 m mod lørdagens 1250 m. Den rammer også kl. 20 lørdag (225 m), hvilket dækker den uverificerede kl. 20-løftning spec-reviewet fandt, og svarer til pilotens ord: godt til kl. 19.

**Krav til denne task:**

1. **Skydække-delta-værn på `effective_radiation`**, så hukommelsen kun gælder når strålingsfaldet ikke skyldes tilkommende skyer. Kalibrér mod lørdag aften, hvor skydækket faldt og hukommelsen skal virke.
2. **Grænselagshøjde til kriterium 3**, kalibreret mod tabellen ovenfor.
3. **Acceptteste frontscenariet i to varianter**, begge skal falde tilbage til omkring 3.0 og ikke 8.8:
   - mellemhøjt dække ved overflade-lapse 0.84
   - samme dække ved rå dækning 90, som fanger interaktionen med Task 5 nedenfor
4. **Verificér før du bygger:** grænselagshøjden under et dække midt på dagen, ikke kun ved solnedgang. Tallene 1250/1000/225 sampler kun solnedgangsmekanismen. Findes der en overskyet eftermiddagstime i Task 2-data, så tjek den, i stedet for at bygge på antagelsen om at dybden kollapser.

### Baggrund

Tilføjet efter Task 2. Søndagens værste time, kl. 18 med 7.4, røres ikke af hverken Task 3 eller Task 5: himlen var klaret op og strålingen lå over gate-tærsklen. Grænselagshøjden er det eneste felt der skiller timen, 780 m mod lørdagens 1250 m ved samme klokkeslæt. Feltet hentes allerede (`config.py:38`), persisteres allerede og vises allerede i popup'en, men bruges kun i `comments.py:106` og aldrig i scoringen.

**Files:**
- Modify: `termik/config.py`
- Modify: `termik/scoring.py` (ny score-funktion plus vægt, eller cap, se trin 1)
- Test: `termik/tests/test_scoring.py`

**Step 1: Beslut mekanisme før du skriver kode**

To muligheder, og valget skal træffes på data, ikke på smag:

- **Som cap:** lav grænselagshøjde begrænser scoren, i stil med de øvrige dealbreakers.
- **Som vægtet delscore:** grænselagshøjde bliver en faktor i `WEIGHTS` på linje med lapse rate og solar.

Kør begge mod referencedagene før du vælger. Afgørende forbehold fra Task 2: grænselagshøjden skiller **ikke** dagene kl. 11 til 13 (1270 mod 1210), så den kan ikke bære kriterium 2 og må ikke sættes så aggressivt at den prøver. Den skal ramme kriterium 3 uden at røre kriterium 1, hvor lørdag kl. 18 og 19 har 1250 og 1000 m.

En vægtet delscore ændrer alle scores på alle dage og kræver rekalibrering af hele fordelingen. En cap rammer kun de timer der falder under tærsklen. Start med at afprøve cap'en, den er billigere at verificere, og gå kun til delscoren hvis cap'en ikke kan skille timerne.

**Step 2: Skriv de fejlende tests**

Mindst disse tre, med de faktiske målte værdier:

```python
def test_shallow_boundary_layer_caps_score():
    # 2026-08-09 kl. 18: himlen klaret op, stråling 429, men
    # grænselaget kun 780 m. Systemet gav 7.4, virkeligheden var ingenting.
    ...  # forvent <= 5.0

def test_deep_boundary_layer_does_not_cap():
    # 2026-08-08 kl. 18: 1250 m, piloten fløj god termik.
    ...  # forvent > 6.5

def test_boundary_layer_does_not_separate_midday_reference_hours():
    # Kl. 11-13 er dagene næsten ens (1270 mod 1210). Mekanismen må
    # ikke lade som om den kan skille dem: begge skal falde på samme
    # side af tærsklen, så kriterium 2 løses af cirrus-skjoldet.
    ...
```

Den tredje test er den vigtigste. Den forhindrer at nogen sætter tærsklen et sted der tilfældigvis får kriterium 2 til at bestå af den forkerte grund.

**Step 3 til 6:** Kør, implementér, kør, commit. Følg samme TDD-rytme som Task 3.

**Step 7: Replay alle tre kriterier**

```bash
python3 -m termik.tools.replay_day ringsted 2026-08-08
python3 -m termik.tools.replay_day ringsted 2026-08-09
```

Alle tre acceptkriterier skal holde samtidig. Kør også sæsonanalysen igen: en ny cap på et felt der aldrig har været brugt i scoringen kan flytte mange timer, og den slags skal ses før det deployes.

**Step 8: Commit**

```bash
git add termik/scoring.py termik/config.py termik/tests/test_scoring.py
git commit -m "scoring: brug grænselagshøjde til at fange lave blandingslag"
```

---

## Task 7: Regressionstests, referat og deploy

**Files:**
- Create: `termik/tests/test_reference_days.py`
- Create: `docs/Referat/2026-08-12-straale-gate.md` (udvid den fra Task 2)
- Modify: `docs/PROJEKT-DOKUMENTATION.md`

**Step 1: Lås de tre sager fast som regressionstests**

Skriv `test_reference_days.py` med de faktiske timedata fra Task 2 hårdkodet ind, så testene kører uden netværk. Tre tests: lørdag 18 og 19 over 6.5, søndag 10 til 14 på 3.0 eller derunder, søndag 18 på 5.0 eller derunder. Det er de eneste sager vi har pilot-verificeret, og de skal ikke kunne knække stille.

Hårdkod fra **forecast-endpointet**, ikke arkivet, jf. modelfundet i Task 2.

**Step 2: Kør dem**

Kør: `python3 -m pytest termik/tests/test_reference_days.py -v`
Forventet: PASS

**Step 3: Skriv referatet færdigt**

Udvid `docs/Referat/2026-08-12-straale-gate.md` efter mønstret i `2026-05-24-cirrus-direct-radiation.md`: udgangspunkt, diagnose med sæsonmålingen, løsningsvalg, implementering, verifikation, åbne emner.

Åbne emner der skal med:

- **Vindretning og luftmasse er stadig ikke scoret.** `wind_dir` bruges kun til søbrise. Pilotens tommelfingerregel, højtryk nordvest for Danmark giver god termik, er ikke kodet. `calculate_modifiers` (`scoring.py:428-448`) har `pressure_trend` og `temp_850hpa_trend` som svage proxyer, ±0.5 på en 0-10 skala. Task 2 bekræftede mønsteret i data: lørdag W 273 til 236 grader med 1018 til 1019 hPa fladt, søndag S 150 til 179 grader med trykfald 1014.9 til 1007.1.
- **Lapse rate skelnede ikke 8. fra 9. august.** Den tungest vægtede variabel (0.30) adskilte ikke de to dage. Task 6 tager grænselagshøjden, som skiller dem klart uden for kl. 11 til 13, men lapse rate-vægten er stadig ikke efterprøvet.
- **Strålingsfeltet reagerer knap på modellens egen cirrus.** Søndag kl. 13 gav 690 W/m² mod lørdagens 736, direkte-andel 68 mod 73 %, og ophobet morgenstråling kl. 06 til 10 var 833 mod 843. Reelt ens, på en dag hvor himlen var lukket. Kun `cloud_cover_high` vidste besked. Samme svaghed som maj-referatet flaggede.
- **`cloud_cover`-totalen modsiger sine egne lag** i `best_match`. Caps læser den ikke længere efter Task 5, men `score_solar` gør stadig som fallback, og feltet vises i UI.
- **Begrænsende faktor vises stadig ikke i UI.** Samme åbne punkt som i maj-referatet. Med Task 1 på plads er data der nu.
- **Kalibreringsgrundlaget er n=2.** Kriterium 1 klarer sig med cirka 7 % margin (mindste brugbare `RADIATION_MEMORY_FACTOR` er 0.609 mod valgte 0.65) og afhænger af at hukommelsen når præcis tre timer tilbage. Flere pilot-verificerede dage ville være det billigste næste skridt.

**Step 4: Kør hele suiten en sidste gang**

Kør: `python3 -m pytest termik/tests -q`
Forventet: alle består.

**Step 5: Commit og push**

```bash
git add docs/ termik/tests/test_reference_days.py
git commit -m "docs: referat for stråle-gate og cirrus-caps"
git push origin main
```

**Step 6: Trig et forecast-run manuelt**

```bash
gh workflow run update-forecast.yml
gh run watch
```

Verificér at `termik/output/data/current.json` nu indeholder `shortwave_radiation` og `cloud_cover_high` på en flyveplads, og at deployet gik igennem.

---

## Rækkefølge og afhængigheder

```
Task 1 (persister felter)  ✅ e606849
   │
   ├─→ Task 2 (hent referencedage)  ✅ 0d04f77  ← præmis bekræftet
   │        │
   │        ├─→ Task 3 (gate med hukommelse) ─→ Task 4 (kalibrer)
   │        │                                        │
   │        ├─→ Task 5 (cirrus i caps) ──────────────┤
   │        │                                        │
   │        └─→ Task 6 (grænselagshøjde) ────────────┤
   │                                                 │
   └─────────────────────────────────────────────────┴─→ Task 7 (regression + deploy)
```

Task 2 var den kritiske og er passeret: søndagens lave skydække var 0 hele dagen, cirrus 99/81/59/84/100 kl. 10 til 14. Præmissen for Task 5 holder.

Task 6 er tilføjet efter Task 2 og **rykket frem foran Task 4** efter code review af Task 3: den skal levere grænselags-værnet der lukker C1, før der kalibreres. Rækkefølgen er nu Task 3, Task 6, Task 4, Task 5, Task 7.

**Denne branch må ikke merges til `main` før C1 er lukket.** `update-forecast.yml` kører på cron fra `main`, så et merge er ude hos piloterne inden for 3 timer. Task 3 alene indfører en ny "god score på en døende dag"-vej, hvilket er værre end den fejl den retter. Deploy sker først i Task 7, som planlagt.

## Risici

- **Kriterie 2 er skrøbeligt, og mere end først antaget.** Task 5 fjerner den gamle totalbaserede cap, som tilfældigvis fangede søndag i morgen-runnet. Efter Task 5 er cirrus-skjoldet det eneste der holder søndag nede, og det virker kun med trailing-maksimum. Replay efter hver ændring, ikke kun til sidst.
- **Kriterie 1 og 3 trækker mod hinanden.** Kriterie 3 skal trække søndag kl. 18 ned med grænselagshøjde, kriterie 1 skal holde lørdag kl. 18 og 19 oppe. Timerne ligger tæt: 780 mod 1250 m. Sættes tærsklen for højt, ryger lørdag med.
- **Tre scoringsændringer på én gang.** Task 3, 5 og 6 rører alle det samme resultat. Sæsonanalysen skal køres efter hver af dem, ikke kun til sidst, ellers kan man ikke se hvilken ændring der flyttede hvad.
- **To pilot-observationer er et tyndt datagrundlag.** Vi kalibrerer på n=2, og kriterium 1 klarer sig med cirka 7 % margin. Sæsonanalysen i Task 4 Step 5 er modvægten: den viser om ændringen flytter hele fordelingen fornuftigt eller kun de to dage.
- **Payload vokser.** Målt +600 KB på 5.99 MB. Tåleligt over ledningen (filen gzipper 12:1), men det lander på hver 3-timers commit. `.git` er allerede 674 MB over 946 data-commits. Separat problem, ikke skabt af denne plan, men den accelererer det.
