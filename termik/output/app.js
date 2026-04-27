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
        this._mask = null; // GeoJSON Feature with MultiPolygon coordinates
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
    setScoreCanvas: function(canvas) {
        this._scoreCanvas = canvas;
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
        ctx.imageSmoothingEnabled = true;
        ctx.imageSmoothingQuality = 'high';
        ctx.drawImage(this._scoreCanvas, tl.x, tl.y, br.x - tl.x, br.y - tl.y);

        if (maskPath) ctx.restore();
    },
});

function updateHeatmap() {
    if (!scoreLayer) {
        scoreLayer = new ScoreCanvasLayer();
        scoreLayer.addTo(map);
        if (countryMask) scoreLayer.setMask(countryMask);
    }
    scoreLayer.setScoreCanvas(buildScoreCanvas());
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

        marker.bindPopup('', { maxWidth: 340, className: 'termik-popup' });

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
function createPopupContent(airfield) {
    const hourData = getPointAtTime(airfield, currentDay, currentHour);
    if (!hourData) {
        return '<div class="popup-content"><h3>' + escapeHtml(airfield.name) + '</h3><p>Ingen data for dette tidspunkt.</p></div>';
    }

    const d = hourData.data;
    const windArrow = getWindArrow(d.wind_dir);
    const stars = buildScoreStars(hourData.score);
    const dayChart = buildDayChart(airfield);

    return '<div class="popup-content">'
        + '<h3>' + escapeHtml(airfield.name) + '</h3>'
        + '<div class="popup-score">'
        +   stars
        +   '<span class="score-value">' + hourData.score + '/10</span>'
        +   '<span class="score-label">' + escapeHtml(hourData.label) + '</span>'
        + '</div>'
        + '<p class="popup-comment">' + escapeHtml(hourData.comment) + '</p>'
        + '<div class="popup-grid">'
        +   popupItem('Temp', d.temp + '\u00B0C', 'Temperatur ved jordoverfladen (2m)')
        +   popupItem('Spread', d.spread + '\u00B0C', 'Forskellen mellem temperatur og dugpunkt. Optimalt 8\u201315\u00B0C for cumulus.')
        +   popupItem('Skybase', d.skybase_m + 'm (' + d.skybase_ft + ' ft)', 'Estimeret skybase (Henning-formel: spread \u00D7 125m)')
        +   popupItem('Vind', windArrow + ' ' + d.wind_dir + '\u00B0/' + Math.round(d.wind_speed_kt) + ' kt', 'Vindretning og -hastighed i 10m h\u00F8jde (jordniveau)')
        +   popupItem('Lapse rate', d.lapse_rate + '\u00B0C/100m', 'Temperaturfaldet pr. 100m stigning. H\u00F8jere = mere ustabil luft = bedre termik.')
        +   popupItem('Vindst\u00F8d', Math.round(d.wind_gusts_kt) + ' kt (eff. ' + Math.round(d.wind_speed_kt + d.wind_gusts_kt / 2) + ')', 'Vindst\u00F8d i kt. Eff. = vind+(gust/2). Over 25 = nedsat, over 30 = kun erfarne.')
        + (d.wind_speed_80m_kt != null
            ? popupItem('Vind 80m', Math.round(d.wind_speed_80m_kt) + ' kt', 'Vindhastighed i 80m h\u00F8jde \u2014 t\u00E6ttere p\u00E5 flyveh\u00F8jde end 10m')
            : '')
        + (d.wind_speed_180m_kt != null
            ? popupItem('Vind 180m', Math.round(d.wind_speed_180m_kt) + ' kt', 'Vindhastighed i 180m h\u00F8jde')
            : '')
        + (d.surface_lapse_rate != null
            ? popupItem('Overfladelag', d.surface_lapse_rate + '\u00B0C/100m', 'Lapse rate 2m\u2192180m. Over 0.98 = termik starter. Under 0.5 = ingen initiering.')
            : '')
        + (d.boundary_layer_height != null
            ? popupItem('Blandingslag', Math.round(d.boundary_layer_height) + 'm', 'H\u00F8jde p\u00E5 det konvektive blandingslag \u2014 estimat for maksimal termikh\u00F8jde')
            : '')
        +   popupItem('CAPE', d.cape + ' J/kg', 'Convective Available Potential Energy. H\u00F8j v\u00E6rdi = risiko for byger/overudvikling.')
        +   popupItem('Skyd\u00E6kke', d.cloud_cover + '%', 'Samlet skyd\u00E6kke. Over 87% blokerer solinstr\u00E5ling og dr\u00E6ber termik.')
        +   popupItem('Fugtighed', d.relative_humidity + '%', 'Relativ luftfugtighed ved jordoverfladen')
        + '</div>'
        + '<div class="popup-chart-section">'
        +   '<h4>Dagsforl\u00F8b</h4>'
        +   dayChart
        + '</div>'
        + '</div>';
}

function popupItem(key, val, tooltip) {
    var titleAttr = tooltip ? ' title="' + escapeHtml(tooltip) + '"' : '';
    return '<div class="popup-item"' + titleAttr + '>'
        + '<span class="popup-key">' + key + '</span>'
        + '<span class="popup-val">' + val + '</span>'
        + '</div>';
}

function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.appendChild(document.createTextNode(text));
    return div.innerHTML;
}

function buildScoreStars(score) {
    let html = '<div class="stars">';
    for (let i = 1; i <= 10; i++) {
        const filled = i <= Math.round(score);
        const color = filled ? scoreToColor(score) : '#ddd';
        html += '<span class="star" style="background:' + color + '"></span>';
    }
    html += '</div>';
    return html;
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

    // Show generated timestamp
    const genDate = new Date(forecastData.generated);
    document.getElementById('update-info').textContent =
        'Opdateret: ' + genDate.toLocaleString('da-DK');
}

// === Update everything ===
function updateAll() {
    updateHeatmap();
    updateMarkerColors();
    updateFavoriteForecast();
}

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

    // Parse the base date from the generated timestamp (day 0 = date of generated)
    const genParts = forecastData.generated.split('T')[0].split('-');
    baseDate = new Date(
        parseInt(genParts[0], 10),
        parseInt(genParts[1], 10) - 1,
        parseInt(genParts[2], 10)
    );

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
    createAirfieldMarkers();
    setupControls();
    populateFavoriteSelect();
    updateAll();
    updateHash();
    map.on('moveend', updateHash);
}

init();

if ('serviceWorker' in navigator) {
    window.addEventListener('load', function () {
        navigator.serviceWorker.register('sw.js').catch(function () {});
    });
}
