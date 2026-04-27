# Referat — Solindstrålings-gate i termik-scoring

**Dato:** 2026-04-27
**Branch:** main
**Commit:** `d7f6bd6`

## Udgangspunkt
Brugeren observerede at Øst-Sjællands Flyveklub (Kongsted) fik **score 5/10 ("Moderat termik")** kl. 21:00 i dag — efter solnedgang. Spørgsmål: tager scoringen højde for solopgang/-nedgang og solens indstrålingsgrad (45°-reglen)?

## Diagnose
Gennemgang af `termik/scoring.py` viste:
- Ingen eksplicit solhøjde- eller stråling-gate.
- `score_solar()` bruger `shortwave_radiation`, men kun som 20% af vægten.
- For Kongsted kl. 21:00 (stråling ~0 W/m²) gav de andre faktorer (spread=10, vind=7, gusts=10, precip=10) stadig nok point til en score på 5.0, kun bremset tilfældigt af lapse-rate-dealbreakeren ved 0.69 < 0.70.

## Løsningsvalg
Diskuteret to muligheder:
1. **Strålings-gate** — cap baseret på faktisk `shortwave_radiation` (W/m²).
2. **Solhøjde-gate** — cap baseret på beregnet solelevation.

Brugeren valgte **mulighed 1**, fordi den afspejler virkeligheden direkte (stråling tager allerede højde for både solhøjde og skydække).

## Implementering
Tilføjet ny parameter `shortwave_radiation` til `apply_dealbreakers()` i `termik/scoring.py:246` med tre tærskler:

| Stråling | Cap |
|---|---|
| < 100 W/m² | 1 |
| < 250 W/m² | 3 |
| < 400 W/m² | 5 |
| ≥ 400 W/m² | ingen |

`compute_thermal_score()` videresender den eksisterende `shortwave_radiation`-værdi til dealbreaker-funktionen.

## Verifikation
Kongsted i dag efter ændringen:

| Time | Før | Efter |
|---|---|---|
| 17:00 | — | 6.4 |
| 18:00 | — | 4.7 |
| 19:00 | — | 3.0 |
| 20:00 | — | 1.0 |
| **21:00** | **5.0** | **1.0** |

## Tests
Tilføjet 7 nye tests i `termik/tests/test_scoring.py`:
- 6 unit-tests for hver tærskel + grænseværdier + bagudkompatibilitet (`None`).
- 1 integrationstest (`test_scenario_evening_after_sunset`) baseret direkte på Kongsted kl. 21:00.

**Resultat:** alle 148 tests består.

## Commit
```
d7f6bd6 scoring: add solar radiation gate to prevent post-sunset false positives
```
2 filer ændret, 73 linjer tilføjet. Øvrige urelaterede ændringer i working tree blev ikke rørt.
