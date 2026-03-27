# Termik-forecast for Danmark — Designdokument

**Dato:** 2026-03-27
**Formål:** Automatisk termik-vurdering for danske svæveflyvere baseret på Open-Meteo vejrdata.

## Arkitektur

```
Open-Meteo API
      |
      v
Python-script (cron, /3t) --> JSON-filer --> Statisk HTML/Leaflet.js
```

- Python-script henter vejrdata, beregner termik-score, genererer JSON
- Statisk HTML-side med Leaflet.js viser heatmap-kort + svæveflyveplads-pins
- Ingen server nødvendig — kan hostes som statiske filer

## Geografi

### Svæveflyvepladser (~28 stk)

| Plads | Region |
|-------|--------|
| Aars | Nordjylland |
| Sæby/Ottestrup | Nordjylland |
| Vinkel/Skive | Nordjylland |
| Svævethy/Mors | Nordjylland |
| Viborg | Nordjylland |
| True/Aarhus | Midtjylland |
| Arnborg | Midtjylland |
| Chr. Hede/Silkeborg | Midtjylland |
| Skinderholm/Herning | Midtjylland |
| Lemvig | Midtjylland |
| Nr. Felding/Holstebro | Midtjylland |
| Videbæk | Midtjylland |
| Billund | Sydjylland |
| Skrydstrup | Sydjylland |
| Gesten/Kolding | Sydjylland |
| Rødekro | Sydjylland |
| Tønder | Sydjylland |
| Vejle | Sydjylland |
| Bolhede | Sydjylland |
| Broby/Fyn | Fyn |
| Gørløse | Sjælland |
| Frederikssund | Sjælland |
| Kalundborg | Sjælland |
| Kongsted | Sjælland |
| Ringsted/Midtsjælland | Sjælland |
| Tølløse | Sjælland |
| Lolland-Falster | Sjælland |
| Rønne | Bornholm |

### Grid-punkter (~70 stk)

0.4 x 0.4 grader grid over Danmark (54.5N-57.8N, 8.0E-15.2E). Punkter i havet filtreres fra.

## Dataopdatering

- Hver 3. time via cron
- 3 dages prognose, time-opløsning
- Open-Meteo API (gratis, ingen nøgle)
- ~2 batch-kald per opdatering (max 50 koordinater per kald)

## Open-Meteo parametre

### Hourly
- temperature_2m
- dewpoint_2m
- relativehumidity_2m
- windspeed_10m, winddirection_10m, windgusts_10m
- cloudcover, cloudcover_low, cloudcover_mid, cloudcover_high
- precipitation
- shortwave_radiation
- cape
- surface_pressure

### Pressure levels
- temperature_850hPa, temperature_700hPa
- windspeed_850hPa, winddirection_850hPa

### Afledte beregninger
- Spread = temperature_2m - dewpoint_2m
- Skybase (m) = spread x 125
- Skybase (ft) = spread x 400
- Lapse rate = (temperature_2m - temperature_850hPa) / 15
- Tryktendens = surface_pressure delta over 3 timer

## Scoringsmodel

### Basis-scorer (vægtet sum, 0-10)

| Faktor | Vægt | 10 point | 0 point |
|--------|------|----------|---------|
| Lapse rate | 30% | >= 1.2 C/100m | < 0.65 C/100m |
| Solindstråling | 20% | SKC + fuld stråling | OVC + ingen stråling |
| Spread | 15% | 8-15 C (optimal skybase) | < 3 C (tåge) |
| Vindstyrke | 15% | 5-15 kt | > 35 kt eller 0 kt |
| Temperatur | 10% | Høj (sæsonjusteret) | < 5 C |
| Nedbør | 10% | Ingen, tørt seneste 6t | Aktiv nedbør |

### Modifikatorer
- CAPE > 300: +0.5, CAPE > 700: +1.0
- Søbrise-penalty: -1 til -3 (kystpunkter)
- Tryktendens stigende: +0.5, faldende: -0.5
- Koldluftsadvektion (faldende temp_850): +0.5

### Dealbreakers (sætter loft for score)
- Lapse rate < 0.50: max 1
- Lapse rate < 0.65: max 3
- Skydække >= 87%: max 2
- Aktiv nedbør: max 1
- Vind > 35 kt: max 2
- Temperatur < 5 C: max 3

### Score-labels
- 9-10: Fremragende termik
- 7-8: God termik
- 5-6: Moderat termik
- 3-4: Svag termik
- 0-2: Ingen brugbar termik

## Søbrise-model

For hvert punkt:
1. Forudberegnet kystafstand (statisk)
2. Vindretning ift. kystretning -> fraland/påland
3. Land/hav temperaturforskel (hav-temp estimeret fra måned)
4. Søbrise-penalty skaleret med afstand (max 80 km fra kyst)

Fyn og Sjælland rammes hårdest, Midtjylland mindst.

## Kommentargenerering

Automatisk genereret tekst fra byggeklodser:
- Stabilitetsvurdering (altid med)
- Skybase-info (hvis termik mulig)
- Advarsler (søbrise, udkagning, overudvikling, stærk vind, front)
- Vindvurdering
- Termik-tidsvindue (start, slut, peak)

## Filstruktur

```
termik/
  fetch_weather.py        # Hovedscript
  scoring.py              # Scoringsmodel
  locations.py            # Koordinater (pladser + grid)
  comments.py             # Kommentargenerering
  config.py               # Konfiguration
  requirements.txt
  output/
    index.html            # Hovedside med kort
    style.css
    app.js                # Leaflet + heatmap + interaktion
    data/
      current.json        # Alle punkter, alle timer, 3 dage
      airfields.json      # Svæveflyveplads-metadata
      meta.json           # Tidsstempel
  cron_setup.sh
```

## Frontend

- Leaflet.js kort centreret på Danmark (zoom 7)
- Heatmap-lag fra grid-punkter (leaflet-heat)
- Farverampe: mørkeblå (0) -> gul (5) -> rød (10)
- Svæveflyveplads-pins med farvekodning
- Dagvælger (3 knapper)
- Timeslider (06-21)
- Sidepanel med top-5 bedste pladser
- Klik-popup med detaljer og dagsforløb-diagram
- Responsivt (mobil: panel glider op fra bunden)

## Validering

Scoringsmodellen er testet mod 8 realistiske danske scenarier:
- Perfekt bagsidevejr: 9.7 (forventet 9-10)
- Moderat højtryk: 7.5 (forventet 5-7)
- Varmefront: 3.0 (forventet 2-3)
- Overskyet vinter: 1.0 (forventet 0-1)
- Kraftig vind + koldfront: 7.0 (forventet 5-7)
- Søbrise kyst: 6.4, indland: 8.4 (god differentiering)
- Udkagning: 4.8 (forventet 3-5)
- Sahara-luft: 3.0 (forventet 1-3, rettet via lapse rate dealbreaker)
