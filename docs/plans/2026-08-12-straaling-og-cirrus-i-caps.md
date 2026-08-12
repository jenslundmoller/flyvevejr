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

Disse to sager er sandheden vi kalibrerer mod. Begge skal holde til sidst:

1. **Ringsted 2026-08-08 kl. 18:00 og 19:00** skal score over 6.5 (var 5.0). Piloten fløj god termik til 19.
2. **Ringsted 2026-08-09 kl. 10:00 til 14:00** skal blive på 3.0 eller derunder (var 2.0 i morgen-run, 6.2 i hindcast). Det var umuligt at finde noget.

Kriterium 2 er den farlige: WP3 gør cirrus-cap'en mildere, og hvis den bliver for mild, ryger søndag op i det grønne igen.

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
# 0.65 er valgt så en august-eftermiddag med peak ~640 W/m² holder sig
# over 400-tærsklen til omkring kl. 19. Kalibreres i Task 4.
RADIATION_MEMORY_FACTOR = 0.65
RADIATION_MEMORY_HOURS = 3
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
    """
    if not trailing:
        return current
    return max(current, RADIATION_MEMORY_FACTOR * max(trailing))
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
CIRRUS_SHIELD_THRESHOLD = 85
CIRRUS_SHIELD_MAX_SCORE = 3
```

**Step 9: Ret `apply_dealbreakers`**

Tilføj `cloud_cover_low`, `cloud_cover_mid`, `cloud_cover_high` som keyword-parametre med default `None`. Erstat cloud-cap'en:

```python
    eff_cloud = effective_cloud_cover(
        cloud_cover, cloud_cover_low, cloud_cover_mid, cloud_cover_high
    )
    if eff_cloud >= 87:
        max_score = min(max_score, 2)
    if cloud_cover_high is not None and cloud_cover_high >= CIRRUS_SHIELD_THRESHOLD:
        max_score = min(max_score, CIRRUS_SHIELD_MAX_SCORE)
```

Opdater kaldestedet (`scoring.py:608-614`) så lagene sendes med. De findes allerede i `compute_thermal_score`s signatur fra maj-fixet.

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

## Task 6: Regressionstests, referat og deploy

**Files:**
- Create: `termik/tests/test_reference_days.py`
- Create: `docs/Referat/2026-08-12-straale-gate.md` (udvid den fra Task 2)
- Modify: `docs/PROJEKT-DOKUMENTATION.md`

**Step 1: Lås de to sager fast som regressionstests**

Skriv `test_reference_days.py` med de faktiske timedata fra Task 2 hårdkodet ind, så testene kører uden netværk. To tests: lørdag 18 og 19 over 6.5, søndag 10 til 14 på 3.0 eller derunder. Det er de eneste to sager vi har pilot-verificeret, og de skal ikke kunne knække stille.

**Step 2: Kør dem**

Kør: `python3 -m pytest termik/tests/test_reference_days.py -v`
Forventet: PASS

**Step 3: Skriv referatet færdigt**

Udvid `docs/Referat/2026-08-12-straale-gate.md` efter mønstret i `2026-05-24-cirrus-direct-radiation.md`: udgangspunkt, diagnose med sæsonmålingen, løsningsvalg, implementering, verifikation, åbne emner.

Åbne emner der skal med:

- **Vindretning og luftmasse er stadig ikke scoret.** `wind_dir` bruges kun til søbrise. Pilotens tommelfingerregel, højtryk nordvest for Danmark giver god termik, er ikke kodet. `calculate_modifiers` (`scoring.py:428-448`) har `pressure_trend` og `temp_850hpa_trend` som svage proxyer, ±0.5 på en 0-10 skala.
- **Lapse rate skelnede ikke 8. fra 9. august.** Den tungest vægtede variabel adskilte ikke de to dage. Det er den næste rigtige undersøgelse.
- **Begrænsende faktor vises stadig ikke i UI.** Samme åbne punkt som i maj-referatet. Med Task 1 på plads er data der nu.

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
Task 1 (persister felter)
   │
   ├─→ Task 2 (hent referencedage)  ← låser op for al kalibrering
   │        │
   │        ├─→ Task 3 (gate med hukommelse) ─→ Task 4 (kalibrer)
   │        │                                        │
   │        └─→ Task 5 (cirrus i caps) ──────────────┤
   │                                                 │
   └─────────────────────────────────────────────────┴─→ Task 6 (regression + deploy)
```

Task 2 er den kritiske: hvis søndagens skydække viser sig at være lavt og ikke cirrus, falder præmissen for Task 5, og planen skal revideres før der skrives mere kode.

## Risici

- **Kriterie 2 er skrøbeligt.** Task 5 gør cirrus-cap'en mildere for tynd cirrus. Bliver `CIRRUS_SHIELD_THRESHOLD` sat for højt, ryger søndag op i det grønne igen. Replay efter hver ændring, ikke kun til sidst.
- **To pilot-observationer er et tyndt datagrundlag.** Vi kalibrerer på n=2. Sæsonanalysen i Task 4 Step 5 er modvægten: den viser om ændringen flytter hele fordelingen fornuftigt eller kun de to dage.
- **Payload vokser.** Anslået +550 KB på 6 MB. Tåleligt, men hold øje. Grid-punkter skal blive ved med at være strippede.
