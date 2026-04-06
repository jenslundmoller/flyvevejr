from termik.comments import generate_comment


def test_comment_includes_stability():
    comment = generate_comment(
        lapse_rate=1.1, spread=10, skybase_m=1250, wind_kt=12, wind_gusts_kt=18,
        cloud_cover=30, cape=300, precipitation=0,
        seabreeze_risk=0, pressure_trend=1.0, score=8.5,
    )
    assert "Labil" in comment


def test_comment_includes_skybase():
    comment = generate_comment(
        lapse_rate=0.9, spread=10, skybase_m=1250, wind_kt=10, wind_gusts_kt=15,
        cloud_cover=30, cape=200, precipitation=0,
        seabreeze_risk=0, pressure_trend=0, score=6.0,
    )
    assert "1250" in comment


def test_comment_warns_seabreeze():
    comment = generate_comment(
        lapse_rate=0.9, spread=10, skybase_m=1250, wind_kt=8, wind_gusts_kt=12,
        cloud_cover=20, cape=200, precipitation=0,
        seabreeze_risk=2, pressure_trend=0, score=6.0,
    )
    assert "brise" in comment.lower()


def test_comment_warns_overdevelopment():
    comment = generate_comment(
        lapse_rate=1.2, spread=8, skybase_m=1000, wind_kt=10, wind_gusts_kt=15,
        cloud_cover=40, cape=1200, precipitation=0,
        seabreeze_risk=0, pressure_trend=0, score=8.0,
    )
    assert "overudvikling" in comment.lower() or "Cb" in comment


def test_comment_warns_effective_wind_high():
    """effective = 15 + 17.5 = 32.5 → should warn experienced only."""
    comment = generate_comment(
        lapse_rate=1.1, spread=10, skybase_m=1250, wind_kt=15, wind_gusts_kt=35,
        cloud_cover=30, cape=300, precipitation=0,
        seabreeze_risk=0, pressure_trend=0, score=3.0,
    )
    assert "erfarne" in comment.lower()

def test_comment_warns_effective_wind_reduced():
    """effective = 18 + 10 = 28 → should warn reduced conditions."""
    comment = generate_comment(
        lapse_rate=1.0, spread=10, skybase_m=1250, wind_kt=18, wind_gusts_kt=20,
        cloud_cover=30, cape=200, precipitation=0,
        seabreeze_risk=0, pressure_trend=0, score=5.0,
    )
    assert "nedsat" in comment.lower()


def test_comment_warns_strong_wind():
    comment = generate_comment(
        lapse_rate=1.1, spread=10, skybase_m=1250, wind_kt=28, wind_gusts_kt=35,
        cloud_cover=40, cape=500, precipitation=0,
        seabreeze_risk=0, pressure_trend=1.0, score=7.0,
    )
    assert "vind" in comment.lower() or "turbulent" in comment.lower()


def test_comment_stable_atmosphere():
    comment = generate_comment(
        lapse_rate=0.5, spread=20, skybase_m=2500, wind_kt=5, wind_gusts_kt=8,
        cloud_cover=5, cape=50, precipitation=0,
        seabreeze_risk=0, pressure_trend=0, score=3.0,
    )
    assert "Stabil" in comment or "stabil" in comment


def test_comment_rain():
    comment = generate_comment(
        lapse_rate=0.8, spread=5, skybase_m=625, wind_kt=10, wind_gusts_kt=15,
        cloud_cover=90, cape=0, precipitation=2.0,
        seabreeze_risk=0, pressure_trend=-1.0, score=1.0,
    )
    assert "nedbør" in comment.lower() or "regn" in comment.lower()


def test_comment_is_string_with_reasonable_length():
    comment = generate_comment(
        lapse_rate=1.0, spread=10, skybase_m=1250, wind_kt=10, wind_gusts_kt=15,
        cloud_cover=30, cape=200, precipitation=0,
        seabreeze_risk=0, pressure_trend=0, score=7.0,
    )
    assert isinstance(comment, str)
    assert len(comment) > 10
    assert len(comment) < 300


def test_comment_backside_weather():
    comment = generate_comment(
        lapse_rate=1.1, spread=12, skybase_m=1500, wind_kt=12, wind_gusts_kt=18,
        cloud_cover=30, cape=400, precipitation=0,
        seabreeze_risk=0, pressure_trend=3.0, score=9.0,
    )
    assert "agside" in comment.lower() or "cumulus" in comment.lower()


def test_comment_dry_thermal():
    comment = generate_comment(
        lapse_rate=0.8, spread=22, skybase_m=2750, wind_kt=8, wind_gusts_kt=12,
        cloud_cover=5, cape=100, precipitation=0,
        seabreeze_risk=0, pressure_trend=0, score=5.0,
    )
    assert "ørtermik" in comment.lower() or "kondensation" in comment.lower()
