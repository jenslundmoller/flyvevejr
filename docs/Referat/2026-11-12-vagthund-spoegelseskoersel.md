# 2026-11-12: Vagthunden fejlede på en spøgelseskørsel

## Hvad skete

Fra 11/11 kl. 21:05 UTC fejlede hver eneste kørsel af `forecast-fallback.yml`
(17 røde 12/11 frem til 13:13 UTC). Selve prognosen kørte fint på OMV-runneren
(12/11 kl. 05:20, 08:23 og 11:20 UTC, alle grønne og deployet).

Årsag: kørsel **43097108052** af `update-forecast.yml`, oprettet 11/11 kl.
20:36 UTC (den planlagte 20:15-kørsel, forsinket af GitHub), blev hængende
hos GitHub:

- `status: queued`, `conclusion: null`, **0 jobs**, titlen uden "(self-hosted)"
  (run-name blev aldrig evalueret).
- `gh run cancel`: "Cannot cancel a workflow run that is completed".
- `POST .../force-cancel`: 409 "Cannot cancel a workflow run that has not been
  queued yet".
- `gh run delete`: 403.

Vagthunden meldte den som hængende hver halve time, `gh run cancel` fejlede
under `bash -e`, og trinnet stoppede med exit 1 før reservekørslen. Der blev
derfor ikke brugt ekstra Open-Meteo-kald, men vagthunden var i praksis slået
fra, så længe kørslen lå blandt de seneste 20 (cirka 3 dage).

Konsekvens: prognosen kl. 20:15 UTC 11/11 udeblev. Siden viste 17:20-prognosen
til 05:20 UTC 12/11.

## Rettelse

- `forecast_watchdog.py`: kørsler over `MAX_AGE_HOURS = 6` gamle ignoreres.
  Den næste planlagte kørsel (hver 3. time) har alligevel overtaget.
- `forecast-fallback.yml`: en mislykket aflysning giver en advarsel og springes
  over. Der startes kun en reservekørsel, hvis mindst én aflysning lykkedes;
  ellers ville en kørsel GitHub ikke vil aflyse udløse ~1.000 Open-Meteo-kald
  hver halve time.
- To nye tests (9 i `test_forecast_watchdog.py`, 511 i alt).

Afprøvet mod den aktuelle kørselsliste 12/11: ingen kørsler meldes som
hængende. Spøgelset ligger stadig hos GitHub og kan ikke fjernes af os.
