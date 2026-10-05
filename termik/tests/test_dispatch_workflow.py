"""Tests for termik.tools.dispatch_workflow.

Forecast-kørslen starter deploy-pages.yml efter et datacommit. Det skete med
`gh workflow run`, men den selvhostede runner på OMV har ikke gh; kaldet går
derfor direkte til GitHubs REST-API med requests, som venv'et har i forvejen.
"""

import pytest
import requests

from termik.tools import dispatch_workflow as dw


class FakeResponse:
    def __init__(self, status):
        self.status_code = status
        self.text = f"status {status}"


def recorder(statuses):
    calls = []
    statuses = iter(statuses)

    def post(url, **kwargs):
        calls.append((url, kwargs))
        status = next(statuses)
        if isinstance(status, Exception):
            raise status
        return FakeResponse(status)

    post.calls = calls
    return post


def test_dispatch_posts_the_ref_to_the_workflow_endpoint():
    post = recorder([204])
    dw.dispatch("owner/repo", "deploy-pages.yml", "main", "tok", post=post, sleep=lambda s: None)
    url, kwargs = post.calls[0]
    assert url == "https://api.github.com/repos/owner/repo/actions/workflows/deploy-pages.yml/dispatches"
    assert kwargs["json"] == {"ref": "main"}
    assert kwargs["headers"]["Authorization"] == "Bearer tok"
    assert kwargs["timeout"] > 0


def test_dispatch_retries_then_succeeds():
    post = recorder([500, requests.exceptions.ConnectionError("x"), 204])
    slept = []
    dw.dispatch("o/r", "w.yml", "main", "t", post=post, sleep=slept.append)
    assert len(post.calls) == 3
    assert slept == [10, 20]


def test_dispatch_gives_up_after_three_attempts():
    post = recorder([500, 502, 503])
    with pytest.raises(RuntimeError):
        dw.dispatch("o/r", "w.yml", "main", "t", post=post, sleep=lambda s: None)
    assert len(post.calls) == 3


def test_main_reads_repo_ref_and_token_from_the_environment(monkeypatch):
    seen = {}
    monkeypatch.setenv("GITHUB_REPOSITORY", "o/r")
    monkeypatch.setenv("REF", "main")
    monkeypatch.setenv("GH_TOKEN", "t")
    monkeypatch.setattr(dw, "dispatch", lambda *a, **k: seen.setdefault("args", a))
    dw.main(["deploy-pages.yml"])
    assert seen["args"] == ("o/r", "deploy-pages.yml", "main", "t")
