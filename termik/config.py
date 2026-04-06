"""Configuration for termik forecast system."""

# Open-Meteo API
API_BASE_URL = "https://api.open-meteo.com/v1/forecast"
API_BATCH_SIZE = 50  # Max locations per request
FORECAST_DAYS = 3
TIMEZONE = "Europe/Berlin"

# Hourly parameters to fetch
HOURLY_PARAMS = [
    "temperature_2m",
    "dewpoint_2m",
    "relative_humidity_2m",
    "wind_speed_10m",
    "wind_direction_10m",
    "wind_gusts_10m",
    "cloud_cover",
    "cloud_cover_low",
    "cloud_cover_mid",
    "cloud_cover_high",
    "precipitation",
    "shortwave_radiation",
    "cape",
    "surface_pressure",
    "temperature_850hPa",
    "temperature_700hPa",
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

# Sea surface temperature estimate by month (1-12)
# Based on average Danish waters temperature
SEA_TEMP_BY_MONTH = {
    1: 4, 2: 3, 3: 4, 4: 6, 5: 10, 6: 14,
    7: 17, 8: 18, 9: 16, 10: 12, 11: 9, 12: 6,
}

# Output paths (relative to project root)
OUTPUT_DIR = "termik/output"
DATA_DIR = "termik/output/data"
