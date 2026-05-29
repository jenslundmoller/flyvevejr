# Vejr-widget for favorit-plads — design

Dato: 2026-05-29

## Mål

Vis dagens generelle vejr "lige nu" for den plads brugeren har valgt som
favorit-plads, i en lille widget i kortets venstre top under zoom-knapperne.

## Beslutninger (afklaret med bruger)

- **Datakilde:** Genbrug `current.json`. Ingen nyt fetch, ingen serverside-kode.
  Widgeten slår favorit-pladsen op, dag 0, den aktuelle lokale time via det
  eksisterende `getPointAtTime(plads, dag, time)`. Data fornyes som hidtil hver
  3. time via GitHub Actions, så caching-effekten kommer gratis.
- **Indhold:** Store tal = temperatur + pladsnavn. Detalje-række =
  luftfugtighed, vind (kt + pil), Real Feel (beregnet), tryk (hPa). Bund-bjælke
  = termik-label (fx "God termik") farvet med scorens farve via `scoreToColor`.
  AQI udeladt (findes ikke i data).
- **Ikon:** Dynamisk inline-SVG ud fra `cloud_cover` + `precipitation`
  (klart / sol+sky / overskyet / regn). Ingen tunge base64-assets — holder sig
  inden for CSP (`img-src 'self' data:` og inline SVG-DOM).
- **Ingen favorit valgt:** widget skjult.
- **Mobil (<768px):** widget skjult helt (CSS media query).
- **Desktop:** hover folder detalje-rækken ud, som i den ønskede demo-widget.

## Teknik

- Tilføjes som et Leaflet-kontrol i position `topleft`, så den stables under
  zoom-knapperne uden z-index-konflikter.
- Markup + opdatering i `app.js`; styling i `style.css`. `index.html`,
  Python-backend og datagenerering er urørt.
- Opdateres ved: data loadet, favorit-plads skiftet, og hvert minut (fanger
  timeskift uden reload).

## Real Feel

Australian Apparent Temperature:
`AT = T + 0.33·e − 0.70·ws − 4.0`, hvor `e = (RH/100)·6.105·exp(17.27·T/(237.7+T))`
og `ws` er vind i m/s (kt × 0.514444). Alle input findes i data.
