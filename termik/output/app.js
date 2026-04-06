// ============================================================
// Termik-forecast Danmark — Frontend Application
// ============================================================

// === State ===
let forecastData = null;
let currentDay = 0;
let currentHour = 14;
let heatLayer = null;
let airfieldMarkers = [];
let map = null;
let baseDate = null; // Date object for day 0 (parsed from generated timestamp)

// === Color interpolation ===
const COLOR_STOPS = [
    [0,  [30,  60, 150]],   // dark blue
    [3,  [100, 150, 220]],  // light blue
    [5,  [240, 220, 50]],   // yellow
    [7,  [240, 140, 30]],   // orange
    [10, [220, 30,  30]],   // red
];

function scoreToColor(score) {
    const s = Math.max(0, Math.min(10, score));

    // Find bounding stops
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

    const r = Math.round(lower[1][0] + t * (upper[1][0] - lower[1][0]));
    const g = Math.round(lower[1][1] + t * (upper[1][1] - lower[1][1]));
    const b = Math.round(lower[1][2] + t * (upper[1][2] - lower[1][2]));

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
    map = L.map('map', {
        zoomControl: true,
    }).setView([56.2, 10.5], 7);

    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
        maxZoom: 12,
    }).addTo(map);
}

// === Heatmap ===
function updateHeatmap() {
    if (heatLayer) {
        map.removeLayer(heatLayer);
        heatLayer = null;
    }

    const gridPoints = forecastData.points.filter(function(p) { return p.type === 'grid'; });
    const heatData = [];

    for (const point of gridPoints) {
        const hourData = getPointAtTime(point, currentDay, currentHour);
        if (!hourData) continue;
        heatData.push([point.lat, point.lon, scoreToHeatIntensity(hourData.score)]);
    }

    heatLayer = L.heatLayer(heatData, {
        radius: 35,
        blur: 25,
        maxZoom: 10,
        max: 1.0,
        gradient: {
            0.0: '#1e3c96',
            0.3: '#6496dc',
            0.5: '#f0dc32',
            0.7: '#f08c1e',
            1.0: '#dc1e1e',
        }
    }).addTo(map);
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
        +   popupItem('Vind', windArrow + ' ' + d.wind_dir + '\u00B0/' + Math.round(d.wind_speed_kt) + ' kt', 'Gennemsnitlig vindretning og -hastighed i 10m h\u00F8jde')
        +   popupItem('Lapse rate', d.lapse_rate + '\u00B0C/100m', 'Temperaturfaldet pr. 100m stigning. H\u00F8jere = mere ustabil luft = bedre termik.')
        +   popupItem('Vindst\u00F8d', Math.round(d.wind_gusts_kt) + ' kt (eff. ' + Math.round(d.wind_speed_kt + d.wind_gusts_kt / 2) + ')', 'Vindst\u00F8d i kt. Eff. = vind+(gust/2). Over 25 = nedsat, over 30 = kun erfarne.')
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

// === Sidebar (Top 5) ===
function updateTopList() {
    const airfields = forecastData.points.filter(function(p) { return p.type === 'airfield'; });
    const scored = airfields.map(function(af) {
        const data = getPointAtTime(af, currentDay, currentHour);
        return {
            id: af.id,
            name: af.name,
            score: data ? data.score : 0,
            label: data ? data.label : '',
            lat: af.lat,
            lon: af.lon,
        };
    });
    scored.sort(function(a, b) { return b.score - a.score; });
    const top5 = scored.slice(0, 5);

    const listEl = document.getElementById('top-list');
    listEl.innerHTML = top5.map(function(item, i) {
        return '<div class="top-item" data-id="' + item.id + '">'
            + '<span class="top-rank">' + (i + 1) + '.</span>'
            + '<span class="top-name">' + escapeHtml(item.name) + '</span>'
            + '<span class="top-score" style="background:' + scoreToColor(item.score) + '">' + item.score + '</span>'
            + '</div>';
    }).join('');

    // Click on top-list item zooms to it and opens popup
    listEl.querySelectorAll('.top-item').forEach(function(el) {
        el.addEventListener('click', function() {
            const id = el.dataset.id;
            const entry = airfieldMarkers.find(function(m) { return m.point.id === id; });
            if (entry) {
                map.setView([entry.point.lat, entry.point.lon], 9, { animate: true });
                entry.marker.setPopupContent(createPopupContent(entry.point));
                entry.marker.openPopup();
            }
        });
    });
}

// === Controls ===
function setupControls() {
    // Day buttons
    document.querySelectorAll('.day-btn').forEach(function(btn) {
        btn.addEventListener('click', function() {
            document.querySelector('.day-btn.active').classList.remove('active');
            btn.classList.add('active');
            currentDay = parseInt(btn.dataset.day, 10);
            updateAll();
        });
    });

    // Time slider
    const slider = document.getElementById('time-slider');
    const display = document.getElementById('time-display');
    slider.addEventListener('input', function() {
        currentHour = parseInt(slider.value, 10);
        display.textContent = String(currentHour).padStart(2, '0') + ':00';
        updateAll();
    });

    // Sidebar toggle
    const sidebar = document.getElementById('sidebar');
    document.getElementById('sidebar-toggle').addEventListener('click', function() {
        sidebar.classList.toggle('collapsed');
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
    updateTopList();
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
        const resp = await fetch('data/current.json');
        if (!resp.ok) throw new Error('HTTP ' + resp.status + ': ' + resp.statusText);
        forecastData = await resp.json();
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

    // Set initial day and hour to nearest upcoming hour
    var now = new Date();
    var todayStr = now.getFullYear() + '-'
        + String(now.getMonth() + 1).padStart(2, '0') + '-'
        + String(now.getDate()).padStart(2, '0');
    var baseDateStr = getTargetDateStr(0);
    var dayDiff = Math.round((new Date(todayStr) - new Date(baseDateStr)) / 86400000);
    if (dayDiff >= 0 && dayDiff <= 2) {
        currentDay = dayDiff;
        var btn = document.querySelector('.day-btn[data-day="' + dayDiff + '"]');
        if (btn) {
            document.querySelector('.day-btn.active').classList.remove('active');
            btn.classList.add('active');
        }
    }
    var nextHour = now.getMinutes() > 0 ? now.getHours() + 1 : now.getHours();
    nextHour = Math.max(6, Math.min(21, nextHour));
    currentHour = nextHour;
    var slider = document.getElementById('time-slider');
    var display = document.getElementById('time-display');
    slider.value = currentHour;
    display.textContent = String(currentHour).padStart(2, '0') + ':00';

    hideLoading();
    initMap();
    createAirfieldMarkers();
    setupControls();
    updateAll();
}

init();
