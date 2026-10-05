#!/usr/bin/env python3
"""Start a workflow_dispatch workflow through GitHub's REST API.

Erstatter `gh workflow run` i update-forecast.yml: den selvhostede runner på
OMV har ikke gh-CLI'en, men venv'et har requests. Et push med GITHUB_TOKEN
starter ikke andre workflows, så deploy-pages.yml skal startes eksplicit;
workflow_dispatch er undtaget fra den regel.

Brug: GH_TOKEN=... REF=main GITHUB_REPOSITORY=owner/repo \\
      python -m termik.tools.dispatch_workflow deploy-pages.yml
"""

import os
import sys
import time

import requests

ATTEMPTS = 3
TIMEOUT_SECONDS = 30


def dispatch(repo, workflow, ref, token, post=requests.post, sleep=time.sleep):
    url = f"https://api.github.com/repos/{repo}/actions/workflows/{workflow}/dispatches"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    last = None
    for attempt in range(1, ATTEMPTS + 1):
        try:
            response = post(url, json={"ref": ref}, headers=headers, timeout=TIMEOUT_SECONDS)
            if response.status_code == 204:
                print(f"{workflow} startet på {ref} (forsøg {attempt})")
                return
            last = f"HTTP {response.status_code}: {response.text[:200]}"
        except requests.exceptions.RequestException as e:
            last = str(e)
        if attempt < ATTEMPTS:
            print(f"Forsøg {attempt} fejlede ({last}), prøver igen om {attempt * 10} s")
            sleep(attempt * 10)
    raise RuntimeError(f"Kunne ikke starte {workflow} efter {ATTEMPTS} forsøg: {last}")


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    dispatch(os.environ["GITHUB_REPOSITORY"], argv[0], os.environ["REF"], os.environ["GH_TOKEN"])


if __name__ == "__main__":
    main()
