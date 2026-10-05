"""Tests for termik.tools.probe_throttle.

Proben måler, hvor længe Open-Meteo holder igen over for GitHub-runnerne
efter et vellykket kald (punkt 13 i overdragelsen 2026-10-05). Netværket er
erstattet af en falsk klokke og en falsk fetch, så testene kører på
millisekunder og aldrig rammer API'et.
"""

from termik.tools import probe_throttle as pt


class FakeClock:
    def __init__(self):
        self.now = 0.0
        self.sleeps = []

    def monotonic(self):
        return self.now

    def sleep(self, seconds):
        self.sleeps.append(seconds)
        self.now += seconds


def make_fetch(clock, outcomes, duration_ok=0.5, duration_hang=30.0):
    """outcomes: iterable of True/False, one per call. Logs call start times."""
    outcomes = iter(outcomes)
    starts = []

    def fetch(url):
        starts.append(clock.now)
        ok = next(outcomes)
        clock.now += duration_ok if ok else duration_hang
        return ok

    fetch.starts = starts
    return fetch


def test_plan_has_every_arm_reps_times_in_shuffled_order():
    plan = pt.plan_trials(gaps=[20, 60], reps=3, seed=1)
    assert sorted(plan, key=str) == sorted([20, 60, "hang30"] * 3, key=str)
    assert plan != sorted(plan, key=str)  # seedet blanding, ikke grupperet


def test_plan_is_reproducible_for_a_seed():
    assert pt.plan_trials([20, 40], 2, seed=7) == pt.plan_trials([20, 40], 2, seed=7)


def test_gap_trial_starts_second_call_gap_seconds_after_first_started():
    clock = FakeClock()
    fetch = make_fetch(clock, [True, False])
    result = pt.run_trial(40, fetch, ["u1", "u2"], clock)
    assert fetch.starts[1] - fetch.starts[0] == 40
    assert result["arm"] == 40
    assert result["ok"] is False
    assert result["since_success_s"] == 40


def test_trial_waits_out_a_failing_first_call_before_measuring():
    """Uden et vellykket første kald er der intet at måle afstanden fra."""
    clock = FakeClock()
    fetch = make_fetch(clock, [False, True, True])
    result = pt.run_trial(20, fetch, ["u1", "u2", "u3"], clock)
    assert pt.FIRST_CALL_RETRY_PAUSE in clock.sleeps
    assert fetch.starts[2] - fetch.starts[1] == 20
    assert result["ok"] is True
    assert result["first_call_attempts"] == 2


def test_trial_gives_up_when_the_first_call_never_succeeds():
    clock = FakeClock()
    fetch = make_fetch(clock, [False] * pt.FIRST_CALL_MAX_ATTEMPTS)
    result = pt.run_trial(20, fetch, ["u"], clock)
    assert result["ok"] is None
    assert len(fetch.starts) == pt.FIRST_CALL_MAX_ATTEMPTS


def test_hang30_retries_30s_after_the_hang_ended():
    clock = FakeClock()
    fetch = make_fetch(clock, [True, False, True])
    result = pt.run_trial("hang30", fetch, ["u1", "u2", "u3"], clock)
    assert fetch.starts[1] - fetch.starts[0] == pt.HANG30_FIRST_GAP
    assert fetch.starts[2] - (fetch.starts[1] + 30.0) == 30
    assert result["hung"] is True
    assert result["ok"] is True
    assert result["since_success_s"] == fetch.starts[2] - fetch.starts[0]


def test_hang30_without_a_hang_has_nothing_to_retry():
    clock = FakeClock()
    fetch = make_fetch(clock, [True, True])
    result = pt.run_trial("hang30", fetch, ["u1", "u2"], clock)
    assert result["hung"] is False
    assert result["ok"] is None
    assert len(fetch.starts) == 2


def test_run_resets_between_trials():
    clock = FakeClock()
    fetch = make_fetch(clock, [True, True] * 2)
    results = pt.run_probe([20, 20], fetch, ["u"], clock, log=lambda r: None)
    assert len(results) == 2
    assert clock.sleeps.count(pt.RESET_SECONDS) == 1


def test_summary_counts_failures_per_arm_and_skips_unmeasured():
    rows = [
        {"arm": 20, "ok": False}, {"arm": 20, "ok": True},
        {"arm": 100, "ok": True}, {"arm": 100, "ok": None},
    ]
    assert pt.summarize(rows) == {"20": (2, 1), "100": (1, 0)}
