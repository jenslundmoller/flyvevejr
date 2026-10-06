---
description: Drift: workflows, den selvhostede runner på OMV og Open-Meteo-kvoten
paths:
  - ".github/workflows/**"
  - "termik/tools/**"
  - "termik/cron_setup.sh"
---

# Drift

## Workflows

| Workflow | Gør |
|---|---|
| `update-forecast.yml` | Cron `15 5-20/3 * * *` UTC på `[self-hosted, flyvevejr]` (OMV). Kører `python -m termik`, committer `termik/output/data/`, pusher med op til 3 rebase-forsøg, starter deploy via `termik/tools/dispatch_workflow.py` |
| `forecast-fallback.yml` | Hver halve time på GitHub: en kørsel i kø over 15 min aflyses og erstattes af én på `ubuntu-latest`. Logik i `termik/tools/forecast_watchdog.py` |
| `rerun-failed-forecast.yml` | Genstarter en fejlet kørsel (op til 3 forsøg). Kan ikke reparere en push-race |
| `deploy-pages.yml` | Push til `termik/output/**` eller dispatch: deployer siden |

`termik/tests/test_workflow_schedule.py` tester kørselsplanen. Ændres cron,
ændres testen med.

## Sikkerhed (repoet er offentligt)

- **Ingen `pull_request`- eller `pull_request_target`-trigger**, i nogen
  workflow. En fork ville ellers køre kode på OMV.
- Kun `actions/*` og `github/*`. Ingen tredjeparts-actions.
- Runneren har ikke `gh` eller `curl`; brug Python og `requests` i trin der
  kører på OMV.
- Hemmeligheder kun via `secrets.*`, aldrig i loggen.

## OMV

- Maskinen: 10.71.21.238, Debian 13, Python 3.13, login `omvadmin` med
  password (ingen SSH-nøgle til Claude). Runner i `/opt/gh-runner` som
  systembrugeren `gh-runner`, unit
  `actions.runner.jenslundmoller-flyvevejr.omv.service`, hærdet med en
  systemd-drop-in.
- **Kommandoer til OMV kører brugeren selv**, i en rigtig terminal (`!` i
  Claude Code har ingen tty, så password-prompten fejler). Giv ét nummereret
  trin pr. kommando, sig hvilken maskine, sig hvilket output der forventes,
  og sig når en kommando skal køres uændret.
- **Ingen heredocs** i SSH-sessioner (de hænger på `>`). Brug én linje:
  `printf '%s\n' ... | sudo tee fil`.
- Tokens hentes af brugeren i egen terminal (`read -rs`) og holdes ude af
  samtalen.
- Brugerens driftsdokument for OMV (HTML, "OMV-webhosting-reference")
  opdateres når noget nyt kommer til at køre dér.

## Open-Meteo

- Gratis, ingen nøgle, **10.000 kald/døgn pr. IP**. Hver påbegyndt 10.
  variabel tæller som ét kald pr. punkt. Produktionen bruger ~1.000 pr.
  kørsel, ~6.000 i døgnet. Hjemme-IP'en deler kvoten med analyser.
- Open-Meteo drosler GitHubs runnere (halvdelen af kaldene hang 30 s); fra
  OMV hænger intet. Se `docs/Referat/2026-09-02-api-robusthed.md`.
