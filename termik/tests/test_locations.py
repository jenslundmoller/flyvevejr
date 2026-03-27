from termik.locations import AIRFIELDS, GRID_POINTS, ALL_POINTS


def test_airfields_is_list_of_dicts():
    assert isinstance(AIRFIELDS, list)
    assert len(AIRFIELDS) >= 25


def test_airfield_has_required_fields():
    for af in AIRFIELDS:
        assert "id" in af
        assert "name" in af
        assert "lat" in af
        assert "lon" in af
        assert "region" in af
        assert "coast_distance_km" in af
        assert "coast_direction_deg" in af


def test_airfield_coordinates_in_denmark():
    for af in AIRFIELDS:
        assert 54.4 < af["lat"] < 58.0, f"{af['id']} lat out of range"
        assert 7.5 < af["lon"] < 15.5, f"{af['id']} lon out of range"


def test_grid_points_cover_denmark():
    assert isinstance(GRID_POINTS, list)
    assert len(GRID_POINTS) >= 40
    lats = [p["lat"] for p in GRID_POINTS]
    lons = [p["lon"] for p in GRID_POINTS]
    assert min(lats) < 55.0
    assert max(lats) > 57.0
    assert min(lons) < 9.0
    assert max(lons) > 12.0


def test_grid_point_has_required_fields():
    for gp in GRID_POINTS:
        assert "id" in gp
        assert "lat" in gp
        assert "lon" in gp
        assert "coast_distance_km" in gp
        assert "coast_direction_deg" in gp
        assert gp["id"].startswith("grid_")


def test_all_points_combines_both():
    assert len(ALL_POINTS) == len(AIRFIELDS) + len(GRID_POINTS)


def test_arnborg_exists():
    ids = [af["id"] for af in AIRFIELDS]
    assert "arnborg" in ids
    arnborg = next(af for af in AIRFIELDS if af["id"] == "arnborg")
    assert 55.8 < arnborg["lat"] < 56.0
    assert 8.9 < arnborg["lon"] < 9.2
    assert arnborg["coast_distance_km"] > 50


def test_kongsted_is_coastal():
    kongsted = next(af for af in AIRFIELDS if af["id"] == "kongsted")
    assert kongsted["coast_distance_km"] < 25
