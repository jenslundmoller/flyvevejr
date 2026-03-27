"""
Locations for the Termik Forecast project.

Defines Danish glider airfields and a grid of land-based forecast points
covering Denmark.
"""

import math

# ---------------------------------------------------------------------------
# 1. AIRFIELDS
# ---------------------------------------------------------------------------

AIRFIELDS = [
    # --- Nordjylland ---
    {
        "id": "aars",
        "name": "Aars (Aviator Aalborg)",
        "lat": 56.82,
        "lon": 9.51,
        "region": "Nordjylland",
        "coast_distance_km": 45,
        "coast_direction_deg": 360,
    },
    {
        "id": "saeby",
        "name": "Sæby/Ottestrup (Nordjysk)",
        "lat": 57.33,
        "lon": 10.53,
        "region": "Nordjylland",
        "coast_distance_km": 5,
        "coast_direction_deg": 30,
    },
    {
        "id": "skive",
        "name": "Vinkel/Skive",
        "lat": 56.58,
        "lon": 9.10,
        "region": "Nordjylland",
        "coast_distance_km": 30,
        "coast_direction_deg": 310,
    },
    {
        "id": "svaevethy",
        "name": "Svævethy/Mors",
        "lat": 56.83,
        "lon": 8.58,
        "region": "Nordjylland",
        "coast_distance_km": 10,
        "coast_direction_deg": 270,
    },
    {
        "id": "viborg",
        "name": "Viborg",
        "lat": 56.36,
        "lon": 9.40,
        "region": "Nordjylland",
        "coast_distance_km": 50,
        "coast_direction_deg": 290,
    },
    # --- Midtjylland ---
    {
        "id": "aarhus",
        "name": "True/Aarhus",
        "lat": 56.11,
        "lon": 10.06,
        "region": "Midtjylland",
        "coast_distance_km": 20,
        "coast_direction_deg": 90,
    },
    {
        "id": "arnborg",
        "name": "Arnborg (DSvU)",
        "lat": 55.92,
        "lon": 9.07,
        "region": "Midtjylland",
        "coast_distance_km": 65,
        "coast_direction_deg": 270,
    },
    {
        "id": "silkeborg",
        "name": "Chr. Hede/Silkeborg",
        "lat": 56.07,
        "lon": 9.43,
        "region": "Midtjylland",
        "coast_distance_km": 45,
        "coast_direction_deg": 270,
    },
    {
        "id": "herning",
        "name": "Skinderholm/Herning",
        "lat": 56.16,
        "lon": 9.02,
        "region": "Midtjylland",
        "coast_distance_km": 55,
        "coast_direction_deg": 270,
    },
    {
        "id": "lemvig",
        "name": "Lemvig",
        "lat": 56.55,
        "lon": 8.30,
        "region": "Midtjylland",
        "coast_distance_km": 10,
        "coast_direction_deg": 270,
    },
    {
        "id": "holstebro",
        "name": "Nr. Felding/Holstebro",
        "lat": 56.38,
        "lon": 8.52,
        "region": "Midtjylland",
        "coast_distance_km": 30,
        "coast_direction_deg": 270,
    },
    {
        "id": "videbaek",
        "name": "Videbæk",
        "lat": 55.98,
        "lon": 8.63,
        "region": "Midtjylland",
        "coast_distance_km": 40,
        "coast_direction_deg": 270,
    },
    # --- Sydjylland ---
    {
        "id": "billund",
        "name": "Billund",
        "lat": 55.74,
        "lon": 9.15,
        "region": "Sydjylland",
        "coast_distance_km": 50,
        "coast_direction_deg": 270,
    },
    {
        "id": "skrydstrup",
        "name": "Skrydstrup",
        "lat": 55.22,
        "lon": 9.26,
        "region": "Sydjylland",
        "coast_distance_km": 40,
        "coast_direction_deg": 210,
    },
    {
        "id": "kolding",
        "name": "Gesten/Kolding",
        "lat": 55.52,
        "lon": 9.32,
        "region": "Sydjylland",
        "coast_distance_km": 25,
        "coast_direction_deg": 180,
    },
    {
        "id": "roedekro",
        "name": "Rødekro",
        "lat": 55.07,
        "lon": 9.34,
        "region": "Sydjylland",
        "coast_distance_km": 25,
        "coast_direction_deg": 180,
    },
    {
        "id": "toender",
        "name": "Tønder",
        "lat": 54.93,
        "lon": 8.84,
        "region": "Sydjylland",
        "coast_distance_km": 15,
        "coast_direction_deg": 210,
    },
    {
        "id": "vejle",
        "name": "Vejle",
        "lat": 55.69,
        "lon": 9.38,
        "region": "Sydjylland",
        "coast_distance_km": 15,
        "coast_direction_deg": 120,
    },
    {
        "id": "bolhede",
        "name": "Bolhede",
        "lat": 55.46,
        "lon": 8.56,
        "region": "Sydjylland",
        "coast_distance_km": 25,
        "coast_direction_deg": 270,
    },
    # --- Fyn ---
    {
        "id": "broby",
        "name": "Broby/Fyn",
        "lat": 55.27,
        "lon": 10.22,
        "region": "Fyn",
        "coast_distance_km": 20,
        "coast_direction_deg": 180,
    },
    # --- Sjælland ---
    {
        "id": "goerloese",
        "name": "Gørløse",
        "lat": 55.85,
        "lon": 12.15,
        "region": "Sjælland",
        "coast_distance_km": 20,
        "coast_direction_deg": 0,
    },
    {
        "id": "frederikssund",
        "name": "Frederikssund",
        "lat": 55.84,
        "lon": 12.07,
        "region": "Sjælland",
        "coast_distance_km": 10,
        "coast_direction_deg": 0,
    },
    {
        "id": "kalundborg",
        "name": "Kalundborg",
        "lat": 55.68,
        "lon": 11.25,
        "region": "Sjælland",
        "coast_distance_km": 5,
        "coast_direction_deg": 270,
    },
    {
        "id": "kongsted",
        "name": "Kongsted",
        "lat": 55.28,
        "lon": 12.10,
        "region": "Sjælland",
        "coast_distance_km": 15,
        "coast_direction_deg": 120,
    },
    {
        "id": "ringsted",
        "name": "Ringsted/Midtsjælland",
        "lat": 55.45,
        "lon": 11.78,
        "region": "Sjælland",
        "coast_distance_km": 25,
        "coast_direction_deg": 180,
    },
    {
        "id": "toelloese",
        "name": "Tølløse",
        "lat": 55.62,
        "lon": 11.75,
        "region": "Sjælland",
        "coast_distance_km": 20,
        "coast_direction_deg": 0,
    },
    {
        "id": "lolland",
        "name": "Lolland-Falster",
        "lat": 54.76,
        "lon": 11.87,
        "region": "Sjælland",
        "coast_distance_km": 10,
        "coast_direction_deg": 180,
    },
    # --- Bornholm ---
    {
        "id": "roenne",
        "name": "Rønne/Bornholm",
        "lat": 55.07,
        "lon": 14.75,
        "region": "Bornholm",
        "coast_distance_km": 5,
        "coast_direction_deg": 270,
    },
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


def _build_grid():
    """Build a 0.4 x 0.4 degree grid of land points over Denmark."""
    points = []
    lat = 54.5
    while lat <= 57.8:
        lon = 8.0
        while lon <= 15.2:
            if _is_land(lat, lon):
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
            lon += 0.4
        lat += 0.4
    return points


GRID_POINTS = _build_grid()

# ---------------------------------------------------------------------------
# 3. ALL_POINTS
# ---------------------------------------------------------------------------

ALL_POINTS = AIRFIELDS + GRID_POINTS
