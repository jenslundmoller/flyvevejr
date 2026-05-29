# Referat — Vejr-widget for favorit-plads

**Dato:** 2026-05-29
**Branch:** main
**Commit:** `13541a0` (widget) + opfølgende commit (sw-bump + dokumentation)
**Design:** [`docs/plans/2026-05-29-vejr-widget-design.md`](../plans/2026-05-29-vejr-widget-design.md)

## Udgangspunkt

Brugeren ønskede en visning af dagens generelle vejr "lige nu" for den plads,
man har sat som favorit-plads, i en widget i kortets venstre top under
zoom-knapperne. Vejret skulle ikke hentes ved hvert sidebesøg, men "hentes 1
gang i timen og caches på server".

Brugeren havde fundet en konkret widget på Uiverse.io (Praashoo7) med HTML+CSS,
som han ønskede genbrugt: et hvidt kort med stort temperaturtal, pladsnavn,
vejr-ikon, en udfoldelig detalje-række (Humidity, Wind, AQI, Real Feel,
Pressure) og en farvet bund-bjælke ("Healthy").

## Brainstorm og afklaring

Brainstorming-skill brugt før kodning. Tre afgørende fund fra kodebasen ændrede
præmissen for "caches på server":

1. **Der er ingen server.** Siden er 100 % statisk på GitHub Pages. Data
   genereres af `python -m termik` via GitHub Actions hver 3. time og committes
   som JSON.
2. **Favorit-pladsen er per-bruger** (gemt i `localStorage` under
   `termik-favorite-airfield`), så en server kan ikke vide hvilken plads der
   skal hentes vejr for.
3. **Al nødvendig data findes allerede** i `current.json`: hver airfield har
   time-for-time `temp`, `relative_humidity`, `wind_speed_kt`, `wind_dir`,
   `pressure`, `cloud_cover`, `dewpoint` m.m. for 7 dage, opdateret hver 3. time.

Konklusionen blev derfor at "vejret lige nu" kan læses direkte fra eksisterende
`current.json` ved at slå favorit-pladsens aktuelle time op — uden nyt fetch og
uden serverside-cache. Den ønskede caching-effekt kommer gratis, da data
fornyes hver 3. time på data-laget.

### Designvalg (afklaret via spørgsmål)

| Spørgsmål | Valg |
|-----------|------|
| Datakilde | Genbrug `current.json`, aktuel time for favorit-pladsen |
| Indhold | "Behold layout, drop AQI": Luftfugtighed, Vind, Real Feel (beregnet), Tryk + termik-label på bund-bjælken |
| Ingen favorit valgt | Skjul widgeten |
| Mobil | Skjul widgeten helt (`<768px`) |
| Desktop | Hover folder detalje-rækken ud, som i demoen |
| Ikon | Dynamisk inline-SVG ud fra `cloud_cover` + `precipitation` |
| Vindenhed | kt (konsistent med resten af siden) |

AQI blev udeladt, da det ikke findes i data og ville kræve et separat
luftkvalitets-API, som brugeren fravalgte. Real Feel beregnes i stedet med
Australian Apparent Temperature.

## Implementering

Alt foregik i frontend. Python-backend, datagenerering og `index.html` er urørt.
CSP tillader `data:`-billeder og inline-styles, så widgeten bygges uden at røre
sikkerhedsopsætningen; ikonet er inline-SVG (ingen tunge base64-assets).

### `termik/output/app.js` (+~140 linjer)

- `apparentTemp(tempC, rh, windKt)` — Australian Apparent Temperature
  (`AT = T + 0.33·e − 0.70·ws − 4.0`, hvor `e` er damptryk fra fugtighed og `ws`
  er vind i m/s).
- `textColorForScore(score)` — vælger mørk/lys tekst på bund-bjælken ud fra
  baggrundsfarvens luminans (så fx gul giver mørk tekst).
- `weatherIconSvg(cloud, precip)` — returnerer inline-SVG: regn (precip > 0.1),
  overskyet (cloud ≥ 80), sol+sky (cloud ≥ 30), ellers sol.
- `getNowDayHour()` — dag-offset for i dag + faktisk aktuel time (0-23,
  IKKE clamped til 6-21 som kort-slideren, så aften/nat vises korrekt).
- `addWeatherControl()` — registrerer et `L.Control` i `topleft`, med
  `disableClickPropagation`/`disableScrollPropagation` så klik/scroll på
  widgeten ikke panorerer kortet.
- `updateWeatherWidget()` — læser favorit fra localStorage, finder airfield,
  slår den aktuelle time op (med fallback til nærmeste tilgængelige time ±6t),
  og renderer kortet. Tilføjer/fjerner `.ww-hidden` ved manglende favorit/data.

Wiret ind i `init()` (control oprettes, første render, `setInterval` hvert 60.
sekund) og i favorit-`select`-handleren (`updateWeatherWidget()` ud over den
eksisterende `updateFavoriteForecast()`).

### `termik/output/style.css` (+~95 linjer)

`.ww-*`-klasser: afrundet hvidt kort, gul `#ffe87c` hover (matcher demoen),
detalje-grid der folder ud via `max-height`/`opacity`/`padding`-transition på
hover, farvet bund-bjælke, og en `@media (max-width: 768px)`-regel der skjuler
widgeten helt med `!important` (så JS' `display`-toggling ikke overstyrer den).

### `termik/output/sw.js`

`CACHE_VERSION` bumpet `termik-v13` → `termik-v14`. Nødvendigt fordi `app.js` og
`style.css` ligger i app-shell-precachen med cache-first-strategi; uden et bump
ville eksisterende PWA-brugere fortsat blive serveret de gamle filer og aldrig
se widgeten. (Samme klient-cache-fælde som dokumenteret i
[Referat 2026-05-28](2026-05-28-termik-top.md).)

## Verifikation

Drevet med Playwright (headless Chromium) mod en lokal `http.server`:

- **Favorit sat** (`aars`): widgeten viste sol-ikon, 16°, "Aviator - Aalborg
  Svæveflyveklub" og en score-farvet bund-bjælke. Hover foldede detaljerne ud
  (Luftfugtighed 56 %, Vind ↗ 8 kt, Føles som 12°, Tryk 1018 hPa) med gult
  hover-kort — visuelt identisk med den ønskede demo.
- **Ingen favorit**: `display: none`, `.ww-hidden` sat. ✓
- **Mobil (390px)**: `display: none` via media query. ✓
- **Dataadgang**: alle felter (`temp`, `relative_humidity`, `wind_speed_kt`,
  `wind_dir`, `pressure`, `cloud_cover`, `precipitation`) findes i data og gav
  fornuftige værdier; label og score hentes direkte fra time-objektet.

`node --check termik/output/app.js` grøn.

## Deployment

1. Commit `13541a0` (app.js + style.css + design-doc) pushet til main.
2. Første push afvist (`fetch first`) pga. en automatisk cron-data-commit på
   remote. `git pull --rebase` var konfliktfri (mine filer rører ikke
   `current.json`), derefter push.
3. Push til main ændrer `termik/output/**` → trigger `deploy-pages`-workflowen.
4. Opfølgende commit med sw-bump (v14) + denne dokumentation.

## Kendte begrænsninger og fremtidigt arbejde

1. **"Lige nu" = prognose-værdi**, ikke en observation. Open-Meteo-data er en
   modelprognose, og widgeten viser den aktuelle times prognose. For en
   termik-side er det rigeligt præcist.
2. **Real Feel er en approksimation** (Australian AT). Open-Meteo har et
   `apparent_temperature`-felt der kunne hentes direkte, hvis man vil have
   modellens egen værdi i stedet for en lokal beregning.
3. **Ikon ud fra cloud/precip** er en grov klassifikation (4 tilstande). Kunne
   forfines med `weathercode` fra Open-Meteo, hvis ønsket.
4. **Klient-cache**: brugere med siden åben fra før data-regenerering ser
   data fra hukommelsen indtil reload — som ved tidligere features.

## Filer ændret

| Fil | Indhold |
|-----|---------|
| `termik/output/app.js` | Widget-funktioner + Leaflet-control + wiring |
| `termik/output/style.css` | `.ww-*`-styling, hover-udfold, mobil-skjul |
| `termik/output/sw.js` | CACHE_VERSION v13 → v14 |
| `docs/plans/2026-05-29-vejr-widget-design.md` | Design-doc |
| `docs/PROJEKT-DOKUMENTATION.md` | Kontrol-liste + nyt "Vejr-widget"-afsnit |
| `docs/Referat/2026-05-29-vejr-widget.md` | Dette dokument |

## Kilder

- [Uiverse.io — Praashoo7 weather card](https://uiverse.io/) — design-forlæg for widgeten
- [Open-Meteo Docs](https://open-meteo.com/en/docs) — datafelter (allerede hentet i fetch_weather.py)
- Australian Apparent Temperature (Steadman) — formel for Real Feel
