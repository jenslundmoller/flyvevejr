# Heatmap-omlægning: fra spredte cirkler til glat kort-baggrund

**Dato:** 2026-04-27
**Commit:** `caf7e00 ui: render score field as smooth canvas heatmap clipped to DK coastline`

## Udgangspunkt

Det eksisterende `L.heatLayer` viste flyvevejr-scoren som spredte cirkler omkring hvert gridpunkt. Det var svært at tolke og dækkede ikke landet sammenhængende. Målet blev at få et flydende heatmap der dækker hele Danmark, følger kystlinjen og blender pænt mellem nabopunkter.

## Forløb i iterationer

### 1. Rektangler i stedet for heat-cirkler
Erstattede `L.heatLayer` med én `L.rectangle` pr. gridpunkt (0.4° × 0.4°, ~22 × 25 km), tegnet i en ny Leaflet-pane `scoreGrid` med z-index 350 så de ligger over OSM-fliser men under markører. Mosaik-look — mere læseligt, men hårde firkanter.

### 2. Kystlinje-clipping via turf.js
Bundlede en Denmark GeoJSON og brugte `turf.intersect` til at klippe hver celle mod kystlinjen, så firkanter ikke længere stak ud i havet.

### 3. Tættere grid (0.4° → 0.2°)
Halverede gridafstanden i `locations.py` fra 0.4° til 0.2° (~11 × 13 km). Antal gridpunkter steg fra 51 til 232. Tilføjede `_cell_overlaps_land()` der bruger 5×5 sampling pr. celle mod den rigtige DK-polygon, så coastal-celler hvis centrum ligger lige uden for kysten stadig inkluderes.

### 4. Slim JSON-payload
Opdagede at `current.json` var 45 MB. Hver gridpunkt havde 168 timers fuld vejrdata + dansk kommentartekst — men popups vises kun for flyvepladser. Fix i `fetch_weather.py`: gridpunkter får kun `time + score` pr. time, flyvepladser beholder fuld payload. Også droppet JSON-indent. Resultat: ~10× mindre fil.

### 5. Canvas-baseret renderer (det store skift)
Rektangel-løsningen havde stadig hårde overgange mellem nabokasser. To alternativer overvejet:
- **Subdivision** (10×10 sub-celler pr. gridcelle): ~23.000 polygoner, ~30-60 sek build-tid, tungt på mobil. Forkastet.
- **Canvas med bilinear interpolation**: én canvas-overlay, browser-native smoothing, klippet via `Path2D.clip()`. Valgt.

Implementation:
- `buildScoreCanvas()`: bygger en lille 37×17 px offscreen-canvas, hvor hver pixel = ét gridpunkt. Manglende celler får nærmeste-nabo-fyld, så browser-smoothing aldrig render mod tom alpha.
- `ScoreCanvasLayer` (custom `L.Layer`): tegner offscreen-canvas op til hele kortet via `ctx.drawImage()` med `imageSmoothingEnabled = true` + `quality: 'high'`. Klipper mod DK-polygon via `ctx.clip(Path2D)`. Re-renderer på `moveend`/`zoomend`/`resize`.
- Render-cost uafhængig af gridtæthed — én `drawImage` + ét clip pr. frame.

### 6. Tåsinge mangler
Den oprindelige Natural Earth 1:50m DK-polygon havde kun 15 polygoner og udelod småøer som Tåsinge, Strynø, Avernakø. Forsøgte:
- **geoBoundaries** (118 polygoner, 230 KB): havde Tåsinge, men østkysten af Sjælland og Lolland-Falsters sydkyst var skåret væk → polygon shifted med ~5-10 km. Forkastet.
- **OSM polygons.openstreetmap.fr**: kun 2 polygoner — DK var foldet sammen med havstrækninger som "land". Forkastet.
- **Endelig:** Natural Earth 1:10m (samme 15 nøjagtige polygoner) + Tåsinge manuelt ekstraheret fra geoBoundaries-data. 45 KB, 16 polygoner.

### 7. Halv-pixel offset bug
Da den nye præcise mask hægtede sig på kystlinjen, blev en latent bug synlig: `drawImage` mapper kilde-rektanglets KANTER til destinations-kanter, men vores pixel-CENTRE skal flugte med gridpunkter. Fix: udvid destinations-rektanglet med en halv gridcelle i alle retninger, så pixel-CENTRE lander på `[lonMin, latMax]` osv. Det fiksede både den interne ~5-10 km diagonal forskydning og udskårne kanter ved Skagen og Falsters sydspids.

## Ændrede filer

- `termik/locations.py` — `GRID_STEP_DEG = 0.2`, `_load_dk_rings()`, `_is_land_strict()`, `_cell_overlaps_land()`.
- `termik/fetch_weather.py` — slim hours for gridpunkter, kompakt JSON.
- `termik/output/app.js` — `ScoreCanvasLayer`, `buildScoreCanvas()`, `scoreToRgb()`. Fjernet rektangel/turf-logik.
- `termik/output/index.html` — fjernet `leaflet.heat`-script.
- `termik/output/sw.js` — cache `termik-v9`, `denmark.geojson` i app shell.
- `termik/output/data/denmark.geojson` — ny fil (NE 1:10m + Tåsinge).

## Performance-status

- **JSON-payload:** 45 MB → ~4-5 MB (262 punkter, 7 dage).
- **API-belastning:** 9 → 25 batches pr. forecast-kørsel (~2 min total). Stadig langt under Open-Meteo's 10.000 kald/dag.
- **Render-cost:** Konstant pr. frame uanset gridtæthed.
- **Cell-størrelse:** ~11 × 13 km, glat blendet via browser-bilinear, klippet til kystlinje.

## Forkastede / overvejede alternativer

- **SVG Gaussian blur** på score-pane: enkelt, men ville have blurret kysten også.
- **Polygon-subdivision med bilinear**: korrekt men 100× tungere DOM.
- **0.1° grid** (~830 gridpunkter): muligt med slim payload, ~140 MB → ~12 MB. Ikke aktuelt; 0.2° opløsning matcher Open-Meteo's underliggende model.

## Mulige næste skridt

- Tilføj flere manglende småøer hvis de bemærkes (Endelave, Fejø, Femø, Lyø, Strynø).
- Overvej `_LAND_POLYGONS` oprydning i `locations.py` (det gamle `_is_land()` er nu uudbrugt).
