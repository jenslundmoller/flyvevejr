"""Configuration for termik forecast system."""

# Open-Meteo API
API_BASE_URL = "https://api.open-meteo.com/v1/forecast"
API_BATCH_SIZE = 10  # Max locations per request (low to avoid 429s)
FORECAST_DAYS = 7
TIMEZONE = "Europe/Berlin"

# Hourly parameters to fetch
HOURLY_PARAMS = [
    "temperature_2m",
    "dewpoint_2m",
    "relative_humidity_2m",
    "wind_speed_10m",
    "wind_direction_10m",
    "wind_gusts_10m",
    # Multi-level wind (80m/120m/180m)
    "wind_speed_80m",
    "wind_direction_80m",
    "wind_speed_120m",
    "wind_direction_120m",
    "wind_speed_180m",
    "wind_direction_180m",
    # Multi-level temperature
    "temperature_80m",
    "temperature_120m",
    "temperature_180m",
    # Standard parameters
    "cloud_cover",
    "cloud_cover_low",
    "cloud_cover_mid",
    "cloud_cover_high",
    "precipitation",
    "shortwave_radiation",
    "direct_radiation",
    "cape",
    "surface_pressure",
    "boundary_layer_height",
    # Pressure levels — temperatures
    "temperature_950hPa",
    "temperature_925hPa",
    "temperature_900hPa",
    "temperature_850hPa",
    "temperature_800hPa",
    "temperature_700hPa",
    "temperature_600hPa",
    # Pressure levels — geopotential heights for parcel-theory thermal-top
    "geopotential_height_950hPa",
    "geopotential_height_925hPa",
    "geopotential_height_900hPa",
    "geopotential_height_850hPa",
    "geopotential_height_800hPa",
    "geopotential_height_700hPa",
    "geopotential_height_600hPa",
    # Pressure level winds (existing — used for shear/seabreeze diagnostics)
    "wind_speed_850hPa",
    "wind_direction_850hPa",
]

# Scoring weights
WEIGHTS = {
    "lapse_rate": 0.30,
    "solar": 0.20,
    "spread": 0.15,
    "wind": 0.10,
    "gusts": 0.10,
    "temperature": 0.08,
    "precipitation": 0.07,
}

# Score labels (min_score, max_score, label)
SCORE_LABELS = [
    (9, 10, "Fremragende termik"),
    (7, 8, "God termik"),
    (5, 6, "Moderat termik"),
    (3, 4, "Svag termik"),
    (0, 2, "Ingen brugbar termik"),
]

# Dealbreaker thresholds
DEALBREAKERS = {
    "lapse_rate_inversion": {"threshold": 0.50, "max_score": 1},
    "lapse_rate_stable": {"threshold": 0.65, "max_score": 3},
    "cloud_cover": {"threshold": 87, "max_score": 2},
    "precipitation": {"threshold": 0, "max_score": 1},
    "wind_extreme": {"threshold": 35, "max_score": 2},
    "temp_cold": {"threshold": 5, "max_score": 3},
}

# Radiation gate: (threshold W/m², max score below that threshold).
# Tested against the effective radiation, not the instantaneous value,
# see scoring.effective_radiation.
# Both columns must decrease together. The gate applies every tier whose
# threshold the radiation is below and keeps the strictest cap, so the list
# order does not matter, but a non-monotone tier like (300, 8) would never
# bind: anything below 300 is also below 400, whose cap of 5 already wins.
RADIATION_GATE = [(400, 5), (250, 3), (100, 1)]

# How much of the highest radiation of the recent hours still counts.
# 0.65 is calibrated against 2026-08-08: the binding hour is 19:00, where the
# maximum over the preceding three hours is 657 W/m². The smallest usable
# factor is 400/657 = 0.609, so 0.65 clears the threshold by about 7 %.
# The two constants below are NOT independent knobs. During a monotone
# afternoon decline the maximum over the window is always its oldest hour, so
# the memory is really "factor x the radiation at t minus HOURS", and 0.65 is
# fitted to a 3-hour lag specifically. Widening the window to 4 hours has
# roughly the effect of raising the factor to 0.80: changing
# RADIATION_MEMORY_HOURS invalidates the calibration of
# RADIATION_MEMORY_FACTOR, and both must be re-fitted together.
RADIATION_MEMORY_FACTOR = 0.65
RADIATION_MEMORY_HOURS = 3

# The memory must not rescue an hour whose own radiation is below the floor.
# Without it, 21:00 with 30 W/m² is lifted from cap 1 to cap 5, after sunset.
# Deliberately equal to the lowest RADIATION_GATE threshold: the memory can
# lift an hour out of cap 3, but never out of cap 1. An hour dark enough for
# the bottom tier is too dark for the memory to have anything to say. Keep the
# two in step if either moves.
RADIATION_MEMORY_FLOOR = 100

# Sea surface temperature estimate by month (1-12)
# Based on average Danish waters temperature
SEA_TEMP_BY_MONTH = {
    1: 4, 2: 3, 3: 4, 4: 6, 5: 10, 6: 14,
    7: 17, 8: 18, 9: 16, 10: 12, 11: 9, 12: 6,
}

# Output paths (relative to project root)
OUTPUT_DIR = "termik/output"
DATA_DIR = "termik/output/data"
