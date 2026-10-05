"""Tests for termik.tools.forecast_watchdog.

Vagthunden flytter en forecast-kørsel til en GitHub-hostet runner, når den
selvhostede runner (maskinen derhjemme) ikke har samlet den op. Den læser
outputtet fra `gh run list --json databaseId,status,createdAt,displayTitle`.
"""

from datetime import datetime, timezone

from termik.tools import forecast_watchdog as wd

NOW = datetime(2026, 10, 5, 13, 0, tzinfo=timezone.utc)


def run(run_id, status, minutes_ago, title="Update Termik Forecast (self-hosted)"):
    created = NOW.timestamp() - minutes_ago * 60
    return {
        "databaseId": run_id,
        "status": status,
        "createdAt": datetime.fromtimestamp(created, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "displayTitle": title,
    }


def test_a_run_queued_past_the_limit_is_stuck():
    assert wd.stuck_runs([run(1, "queued", 16)], NOW) == [1]


def test_a_freshly_queued_run_is_left_alone():
    """Runneren kan være i gang med at samle den op."""
    assert wd.stuck_runs([run(1, "queued", 5)], NOW) == []


def test_the_limit_is_inclusive():
    assert wd.stuck_runs([run(1, "queued", wd.MAX_QUEUED_MINUTES)], NOW) == [1]


def test_running_and_finished_runs_are_never_stuck():
    runs = [run(1, "in_progress", 60), run(2, "completed", 60)]
    assert wd.stuck_runs(runs, NOW) == []


def test_waiting_and_pending_count_as_queued():
    runs = [run(1, "waiting", 20), run(2, "pending", 20)]
    assert wd.stuck_runs(runs, NOW) == [1, 2]


def test_a_fallback_run_is_never_cancelled():
    """GitHubs egen kø kan være langsom; at aflyse reserven ville give et
    hul uden nogen kørsel overhovedet."""
    fallback = run(1, "queued", 40, title="Update Termik Forecast (ubuntu-latest)")
    assert wd.stuck_runs([fallback], NOW) == []


def test_main_prints_stuck_ids_one_per_line(capsys):
    import io, json
    runs = [run(7, "queued", 30), run(8, "queued", 1), run(9, "completed", 90)]
    wd.main(io.StringIO(json.dumps(runs)), now=NOW)
    assert capsys.readouterr().out == "7\n"
