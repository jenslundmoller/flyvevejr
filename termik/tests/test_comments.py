from termik.comments import generate_comment


def test_comment_includes_stability():
    comment = generate_comment(
        lapse_rate=1.1, spread=10, skybase_m=1250, wind_kt=12, wind_gusts_kt=18,
        cloud_cover=30, cape=300, precipitation=0,
        seabreeze_risk=0, pressure_trend=1.0, score=8.5,
    )
    assert "Labil" in comment


def test_comment_omits_skybase_number():
    # Skybasen står i popup'ens felter og højdeakse; teksten gentager den
    # ikke (popup-redesign 2026-08-26)
    comment = generate_comment(
        lapse_rate=0.9, spread=10, skybase_m=1250, wind_kt=10, wind_gusts_kt=15,
        cloud_cover=30, cape=200, precipitation=0,
        seabreeze_risk=0, pressure_trend=0, score=6.0,
    )
    assert "1250" not in comment


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
    """effective = 20 + 14.5 = 34.5 → should warn experienced only."""
    comment = generate_comment(
        lapse_rate=1.1, spread=10, skybase_m=1250, wind_kt=20, wind_gusts_kt=29,
        cloud_cover=30, cape=300, precipitation=0,
        seabreeze_risk=0, pressure_trend=0, score=3.0,
    )
    assert "erfarne" in comment.lower()

def test_comment_warns_absolute_gusts_35():
    """Gusts >= 35 → should warn can't fly."""
    comment = generate_comment(
        lapse_rate=1.1, spread=10, skybase_m=1250, wind_kt=15, wind_gusts_kt=35,
        cloud_cover=30, cape=300, precipitation=0,
        seabreeze_risk=0, pressure_trend=0, score=1.0,
    )
    assert "kan ikke flyves" in comment.lower()

def test_comment_warns_absolute_gusts_30():
    """Gusts >= 30 → should warn strong reduction."""
    comment = generate_comment(
        lapse_rate=1.0, spread=10, skybase_m=1250, wind_kt=12, wind_gusts_kt=31,
        cloud_cover=30, cape=200, precipitation=0,
        seabreeze_risk=0, pressure_trend=0, score=2.0,
    )
    assert "reduktion" in comment.lower()

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


def test_comment_warns_wind_shear():
    """High wind shear should produce a warning."""
    comment = generate_comment(
        lapse_rate=1.1, spread=10, skybase_m=1250, wind_kt=8, wind_gusts_kt=14,
        cloud_cover=30, cape=300, precipitation=0,
        seabreeze_risk=0, pressure_trend=0, score=7.0,
        wind_shear_kt=18,
    )
    assert "vindforskydning" in comment.lower() or "shear" in comment.lower()


def test_comment_omits_bl_height_number():
    """Blandingslaget vises i felterne; teksten gentager ikke tallet."""
    comment = generate_comment(
        lapse_rate=1.0, spread=10, skybase_m=1250, wind_kt=10, wind_gusts_kt=15,
        cloud_cover=30, cape=200, precipitation=0,
        seabreeze_risk=0, pressure_trend=0, score=7.0,
        boundary_layer_height=1500,
    )
    assert "1500" not in comment


def test_comment_no_new_params_still_works():
    """Existing calls without new params still work."""
    comment = generate_comment(
        lapse_rate=1.0, spread=10, skybase_m=1250, wind_kt=10, wind_gusts_kt=15,
        cloud_cover=30, cape=200, precipitation=0,
        seabreeze_risk=0, pressure_trend=0, score=7.0,
    )
    assert isinstance(comment, str)
    assert len(comment) > 10


# --- Ny tekststruktur (popup-redesign 2026-08-26): bindende faktor først ---

def _base_kwargs(**overrides):
    kwargs = dict(
        lapse_rate=0.99, spread=10.6, skybase_m=1325, wind_kt=11.5,
        wind_gusts_kt=21.2, cloud_cover=58, cape=0, precipitation=0,
        seabreeze_risk=0, pressure_trend=0, score=7.4,
    )
    kwargs.update(overrides)
    return kwargs


def test_comment_leads_with_binding_factor_lcl():
    comment = generate_comment(**_base_kwargs(
        thermal_top_m=1077, thermal_top_limited_by="lcl",
    ))
    assert comment.startswith("Toppen begrænses af skybasen")
    assert "1100 m" in comment


def test_comment_leads_with_binding_factor_ti_zero():
    comment = generate_comment(**_base_kwargs(
        thermal_top_m=1423, thermal_top_limited_by="ti_zero",
    ))
    assert "temperaturen i højden" in comment
    assert "1400 m" in comment


def test_comment_mentions_cirrus_banks():
    comment = generate_comment(**_base_kwargs(
        thermal_top_m=1077, thermal_top_limited_by="lcl", cloud_cover_high=65,
    ))
    assert "cirrus" in comment.lower()


def test_comment_mentions_wind_increase_aloft():
    comment = generate_comment(**_base_kwargs(
        thermal_top_m=1077, thermal_top_limited_by="lcl",
        cloud_cover_high=0, wind_speed_180m_kt=14.9,
    ))
    assert "15 kt i højden" in comment


def test_comment_drops_redundant_field_numbers():
    # Skybase og blandingslag står nu visuelt i popup'en; teksten må ikke
    # gentage felt-tallene
    comment = generate_comment(**_base_kwargs(
        thermal_top_m=1077, thermal_top_limited_by="lcl",
        boundary_layer_height=1095,
    ))
    assert "1325" not in comment
    assert "Blandingslag" not in comment


def test_comment_has_no_em_dash():
    for kwargs in (
        _base_kwargs(),
        _base_kwargs(score=1.0, lapse_rate=0.4),
        _base_kwargs(precipitation=1.2, score=1.0),
        _base_kwargs(thermal_top_m=1077, thermal_top_limited_by="lcl",
                     cloud_cover_high=65, wind_speed_180m_kt=14.9),
    ):
        assert "—" not in generate_comment(**kwargs)


def test_comment_low_score_still_explains_stability():
    comment = generate_comment(**_base_kwargs(score=1.0, lapse_rate=0.45))
    assert "Inversion" in comment


def test_comment_without_thermal_top_falls_back_to_stability():
    comment = generate_comment(**_base_kwargs())
    assert "labil" in comment.lower()
