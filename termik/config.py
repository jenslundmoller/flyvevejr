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

# The memory keys on how far the radiation fell, never on why. A cloud deck
# arriving mid-afternoon produces the same signature as sunset and used to get
# the same rescue: measured end to end, a mid-level deck that crushed the
# radiation from 720 to 150 W/m² scored 8.4 ("God termik") on the memory's
# credit, where the same hour without a memory scored 3.0. These two constants
# close that. The memory is blocked when the sky is BOTH substantially covered
# now AND materially clearer at some point in the memory window.
#
# Both conditions are needed, and each is calibrated on a measured hour:
#
# COVER makes the guard about attenuation rather than about any rise at all.
# At Tønder on 2026-08-08 20:00 the cover rose from 2 to 34 % while the
# radiation fell to under a third of the window's peak. A third of the sky
# cannot be what crushed it, that hour is sunset, and it keeps its memory.
#
# RISE keeps the guard off a sky that was already covered, where the radiation
# was never high enough for the memory to lift anything anyway, and off the
# ordinary hour-to-hour churn of the cloud field.
#
# Calibrated against 2026-08-08, the evening the memory exists to serve, where
# cover fell across the afternoon (57, 61, 48, 32, 31, 26). At 18:00 and 19:00
# the cover of 32 and 31 is far below COVER and the change against the
# clearest hour of the window is negative, so both conditions fail with a wide
# margin. Across 30 airfields x 11 days the guard blocks 27 of the 255 hours
# where the memory is what sets the cap, and every one of those has 70 to 86 %
# cover with the radiation cut to between 18 and 58 % of the window's peak.
#
# Read against the raw cloud_cover total, not the layer-weighted cover
# score_solar uses. Deliberate, and measured: on the calibration evening the
# layer-weighted value ROSE 13.6 points while the total fell 16, because the
# low cloud building through the afternoon was thermal cumulus. Weighting the
# layers here would read a good day's own cumulus as an arriving deck and shut
# the memory off on exactly the days it exists for.
#
# Coupled to RADIATION_MEMORY_HOURS: the cloud window is the radiation window,
# since the question is only ever asked about the hours the memory credits.
# Both conditions are evaluated against the clearest hour in that window,
# so a single cloudy hour inside it cannot mask a deck.
CLOUD_ARRIVAL_COVER = 70
CLOUD_ARRIVAL_RISE = 25

# The memory must not rescue an hour whose own radiation is below the floor.
# Without it, 21:00 with 30 W/m² is lifted from cap 1 to cap 5, after sunset.
# Deliberately equal to the lowest RADIATION_GATE threshold: the memory can
# lift an hour out of cap 3, but never out of cap 1. An hour dark enough for
# the bottom tier is too dark for the memory to have anything to say. Keep the
# two in step if either moves.
RADIATION_MEMORY_FLOOR = 100

# Mixed-layer depth gate: a threshold in metres, and the score ceiling that
# applies below it.
# Thermals need vertical room. A boundary layer under this depth leaves a
# working band too thin to stay up in, whatever the radiation says.
#
# Calibrated against Ringsted on 2026-08-09 at 18:00, the worst prediction of
# the two reference days: 429 W/m² with the sky cleared to 15 % cover and no
# cirrus, so neither the radiation gate nor a cloud cap reaches the hour, and
# published "God termik" on a day the pilot found nothing at all. Boundary
# layer height is the only fetched field that separates it: 780 m against
# 1250 m at the same hour on the Saturday the pilot flew.
#
# The threshold has measured bounds on both sides and little room between
# them: above 780 m or the Sunday evening is not caught, at most 1000 m or the
# Saturday evening at 19:00 comes down with it. 900 sits between the two with
# about 15 % clearance below and 10 % above.
#
# It must NOT be raised past 1210. Depth does not separate the two days from
# 11:00 to 13:00 (1270, 1515, 1600 against 1210, 1280, 1295), and a threshold
# that reached up there would only appear to fix the midday half of the
# calibration while dragging the good day down by the same amount. That half
# belongs to the cirrus shield.
#
# What this gate can claim is deliberately narrow. Measured across 30
# airfields x 11 days, a midday hour under a deck thick enough to cut the
# radiation below 250 W/m² still has a boundary layer of 900 m or more 41 % of
# the time, up to 1500 m, while 25 % of full-sun midday hours sit below 900 m.
# Depth therefore cannot detect that cloud has killed the convection, which is
# what cloud_deck_arrived above is for. It detects only a mixing layer that is
# genuinely too shallow to work in, whatever made it shallow.
#
# The cap of 5 matches the radiation gate's top tier: a hard ceiling at
# "Moderat termik", not a claim that the hour is dead.
SHALLOW_BOUNDARY_LAYER_M = 900
SHALLOW_BOUNDARY_LAYER_MAX_SCORE = 5

# Sea surface temperature estimate by month (1-12)
# Based on average Danish waters temperature
SEA_TEMP_BY_MONTH = {
    1: 4, 2: 3, 3: 4, 4: 6, 5: 10, 6: 14,
    7: 17, 8: 18, 9: 16, 10: 12, 11: 9, 12: 6,
}

# Output paths (relative to project root)
OUTPUT_DIR = "termik/output"
DATA_DIR = "termik/output/data"
