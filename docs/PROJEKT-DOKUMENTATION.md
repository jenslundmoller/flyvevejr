# Termik-forecast Danmark — Projektdokumentation

## Oversigt

Automatisk termik-vurdering for danske svæveflyvere. Systemet henter vejrdata fra Open-Meteo API, beregner en termik-score (0-10) for 79 punkter over hele Danmark, og viser resultatet som et interaktivt heatmap-kort på **https://flyvevejr.dk**.

Data opdateres automatisk hver 3. time via GitHub Actions.

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
│ (GitHub Actions, │     │ current.json   │     │ Leaflet.js heatmap  │
│  hver 3. time)   │     │ airfields.json │     │ flyvevejr.dk        │
└──────────────────┘     │ meta.json      │     └─────────────────────┘
                         └────────────────┘
```

### Dataflow

1. GitHub Actions kører `python -m termik` hver 3. time (kl. XX:15)
2. Scriptet henter vejrdata fra Open-Meteo for 79 punkter (2 batch-kald)
3. For hvert punkt beregnes termik-score for hver time, 3 dage frem (72 timer)
4. Resultatet skrives som JSON-filer
5. GitHub Actions committer de opdaterede JSON-filer og pusher
6. Push trigger GitHub Pages deploy
7. https://flyvevejr.dk viser den opdaterede side

### Hosting

| Komponent | Tjeneste |
|-----------|----------|
| Kode + data | GitHub repo `jenslundmoller/flyvevejr` |
| Automatisering | GitHub Actions (gratis for public repos) |
| Webhosting | GitHub Pages |
| Domæne | flyvevejr.dk |
| DNS | Cloudflare (CNAME → jenslundmoller.github.io, proxy fra) |
| SSL | GitHub Pages (Let's Encrypt) |
| Vejrdata | Open-Meteo API (gratis, ingen nøgle) |

---

## Geografi

### Svæveflyvepladser (28 stk)

Baseret på listen fra [Svæveflyveklubber i Danmark (Wikipedia)](https://da.wikipedia.org/wiki/Sv%C3%A6veflyveklubber_i_Danmark).

**Nordjylland:** Aars (Aviator Aalborg), Sæby/Ottestrup (Nordjysk), Vinkel/Skive, Svævethy/Mors, Viborg

**Midtjylland:** True/Aarhus, Arnborg (DSvU), Chr. Hede/Silkeborg, Skinderholm/Herning, Lemvig, Nr. Felding/Holstebro, Videbæk

**Sydjylland:** Billund, Skrydstrup, Gesten/Kolding, Rødekro, Tønder, Vejle, Bolhede

**Fyn:** Broby

**Sjælland:** Gørløse, Frederikssund, Kalundborg, Kongsted, Ringsted/Midtsjælland, Tølløse, Lolland-Falster

**Bornholm:** Rønne

### Grid-punkter (51 stk)

Et 0.4° × 0.4° grid over Danmark (54.5°N-57.8°N, 8.0°E-15.2°E). Punkter i havet er filtreret fra med en polygon-baseret landmassedetektering for Jylland, Fyn, Sjælland, Lolland-Falster og Bornholm.

**Total: 79 punkter** med vejrdata for hver time i 3 dage = 5.688 datapunkter per opdatering.

---

## Scoringsmodel

### Basis-scorer (vægtet sum)

| Faktor | Vægt | Score 10 | Score 0 |
|--------|------|----------|---------|
| Lapse rate (stabilitet) | 30% | ≥1.2°C/100m (meget labil) | <0.65°C/100m (stabil) |
| Solindstråling | 20% | Skyfrit + stærk stråling | Overskyet + ingen stråling |
| Spread (dugpunktsspredning) | 15% | 8-15°C (optimal skybase) | <3°C (tåge-risiko) |
| Vindstyrke | 15% | 5-15 kt (optimal udløsning) | >35 kt eller vindstille |
| Temperatur | 10% | Høj overfladetemperatur | <5°C |
| Nedbør | 10% | Tørt, ingen nedbør seneste 6t | Aktiv nedbør |

### Modifikatorer (justerer basis-scoren)

| Modifier | Effekt | Betingelse |
|----------|--------|-----------|
| CAPE-bonus | +0.5 / +1.0 | CAPE >300 / >700 J/kg |
| Tryktendens | +0.5 / -0.5 | Stigende / faldende >1.5 hPa/3t |
| Koldluftsadvektion | +0.5 | Faldende temp i 850 hPa |
| Søbrise-penalty | -1 til -3 | Kystpunkter med pålandsvind |

### Dealbreakers (hårdt loft for scoren)

| Betingelse | Max score | Begrundelse |
|-----------|-----------|------------|
| Lapse rate <0.50 | 1 | Stærk inversion — ingen termik mulig |
| Lapse rate <0.65 | 3 | Stabil atmosfære — meget begrænset termik |
| Skydække ≥87% | 2 | Sol blokeret — ingen opvarmning |
| Aktiv nedbør | 1 | Jorden afkøles |
| Vind >35 kt | 2 | For turbulent til brugbar termik |
| Temperatur <5°C | 3 | For koldt til konvektion |

Lapse rate-dealbreakeren er den vigtigste: **uden atmosfærisk instabilitet kan der ikke være termik**, uanset hvor godt de andre faktorer ser ud. Dette fanger f.eks. "Sahara-dage" med 30°C og blå himmel men stabil luft i højden.

### Score-labels

| Score | Label | Farve |
|-------|-------|-------|
| 9-10 | Fremragende termik | Rød |
| 7-8 | God termik | Orange |
| 5-6 | Moderat termik | Gul |
| 3-4 | Svag termik | Lyseblå |
| 0-2 | Ingen brugbar termik | Mørkeblå |

### Søbrise-model

Danmark er meget kystnært, og søbrisen er en af de vigtigste termik-dræbere. For hvert punkt beregnes:

1. **Kystafstand** (forudberegnet, statisk)
2. **Vindretning vs. kystretning** — er vinden fralands eller pålands?
3. **Land/hav temperaturforskel** — stor forskel + svag vind = høj søbrise-risiko
4. **Penalty skaleret med afstand** — max effekt inden for 80 km fra kysten

Fyn og Sjælland rammes hårdest, Midtjylland mindst.

### Validering

Modellen er testet mod 8 realistiske danske scenarier:

| Scenario | Resultat | Forventet |
|----------|----------|-----------|
| Perfekt bagsidevejr (juni) | 9.7 | 9-10 |
| Moderat dansk sommerdag | 7.5 | 5-7 |
| Varmefront nærmer sig | 3.0 | 2-3 |
| Overskyet vinterdag | 1.0 | 0-1 |
| Kraftig vind + koldfront | 7.0 | 5-7 |
| Søbrise kyst (Kongsted) | 6.4 | 5-7 |
| Søbrise indland (Arnborg) | 8.4 | 8-9 |
| Udkagningsdag | 4.8 | 3-5 |
| Sahara-luft (30°C, stabil) | 3.0 | 1-3 |

### Kommentargenerering

Systemet genererer en kort dansk kommentar (2-3 sætninger) der forklarer scoren. Kommentaren opbygges af moduler:

- **Stabilitetsvurdering** (altid med): "Labil atmosfære — god konvektion."
- **Skybase** (hvis termik mulig): "Skybase ca. 1290m (4200 ft)."
- **Advarsler** (betinget): søbrise, udkagning, overudvikling, stærk vind, front
- **Positive noter** (betinget): bagsidevejr, skygade-betingelser

---

## Open-Meteo API

### Endpoint

```
https://api.open-meteo.com/v1/forecast
```

Gratis, ingen API-nøgle. Understøtter multi-location i ét kald (kommaseparerede koordinater).

### Parametre der hentes

**Hourly (overflade):**
temperature_2m, dewpoint_2m, relative_humidity_2m, wind_speed_10m, wind_direction_10m, wind_gusts_10m, cloud_cover, cloud_cover_low, cloud_cover_mid, cloud_cover_high, precipitation, shortwave_radiation, cape, surface_pressure

**Pressure levels:**
temperature_850hPa, temperature_700hPa, wind_speed_850hPa, wind_direction_850hPa

### Afledte beregninger

| Beregning | Formel |
|-----------|--------|
| Spread | temperature_2m - dewpoint_2m |
| Skybase (m) | spread × 125 |
| Skybase (ft) | spread × 400 |
| Lapse rate | (temperature_2m - temperature_850hPa) / 15 |
| Tryktendens | Delta surface_pressure over 3 timer |
| Nedbør seneste 6t | Sum af precipitation for foregående 6 timer |

---

## Filstruktur

```
flyvevejr/
├── .github/
│   └── workflows/
│       ├── update-forecast.yml    # Henter vejrdata hver 3. time
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
│   ├── locations.py               # 28 svæveflyvepladser + 51 grid-punkter
│   ├── scoring.py                 # Scoringsmodel (11 funktioner)
│   ├── comments.py                # Kommentargenerering på dansk
│   ├── fetch_weather.py           # Open-Meteo API + databehandling
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
│   └── tests/
│       ├── __init__.py
│       ├── test_locations.py      # 8 tests
│       ├── test_scoring.py        # 50 tests
│       ├── test_comments.py       # 10 tests
│       └── test_fetch_weather.py  # 10 tests
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

- **Dagvælger**: 3 knapper (I dag / I morgen / Overmorgen)
- **Timeslider**: Kl. 06-21, opdaterer heatmap og markører i realtid
- **Sidepanel**: Top 5 bedste pladser for valgt tidspunkt

### Popup ved klik på svæveflyveplads

Viser: score med farvede prikker, label, kommentar, temperatur, spread, skybase, vind (retning + styrke), lapse rate, CAPE, skydække, fugtighed, samt et mini-søjlediagram med dagsforløbet.

### Responsivt

Desktop: sidepanel til højre. Mobil (<768px): sidepanel som bund-panel.

---

## GitHub Actions

### update-forecast.yml

- **Trigger**: Cron `0 */3 * * *` (hver 3. time kl. XX:15) + manuel dispatch
- **Kører**: Python 3.12, installerer requests, kører `python -m termik`
- **Committer**: Opdaterede JSON-filer til repo'et med bot-bruger

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

78 automatiserede tests fordelt på 4 moduler:

| Modul | Tests | Dækker |
|-------|-------|--------|
| test_locations.py | 8 | Datastruktur, koordinatvalidering, grid-dækning |
| test_scoring.py | 50 | Alle score-funktioner, dealbreakers, modifikatorer, 5 fuld-scenario tests |
| test_comments.py | 10 | Kommentargenerering for alle vejrsituationer |
| test_fetch_weather.py | 10 | URL-bygning, response-parsing, trendberegninger |

Kør alle tests:
```bash
source termik/.venv/bin/activate
python -m pytest termik/tests/ -v
```

---

## Drift og vedligeholdelse

### Automatisk drift

Systemet kører fuldautomatisk via GitHub Actions. Ingen server eller lokal maskine nødvendig.

### Manuel kørsel

```bash
cd /home/jens/Documents/Flyveteori
source termik/.venv/bin/activate
python -m termik
```

### Manuel trigger via GitHub

1. Gå til Actions-fanen på GitHub
2. Vælg "Update Termik Forecast"
3. Klik "Run workflow"

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
| **GitHub Actions** | Gratis CI/CD for public repos, cron-scheduling |
| **GitHub Pages** | Gratis hosting, custom domain-support, automatisk SSL |

---

## Kilder

- **Meteorologi SPL-teori kompendium** (EASA/ICAO pensum) — primær kilde for termik-faktorer
- **Open-Meteo API dokumentation** — https://open-meteo.com/en/docs
- **Wikipedia: Svæveflyveklubber i Danmark** — https://da.wikipedia.org/wiki/Svæveflyveklubber_i_Danmark
