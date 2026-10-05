import pytest


def pytest_configure(config):
    config.addinivalue_line(
        "markers", "real_sea_fetch: run the real fetch_sea_temps (with its own stubs)"
    )


@pytest.fixture(autouse=True)
def _no_marine_calls(request, monkeypatch):
    """process_all_points fetches sea temperatures before the forecast
    batches; tests that stub only the batches must not reach the marine API.
    An empty answer is the documented failure path (climatology fallback)."""
    if request.node.get_closest_marker("real_sea_fetch"):
        return
    import termik.fetch_weather as fetch_weather
    monkeypatch.setattr(fetch_weather, "fetch_sea_temps", lambda *a, **k: {})
