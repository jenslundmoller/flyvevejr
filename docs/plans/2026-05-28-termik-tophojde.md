# Plan: Termik-tophøjde (TI=0 via parcel-teori) + nyt kortlag

Dato: 2026-05-28
Status: v2 — rettet efter parallel review fra to agenter (kode + meteorologi)

## Mål

Tilføj en forudsigelse af maksimal termik-tophøjde til hver grid-celle, beregnet via parcel-teori på en multilevel-sondering fra Open-Meteo. Vis den som et nyt kortlag med diskrete farvede felter, og lad brugeren skifte mellem score-laget og termik-top-laget i et nyt "Kortlag"-afsnit i sidebaren.

## Beslutninger der allerede er truffet

- **Metode**: TI=0 højde via tør-adiabatisk parcel-løft, cap'd med LCL, korrigeret med Hcrit-margin (200-500 m skaleret med shortwave_radiation).
- **Grid**: 0.2° (allerede sat — 232 grid-punkter, fundet i `locations.py:320`. Dokumentationen i `PROJEKT-DOKUMENTATION.md` siger 0.4° og er forældet — opdateres i denne PR).
- **Lag-visning**: kun ét lag aktivt ad gangen (radioknapper).
- **Farveskala**: distinkt fra score'ns blå→rød. Viridis-lignende lilla→orange.

## Arkitektur

```
Open-Meteo (udvidet med 950/900hPa + dew_point_2m + geopotential_height_*hPa)
       │
       ▼
fetch_weather.py → ekstraherer sondering pr. time pr. punkt
       │
       ▼
scoring.compute_thermal_top() → thermal_top_m, ti_zero_m, lcl_m, limited_by
       │
       ▼
current.json (grid-celle payload udvides med thermal_top_m)
       │
       ▼
app.js: ThermalTopCanvasLayer (diskret, viridis-palet, canvas-labels ved zoom ≥ 9)
       │
       ▼
Bruger toggler i sidebar → localStorage husker valget
```

## Backend

### B1. `termik/config.py` — udvid `HOURLY_PARAMS`

Tilføj følgende parameternavne (rækkefølge bevares for læselighed):

```python
"dew_point_2m",                # bruges til Bolton 1980 LCL
# Pressure levels — udvid eksisterende sæt:
"temperature_950hPa",
"temperature_900hPa",
"temperature_800hPa",          # ny
"temperature_600hPa",          # ny
"temperature_500hPa",          # ny (for super-instabile dage)
# Geopotential heights til parcel-teori:
"geopotential_height_950hPa",
"geopotential_height_925hPa",
"geopotential_height_900hPa",
"geopotential_height_850hPa",
"geopotential_height_800hPa",
"geopotential_height_700hPa",
"geopotential_height_600hPa",
"geopotential_height_500hPa",
```

`temperature_850hPa`, `temperature_700hPa`, `temperature_925hPa` er allerede der eller ikke — verificér og ret. Det eksisterende `temperature_850hPa` og `temperature_700hPa` BEHOLDES, fordi `lapse_rate`-feltet og scoring bruger dem.

`surface_pressure` er allerede med. `wind_speed_850hPa`/`wind_direction_850hPa` beholdes som de er.

### B2. `termik/scoring.py` — ny funktion `compute_thermal_top()`

Placér efter `score_lapse_rate`/`score_surface_lapse_rate`-blokken, før `compute_thermal_score`.

Returnerer **`thermal_top_m=None`** (ikke 0) når data mangler eller kun dewpoint mangler, så frontend kan skille "ukendt" fra "rigtig 0". Hcrit-margin interpoleres lineært i SW (ingen diskrete trin → glat kort).

```python
import math

THERMAL_TOP_LEVELS_HPA = [950, 925, 900, 850, 800, 700, 600]   # 500 droppet — DK termik når sjældent over 700 hPa
DALR_K_PER_M = 0.0098                  # tør-adiabatisk lapse rate (g/cp)
MAX_THERMAL_TOP_M = 4000               # cap når pakken aldrig krydser miljø
HCRIT_MARGIN_AT_FULL_SUN_M = 200       # SW >= 600 W/m²
HCRIT_MARGIN_AT_NO_SUN_M = 500         # SW <= 0
HCRIT_FULL_SUN_W_M2 = 600
WEAK_SOLAR_THRESHOLD_W_M2 = 250        # under denne sættes limited_by="weak_solar"


def _hcrit_margin(shortwave_radiation: float | None) -> int:
    """Lineær interpolation mellem 200 m (fuldt sol) og 500 m (intet sol).

    Glat overgang så nabotimer ikke springer 100 m. Default 500 m ved
    None (konservativt — falsk lav værdi er bedre end falsk høj).
    """
    if shortwave_radiation is None or shortwave_radiation <= 0:
        return HCRIT_MARGIN_AT_NO_SUN_M
    if shortwave_radiation >= HCRIT_FULL_SUN_W_M2:
        return HCRIT_MARGIN_AT_FULL_SUN_M
    t = shortwave_radiation / HCRIT_FULL_SUN_W_M2
    return round(HCRIT_MARGIN_AT_NO_SUN_M + t * (HCRIT_MARGIN_AT_FULL_SUN_M - HCRIT_MARGIN_AT_NO_SUN_M))


def _bolton_lcl_temp_k(t_k: float, td_k: float) -> float:
    """Bolton 1980 eq. 22 — LCL temperature in Kelvin."""
    return 56.0 + 1.0 / (1.0 / (td_k - 56.0) + math.log(t_k / td_k) / 800.0)


def _none_result(lcl_m: float | None, limited_by: str) -> dict:
    return {
        "thermal_top_m": None,
        "ti_zero_m": None,
        "lcl_m": round(lcl_m) if lcl_m is not None else None,
        "limited_by": limited_by,
    }


def compute_thermal_top(
    surface_temp_c: float | None,
    surface_dewpoint_c: float | None,
    surface_pressure_hpa: float | None,
    surface_elevation_m: float,
    level_temps_c: dict[int, float | None],
    level_heights_m: dict[int, float | None],
    shortwave_radiation: float | None = None,
) -> dict:
    """Beregn termik-tophøjde via parcel-teori (tør-adiabatisk løft + LCL-cap + Hcrit-margin).

    Returns dict med:
        thermal_top_m: int | None  — Hcrit-korrigeret højde over MSL (m), None ved manglende data
        ti_zero_m:    int | None   — TI=0 højde over MSL (m), None ved manglende data
        lcl_m:        int | None   — LCL højde over MSL (m), None hvis dewpoint mangler
        limited_by:   str          — "lcl" | "ti_zero" | "cap" | "inversion" |
                                     "weak_solar" | "saturated" | "no_data" |
                                     "no_dewpoint" | "margin_collapse"

    Tidsmæssig fortolkning: værdien gælder for DEN time den beregnes for. Tidlig
    morgen og sen eftermiddag har naturligt lave værdier. Brugeren bruger
    time-slideren til at finde dagens peak (typisk kl. 13-15).
    """
    # 0) Manglende basis-data — kan ikke gøre noget
    if surface_temp_c is None or surface_pressure_hpa is None:
        return _none_result(None, "no_data")

    # 1) LCL via Bolton 1980 (eq. 22)
    if surface_dewpoint_c is None:
        # Ingen dewpoint → vi kender ikke LCL. Vi kan stadig beregne TI=0,
        # men ikke cap'pe med LCL. Markér og fortsæt med lcl_m=None.
        lcl_m: float | None = None
    else:
        t_k = surface_temp_c + 273.15
        td_k = surface_dewpoint_c + 273.15
        if td_k >= t_k - 0.1:
            # Mættet — kondensation ved overfladen, ingen termik
            return {
                "thermal_top_m": 0,
                "ti_zero_m": 0,
                "lcl_m": round(surface_elevation_m),
                "limited_by": "saturated",
            }
        else:
            t_lcl_k = _bolton_lcl_temp_k(t_k, td_k)
            lcl_m = surface_elevation_m + (t_k - t_lcl_k) / DALR_K_PER_M

    # 2) Byg miljøprofil (lav → høj højde). Filtrer niveauer under overflade.
    env = [(surface_elevation_m, surface_temp_c)]
    for p in THERMAL_TOP_LEVELS_HPA:
        t = level_temps_c.get(p)
        h = level_heights_m.get(p)
        if t is None or h is None:
            continue
        if p >= surface_pressure_hpa:
            continue              # trykniveau under overfladen
        if h <= surface_elevation_m + 10:
            continue              # roundoff under overflade
        env.append((h, t))
    env.sort(key=lambda x: x[0])

    if len(env) < 2:
        return _none_result(lcl_m, "no_data")

    # 3) Find TI=0 via lineær interpolation
    ti_zero_m = None
    for i in range(1, len(env)):
        h_prev, t_env_prev = env[i - 1]
        h_curr, t_env_curr = env[i]
        t_parcel_prev = surface_temp_c - DALR_K_PER_M * (h_prev - surface_elevation_m)
        t_parcel_curr = surface_temp_c - DALR_K_PER_M * (h_curr - surface_elevation_m)
        d_prev = t_parcel_prev - t_env_prev   # > 0 = pakke varmere end miljø
        d_curr = t_parcel_curr - t_env_curr
        if i == 1 and d_prev <= 0:
            # Overflade-pakke straks koldere end miljøet over jord → inversion
            return {
                "thermal_top_m": 0,
                "ti_zero_m": 0,
                "lcl_m": round(lcl_m) if lcl_m is not None else None,
                "limited_by": "inversion",
            }
        if d_prev > 0 and d_curr <= 0:
            frac = d_prev / (d_prev - d_curr)
            ti_zero_m = h_prev + frac * (h_curr - h_prev)
            break

    limited_by = "ti_zero"
    if ti_zero_m is None:
        ti_zero_m = min(surface_elevation_m + MAX_THERMAL_TOP_M, env[-1][0])
        limited_by = "cap"

    # 4) Cap med LCL (hvis kendt)
    raw_top = ti_zero_m
    if lcl_m is not None and lcl_m < ti_zero_m:
        raw_top = lcl_m
        limited_by = "lcl"
    elif lcl_m is None:
        limited_by = "no_dewpoint"

    # 5) Hcrit-margin (cap'd så den ikke æder hele raw_top)
    margin = _hcrit_margin(shortwave_radiation)
    raw_top_agl = raw_top - surface_elevation_m
    margin = min(margin, raw_top_agl / 2) if raw_top_agl > 0 else margin
    thermal_top_m = max(0, raw_top - margin)

    # 6) Diagnostiske flags
    if raw_top_agl > 0 and thermal_top_m <= surface_elevation_m + 50:
        limited_by = "margin_collapse"
    elif (
        shortwave_radiation is not None
        and shortwave_radiation < WEAK_SOLAR_THRESHOLD_W_M2
        and thermal_top_m > surface_elevation_m
    ):
        limited_by = "weak_solar"

    return {
        "thermal_top_m": round(thermal_top_m),
        "ti_zero_m": round(ti_zero_m),
        "lcl_m": round(lcl_m) if lcl_m is not None else None,
        "limited_by": limited_by,
    }
```

Designvalg (opdateret efter review):

- **`surface_elevation_m`**: passes som airfield-feltet hvor det findes (Arnborg = 38 m, etc.) — kan tilføjes til AIRFIELDS-konstanterne i `locations.py`. For grid-punkter passes `0` (flat DK approksimation, fejl &lt; 50 m).
- **Bolton 1980 eq. 22** (LCL-temperatur), ikke eq. 15.
- **`thermal_top_m=None`** ved no_data / no_dewpoint → frontend skiller "ukendt" (grå celle) fra "rigtig 0" (lilla celle).
- **Lineær Hcrit-interpolation** mellem 200 m (SW≥600 W/m²) og 500 m (SW≤0) → glatte kort.
- **Margin cap'd til raw_top/2** → undgår at margin alene æder en hele beregnet top.
- **`limited_by='weak_solar'`** ved SW &lt; 250 W/m² men positiv top → frontend kan vise advarsel.
- **`limited_by='margin_collapse'`** når raw_top &gt; 0 men margin fjerner næsten det hele → forklarer mystisk lave værdier.
- **`limited_by='saturated'`** ved RH ≈ 100% (LCL = overflade).
- **`limited_by='no_dewpoint'`** når dewpoint mangler → TI=0 beregnes stadig men er ikke cap'd af LCL; brugeren ser tallet er upålideligt.
- **500 hPa droppet** fra `THERMAL_TOP_LEVELS_HPA` (DK termik når sjældent over 600 hPa; sparer 1 parameter per kald). Beholder 600 hPa for ekstreme dage.
- **Eksisterende `lapse_rate = (T_2m - T_850)/15`** og `skybase_m = spread × 125` BEVARES uændret. De bruges af scoring/comments og er separate fra `compute_thermal_top`. **Kendt diskrepans** mellem score_lapse_rate og thermal_top_m dokumenteres i Open spørgsmål.

### B3. `termik/fetch_weather.py` — kald `compute_thermal_top` for hver time

Ændringer i `fetch_weather.py`:

**Import** (linje 17):
```python
from termik.scoring import compute_thermal_score, compute_thermal_top
```

**I `process_point_hour()`** (efter de eksisterende ekstraktioner ca. linje 120-150):

1. Ekstrahér `dewpoint_2m` (allerede gjort på linje 117 som `dewpoint`) — den genbruges.
2. Byg dictionaries:
   ```python
   level_temps_c = {
       p: hourly_data.get(f'temperature_{p}hPa', [None] * (h + 1))[h]
       for p in (950, 925, 900, 850, 800, 700, 600)
   }
   level_heights_m = {
       p: hourly_data.get(f'geopotential_height_{p}hPa', [None] * (h + 1))[h]
       for p in (950, 925, 900, 850, 800, 700, 600)
   }
   ```
3. Beregn `surface_elevation_m = point.get('elevation_m', 0)` — passer airfield-feltet hvor det findes, ellers 0.
4. **Dewpoint må IKKE være med i "critical None"-checken** — `compute_thermal_top` håndterer selv None som "no_dewpoint" og fortsætter med TI=0 beregning.
5. Kald `compute_thermal_top(...)`. Returnerer dict med 4 felter.
6. **Output-placering**:
   - **Airfields** (kommer fra `is_airfield=True` grenen): tilføj alle 4 felter (`thermal_top_m`, `ti_zero_m`, `lcl_m`, `limited_by`) til `data`-dict i return-statementen (linje 259-285).
   - **Grid-punkter** (linje 326-330 trimning): udvid fra `{time, score}` til `{time, score, thermal_top_m}`. Kun det færdige tal — ingen diagnostik for grid (payload-budget).

**P0-1: Early-return ved manglende critical data** (linje 152-184):
Den eksisterende early-return har sin egen `data`-dict. Tilføj `"thermal_top_m": None`, `"ti_zero_m": None`, `"lcl_m": None`, `"limited_by": "no_data"` til den dict så schemaet er konsistent mellem normale timer og "Data mangler"-timer.

**Grid-trimning**: hour_result for grid bliver:
```python
hour_result = {
    "time": hour_result["time"],
    "score": hour_result["score"],
    "thermal_top_m": hour_result["data"].get("thermal_top_m"),
}
```
Frontend læser `point.hours[i].thermal_top_m` for grid og `point.hours[i].data.thermal_top_m` for airfields. Begge mønstre eksisterer allerede for `score` (grid) vs alt-andet (airfield), så det er konsistent.

### B4. `termik/tests/test_scoring.py` — nye unit-tests

Tilføj test-klasse `TestThermalTop`:

- **Inversion**: T_2m=15, T_d=10, T_925=18 @640m. Forventet `thermal_top_m=0`, `limited_by='inversion'`.
- **Klassisk DK sommerdag**: T_2m=22, T_d=10, p_surf=1013, T_925=15 @700m, T_850=10 @1500m, T_700=2 @3000m, SW=600. Forventet TI=0 ≈ 2200 m, LCL ≈ 1500 m → `thermal_top_m` ≈ 1300, `limited_by='lcl'`.
- **Tør super-instabil**: T_2m=30, T_d=5, T_850=15 @1500m, T_700=0 @3000m, T_600=−8 @4200m, SW=700. Forventet `thermal_top_m` 2500-3500 m, `limited_by='ti_zero'`.
- **Manglende sondering**: alle level_temps_c=None. Forventet `thermal_top_m=None`, `limited_by='no_data'`.
- **Manglende dewpoint**: dewpoint=None, ellers god sondering. Forventet `lcl_m=None`, `limited_by='no_dewpoint'`, `thermal_top_m` &gt; 0.
- **Mættet (T=Td)**: spread &lt; 0.1 K. Forventet `thermal_top_m=0`, `limited_by='saturated'`.
- **Weak solar**: god sondering, SW=150 W/m². Forventet `thermal_top_m` &gt; 0 men `limited_by='weak_solar'`.
- **Margin collapse**: lav TI=0 (~300 m), SW=0 → margin cap'd til 150 m, men `limited_by='margin_collapse'`.
- **`_hcrit_margin` enheds-tests**: SW=700 → 200, SW=600 → 200, SW=300 → 350 (lineær), SW=0 → 500, SW=None → 500.
- **Bolton LCL sanity**: T=20°C, Td=10°C → LCL_height ≈ 1200 m (10 m tolerance vs. Bolton-reference).
- **Sondering monotonisk i højde**: `level_heights_m` skal være stigende; test at `compute_thermal_top` selv sorterer korrekt selv ved blandet input.
- **Geopotential sanity**: tilføj test der hævder `0 < 850hPa_height < 3000` og `925hPa_height < 850hPa_height` ved typisk Open-Meteo-input. (Beskytter mod fremtidig API-enhedsændring.)
- **Hcrit-skalering end-to-end**: kald `compute_thermal_top` med SAMME sondering men SW=600 vs SW=0 og verificér at `thermal_top_m`-differencen matcher margin-differencen (300 m).

### B5. `termik/fetch_weather.py` — None-håndtering

`compute_thermal_top` håndterer selv None-værdier:
- Manglende trykniveau-data → filtrer fra, fortsæt med færre niveauer
- Manglende dewpoint → returnér `limited_by='no_dewpoint'` med `lcl_m=None`
- Manglende surface_temp / surface_pressure → returnér `limited_by='no_data'`

Brug samme `.get(key, [None]*(h+1))[h]`-mønster som koden allerede gør på linje 120-147 — ingen ny defensiv kode nødvendig i fetch_weather.

### B5b. `termik/tests/test_fetch_weather.py` — udvidelse

Den eksisterende `test_process_point_hour_passes_multilevel_data` (linje 101-153) verificerer multilevel-felter i `data`-dict. Udvid med:

- **Assertion at airfield-result har `thermal_top_m`, `ti_zero_m`, `lcl_m`, `limited_by` i `data`-dict** når sondering er komplet.
- **Assertion at grid-result har `thermal_top_m` på top-niveau** (efter trimning til `{time, score, thermal_top_m}`).
- **Assertion at early-return ved manglende critical data inkluderer `thermal_top_m: None` og `limited_by: "no_data"`**.

### B6. Backwards compat: gamle current.json uden `thermal_top_m`

Frontend skal håndtere at `thermal_top_m` mangler (cached SW har gammel data, eller første deploy før første cron-cyklus). Frontend defaultet til at vise "—" eller bare blokere termik-top-laget med en advarsel.

## Frontend

### F1. `termik/output/app.js` — udvid `ScoreCanvasLayer` med smoothing-flag

Den eksisterende klasse `ScoreCanvasLayer` (linje 186-267) refaktoreres minimalt:

```js
const ScoreCanvasLayer = L.Layer.extend({
    initialize: function() {
        this._scoreCanvas = null;
        this._mask = null;
        this._smoothing = true;          // NY
        this._labels = null;             // NY: array af {lat, lon, text}
    },
    // ...
    setScoreCanvas: function(canvas, smoothing = true, labels = null) {
        this._scoreCanvas = canvas;
        this._smoothing = smoothing;
        this._labels = labels;
        this._render();
    },
    _render: function() {
        // ... eksisterende logik ...
        ctx.imageSmoothingEnabled = this._smoothing;
        ctx.imageSmoothingQuality = 'high';
        ctx.drawImage(this._scoreCanvas, tl.x, tl.y, br.x - tl.x, br.y - tl.y);

        if (maskPath) ctx.restore();

        // NY: tegn labels oven på, OG efter unclip — så labels ikke clippes mod kysten
        if (this._labels) {
            this._drawLabels(ctx);
        }
    },
    _drawLabels: function(ctx) {
        const map = this._map;
        const cellPx = this._estimateCellPx();
        if (cellPx < 36) return;            // for trængt
        ctx.font = 'bold 11px sans-serif';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.lineWidth = 3;
        ctx.strokeStyle = 'rgba(255,255,255,0.85)';
        ctx.fillStyle = '#222';
        for (const l of this._labels) {
            const pt = map.latLngToContainerPoint([l.lat, l.lon]);
            ctx.strokeText(l.text, pt.x, pt.y);
            ctx.fillText(l.text, pt.x, pt.y);
        }
    },
    _estimateCellPx: function() {
        const map = this._map;
        const a = map.latLngToContainerPoint([56, 10]);
        const b = map.latLngToContainerPoint([56, 10 + GRID_STEP_DEG]);
        return Math.abs(b.x - a.x);
    },
});
```

Eksisterende kald `scoreLayer.setScoreCanvas(buildScoreCanvas())` virker fortsat (default-args bevarer adfærd).

**Eneste eksisterende kaldsted** for `setScoreCanvas` er i `updateHeatmap()` (app.js:275). Det erstattes af ny `updateHeatmap()`-implementation i F3 nedenfor. Ingen anden regression-risiko.

### F2. `app.js` — ny `buildThermalTopCanvas()` og farvefunktion

Placér ved siden af `buildScoreCanvas` (linje 140).

```js
const THERMAL_TOP_STOPS = [
    {m: 0,    rgb: [45, 27, 78]},
    {m: 500,  rgb: [94, 58, 140]},
    {m: 1000, rgb: [42, 123, 155]},
    {m: 1500, rgb: [127, 183, 62]},
    {m: 2000, rgb: [240, 183, 62]},
    {m: 2500, rgb: [232, 90, 26]},
];

function thermalTopToRgb(m) {
    if (m == null) return [200, 200, 200];
    const s = THERMAL_TOP_STOPS;
    if (m <= s[0].m) return s[0].rgb;
    if (m >= s[s.length-1].m) return s[s.length-1].rgb;
    for (let i = 1; i < s.length; i++) {
        if (m <= s[i].m) {
            const t = (m - s[i-1].m) / (s[i].m - s[i-1].m);
            return [
                Math.round(s[i-1].rgb[0] + t * (s[i].rgb[0] - s[i-1].rgb[0])),
                Math.round(s[i-1].rgb[1] + t * (s[i].rgb[1] - s[i-1].rgb[1])),
                Math.round(s[i-1].rgb[2] + t * (s[i].rgb[2] - s[i-1].rgb[2])),
            ];
        }
    }
    return s[s.length-1].rgb;
}

function buildThermalTopCanvas() {
    // Kopi af buildScoreCanvas; udskift hd.score med hd.thermal_top_m.
    // Returnér ALSO labels array til _drawLabels.
    // ... (~50 linjer, struktur identisk med buildScoreCanvas)
}
```

`buildThermalTopCanvas` skal også returnere et `labels`-array med `{lat, lon, text}` for hver grid-celle (text = `Math.round(m / 100) * 100 + 'm'` eller `(m/1000).toFixed(1) + 'k'`).

### F3. `app.js` — state-håndtering for aktivt lag

Ved toppen:
```js
const LAYER_KEY = 'termik-active-layer';
let activeLayer = 'score';        // 'score' | 'thermal-top'
```

Ny `updateHeatmap()`:
```js
function updateHeatmap() {
    if (!scoreLayer) {
        scoreLayer = new ScoreCanvasLayer();
        scoreLayer.addTo(map);
        if (countryMask) scoreLayer.setMask(countryMask);
    }
    if (activeLayer === 'thermal-top') {
        const built = buildThermalTopCanvas();
        if (built) {
            scoreLayer.setScoreCanvas(built.canvas, false, built.labels);
        } else {
            scoreLayer.setScoreCanvas(null, false, null);  // nulstil labels ved no-data
        }
        updateLegend('thermal-top');
    } else {
        scoreLayer.setScoreCanvas(buildScoreCanvas(), true, null);
        updateLegend('score');
    }
}
```

**`setScoreCanvas(null, ...)` skal håndtere null** — `_render` springer drawImage over når `_scoreCanvas` er null (eksisterende adfærd), men `_labels` skal også sættes null så gamle labels ikke "hænger" ved.

### F4. `app.js` — `setupLayerControls()`

Tilføj funktion der binder til radioknapperne i `#layer-section`:

```js
function setupLayerControls() {
    const stored = localStorage.getItem(LAYER_KEY);
    if (stored === 'score' || stored === 'thermal-top') activeLayer = stored;
    const radios = document.querySelectorAll('input[name="map-layer"]');
    for (const r of radios) {
        r.checked = (r.value === activeLayer);
        r.addEventListener('change', () => {
            if (r.checked) {
                activeLayer = r.value;
                localStorage.setItem(LAYER_KEY, activeLayer);
                updateHeatmap();
            }
        });
    }
}
```

Kald `setupLayerControls()` i `init()` FØR første `updateAll()`-kald.

### F5. `app.js` — legend-funktion

```js
function updateLegend(layer) {
    const el = document.getElementById('layer-legend');
    if (layer === 'thermal-top') {
        el.innerHTML = `<div class="legend-bar legend-thermal"></div>
            <div class="legend-labels"><span>0m</span><span>1500m</span><span>2500m+</span></div>`;
    } else {
        el.innerHTML = `<div class="legend-bar legend-score"></div>
            <div class="legend-labels"><span>0</span><span>5</span><span>10</span></div>`;
    }
}
```

### F6. `app.js` — popup udvidelse

I `popupContent`/`popupHtml` (linje ~339-355), tilføj `thermal_top_m` som ny række:

```js
+ (d.thermal_top_m != null
    ? popupItem('Termik-tophøjde', d.thermal_top_m + 'm', 'Beregnet maks. brugbar termikhøjde (parcel-teori, TI=0 cap\'d med skybase, Hcrit-margin)')
    : '')
```

Den eksisterende `boundary_layer_height`-række (linje 355) BEVARES som diagnostic, men kommentaren ændres til "Modellens råe blandingslag (sammenlign med Termik-tophøjde)".

### F7. `index.html` — nyt sidebar-afsnit

Indsæt mellem linje 50 (`</div>` for `favorite-section`) og linje 51 (`<div id="about-link">`):

```html
<div id="layer-section">
    <h2>Kortlag</h2>
    <div class="layer-options">
        <label class="layer-option">
            <input type="radio" name="map-layer" value="score" checked>
            <span>Flyveforhold (score)</span>
        </label>
        <label class="layer-option">
            <input type="radio" name="map-layer" value="thermal-top">
            <span>Termik-tophøjde</span>
        </label>
    </div>
    <div id="layer-legend"></div>
</div>
```

### F8. `style.css` — styling

Tilføj:

```css
#layer-section {
    margin-top: 1.2rem;
    padding-top: 1rem;
    border-top: 1px solid #d8e0e6;
}
#layer-section h2 {
    font-size: 0.95rem;
    margin: 0 0 0.5rem;
}
.layer-options {
    display: flex;
    flex-direction: column;
    gap: 0.35rem;
    margin-bottom: 0.6rem;
}
.layer-option {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    font-size: 0.9rem;
    cursor: pointer;
}
.legend-bar {
    height: 12px;
    border-radius: 3px;
}
.legend-thermal {
    background: linear-gradient(to right, #2d1b4e, #5e3a8c, #2a7b9b, #7fb73e, #f0b73e, #e85a1a);
}
.legend-score {
    background: linear-gradient(to right, #08306b, #2171b5, #f7fcb9, #e34a33, #99000d);
}
.legend-labels {
    display: flex;
    justify-content: space-between;
    font-size: 0.75rem;
    color: #555;
    margin-top: 0.2rem;
}
```

**Mobil-regler (krævet — ikke valgfri):**

style.css linje ~606 har inden for `@media (max-width: 768px)`:
```css
#favorite-section { display: none; }
#sidebar.expanded #favorite-section { display: block; }
```

**Plan-krav**: tilføj nøjagtig samme mønster for `#layer-section`:
```css
@media (max-width: 768px) {
    #layer-section { display: none; }
    #sidebar.expanded #layer-section { display: block; }
}
```
Uden dette bliver layer-section enten skåret af i collapsed mobile bottom-sheet, eller fylder dyrebar plads. Verificér eksakte selektorer i style.css ved implementering.

### F9. `sw.js` — bump cache version

```js
const CACHE_VERSION = 'termik-v13';   // var 'termik-v12'
```

Det tvinger en clean re-fetch af alle app-shell-filer efter deploy.

### F10. `docs/PROJEKT-DOKUMENTATION.md` — opdatering

- Ret "0.4° × 0.4° grid", "51 stk" og "79 punkter" til de korrekte tal (0.2°, 232 grid, 262 total — verificeres ved implementering).
- Opdatér "Hourly parametre"-listen (linje 217-218) med nye trykniveauer + dew_point_2m + geopotential_height_*hPa.
- Tilføj under "Frontend" en under-sektion "Kortlag" der beskriver lag-skifteren og Indstillinger-afsnittet.
- Tilføj under "Afledte beregninger" en linje om termik-top (parcel-teori, Bolton LCL, Hcrit-margin).
- Opdatér "Test"-afsnit (tæller går fra 78 til ~90 tests).
- Tilføj et "Referat 2026-05-28 termik-top"-link.

### F11. Nyt referat i `docs/Referat/`

`docs/Referat/2026-05-28-termik-top.md` — kort beskrivelse af beslutninger (parcel-teori, ikke MetPy, 250 m Hcrit-margin skaleret med SW, distinkt farveskala).

## Test- og verifikationsplan

1. `python3 -m pytest termik/tests/ -v` — alle nye + eksisterende tests grønne.
2. `python3 -m termik` — kør lokalt, verificér at `current.json` indeholder `thermal_top_m` for både grid og airfield-punkter, og at værdier er meteorologisk rimelige (>0 om dagen, 0/None om natten på vinterdage).
3. `cd termik/output && python3 -m http.server 8090` — åbn http://localhost:8090, verificér:
   - Default-lag = score (uændret adfærd for eksisterende brugere).
   - Skift til "Termik-tophøjde" → ser diskrete celler, viridis-palet, labels ved zoom ≥ 9.
   - Skift dag/time → laget opdaterer.
   - Klik flyveplads → popup viser "Termik-tophøjde" + diagnostic-værdier.
   - Reload → valg huskes.
4. Mobile: test i Chrome devtools mobile-emulator (375×667) — bottom-sheet expanded viser layer-section.
5. Service worker: clear cache, første load registrerer SW v13, second load er offline-tilgængelig med nyt lag.

## Rollback-strategi

Hvis termik-top viser sig at være forvirrende eller fejlbehæftet i prod:
- Backend ændringer skader ikke score-laget — kan rulles tilbage ved at fjerne kun de nye felter.
- Frontend: skjul `#layer-section` med CSS `display:none` — score-laget bliver default igen.
- SW-cache: v13 → v14 bump tvinger ny clean load.

## Open spørgsmål / risici

1. **Geopotential_height enhed**: Open-Meteo dokumenterer "meter" for `geopotential_height_*hPa`. Hård sanity-test i `test_fetch_weather.py` hævder `0 < height_850 < 3000` for typisk input — fanger fremtidig API-enhedsændring.
2. **Payload-vækst**: 232 grid × 168 timer × ~12 byte ekstra (`thermal_top_m`) ≈ 0.5 MB rå, ~60 KB gzippet. Acceptabelt.
3. **API-batches**: 262 punkter / 10 per batch = 27 batches × 5s pause ≈ 135s pr. opdatering. GitHub Actions har 6-min limit pr. step — rigeligt. Open-Meteo free tier = 10k calls/dag, vi laver ~216.
4. **`_estimateCellPx` præcision**: fast center-koordinat (56N, 10E). Cellestørrelse varierer ~5% på tværs af DK; OK for zoom-tærskel.
5. **CSP**: ingen ændringer nødvendige.
6. **Diskrepans mellem `score_lapse_rate` og `thermal_top_m`** (P1-2 fra review): scoring bruger fortsat `(T_2m − T_850)/15` mens termik-top bruger fuld parcel-teori. En grid-celle kan vise lapse_rate-score 8 men thermal_top_m=0 (lav inversion under 850 hPa). Dokumenteres som kendt feature i frontend-popup hjælpetekst. **Fremtidig opgave**: cap score_lapse_rate ved lav thermal_top_m, eller harmonisér de to beregninger. Ikke i denne PR — vi ændrer ikke scoring-modellen lige nu.
7. **Tidsmæssig fortolkning** (P1-1 fra review): `thermal_top_m` for time `h` gælder for time `h` — det er ikke "dagens maks". Brugeren navigerer time-slider for at finde peak (typisk kl. 13-15). Dette dokumenteres i Om-siden. Et fremtidig `thermal_top_max_today_m`-felt overvejes, men er ikke med i denne PR.
8. **Hcrit uden surface heat flux**: SW-baseret margin er empirisk approksimation. Klassisk RASP bruger fuld varmestrøm fra modellen. Vores fejl er ±100-200 m, acceptabelt for forecast-formål.
9. **Tests**: parcel-teori er deterministisk men sondering-tests bruger idealiserede tal. Valider mod real-world soundings (Wyoming database, Aalborg/København) som manuel test i en uge før hård deploy.

---

## Review-rettelser (v1 → v2)

Denne plan er v2 efter parallel review fra to agenter. Vigtigste ændringer fra v1:

| P | Område | Ændring |
|---|--------|---------|
| P0 | scoring.py | Bolton 1980 kommentar: eq. **22** ikke eq. 15 |
| P0 | scoring.py | `thermal_top_m=None` (ikke 0) ved no_data / no_dewpoint |
| P0 | scoring.py | Nye `limited_by`: `weak_solar`, `margin_collapse`, `saturated`, `no_dewpoint` |
| P0 | scoring.py | Hcrit-margin lineært interpoleret 200-500 m, cap'd til raw_top/2 |
| P0 | scoring.py | Default ved SW=None er 500 m (konservativt), ikke 250 m |
| P0 | fetch_weather.py | Eksplicit import af `compute_thermal_top` (linje 17) |
| P0 | fetch_weather.py | Early-return data-dict udvides med `thermal_top_m: None` etc. |
| P0 | fetch_weather.py | Eksplicit payload-placering: grid=top-niveau, airfield=`data`-dict |
| P0 | style.css | Eksplicite mobil-regler for `#layer-section` (display:none + .expanded) |
| P0 | scoring.py | 500 hPa droppet fra trykniveauer (DK termik når sjældent dertil) |
| P1 | app.js | `setScoreCanvas(null, ...)` nulstiller labels ved no-data |
| P1 | tests | Udvid `test_fetch_weather.py` med integrationsassertions |
| P1 | tests | Geopotential sanity-test som CI-vagthund |
| P1 | tests | End-to-end SW-skalering test |
| P2 | scoring.py | Lineær Hcrit-interpolation (glatte kort, ingen trin-spring) |
| P2 | locations.py | Send airfield-elevation som `surface_elevation_m` hvor det findes |
