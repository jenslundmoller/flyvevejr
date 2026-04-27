"""
Locations for the Termik Forecast project.

Defines Danish glider airfields and a grid of land-based forecast points
covering Denmark.
"""

import json
import math
import os

# ---------------------------------------------------------------------------
# 1. AIRFIELDS
# ---------------------------------------------------------------------------

# Club names, coordinates and addresses from DSvU:
# https://dsvu.dk/svaeveflyvning-i-danmark/danske-svaeveflyveklubber
# coast_distance_km / coast_direction_deg computed via _nearest_coast().
AIRFIELDS = [
    # --- Nordjylland ---
    {"id": "aars", "name": "Aviator - Aalborg Svæveflyveklub", "lat": 56.8454026, "lon": 9.4644496, "region": "Nordjylland", "coast_distance_km": 10, "coast_direction_deg": 54},
    {"id": "saeby", "name": "Nordjysk Svæveflyveklub", "lat": 57.34477, "lon": 10.414422, "region": "Nordjylland", "coast_distance_km": 8, "coast_direction_deg": 40},
    {"id": "skive", "name": "Skive Svæveflyveklub", "lat": 56.547204, "lon": 9.18163, "region": "Nordjylland", "coast_distance_km": 20, "coast_direction_deg": 327},
    {"id": "svaevethy", "name": "Svævethy", "lat": 56.825374, "lon": 8.78893, "region": "Nordjylland", "coast_distance_km": 19, "coast_direction_deg": 137},
    {"id": "viborg", "name": "Viborg Svæveflyveklub", "lat": 56.410191, "lon": 9.412827, "region": "Nordjylland", "coast_distance_km": 41, "coast_direction_deg": 322},
    # --- Midtjylland ---
    {"id": "aarhus", "name": "Aarhus Svæveflyveklub", "lat": 56.180727, "lon": 10.071415, "region": "Midtjylland", "coast_distance_km": 22, "coast_direction_deg": 158},
    {"id": "arnborg", "name": "Billund Svæveflyveklub", "lat": 56.010733, "lon": 9.02249, "region": "Midtjylland", "coast_distance_km": 48, "coast_direction_deg": 136},
    {"id": "arnborg_dsvhk", "name": "Dansk Svæveflyvehistorisk Klub", "lat": 56.0107544, "lon": 9.0252296, "region": "Midtjylland", "coast_distance_km": 48, "coast_direction_deg": 136},
    {"id": "arnborg_jas", "name": "Jysk Aero Sport", "lat": 56.0095823, "lon": 9.020431, "region": "Midtjylland", "coast_distance_km": 48, "coast_direction_deg": 136},
    {"id": "arnborg_sg70", "name": "SG 70", "lat": 56.0102939, "lon": 9.016545520539, "region": "Midtjylland", "coast_distance_km": 48, "coast_direction_deg": 136},
    {"id": "silkeborg", "name": "Silkeborg Flyveklub", "lat": 56.104818, "lon": 9.393871, "region": "Midtjylland", "coast_distance_km": 46, "coast_direction_deg": 168},
    {"id": "herning", "name": "Herning Svæveflyveklub", "lat": 56.187885, "lon": 9.038394, "region": "Midtjylland", "coast_distance_km": 57, "coast_direction_deg": 324},
    {"id": "lemvig", "name": "Lemvig Flyveklub", "lat": 56.5037649, "lon": 8.3046264277665, "region": "Midtjylland", "coast_distance_km": 13, "coast_direction_deg": 268},
    {"id": "holstebro", "name": "Holstebro Flyveklub", "lat": 56.309451, "lon": 8.587248, "region": "Midtjylland", "coast_distance_km": 33, "coast_direction_deg": 351},
    {"id": "vestjylland", "name": "Vestjyllands Svæveflyveklub", "lat": 56.01995, "lon": 8.692003, "region": "Midtjylland", "coast_distance_km": 38, "coast_direction_deg": 284},
    # --- Sydjylland ---
    {"id": "skrydstrup", "name": "Flyvestation Skrydstrup Svæveflyveklub", "lat": 55.238238, "lon": 9.255881, "region": "Sydjylland", "coast_distance_km": 16, "coast_direction_deg": 85},
    {"id": "kolding", "name": "Kolding Flyveklub", "lat": 55.551061, "lon": 9.193698, "region": "Sydjylland", "coast_distance_km": 28, "coast_direction_deg": 53},
    {"id": "roedekro", "name": "Sønderjysk Flyveklub", "lat": 55.077034, "lon": 9.299691, "region": "Sydjylland", "coast_distance_km": 13, "coast_direction_deg": 132},
    {"id": "toender", "name": "Tønder Flyveklub", "lat": 54.926836, "lon": 8.843816, "region": "Sydjylland", "coast_distance_km": 13, "coast_direction_deg": 130},
    {"id": "vejle", "name": "Vejle Svæveflyveklub", "lat": 55.905979, "lon": 9.453807, "region": "Sydjylland", "coast_distance_km": 24, "coast_direction_deg": 165},
    {"id": "bolhede", "name": "Vestjysk Svæveflyveklub", "lat": 55.631233, "lon": 8.754528, "region": "Sydjylland", "coast_distance_km": 42, "coast_direction_deg": 250},
    # --- Fyn ---
    {"id": "broby", "name": "Fyns Svæveflyveklub", "lat": 55.249029, "lon": 10.20772, "region": "Fyn", "coast_distance_km": 28, "coast_direction_deg": 234},
    # --- Sjælland ---
    {"id": "goerloese", "name": "Nordsjællands Svæveflyveklub", "lat": 55.883228, "lon": 12.228438, "region": "Sjælland", "coast_distance_km": 19, "coast_direction_deg": 13},
    {"id": "frederikssund", "name": "Frederikssund Frederiksværk Flyveklub", "lat": 55.851737, "lon": 12.068724, "region": "Sjælland", "coast_distance_km": 26, "coast_direction_deg": 33},
    {"id": "kalundborg", "name": "Kalundborg Flyveklub", "lat": 55.699723, "lon": 11.259246, "region": "Sjælland", "coast_distance_km": 13, "coast_direction_deg": 270},
    {"id": "eskebjerg_polyt", "name": "Polyteknisk Flyvegruppe", "lat": 55.7010215, "lon": 11.2615806, "region": "Sjælland", "coast_distance_km": 13, "coast_direction_deg": 270},
    {"id": "kongsted", "name": "Øst-Sjællands Flyveklub", "lat": 55.250158, "lon": 12.060847, "region": "Sjælland", "coast_distance_km": 16, "coast_direction_deg": 110},
    {"id": "ringsted", "name": "Midtsjællands Svæveflyveklub", "lat": 55.451748, "lon": 11.642456, "region": "Sjælland", "coast_distance_km": 33, "coast_direction_deg": 239},
    {"id": "toelloese", "name": "Tølløse Flyveklub", "lat": 55.58106, "lon": 11.755577, "region": "Sjælland", "coast_distance_km": 46, "coast_direction_deg": 287},
    {"id": "lolland", "name": "Lolland Falster Svæveflyveklub", "lat": 54.697558, "lon": 11.445898, "region": "Sjælland", "coast_distance_km": 11, "coast_direction_deg": 195},
]

# ---------------------------------------------------------------------------
# 2. GRID POINTS — 0.4 x 0.4 degree grid over Denmark, land points only
# ---------------------------------------------------------------------------

# Simple point-in-polygon test using ray casting algorithm.
def _point_in_polygon(lat, lon, polygon):
    """
    Ray casting algorithm to test if point (lat, lon) is inside a polygon.
    polygon is a list of (lat, lon) tuples forming a closed polygon.
    """
    n = len(polygon)
    inside = False
    j = n - 1
    for i in range(n):
        yi, xi = polygon[i]
        yj, xj = polygon[j]
        if ((yi > lat) != (yj > lat)) and (
            lon < (xj - xi) * (lat - yi) / (yj - yi) + xi
        ):
            inside = not inside
        j = i
    return inside


# Define simplified polygons for Danish land masses.
# These are generous outlines to capture grid points that fall on land.

_JYLLAND = [
    (57.60, 8.20),   # Skagen west
    (57.75, 10.70),  # Skagen east
    (57.10, 10.70),  # East of Frederikshavn
    (56.90, 10.30),  # Djursland north
    (56.40, 10.90),  # Aarhus area east
    (56.20, 10.60),  # Horsens east
    (55.60, 9.80),   # Vejle Fjord east
    (55.50, 9.80),   # Fredericia east
    (55.30, 9.50),   # Kolding east
    (55.05, 9.50),   # Haderslev east
    (54.80, 9.40),   # Aabenraa area
    (54.80, 8.60),   # South Jylland / Tønder
    (54.90, 8.20),   # Southwest coast
    (55.20, 8.20),   # Esbjerg area
    (55.50, 8.10),   # Ringkøbing area
    (56.00, 8.05),   # Holmsland
    (56.50, 8.05),   # Thyborøn
    (56.70, 8.20),   # Lemvig
    (56.95, 8.40),   # Mors area
    (57.10, 8.50),   # Thisted area
    (57.60, 8.20),   # Back to start
]

_FYN = [
    (55.55, 9.80),   # NW Fyn
    (55.55, 10.80),  # NE Fyn
    (55.05, 10.80),  # SE Fyn
    (55.05, 9.80),   # SW Fyn
    (55.55, 9.80),   # Close
]

_SJAELLAND = [
    (56.10, 11.00),  # NW Sjælland (Rørvig)
    (56.10, 12.40),  # NE Sjælland (Helsingør)
    (55.60, 12.70),  # Copenhagen area
    (55.20, 12.40),  # SE Sjælland (Stevns)
    (55.00, 11.80),  # South Sjælland
    (55.20, 11.00),  # SW Sjælland (Korsør)
    (55.50, 11.00),  # West Sjælland (Kalundborg)
    (56.10, 11.00),  # Close
]

_LOLLAND_FALSTER = [
    (54.95, 11.10),  # NW Lolland
    (54.95, 12.20),  # NE Falster
    (54.55, 12.20),  # SE Falster
    (54.55, 11.10),  # SW Lolland
    (54.95, 11.10),  # Close
]

_BORNHOLM = [
    (55.30, 14.60),  # NW
    (55.30, 15.20),  # NE
    (54.95, 15.20),  # SE
    (54.95, 14.60),  # SW
    (55.30, 14.60),  # Close
]

_LAND_POLYGONS = [_JYLLAND, _FYN, _SJAELLAND, _LOLLAND_FALSTER, _BORNHOLM]


def _is_land(lat, lon):
    """Check if a point is on Danish land using polygon test."""
    for polygon in _LAND_POLYGONS:
        if _point_in_polygon(lat, lon, polygon):
            return True
    return False


# Higher-fidelity Denmark land polygon, loaded from the same GeoJSON file the
# frontend uses for clipping. Used in _build_grid() so that coastal cells whose
# centre lies just offshore are still included whenever any sample point inside
# the cell falls on land.
def _load_dk_rings():
    """Return list of outer rings as [(lat, lon), ...] from denmark.geojson."""
    path = os.path.join(
        os.path.dirname(__file__), "output", "data", "denmark.geojson"
    )
    if not os.path.exists(path):
        return []
    with open(path) as f:
        gj = json.load(f)
    rings = []
    for feat in gj.get("features", []):
        geom = feat.get("geometry", {})
        if geom.get("type") == "MultiPolygon":
            polys = geom["coordinates"]
        elif geom.get("type") == "Polygon":
            polys = [geom["coordinates"]]
        else:
            continue
        for poly in polys:
            outer = poly[0]
            rings.append([(lat, lon) for lon, lat in outer])
    return rings


_DK_RINGS = _load_dk_rings()


def _is_land_strict(lat, lon):
    """Check land using the real Denmark GeoJSON outline."""
    for ring in _DK_RINGS:
        if _point_in_polygon(lat, lon, ring):
            return True
    return False


def _cell_overlaps_land(lat, lon, step):
    """Return True if any sample point in the lat/lon-centred cell is on land.

    Samples a 5x5 grid of points across the cell so coastal cells with centre
    just offshore are still included.
    """
    half = step / 2
    n = 5
    for i in range(n):
        for j in range(n):
            sample_lat = lat - half + (i + 0.5) * step / n
            sample_lon = lon - half + (j + 0.5) * step / n
            if _is_land_strict(sample_lat, sample_lon):
                return True
    return False


# Danish coastal reference points for distance/direction calculation.
# A selection of points along the Danish coastline.
_COAST_POINTS = [
    # Jylland west coast (north to south)
    (57.59, 9.96),   # Skagen
    (57.45, 10.00),
    (57.20, 9.80),
    (57.05, 9.20),
    (56.95, 8.40),   # Hanstholm
    (56.70, 8.12),   # Thyborøn
    (56.50, 8.10),
    (56.10, 8.10),   # Hvide Sande
    (55.80, 8.12),
    (55.50, 8.12),   # Esbjerg
    (55.30, 8.30),
    (55.05, 8.60),   # SW Jylland
    (54.88, 8.60),   # Tønder area coast
    (54.85, 9.00),
    (54.85, 9.40),
    # Jylland east coast (south to north)
    (55.00, 9.45),
    (55.25, 9.50),
    (55.45, 9.70),   # Kolding Fjord
    (55.55, 9.75),   # Fredericia
    (55.70, 9.55),   # Vejle Fjord
    (55.85, 10.00),
    (56.00, 10.20),
    (56.15, 10.50),  # Aarhus
    (56.40, 10.80),  # Djursland
    (56.70, 10.30),
    (56.90, 10.30),
    (57.10, 10.60),  # Frederikshavn
    (57.40, 10.50),
    # Limfjorden (inner coast)
    (56.60, 8.50),
    (56.70, 9.00),
    (56.80, 9.30),
    (56.90, 9.60),
    (56.95, 9.90),
    # Fyn coast
    (55.50, 9.85),
    (55.50, 10.60),
    (55.10, 10.60),
    (55.10, 9.85),
    (55.30, 10.70),
    # Sjælland coast
    (55.95, 11.10),
    (55.70, 11.05),
    (55.30, 11.20),
    (55.10, 11.50),
    (55.20, 12.30),
    (55.40, 12.50),
    (55.60, 12.60),
    (55.80, 12.50),
    (56.05, 12.30),
    (56.05, 11.50),
    # Lolland-Falster coast
    (54.90, 11.20),
    (54.60, 11.40),
    (54.60, 12.10),
    (54.90, 12.00),
    # Bornholm coast
    (55.10, 14.68),
    (55.10, 15.10),
    (55.25, 14.90),
    (55.00, 14.80),
]


def _haversine_km(lat1, lon1, lat2, lon2):
    """Approximate distance in km between two lat/lon points."""
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(dlon / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


def _bearing_deg(lat1, lon1, lat2, lon2):
    """Calculate bearing in degrees from point 1 to point 2."""
    dlon = math.radians(lon2 - lon1)
    lat1_r = math.radians(lat1)
    lat2_r = math.radians(lat2)
    x = math.sin(dlon) * math.cos(lat2_r)
    y = math.cos(lat1_r) * math.sin(lat2_r) - math.sin(lat1_r) * math.cos(
        lat2_r
    ) * math.cos(dlon)
    bearing = math.degrees(math.atan2(x, y))
    return round(bearing % 360)


def _nearest_coast(lat, lon):
    """Find distance and direction to nearest coast point."""
    min_dist = float("inf")
    nearest = None
    for clat, clon in _COAST_POINTS:
        d = _haversine_km(lat, lon, clat, clon)
        if d < min_dist:
            min_dist = d
            nearest = (clat, clon)
    direction = _bearing_deg(lat, lon, nearest[0], nearest[1])
    return round(min_dist), direction


GRID_STEP_DEG = 0.2


def _build_grid():
    """Build a GRID_STEP_DEG x GRID_STEP_DEG grid of land points over Denmark."""
    points = []
    lat = 54.5
    while lat <= 57.8:
        lon = 8.0
        while lon <= 15.2:
            if _cell_overlaps_land(lat, lon, GRID_STEP_DEG):
                coast_km, coast_dir = _nearest_coast(lat, lon)
                lat_str = f"{lat:.1f}".replace(".", "_")
                lon_str = f"{lon:.1f}".replace(".", "_")
                grid_id = f"grid_{lat_str}_{lon_str}"
                points.append(
                    {
                        "id": grid_id,
                        "lat": round(lat, 1),
                        "lon": round(lon, 1),
                        "coast_distance_km": coast_km,
                        "coast_direction_deg": coast_dir,
                    }
                )
            lon += GRID_STEP_DEG
        lat += GRID_STEP_DEG
    return points


GRID_POINTS = _build_grid()

# ---------------------------------------------------------------------------
# 3. ALL_POINTS
# ---------------------------------------------------------------------------

ALL_POINTS = AIRFIELDS + GRID_POINTS
