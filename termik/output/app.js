// ============================================================
// Termik-forecast Danmark — Frontend Application
// ============================================================

// === State ===
let forecastData = null;
let currentDay = 0;
let currentHour = 14;
let scoreLayer = null;      // Custom Leaflet layer that paints the interpolated score canvas
let countryMask = null;     // Denmark land polygon as GeoJSON Feature (used for clipping)
let airfieldMarkers = [];
let map = null;
let baseDate = null; // Date object for day 0 (parsed from generated timestamp)
let activeLayer = 'score';  // 'score' | 'thermal-top'
const LAYER_KEY = 'termik-active-layer';

// === URL hash parameters ===
function parseHash() {
    var params = {};
    var hash = window.location.hash.replace('#', '');
    if (!hash) return params;
    hash.split('&').forEach(function(part) {
        var kv = part.split('=');
        if (kv.length === 2) params[kv[0]] = decodeURIComponent(kv[1]);
    });
    return params;
}

function updateHash() {
    var center = map.getCenter();
    var parts = [
        'day=' + currentDay,
        'hour=' + currentHour,
        'lat=' + center.lat.toFixed(2),
        'lon=' + center.lng.toFixed(2),
        'zoom=' + map.getZoom()
    ];
    history.replaceState(null, '', '#' + parts.join('&'));
}

// === Color interpolation ===
const COLOR_STOPS = [
    [0,  [30,  60, 150]],   // dark blue
    [3,  [100, 150, 220]],  // light blue
    [5,  [240, 220, 50]],   // yellow
    [7,  [240, 140, 30]],   // orange
    [10, [220, 30,  30]],   // red
];

function scoreToRgb(score) {
    const s = Math.max(0, Math.min(10, score));
    let lower = COLOR_STOPS[0];
    let upper = COLOR_STOPS[COLOR_STOPS.length - 1];
    for (let i = 0; i < COLOR_STOPS.length - 1; i++) {
        if (s >= COLOR_STOPS[i][0] && s <= COLOR_STOPS[i + 1][0]) {
            lower = COLOR_STOPS[i];
            upper = COLOR_STOPS[i + 1];
            break;
        }
    }
    const range = upper[0] - lower[0];
    const t = range === 0 ? 0 : (s - lower[0]) / range;
    return [
        Math.round(lower[1][0] + t * (upper[1][0] - lower[1][0])),
        Math.round(lower[1][1] + t * (upper[1][1] - lower[1][1])),
        Math.round(lower[1][2] + t * (upper[1][2] - lower[1][2])),
    ];
}

function scoreToColor(score) {
    const [r, g, b] = scoreToRgb(score);
    return `rgb(${r},${g},${b})`;
}

function scoreToHeatIntensity(score) {
    return Math.max(0, Math.min(1, score / 10));
}

// Distinct viridis-like palette for thermal-top altitudes (meters MSL).
// Chosen to be perceptually different from the score palette so the two
// layers are immediately distinguishable in screenshots and on shared links.
const THERMAL_TOP_STOPS = [
    [0,    [45,  27,  78]],   // dark purple — no thermal
    [500,  [94,  58,  140]],  // purple-blue — very weak
    [1000, [42,  123, 155]],  // blue-teal — typical DK day
    [1500, [127, 183, 62]],   // green-yellow — good soaring
    [2000, [240, 183, 62]],   // yellow-orange — strong
    [2500, [232, 90,  26]],   // orange-red — extreme
];

function thermalTopToRgb(m) {
    if (m == null) return [200, 200, 200]; // unknown — neutral grey
    if (m <= THERMAL_TOP_STOPS[0][0]) return THERMAL_TOP_STOPS[0][1];
    const last = THERMAL_TOP_STOPS[THERMAL_TOP_STOPS.length - 1];
    if (m >= last[0]) return last[1];
    for (let i = 1; i < THERMAL_TOP_STOPS.length; i++) {
        if (m <= THERMAL_TOP_STOPS[i][0]) {
            const a = THERMAL_TOP_STOPS[i - 1];
            const b = THERMAL_TOP_STOPS[i];
            const t = (m - a[0]) / (b[0] - a[0]);
            return [
                Math.round(a[1][0] + t * (b[1][0] - a[1][0])),
                Math.round(a[1][1] + t * (b[1][1] - a[1][1])),
                Math.round(a[1][2] + t * (b[1][2] - a[1][2])),
            ];
        }
    }
    return last[1];
}

// === Data access ===
function getTargetDateStr(day) {
    // Return "YYYY-MM-DD" string for the given day offset
    const d = new Date(baseDate);
    d.setDate(d.getDate() + day);
    const yyyy = d.getFullYear();
    const mm = String(d.getMonth() + 1).padStart(2, '0');
    const dd = String(d.getDate()).padStart(2, '0');
    return `${yyyy}-${mm}-${dd}`;
}

function getHourIndex(point, day, hour) {
    const dateStr = getTargetDateStr(day);
    const hourStr = String(hour).padStart(2, '0');
    const target = `${dateStr}T${hourStr}:00`;

    for (let i = 0; i < point.hours.length; i++) {
        if (point.hours[i].time === target) {
            return i;
        }
    }
    return -1;
}

function getPointAtTime(point, day, hour) {
    const idx = getHourIndex(point, day, hour);
    if (idx === -1) return null;
    return point.hours[idx];
}

// === Map ===
function initMap() {
    var params = parseHash();
    var initLat = params.lat ? parseFloat(params.lat) : 56.2;
    var initLon = params.lon ? parseFloat(params.lon) : 10.5;
    var initZoom = params.zoom ? parseInt(params.zoom, 10) : 7;
    map = L.map('map', {
        zoomControl: true,
    }).setView([initLat, initLon], initZoom);

    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
        maxZoom: 19,
    }).addTo(map);

    // Custom pane so the score-grid sits above tiles but below markers
    map.createPane('scoreGrid');
    map.getPane('scoreGrid').style.zIndex = 350;
    map.getPane('scoreGrid').style.pointerEvents = 'none';
}

// === Score canvas layer ===
// Renders the score field as a single canvas with bilinear interpolation
// between grid points (browser-native via imageSmoothingEnabled), clipped
// to the Denmark coastline. Far cheaper than thousands of SVG polygons.
const GRID_STEP_DEG = 0.2;
const SCORE_BBOX = { latMin: 54.5, latMax: 57.7, lonMin: 8.0, lonMax: 15.2 };
const SCORE_OPACITY = 0.55;

// Build a small offscreen canvas: one pixel per 0.2° grid cell, filled with
// the score's RGB. Missing cells (offshore) get the nearest existing score so
// browser smoothing has clean values everywhere — the country-mask clip on the
// display canvas hides anything that ends up over the sea.
function buildScoreCanvas() {
    if (!forecastData) return null;
    const { latMin, latMax, lonMin, lonMax } = SCORE_BBOX;
    const W = Math.round((lonMax - lonMin) / GRID_STEP_DEG) + 1;
    const H = Math.round((latMax - latMin) / GRID_STEP_DEG) + 1;

    const points = [];
    for (const p of forecastData.points) {
        if (p.type !== 'grid') continue;
        const hd = getPointAtTime(p, currentDay, currentHour);
        if (!hd) continue;
        points.push({ lat: p.lat, lon: p.lon, score: hd.score });
    }
    if (!points.length) return null;

    const canvas = document.createElement('canvas');
    canvas.width = W;
    canvas.height = H;
    const ctx = canvas.getContext('2d');
    const img = ctx.createImageData(W, H);
    const alpha = Math.round(255 * SCORE_OPACITY);

    for (let y = 0; y < H; y++) {
        const lat = latMax - y * GRID_STEP_DEG;
        for (let x = 0; x < W; x++) {
            const lon = lonMin + x * GRID_STEP_DEG;
            let bestScore = 0;
            let bestDist = Infinity;
            for (const p of points) {
                const dlat = p.lat - lat;
                const dlon = p.lon - lon;
                const d = dlat * dlat + dlon * dlon;
                if (d < bestDist) { bestDist = d; bestScore = p.score; }
            }
            const [r, g, b] = scoreToRgb(bestScore);
            const idx = (y * W + x) * 4;
            img.data[idx] = r;
            img.data[idx + 1] = g;
            img.data[idx + 2] = b;
            img.data[idx + 3] = alpha;
        }
    }
    ctx.putImageData(img, 0, 0);
    return canvas;
}

const ScoreCanvasLayer = L.Layer.extend({
    initialize: function() {
        this._scoreCanvas = null;
        this._mask = null;     // GeoJSON Feature with MultiPolygon coordinates
        this._smoothing = true; // false → discrete cells (used by thermal-top layer)
        this._labels = null;   // [{lat, lon, text}] — rendered above the canvas when set
    },
    onAdd: function(map) {
        const canvas = L.DomUtil.create('canvas', 'leaflet-score-canvas');
        canvas.style.position = 'absolute';
        canvas.style.pointerEvents = 'none';
        const pane = map.getPane('scoreGrid');
        pane.appendChild(canvas);
        this._canvas = canvas;
        map.on('moveend zoomend resize', this._render, this);
        this._render();
    },
    onRemove: function(map) {
        map.off('moveend zoomend resize', this._render, this);
        L.DomUtil.remove(this._canvas);
        this._canvas = null;
    },
    setScoreCanvas: function(canvas, smoothing, labels) {
        this._scoreCanvas = canvas;
        this._smoothing = smoothing !== false;  // default true
        this._labels = labels || null;
        this._render();
    },
    setMask: function(feature) {
        this._mask = feature;
        this._render();
    },
    _buildMaskPath: function() {
        if (!this._mask) return null;
        const map = this._map;
        const path = new Path2D();
        const geom = this._mask.geometry;
        const polys = geom.type === 'MultiPolygon' ? geom.coordinates : [geom.coordinates];
        for (const poly of polys) {
            for (const ring of poly) {
                let first = true;
                for (const coord of ring) {
                    const pt = map.latLngToContainerPoint([coord[1], coord[0]]);
                    if (first) { path.moveTo(pt.x, pt.y); first = false; }
                    else path.lineTo(pt.x, pt.y);
                }
                path.closePath();
            }
        }
        return path;
    },
    _render: function() {
        const map = this._map;
        const canvas = this._canvas;
        if (!map || !canvas) return;
        const size = map.getSize();
        canvas.width = size.x;
        canvas.height = size.y;
        const topLeft = map.containerPointToLayerPoint([0, 0]);
        L.DomUtil.setPosition(canvas, topLeft);

        const ctx = canvas.getContext('2d');
        ctx.clearRect(0, 0, size.x, size.y);
        if (!this._scoreCanvas) return;

        const maskPath = this._buildMaskPath();
        if (maskPath) {
            ctx.save();
            ctx.clip(maskPath);
        }

        // Extend destination by half a grid step on each side so source pixel
        // centres land on their grid point's lat/lon (drawImage maps source
        // EDGES to destination edges, so without this we'd be off by half a
        // pixel — visible as a ~5 km diagonal shift once the mask hugs the
        // coast precisely).
        const half = GRID_STEP_DEG / 2;
        const tl = map.latLngToContainerPoint([SCORE_BBOX.latMax + half, SCORE_BBOX.lonMin - half]);
        const br = map.latLngToContainerPoint([SCORE_BBOX.latMin - half, SCORE_BBOX.lonMax + half]);
        ctx.imageSmoothingEnabled = this._smoothing;
        ctx.imageSmoothingQuality = 'high';
        ctx.drawImage(this._scoreCanvas, tl.x, tl.y, br.x - tl.x, br.y - tl.y);

        if (maskPath) ctx.restore();

        // Labels render OUTSIDE the coastal clip so they aren't cut at the edge.
        if (this._labels && this._labels.length) {
            this._drawLabels(ctx);
        }
    },
    _drawLabels: function(ctx) {
        const map = this._map;
        const cellPx = this._estimateCellPx();
        if (cellPx < 48) return; // too cramped — labels overlap below zoom 9
        const maskPath = this._buildMaskPath();
        ctx.font = 'bold 11px sans-serif';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.lineWidth = 3;
        ctx.strokeStyle = 'rgba(255,255,255,0.85)';
        ctx.fillStyle = '#222';
        for (const l of this._labels) {
            const pt = map.latLngToContainerPoint([l.lat, l.lon]);
            // Skip labels for grid points that fall outside the country
            // (otherwise "1300m" floats over Kattegat etc.)
            if (maskPath && !ctx.isPointInPath(maskPath, pt.x, pt.y)) continue;
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

function buildThermalTopCanvas() {
    if (!forecastData) return null;
    const { latMin, latMax, lonMin, lonMax } = SCORE_BBOX;
    const W = Math.round((lonMax - lonMin) / GRID_STEP_DEG) + 1;
    const H = Math.round((latMax - latMin) / GRID_STEP_DEG) + 1;

    // Kun celler med en reel værdi: null-celler (ældre data) må ikke ende som
    // grå pixels i kildecanvasset, for med smoothing slået til ville de smøre
    // gråt ind over naboerne. Nærmeste-nabo-udfyldningen nedenfor giver i
    // stedet null-cellerne den nærmeste rigtige værdi, præcis som score-laget
    // håndterer havceller.
    const points = [];
    for (const p of forecastData.points) {
        if (p.type !== 'grid') continue;
        const hd = getPointAtTime(p, currentDay, currentHour);
        if (!hd || hd.thermal_top_m == null) continue;
        points.push({ lat: p.lat, lon: p.lon, m: hd.thermal_top_m });
    }
    if (!points.length) return null;

    const canvas = document.createElement('canvas');
    canvas.width = W;
    canvas.height = H;
    const ctx = canvas.getContext('2d');
    const img = ctx.createImageData(W, H);
    const alpha = Math.round(255 * SCORE_OPACITY);

    for (let y = 0; y < H; y++) {
        const lat = latMax - y * GRID_STEP_DEG;
        for (let x = 0; x < W; x++) {
            const lon = lonMin + x * GRID_STEP_DEG;
            let bestM = null;
            let bestDist = Infinity;
            for (const p of points) {
                const dlat = p.lat - lat;
                const dlon = p.lon - lon;
                const d = dlat * dlat + dlon * dlon;
                if (d < bestDist) { bestDist = d; bestM = p.m; }
            }
            const [r, g, b] = thermalTopToRgb(bestM);
            const idx = (y * W + x) * 4;
            img.data[idx] = r;
            img.data[idx + 1] = g;
            img.data[idx + 2] = b;
            img.data[idx + 3] = alpha;
        }
    }
    ctx.putImageData(img, 0, 0);

    // Build labels for each grid point that has a value
    const labels = [];
    for (const p of points) {
        if (p.m == null) continue;
        const rounded = Math.round(p.m / 100) * 100;
        labels.push({ lat: p.lat, lon: p.lon, text: rounded + 'm' });
    }
    return { canvas: canvas, labels: labels };
}

function updateHeatmap() {
    if (!scoreLayer) {
        scoreLayer = new ScoreCanvasLayer();
        scoreLayer.addTo(map);
        if (countryMask) scoreLayer.setMask(countryMask);
    }
    if (activeLayer === 'thermal-top') {
        // Samme glatte rendering som score-laget: smoothing=true. De diskrete
        // felter fra den oprindelige plan er droppet; højdelabels ovenpå
        // beholder aflæseligheden af de konkrete tal.
        const built = buildThermalTopCanvas();
        if (built) {
            scoreLayer.setScoreCanvas(built.canvas, true, built.labels);
        } else {
            scoreLayer.setScoreCanvas(null, true, null);
        }
        updateLegend('thermal-top');
    } else {
        scoreLayer.setScoreCanvas(buildScoreCanvas(), true, null);
        updateLegend('score');
    }
}

function updateLegend(layer) {
    const el = document.getElementById('layer-legend');
    if (!el) return;
    if (layer === 'thermal-top') {
        el.innerHTML =
            '<div class="legend-bar legend-thermal"></div>' +
            '<div class="legend-labels"><span>0m</span><span>1500m</span><span>2500m+</span></div>';
    } else {
        el.innerHTML =
            '<div class="legend-bar legend-score"></div>' +
            '<div class="legend-labels"><span>0</span><span>5</span><span>10</span></div>';
    }
}

function setupLayerControls() {
    let stored = null;
    try { stored = localStorage.getItem(LAYER_KEY); } catch (e) { /* private mode */ }
    if (stored === 'score' || stored === 'thermal-top') activeLayer = stored;
    const radios = document.querySelectorAll('input[name="map-layer"]');
    for (const r of radios) {
        r.checked = (r.value === activeLayer);
        r.addEventListener('change', function() {
            if (!this.checked) return;
            activeLayer = this.value;
            try { localStorage.setItem(LAYER_KEY, activeLayer); } catch (e) { /* private */ }
            updateHeatmap();
        });
    }
}

// === Airfield markers ===
function createAirfieldMarkers() {
    const airfields = forecastData.points.filter(function(p) { return p.type === 'airfield'; });

    for (const af of airfields) {
        const marker = L.circleMarker([af.lat, af.lon], {
            radius: 9,
            weight: 2,
            color: '#fff',
            fillOpacity: 0.9,
            fillColor: '#888',
        });

        marker.bindPopup('', { maxWidth: 360, maxHeight: popupMaxHeight(), className: 'termik-popup' });

        // Store reference to airfield on marker for popup updates
        marker._airfieldData = af;

        marker.on('click', function() {
            const popup = createPopupContent(af);
            marker.setPopupContent(popup);
        });

        marker.addTo(map);
        airfieldMarkers.push({ marker: marker, point: af });
    }
}

function updateMarkerColors() {
    for (const { marker, point } of airfieldMarkers) {
        const hourData = getPointAtTime(point, currentDay, currentHour);
        const score = hourData ? hourData.score : 0;
        marker.setStyle({ fillColor: scoreToColor(score) });

        // If popup is open, refresh its content
        if (marker.isPopupOpen()) {
            marker.setPopupContent(createPopupContent(point));
        }
    }
}

// === Popup ===
// Popup-højden følger skærmen: på mobil scroller indholdet i popup'en,
// på desktop er der plads til at vise det meste eller det hele. Leaflet
// læser maxHeight ved bind, så resize-lytteren opdaterer alle markørers
// popup-options; næste åbning bruger den nye højde.
function popupMaxHeight() {
    return Math.max(420, window.innerHeight - 150);
}

window.addEventListener('resize', function() {
    for (const entry of airfieldMarkers) {
        const popup = entry.marker && entry.marker.getPopup();
        if (popup) popup.options.maxHeight = popupMaxHeight();
    }
});

// Redesign 2026-08-26: prioriteret hierarki. Ring + termikvindue, tekst,
// dagsforl\u00F8b, tre heltetal, og sektionerne Termik (h\u00F8jdeakse + lapse-
// m\u00E5ler), Temperatur (spread-termometer), Vind (kompas + s\u00F8jler i knob)
// og Himmel og sol (skylag-bj\u00E6lker). Alt bygger p\u00E5 eksisterende felter.
function createPopupContent(airfield) {
    const hourData = getPointAtTime(airfield, currentDay, currentHour);
    if (!hourData) {
        return '<div class="popup-content"><h3>' + escapeHtml(airfield.name) + '</h3><p>Ingen data for dette tidspunkt.</p></div>';
    }

    const d = hourData.data;

    return '<div class="popup-content">'
        + '<h3>' + escapeHtml(airfield.name) + '</h3>'
        + buildScoreHeader(airfield, hourData)
        + '<p class="popup-comment">' + escapeHtml(hourData.comment) + '</p>'
        + '<div class="popup-seclabel first">Dagsforl\u00F8b</div>'
        + buildDayChart(airfield)
        + buildHeroes(d)
        + '<div class="popup-seclabel" title="Beregnet brugbar termikh\u00F8jde (parcel-teori), skybase og blandingslag p\u00E5 samme akse">Termik</div>'
        + buildTermikSection(d)
        + '<div class="popup-seclabel" title="B\u00E5ndet g\u00E5r fra dugpunkt til temperatur; l\u00E6ngden er spread, som s\u00E6tter skybasen">Temperatur (\u00B0C)</div>'
        + buildTempBar(d)
        + '<div class="popup-seclabel" title="Pilene peger med vinden. M\u00F8rk pil: 10 m; lysere: 80 og 180 m. R\u00F8dt m\u00E6rke: dagens st\u00F8d">Vind (knob)</div>'
        + buildWindSection(d)
        + '<div class="popup-seclabel">Himmel og sol</div>'
        + buildSkySection(d)
        + '</div>';
}

function buildScoreHeader(airfield, hourData) {
    // Ringen viser dagens gennemsnit kl. 10-18, samme tal som favorit-
    // panelet (getDaySummary), ikke den valgte times score. Timens score
    // ses i dagsforl\u00F8bet og p\u00E5 kortet.
    const summary = getDaySummary(airfield, currentDay);
    const avg = summary ? summary.avg : hourData.score;
    const color = scoreToColor(avg);
    const deg = Math.round(Math.max(0, Math.min(10, avg)) / 10 * 360);
    const windowText = computeThermalWindow(airfield);
    return '<div class="popup-bigscore">'
        + '<div class="popup-ring" style="background:conic-gradient(' + color + ' 0 ' + deg + 'deg, #e5e7eb ' + deg + 'deg 360deg)">'
        +   '<i style="background:' + color + '">' + avg + '</i>'
        + '</div>'
        + '<div class="popup-window">' + windowText
        +   '<small>' + scoreLabelDa(avg) + ' \u00B7 gennemsnit kl. 10\u201318</small>'
        + '</div>'
        + '</div>';
}

// Klient-udgave af SCORE_LABELS i config.py; bruges til dagsgennemsnittet,
// hvor der ikke findes en server-genereret label.
function scoreLabelDa(score) {
    const s = Math.floor(score);
    if (s >= 9) return 'Fremragende termik';
    if (s >= 7) return 'God termik';
    if (s >= 5) return 'Moderat termik';
    if (s >= 3) return 'Svag termik';
    return 'Ingen brugbar termik';
}

// Termikvinduet afl\u00E6ses af dagens timer: f\u00F8rste og sidste time med
// score >= 5, og "bedst"-intervallet er timerne med score >= 8.5.
function computeThermalWindow(airfield) {
    let first = null, last = null, bestFirst = null, bestLast = null;
    for (let h = 6; h <= 21; h++) {
        const hd = getPointAtTime(airfield, currentDay, h);
        if (!hd) continue;
        if (hd.score >= 5) {
            if (first === null) first = h;
            last = h;
        }
        if (hd.score >= 8.5) {
            if (bestFirst === null) bestFirst = h;
            bestLast = h;
        }
    }
    if (first === null) return 'Ingen brugbar termik i dag';
    let text = 'Termik ca. ' + first + ' til ' + last;
    if (bestFirst !== null && (bestFirst !== first || bestLast !== last)) {
        text += bestFirst === bestLast
            ? ', bedst kl. ' + bestFirst
            : ', bedst ' + bestFirst + ' til ' + bestLast;
    }
    return text;
}

function limitedByDa(limitedBy) {
    switch (limitedBy) {
        case 'lcl': return 'base-begr\u00E6nset';
        case 'ti_zero': return 'temp-begr\u00E6nset';
        case 'inversion': return 'jordinversion';
        case 'weak_solar': return 'svag sol';
        case 'margin_collapse': return 'svag sol';
        case 'saturated': return 'm\u00E6ttet luft';
        case 'cap': return 'dyb konvektion';
        default: return '';
    }
}

function compassLetter(deg) {
    const dirs = ['N', 'N\u00D8', '\u00D8', 'S\u00D8', 'S', 'SV', 'V', 'NV'];
    return dirs[Math.round(deg / 45) % 8];
}

function buildHeroes(d) {
    const topCell = d.thermal_top_m != null
        ? '<b>' + d.thermal_top_m + ' m</b><small>' + limitedByDa(d.thermal_top_limited_by) + '</small>'
        : '<b>\u2013</b><small>ingen data</small>';
    return '<div class="popup-heroes">'
        + '<div class="popup-hero" title="Beregnet maks. brugbar termikh\u00F8jde"><span>Termiktop</span>' + topCell + '</div>'
        + '<div class="popup-hero" title="Estimeret skybase (spread \u00D7 125 m)"><span>Skybase</span><b>' + d.skybase_m + ' m</b><small>' + d.skybase_ft + ' ft</small></div>'
        + '<div class="popup-hero" title="Vind i 10 m; pilen peger med vinden"><span>Vind</span><b>' + getWindArrow(d.wind_dir) + ' ' + Math.round(d.wind_speed_kt) + ' kt</b><small>' + compassLetter(d.wind_dir) + ' \u00B7 st\u00F8d ' + Math.round(d.wind_gusts_kt) + '</small></div>'
        + '</div>';
}

function buildTermikSection(d) {
    return '<div class="popup-termgrid">'
        + buildAltAxis(d)
        + '<div class="popup-termside">'
        +   buildLapseGauge(d.lapse_rate)
        +   (d.boundary_layer_height != null
            ? '<div class="popup-kv"><span>Blandingslag</span><span>' + Math.round(d.boundary_layer_height) + ' m</span></div>'
            : '')
        +   (d.thermal_top_limited_by && limitedByDa(d.thermal_top_limited_by)
            ? '<div class="popup-kv"><span>Begr\u00E6nses af</span><span>' + limitedByDa(d.thermal_top_limited_by).replace('-begr\u00E6nset', 'n') + '</span></div>'
            : '')
        + '</div>'
        + '</div>';
}

function buildAltAxis(d) {
    const top = d.thermal_top_m;
    const base = d.lcl_m != null ? d.lcl_m : d.skybase_m;
    const bl = d.boundary_layer_height;
    const maxVal = Math.max(top || 0, base || 0, bl || 0, 1300);
    const axisMax = Math.ceil((maxVal + 250) / 400) * 400;
    const pct = (m) => Math.max(0, Math.min(100, m / axisMax * 100));

    let html = '<div class="popup-alt">';
    const step = axisMax / 4;
    for (let i = 0; i <= 4; i++) {
        html += '<span class="alt-tick" style="bottom:' + (i * 25) + '%">' + Math.round(i * step) + '</span>';
    }
    if (d.cloud_cover_high != null && d.cloud_cover_high >= 20) {
        html += '<div class="alt-cloudband" style="opacity:' + (0.35 + d.cloud_cover_high / 200) + '"></div>'
            + '<span class="alt-lab cirrus">cirrus ' + Math.round(d.cloud_cover_high) + ' %</span>';
    }
    if (top != null && top > 0) {
        html += '<div class="alt-thermcol" style="height:' + pct(top) + '%"></div>'
            + '<span class="alt-lab top" style="bottom:' + Math.min(pct(top) + 2.5, 88) + '%">top ' + top + '</span>';
    }
    if (base != null) {
        html += '<div class="alt-hline base" style="bottom:' + pct(base) + '%"></div>'
            + '<span class="alt-lab base" style="bottom:' + Math.min(pct(base) + 2.5, 94) + '%">base ' + Math.round(base) + '</span>';
    }
    if (bl != null) {
        html += '<div class="alt-hline bl" style="bottom:' + pct(bl) + '%"></div>'
            + '<span class="alt-lab bl" style="bottom:' + Math.max(pct(bl) - 8, 2) + '%">bl.lag ' + Math.round(bl) + '</span>';
    }
    html += '</div>';
    return html;
}

function buildLapseGauge(lapse) {
    // Zonegr\u00E6nserne er scoringens egne t\u00E6rskler: 0.65 / 0.8 / 1.0
    const t = Math.max(0, Math.min(1, (lapse - 0.4) / 0.9));
    return '<div class="popup-gauge" title="Zoner: stabil < 0.65, svagt labil, betinget labil, labil \u2265 1.0">'
        + '<div class="gauge-lab"><span>Lapse rate</span><b>' + lapse + '\u00B0/100m</b></div>'
        + '<div class="gauge-track">'
        +   '<i style="width:27.8%;background:#b9c6d1"></i>'
        +   '<i style="width:16.7%;background:#e5c95b"></i>'
        +   '<i style="width:22.2%;background:#e8a13f"></i>'
        +   '<i style="width:33.3%;background:#ce4a3d"></i>'
        +   '<span class="gauge-mark" style="left:' + (t * 100).toFixed(1) + '%"></span>'
        + '</div>'
        + '<div class="gauge-zones"><span>stabil</span><span>labil</span></div>'
        + '</div>';
}

function buildTempBar(d) {
    const tmin = Math.min(0, Math.floor(d.dewpoint));
    const tmax = Math.max(30, Math.ceil(d.temp));
    const range = tmax - tmin;
    const pct = (v) => ((v - tmin) / range * 100);
    const dewPct = pct(d.dewpoint);
    const tmpPct = pct(d.temp);
    let ticks = '';
    for (let i = 0; i <= 3; i++) {
        ticks += '<span>' + Math.round(tmin + range * i / 3) + '\u00B0C</span>';
    }
    return '<div class="popup-temprow">'
        + '<div class="temp-track"></div>'
        + '<div class="temp-band" style="left:' + dewPct.toFixed(1) + '%;width:' + (tmpPct - dewPct).toFixed(1) + '%"></div>'
        + '<span class="temp-spread" style="left:' + ((dewPct + tmpPct) / 2).toFixed(1) + '%">spread <b>' + d.spread + '\u00B0C</b></span>'
        + '<span class="temp-pt dew" style="left:' + dewPct.toFixed(1) + '%">dug ' + d.dewpoint + '\u00B0C</span>'
        + '<span class="temp-pt tmp" style="left:' + tmpPct.toFixed(1) + '%">' + d.temp + '\u00B0C</span>'
        + '</div>'
        + '<div class="temp-ticks">' + ticks + '</div>';
}

function buildWindSection(d) {
    return '<div class="popup-windgrid">'
        + buildCompass(d)
        + buildWindBars(d)
        + '</div>';
}

function buildCompass(d) {
    // Pilene peger MED vinden (nedstr\u00F8ms): rotation = retning + 180.
    const arrow = (dir, len, width, color, opacity, head) => {
        const rot = ((dir + 180) % 360).toFixed(0);
        let g = '<g transform="rotate(' + rot + ' 52 52)" opacity="' + opacity + '">'
            + '<line x1="52" y1="52" x2="52" y2="' + (52 - len) + '" stroke="' + color + '" stroke-width="' + width + '" stroke-linecap="round"/>';
        if (head) {
            g += '<path d="M52 ' + (46 - len) + ' L46.5 ' + (56 - len) + ' L57.5 ' + (56 - len) + ' Z" fill="' + color + '"/>';
        }
        return g + '</g>';
    };
    let arrows = '';
    if (d.wind_speed_180m_kt != null && d.wind_dir_180m != null) {
        arrows += arrow(d.wind_dir_180m, 40, 2.5, '#7ba7c9', 0.55, true);
    }
    if (d.wind_speed_80m_kt != null && d.wind_dir_80m != null) {
        arrows += arrow(d.wind_dir_80m, 33, 3, '#4a86b4', 0.7, false);
    }
    arrows += arrow(d.wind_dir, 36, 4, '#16679f', 1, true);
    return '<svg class="popup-compass" viewBox="0 0 104 104" role="img" aria-label="Vindkompas">'
        + '<circle cx="52" cy="52" r="44" fill="none" stroke="#e5e7eb" stroke-width="1.5"/>'
        + '<text x="52" y="14" text-anchor="middle" class="compass-pt">N</text>'
        + '<text x="95" y="55" text-anchor="middle" class="compass-pt">\u00D8</text>'
        + '<text x="52" y="99" text-anchor="middle" class="compass-pt">S</text>'
        + '<text x="9" y="55" text-anchor="middle" class="compass-pt">V</text>'
        + arrows
        + '<circle cx="52" cy="52" r="3.5" fill="#1e2433"/>'
        + '</svg>';
}

function buildWindBars(d) {
    const gust = d.wind_gusts_kt;
    const maxKt = Math.max(20, Math.ceil(Math.max(gust || 0, d.wind_speed_180m_kt || 0, d.wind_speed_kt) + 4));
    const w = (kt) => Math.min(96, kt / maxKt * 100);
    const row = (label, kt) => {
        if (kt == null) return '';
        return '<div class="wind-row"><span class="wind-h">' + label + '</span>'
            + '<span class="wind-bar"><i style="width:' + w(kt).toFixed(0) + '%"></i>'
            + '<b style="left:' + (w(kt) + 2).toFixed(0) + '%">' + Math.round(kt) + ' kt</b></span></div>';
    };
    let groundExtra = '';
    if (gust != null && gust > d.wind_speed_kt + 2) {
        groundExtra = '<span class="wind-gust" style="left:' + w(gust).toFixed(0) + '%"></span>'
            + '<span class="wind-gustlab" style="left:' + Math.min(w(gust) + 3, 84).toFixed(0) + '%">G' + Math.round(gust) + ' kt</span>';
    }
    const groundRow = '<div class="wind-row"><span class="wind-h">10 m</span>'
        + '<span class="wind-bar"><i style="width:' + w(d.wind_speed_kt).toFixed(0) + '%"></i>'
        + '<b style="left:' + (w(d.wind_speed_kt) + 2).toFixed(0) + '%">' + Math.round(d.wind_speed_kt) + ' kt</b>'
        + groundExtra + '</span></div>';
    let veer = '';
    if (d.wind_dir_180m != null && Math.abs(d.wind_dir_180m - d.wind_dir) >= 5) {
        veer = '<div class="popup-kv"><span>Drejning 10\u2192180 m</span><span>' + Math.round(d.wind_dir) + '\u00B0 \u2192 ' + Math.round(d.wind_dir_180m) + '\u00B0</span></div>';
    }
    return '<div class="wind-rows">'
        + row('180 m', d.wind_speed_180m_kt)
        + row('80 m', d.wind_speed_80m_kt)
        + groundRow
        + veer
        + '</div>';
}

function buildSkySection(d) {
    let bars = '';
    if (d.cloud_cover_low != null && d.cloud_cover_mid != null && d.cloud_cover_high != null) {
        const row = (label, pctVal, color) =>
            '<div class="cloud-row"><span class="cloud-lab">' + label + '</span>'
            + '<span class="cloud-bar"><i style="width:' + Math.round(pctVal) + '%;background:' + color + '"></i></span>'
            + '<span class="cloud-pct">' + Math.round(pctVal) + ' %</span></div>';
        bars = row('H\u00F8j', d.cloud_cover_high, '#c7d8e8')
            + row('Mellem', d.cloud_cover_mid, '#9fb8ce')
            + row('Lav', d.cloud_cover_low, '#7d99b4');
    } else {
        bars = '<div class="cloud-row"><span class="cloud-lab">Sky</span>'
            + '<span class="cloud-bar"><i style="width:' + Math.round(d.cloud_cover) + '%;background:#9fb8ce"></i></span>'
            + '<span class="cloud-pct">' + Math.round(d.cloud_cover) + ' %</span></div>';
    }
    let extras = '';
    if (d.direct_radiation != null) {
        extras += '<div class="popup-kv" title="Direkte solindstr\u00E5ling: det der driver opvarmningen af jorden"><span>Direkte sol</span><span>' + Math.round(d.direct_radiation) + ' W/m\u00B2</span></div>';
    }
    if (d.cape >= 300) {
        extras += '<div class="popup-kv" title="H\u00F8j CAPE = risiko for byger/overudvikling"><span>CAPE</span><span>' + Math.round(d.cape) + ' J/kg</span></div>';
    }
    if (d.precipitation > 0) {
        extras += '<div class="popup-kv"><span>Nedb\u00F8r</span><span>' + d.precipitation + ' mm</span></div>';
    }
    return '<div class="popup-sky">' + bars + extras + '</div>';
}

function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.appendChild(document.createTextNode(text));
    return div.innerHTML;
}

function buildDayChart(airfield) {
    const hours = [];
    for (let h = 6; h <= 21; h++) {
        const data = getPointAtTime(airfield, currentDay, h);
        hours.push({ hour: h, score: data ? data.score : 0 });
    }

    let html = '<div class="day-chart">';
    for (const { hour, score } of hours) {
        const height = Math.max(4, score * 10); // percent of container
        const color = scoreToColor(score);
        const active = hour === currentHour ? ' active' : '';
        html += '<div class="chart-bar' + active + '" style="height:' + height + '%;background:' + color + '" title="' + hour + ':00 \u2014 score ' + score + '"></div>';
    }
    html += '</div>';
    html += '<div class="chart-labels"><span>06</span><span>09</span><span>12</span><span>15</span><span>18</span><span>21</span></div>';
    return html;
}

function getWindArrow(degrees) {
    // Wind direction is where it comes FROM.
    // Arrow points in the direction the wind is blowing TO (downwind).
    const arrows = ['\u2193', '\u2199', '\u2190', '\u2196', '\u2191', '\u2197', '\u2192', '\u2198'];
    const index = Math.round(degrees / 45) % 8;
    return arrows[index];
}

// === Favorite airfield ===
const FAVORITE_KEY = 'termik-favorite-airfield';

function getDayLabel(day) {
    if (day === 0) return 'I dag';
    if (day === 1) return 'I morgen';
    if (!baseDate) return '+' + day + ' dage';
    const weekdays = ['Søndag', 'Mandag', 'Tirsdag', 'Onsdag', 'Torsdag', 'Fredag', 'Lørdag'];
    const d = new Date(baseDate);
    d.setDate(d.getDate() + day);
    return weekdays[d.getDay()];
}

function getDaySummary(airfield, day) {
    let sum = 0;
    let count = 0;
    let goodHours = 0;
    for (let h = 10; h <= 18; h++) {
        const data = getPointAtTime(airfield, day, h);
        if (!data) continue;
        sum += data.score;
        count += 1;
        if (data.score >= 5) goodHours += 1;
    }
    if (count === 0) return null;
    return {
        avg: Math.round((sum / count) * 10) / 10,
        goodHours: goodHours,
        totalHours: count,
    };
}

function populateFavoriteSelect() {
    const select = document.getElementById('favorite-select');
    const airfields = forecastData.points
        .filter(function(p) { return p.type === 'airfield'; })
        .slice()
        .sort(function(a, b) { return a.name.localeCompare(b.name, 'da'); });

    airfields.forEach(function(af) {
        const opt = document.createElement('option');
        opt.value = af.id;
        opt.textContent = af.name;
        select.appendChild(opt);
    });

    const saved = localStorage.getItem(FAVORITE_KEY);
    if (saved && airfields.some(function(af) { return af.id === saved; })) {
        select.value = saved;
    }

    select.addEventListener('change', function() {
        if (select.value) {
            localStorage.setItem(FAVORITE_KEY, select.value);
        } else {
            localStorage.removeItem(FAVORITE_KEY);
        }
        updateFavoriteForecast();
        updateWeatherWidget();
    });
}

function updateFavoriteForecast() {
    const el = document.getElementById('favorite-forecast');
    const select = document.getElementById('favorite-select');
    const id = select.value;
    if (!id) {
        el.innerHTML = '';
        return;
    }

    const airfield = forecastData.points.find(function(p) { return p.id === id; });
    if (!airfield) {
        el.innerHTML = '';
        return;
    }

    let html = '<div class="fav-header">Gennemsnit kl. 10–18</div>';
    html += '<div class="fav-list">';
    for (let day = 0; day <= 6; day++) {
        const sum = getDaySummary(airfield, day);
        const score = sum ? sum.avg : 0;
        const color = sum ? scoreToColor(score) : '#ddd';
        const good = sum ? sum.goodHours + '/' + sum.totalHours + ' gode t.' : '—';
        const active = day === currentDay ? ' active' : '';
        html += '<div class="fav-row' + active + '" data-day="' + day + '">'
            + '<span class="fav-day">' + getDayLabel(day) + '</span>'
            + '<span class="fav-hour">' + good + '</span>'
            + '<span class="fav-score" style="background:' + color + '">' + (sum ? sum.avg : '–') + '</span>'
            + '</div>';
    }
    html += '</div>';
    el.innerHTML = html;

    el.querySelectorAll('.fav-row').forEach(function(row) {
        row.addEventListener('click', function() {
            const day = parseInt(row.dataset.day, 10);
            const btn = document.querySelector('.day-btn[data-day="' + day + '"]');
            if (btn) btn.click();
            updateHash();
            map.setView([airfield.lat, airfield.lon], Math.max(map.getZoom(), 9), { animate: true });
            const entry = airfieldMarkers.find(function(m) { return m.point.id === airfield.id; });
            if (entry) {
                entry.marker.setPopupContent(createPopupContent(entry.point));
                entry.marker.openPopup();
            }
        });
    });
}

// === Weather widget (current conditions for favorite airfield) ===

// Apparent temperature (Australian AT model) from temp (°C), RH (%), wind (kt)
function apparentTemp(tempC, rh, windKt) {
    const ws = (windKt || 0) * 0.514444; // kt -> m/s
    const e = (rh / 100) * 6.105 * Math.exp((17.27 * tempC) / (237.7 + tempC));
    return tempC + 0.33 * e - 0.70 * ws - 4.0;
}

// Pick a readable text colour (dark/light) against a score-coloured background
function textColorForScore(score) {
    const [r, g, b] = scoreToRgb(score);
    const lum = 0.299 * r + 0.587 * g + 0.114 * b;
    return lum > 150 ? '#222' : '#fff';
}

// Inline SVG weather icon chosen from cloud cover (%) and precipitation (mm)
function weatherIconSvg(cloud, precip) {
    if (precip != null && precip > 0.1) {
        return '<svg viewBox="0 0 64 64" width="54" height="54" aria-hidden="true">'
            + '<path d="M18 42 a12 12 0 0 1 12-12 a14 14 0 0 1 14 13 a9 9 0 0 1 -1 17 H18 a10 10 0 0 1 0-18 Z" fill="#aeb8c2" stroke="#8c97a3" stroke-width="1.5"/>'
            + '<g stroke="#4a90d9" stroke-width="3" stroke-linecap="round">'
            + '<line x1="24" y1="56" x2="21" y2="62"/><line x1="34" y1="56" x2="31" y2="62"/><line x1="44" y1="56" x2="41" y2="62"/></g></svg>';
    }
    if (cloud != null && cloud >= 80) {
        return '<svg viewBox="0 0 64 64" width="54" height="54" aria-hidden="true">'
            + '<path d="M16 46 a13 13 0 0 1 13-13 a15 15 0 0 1 15 14 a9 9 0 0 1 -1 18 H16 a10 10 0 0 1 0-19 Z" fill="#b8c2cc" stroke="#9aa6b2" stroke-width="1.5"/></svg>';
    }
    if (cloud != null && cloud >= 30) {
        return '<svg viewBox="0 0 64 64" width="54" height="54" aria-hidden="true">'
            + '<circle cx="24" cy="22" r="10" fill="#f6c343"/>'
            + '<g stroke="#f6c343" stroke-width="3" stroke-linecap="round">'
            + '<line x1="24" y1="3" x2="24" y2="9"/><line x1="5" y1="22" x2="11" y2="22"/>'
            + '<line x1="10" y1="8" x2="14" y2="12"/><line x1="38" y1="8" x2="34" y2="12"/></g>'
            + '<path d="M22 46 a11 11 0 0 1 11-11 a13 13 0 0 1 13 12 a8 8 0 0 1 -1 16 H22 a9 9 0 0 1 0-17 Z" fill="#e2e8ee" stroke="#c2ccd6" stroke-width="1.5"/></svg>';
    }
    return '<svg viewBox="0 0 64 64" width="54" height="54" aria-hidden="true">'
        + '<circle cx="32" cy="32" r="13" fill="#f6c343"/>'
        + '<g stroke="#f6c343" stroke-width="3.5" stroke-linecap="round">'
        + '<line x1="32" y1="5" x2="32" y2="14"/><line x1="32" y1="50" x2="32" y2="59"/>'
        + '<line x1="5" y1="32" x2="14" y2="32"/><line x1="50" y1="32" x2="59" y2="32"/>'
        + '<line x1="13" y1="13" x2="19" y2="19"/><line x1="45" y1="45" x2="51" y2="51"/>'
        + '<line x1="13" y1="51" x2="19" y2="45"/><line x1="45" y1="19" x2="51" y2="13"/></g></svg>';
}

// Sunrise/sunset (official zenith 90.833°) from the Almanac for Computers
// algorithm. Returns a Date, or null at latitudes where the sun never
// rises/sets that day.
function sunEventUTC(year, month, day, lat, lon, isRise) {
    const rad = Math.PI / 180;
    const mod = function (a, n) { return ((a % n) + n) % n; };
    const N = Math.floor((Date.UTC(year, month - 1, day) - Date.UTC(year, 0, 1)) / 86400000) + 1;
    const lngHour = lon / 15;
    const t = N + ((isRise ? 6 : 18) - lngHour) / 24;
    const M = 0.9856 * t - 3.289;
    const L = mod(M + 1.916 * Math.sin(M * rad) + 0.020 * Math.sin(2 * M * rad) + 282.634, 360);
    let RA = mod(Math.atan(0.91764 * Math.tan(L * rad)) / rad, 360);
    RA = (RA + Math.floor(L / 90) * 90 - Math.floor(RA / 90) * 90) / 15;
    const sinDec = 0.39782 * Math.sin(L * rad);
    const cosDec = Math.cos(Math.asin(sinDec));
    const cosH = (Math.cos(90.833 * rad) - sinDec * Math.sin(lat * rad)) / (cosDec * Math.cos(lat * rad));
    if (cosH > 1 || cosH < -1) return null;
    const H = (isRise ? 360 - Math.acos(cosH) / rad : Math.acos(cosH) / rad) / 15;
    const T = H + RA - 0.06571 * t - 6.622;
    return new Date(Date.UTC(year, month - 1, day) + mod(T - lngHour, 24) * 3600000);
}

// Today's sunrise/sunset at a position, formatted as local HH:MM (or "–")
function sunTimesText(lat, lon) {
    const now = new Date();
    const fmt = function (d) {
        return d ? d.toLocaleTimeString('da-DK', { hour: '2-digit', minute: '2-digit' }) : '–';
    };
    const y = now.getFullYear(), m = now.getMonth() + 1, day = now.getDate();
    return {
        rise: fmt(sunEventUTC(y, m, day, lat, lon, true)),
        set: fmt(sunEventUTC(y, m, day, lat, lon, false)),
    };
}

// Today's day-offset and the actual current hour (0-23, unclamped)
function getNowDayHour() {
    const now = new Date();
    const todayStr = now.getFullYear() + '-'
        + String(now.getMonth() + 1).padStart(2, '0') + '-'
        + String(now.getDate()).padStart(2, '0');
    let dayDiff = Math.round((new Date(todayStr) - new Date(getTargetDateStr(0))) / 86400000);
    if (dayDiff < 0) dayDiff = 0;
    if (dayDiff > 6) dayDiff = 6;
    return { day: dayDiff, hour: now.getHours() };
}

function addWeatherControl() {
    const WeatherControl = L.Control.extend({
        onAdd: function () {
            const div = L.DomUtil.create('div', 'ww-wrap ww-hidden');
            div.id = 'weather-widget';
            L.DomEvent.disableClickPropagation(div);
            L.DomEvent.disableScrollPropagation(div);
            return div;
        },
        onRemove: function () {},
    });
    new WeatherControl({ position: 'topleft' }).addTo(map);
}

function updateWeatherWidget() {
    const el = document.getElementById('weather-widget');
    if (!el || !forecastData) return;

    let favId = null;
    try { favId = localStorage.getItem(FAVORITE_KEY); } catch (e) { /* private mode */ }
    if (!favId) { el.classList.add('ww-hidden'); return; }

    const af = forecastData.points.find(function (p) {
        return p.id === favId && p.type === 'airfield';
    });
    if (!af) { el.classList.add('ww-hidden'); return; }

    const nowdh = getNowDayHour();
    let hd = getPointAtTime(af, nowdh.day, nowdh.hour);
    // Fall back to the nearest available hour today if the exact hour is missing
    for (let off = 1; off <= 6 && !hd; off++) {
        hd = getPointAtTime(af, nowdh.day, nowdh.hour - off)
            || getPointAtTime(af, nowdh.day, nowdh.hour + off);
    }
    if (!hd) { el.classList.add('ww-hidden'); return; }

    const d = hd.data;
    const barColor = scoreToColor(hd.score);
    const barText = textColorForScore(hd.score);
    const feel = Math.round(apparentTemp(d.temp, d.relative_humidity, d.wind_speed_kt));
    const windArrow = getWindArrow(d.wind_dir);
    const sun = sunTimesText(af.lat, af.lon);

    el.innerHTML =
        '<div class="ww-main">'
        +   '<div class="ww-icon">' + weatherIconSvg(d.cloud_cover, d.precipitation) + '</div>'
        +   '<div>'
        +     '<div class="ww-temp">' + Math.round(d.temp) + '°</div>'
        +     '<div class="ww-place">' + escapeHtml(af.name) + '</div>'
        +   '</div>'
        + '</div>'
        + '<div class="ww-details">'
        +   '<div class="ww-stat"><span>Luftfugtighed</span><b>' + Math.round(d.relative_humidity) + '%</b></div>'
        +   '<div class="ww-stat"><span>Vind</span><b>' + windArrow + ' ' + Math.round(d.wind_speed_kt) + ' kt</b></div>'
        +   '<div class="ww-stat"><span>Føles som</span><b>' + feel + '°</b></div>'
        +   '<div class="ww-stat"><span>Tryk</span><b>' + Math.round(d.pressure) + ' hPa</b></div>'
        +   '<div class="ww-stat"><span>Solopgang</span><b>' + sun.rise + '</b></div>'
        +   '<div class="ww-stat"><span>Solnedgang</span><b>' + sun.set + '</b></div>'
        + '</div>'
        + '<div class="ww-bar" style="background:' + barColor + ';color:' + barText + '">'
        +   escapeHtml(hd.label) + '</div>';

    el.classList.remove('ww-hidden');
}

// === Controls ===
function setupControls() {
    // Day buttons
    var uncertaintyNote = document.getElementById('uncertainty-note');
    document.querySelectorAll('.day-btn').forEach(function(btn) {
        btn.addEventListener('click', function() {
            document.querySelector('.day-btn.active').classList.remove('active');
            btn.classList.add('active');
            currentDay = parseInt(btn.dataset.day, 10);
            if (currentDay >= 3) {
                uncertaintyNote.textContent = '\u26A0\uFE0F Prognose ' + currentDay + ' dage frem \u2014 stor usikkerhed';
                uncertaintyNote.style.display = 'block';
            } else {
                uncertaintyNote.style.display = 'none';
            }
            updateAll();
            updateHash();
        });
    });

    // Time slider
    const slider = document.getElementById('time-slider');
    const display = document.getElementById('time-display');
    slider.addEventListener('input', function() {
        currentHour = parseInt(slider.value, 10);
        display.textContent = String(currentHour).padStart(2, '0') + ':00';
        updateAll();
        updateHash();
    });

    // Sidebar toggle — desktop collapses right, mobile toggles expanded (shows favorites)
    const sidebar = document.getElementById('sidebar');
    const toggle = document.getElementById('sidebar-toggle');
    const isMobile = function() { return window.matchMedia('(max-width: 768px)').matches; };

    toggle.addEventListener('click', function() {
        if (isMobile()) {
            sidebar.classList.toggle('expanded');
        } else {
            sidebar.classList.toggle('collapsed');
        }
    });

    // Mobile swipe up/down on the handle to expand/collapse favorites
    let touchStartY = null;
    toggle.addEventListener('touchstart', function(e) {
        touchStartY = e.touches[0].clientY;
    }, { passive: true });
    toggle.addEventListener('touchend', function(e) {
        if (touchStartY === null || !isMobile()) { touchStartY = null; return; }
        const dy = e.changedTouches[0].clientY - touchStartY;
        touchStartY = null;
        if (Math.abs(dy) > 20) {
            if (dy < 0) sidebar.classList.add('expanded');
            else sidebar.classList.remove('expanded');
        }
    });

    // Opdater-knappen henter nyeste data uden at lukke appen
    document.getElementById('refresh-btn').addEventListener('click', function() {
        refreshForecastData();
    });
}

// === Update everything ===
function updateAll() {
    updateHeatmap();
    updateMarkerColors();
    updateFavoriteForecast();
}

// === Genindlæsning af vejrdata ===
// PWA'en genoptages fra hukommelsen på mobil, så forecastData kan være
// timer gammel selv om serveren har friske data. To veje ind: Opdater-
// knappen, og en automatisk hentning når appen kommer i forgrunden og
// sidste hentning er over 30 minutter gammel.
let lastDataFetchMs = 0;
const AUTO_REFRESH_AGE_MS = 30 * 60 * 1000;

function applyGeneratedTimestamp() {
    const genParts = forecastData.generated.split('T')[0].split('-');
    baseDate = new Date(
        parseInt(genParts[0], 10),
        parseInt(genParts[1], 10) - 1,
        parseInt(genParts[2], 10)
    );
    const genDate = new Date(forecastData.generated);
    const info = document.getElementById('update-info');
    if (info) info.textContent = 'Opdateret: ' + genDate.toLocaleString('da-DK');
    applyCoverageNote();
}

// Kørslen afviser output med store huller, men et enkelt tabt gitter-batch
// slipper igennem. Kortet interpolerer nærmeste nabo uden afstandsgrænse, så
// et hul ses ikke som et hul, men som naboens score smurt ud over området.
// Uden denne linje ville brugeren ikke kunne se forskel, og "Opdateret"-
// tidsstemplet lige ovenfor ville se lige så friskt ud som altid.
function applyCoverageNote() {
    const note = document.getElementById('coverage-note');
    if (!note) return;
    const expected = forecastData.expected_point_count;
    const got = forecastData.points ? forecastData.points.length : 0;
    // Datafiler fra før feltet fandtes: intet at sige noget om.
    if (!expected || got >= expected) {
        note.style.display = 'none';
        note.textContent = '';
        return;
    }
    const missing = expected - got;
    note.textContent = 'Delvis prognose: ' + missing + ' af ' + expected
        + ' m\u00E5lepunkter mangler i denne opdatering. Kortet udfylder '
        + 'hullerne med n\u00E6rmeste nabo, s\u00E5 scoren kan v\u00E6re '
        + 'up\u00E5lidelig i enkelte omr\u00E5der.';
    note.style.display = '';
}

async function refreshForecastData() {
    const btn = document.getElementById('refresh-btn');
    if (btn) btn.classList.add('refreshing');
    try {
        // cache: 'no-cache' revaliderer forbi både HTTP-cachen og SW'ens
        // network-first, så knappen altid rammer serveren
        const resp = await fetch('data/current.json', { cache: 'no-cache' });
        if (!resp.ok) throw new Error('HTTP ' + resp.status);
        const fresh = await resp.json();
        lastDataFetchMs = Date.now();
        if (fresh.generated !== forecastData.generated) {
            forecastData = fresh;
            applyGeneratedTimestamp();
            // Markørernes click-handlers lukker over de gamle punkt-objekter,
            // så de bygges om frem for at få nye referencer listet ind
            for (const entry of airfieldMarkers) {
                entry.marker.remove();
            }
            airfieldMarkers = [];
            createAirfieldMarkers();
            document.querySelectorAll('.day-btn').forEach(function(b) {
                const d = parseInt(b.getAttribute('data-day'), 10);
                b.textContent = getDayLabel(d);
            });
            updateAll();
        }
    } catch (e) {
        // Ingen netdækning eller serverfejl: behold de data vi har
    } finally {
        if (btn) btn.classList.remove('refreshing');
    }
}

document.addEventListener('visibilitychange', function() {
    if (
        document.visibilityState === 'visible'
        && forecastData
        && Date.now() - lastDataFetchMs > AUTO_REFRESH_AGE_MS
    ) {
        refreshForecastData();
    }
});

// === Loading UI helpers ===
function showLoading() {
    const overlay = document.createElement('div');
    overlay.id = 'loading-overlay';
    overlay.className = 'loading-overlay';
    overlay.innerHTML = '<div class="loading-spinner"></div><div>Indl\u00E6ser vejrdata\u2026</div>';
    document.body.appendChild(overlay);
}

function hideLoading() {
    const el = document.getElementById('loading-overlay');
    if (el) el.remove();
}

function showError(message) {
    hideLoading();
    const el = document.createElement('div');
    el.className = 'error-message';
    el.innerHTML = '<h1>Fejl ved indl\u00E6sning</h1>'
        + '<p>' + escapeHtml(message) + '</p>'
        + '<p style="margin-top:12px;font-size:12px;">Pr\u00F8v at \u00E5bne siden via en lokal webserver, f.eks.:<br>'
        + '<code style="background:rgba(255,255,255,0.1);padding:4px 8px;border-radius:4px;">python3 -m http.server 8000</code></p>';
    document.body.appendChild(el);
}

// === Init ===
async function init() {
    showLoading();

    try {
        const [forecastResp, maskResp] = await Promise.all([
            fetch('data/current.json'),
            fetch('data/denmark.geojson'),
        ]);
        if (!forecastResp.ok) throw new Error('HTTP ' + forecastResp.status + ': ' + forecastResp.statusText);
        forecastData = await forecastResp.json();
        if (maskResp.ok) {
            const maskGj = await maskResp.json();
            countryMask = maskGj.features && maskGj.features[0];
        }
    } catch (e) {
        showError('Kan ikke indl\u00E6se vejrdata: ' + e.message);
        return;
    }

    lastDataFetchMs = Date.now();

    // Parse the base date from the generated timestamp (day 0 = date of
    // generated) and show it in the sidebar
    applyGeneratedTimestamp();

    // Set initial day and hour from URL hash or current time
    var params = parseHash();
    if (params.day !== undefined && params.hour !== undefined) {
        currentDay = Math.max(0, Math.min(6, parseInt(params.day, 10)));
        currentHour = Math.max(6, Math.min(21, parseInt(params.hour, 10)));
    } else {
        var now = new Date();
        var todayStr = now.getFullYear() + '-'
            + String(now.getMonth() + 1).padStart(2, '0') + '-'
            + String(now.getDate()).padStart(2, '0');
        var baseDateStr = getTargetDateStr(0);
        var dayDiff = Math.round((new Date(todayStr) - new Date(baseDateStr)) / 86400000);
        if (dayDiff >= 0 && dayDiff <= 6) {
            currentDay = dayDiff;
        }
        var nextHour = now.getMinutes() > 0 ? now.getHours() + 1 : now.getHours();
        currentHour = Math.max(6, Math.min(21, nextHour));
    }
    document.querySelectorAll('.day-btn').forEach(function(b) {
        const d = parseInt(b.getAttribute('data-day'), 10);
        b.textContent = getDayLabel(d);
    });
    var btn = document.querySelector('.day-btn[data-day="' + currentDay + '"]');
    if (btn) {
        document.querySelector('.day-btn.active').classList.remove('active');
        btn.classList.add('active');
    }
    var uncertaintyNote = document.getElementById('uncertainty-note');
    if (currentDay >= 3) {
        uncertaintyNote.textContent = '\u26A0\uFE0F Prognose ' + currentDay + ' dage frem \u2014 stor usikkerhed';
        uncertaintyNote.style.display = 'block';
    }
    var slider = document.getElementById('time-slider');
    var display = document.getElementById('time-display');
    slider.value = currentHour;
    display.textContent = String(currentHour).padStart(2, '0') + ':00';

    hideLoading();
    initMap();
    addWeatherControl();
    createAirfieldMarkers();
    setupControls();
    populateFavoriteSelect();
    setupLayerControls();
    updateAll();
    updateWeatherWidget();
    // Refresh the "now" widget every minute so it follows the clock without a reload
    setInterval(updateWeatherWidget, 60000);
    updateHash();
    map.on('moveend', updateHash);
}

init();

if ('serviceWorker' in navigator) {
    window.addEventListener('load', function () {
        navigator.serviceWorker.register('sw.js').catch(function () {});
    });
}
