# Sessionsrapport 2. september 2026: robusthed mod dårlige API-svar

Sessionen begyndte med "de seneste kørsler i GitHub har fejlet" og endte med
fire lag forsvar mod ustabilitet hos Open-Meteo, verificeret i en rigtig
hændelse under to timer efter udrulningen. Undervejs blev det klart at den
oplagte rettelse på egen hånd ville have gjort tingene værre. En designet
udgave findes som Claude-artifact (privat link hos Jens):
https://claude.ai/code/artifact/52372bb8-ea3c-43db-9808-a7094df96221

## Udgangspunkt: en grøn liste der løj

Actions-listen så grøn ud, og fejlfiltret viste intet nyere end 26/8. Men
`Rerun Failed Forecast` var udløst to gange kl. 09:39 og 09:40, og det sker
kun når forecast-kørslen fejler.

Kørsel `33614418624` (09:29 UTC) havde `run_attempt: 3`. Forsøg 1 og 2 fejlede
begge i trinnet `Run forecast`; forsøg 3 lykkedes. Fordi vagthunden reparerede
den, blev den endelige status `success`, og fejlen forsvandt ud af
fejlfiltret. Det er derfor listen kunne se sund ud, mens kørslerne fejlede.

De ældre fejl (26/8, 14/8, 28/5) var en anden sag: de lå alle i trinnet
`Commit and push updated data`, altså push-racet der blev lukket af `6c22a5c`.
Den rettelse holder; ingen push-fejl siden.

## Årsagen

Open-Meteo svarede HTTP 200 med tomt body. `response.json()` kastede
`requests.exceptions.JSONDecodeError`, som hverken er `HTTPError`,
`ConnectionError` eller `Timeout`. Den slap derfor uden om **begge**
fejlhåndteringer: retry-loopet i `fetch_batch` og per-batch-tolerancen i
`process_all_points`.

Ironien var at koden allerede var bygget til at overleve netop det. To
batches fejlede med read-timeouts i samme forsøg og blev tolereret uden
problemer. Havde `JSONDecodeError` stået på listen, var kørslen gået igennem
i første forsøg.

## Første fix, og hvorfor det ikke var nok

Den minimale rettelse var at tilføje `JSONDecodeError` til begge except-tupler.
Tre tests skrevet først, set fejle, så implementeret. Grønt.

To review-agenter gennemgik derefter ændringen med hver sin vinkel, den ene
for korrekthed, den anden for systempåvirkning. De nåede uafhængigt frem til
samme konklusion: **fixet bestod af to halvdele, og kun den ene var god.**

Retry-delen var en klar forbedring. Tolerance-delen var en regression på
systemniveau, fordi den fjernede det eneste automatiske reparationsværktøj
systemet havde. Agenten kørte det efter: med 26 af 27 batches fejlet blev
resultatet exit 0, og 2 af 262 punkter blev committet og deployet oven på de
262 gode. Tre forhold gjorde det værre end det lyder:

1. **Ingen bund.** `main()` afviste kun helt tomt output. En delvis kørsel er
   grøn og udløser derfor ingen rerun.
2. **Frontenden skjuler skaden.** `app.js` interpolerer nærmeste nabo uden
   afstandsgrænse, så et manglende gitterpunkt giver ikke et hul, men naboens
   score smurt ud over området. Målt: ét tabt gitter-batch flytter op til 10
   af 157 landceller med op til 31 km erstatningsafstand.
3. **Flyvepladserne falder samlet.** Alle 30 ligger i batch 1-3, så én fejlet
   batch koster 10 klubber. Brugeren møder et tomt favoritpanel, en
   forsvundet markør og ingen vejr-widget, under et friskt
   "Opdateret"-tidsstempel.

Agenterne fandt desuden tre huller mere i samme familie, alle verificeret mod
en rigtig socket-server: `ChunkedEncodingError` og `ContentDecodingError`
væltede stadig kørslen, Open-Meteos eget fejlsvar `{"error": true, ...}` er
gyldig JSON og gav `KeyError: 'hourly'`, og et for kort svar blev trunkeret
**tavst** af `zip()`, så punkter forsvandt uden at blive talt som fejlede.

## Beslutning: hvor meget data må mangle

Grundlaget var empirisk. De 12 seneste grønne kørsler leverede alle 262/262
punkter. Delvis output er altså ikke normalt, og en streng grænse koster
ingen falske alarmer.

Valgt politik: **alle 30 flyvepladser skal hjem, plus mindst 95 % af de 232
gitterpunkter.** Flyvepladserne har nul tolerance fordi de rammer brugeren
hårdest pr. tabt punkt; gitteret tåler ét hul fordi kortet interpolerer.
Konstanten står som `GRID_COVERAGE_FLOOR` i `termik/config.py`.

## Det færdige forsvar i fire lag

1. **Genforsøg** (`fetch_batch`). Fanger nu hele `RequestException`-familien i
   stedet for tre håndplukkede typer, så tomt body, afklippet body og defekt
   gzip alle behandles som den transiente ustabilitet de er.
   `MissingSchema`, `InvalidSchema` og `InvalidURL` er eksplicit undtaget:
   en forkert `API_BASE_URL` ville ellers brænde ~47 minutters backoff af på
   et svar der aldrig bliver bedre.
2. **Formvalidering** (`validate_batch_response`). Et 200-svar med gyldig JSON
   i forkert form bliver en retry i stedet for et crash, og et for kort svar
   bliver opdaget i stedet for at tabe punkter tavst.
3. **Batch-tolerance** (`process_all_points`). Uændret i princippet, men nu med
   den brede fangst, så en enkelt død batch koster sine punkter og logges,
   frem for at vælte kørslen.
4. **Dækningsgrænse** (`check_coverage`). Afviser at skrive under grænsen.
   Jobbet bliver rødt, den forrige komplette prognose bliver liggende, og
   vagthunden prøver igen. Gammel komplet data slår ny data med huller for en
   7-døgns prognose.

Dertil synlighed: `::error::` og `::warning::` i stedet for `print`, så en
delvis kørsel giver en annotation i Actions, og `expected_point_count` i både
`current.json` og `meta.json`.

## Verifikation

Fire scenarier kørt end-to-end mod den rigtige `main()`:

| Scenarie | Før | Efter |
|---|---|---|
| 26 af 27 batches fejler | exit 0, publicerede 2 af 262 punkter | exit 1, output afvist |
| 1 gitter-batch fejler (`ChunkedEncodingError`) | crash, hele kørslen rød | exit 0 med synlig `::warning::`, 252 punkter |
| 1 flyveplads-batch fejler (`ContentDecodingError`) | crash | exit 1, 20/30 flyvepladser afvist |
| alt lykkes | exit 0 | exit 0 |

Testsuiten gik fra 357 til 376. De 19 nye dækker også stier der slet ikke
havde tests før: at 4xx ikke genforsøges, og at 5xx og 429 gør.

## Prøven i virkeligheden samme dag

Kørsel `33631047313` (12:38 UTC), under to timer efter udrulningen. Open-Meteo
var kraftigt ustabil med read-timeouts på tværs af batches.

```
API request failed (Expecting value: line 1 column 1 (char 0)), retrying in 15s (attempt 1/3)...
WARNING: 1/27 batches failed. Output contains 252 of 262 points.
::error::Ufuldstændig prognose: 20/30 flyvepladser og 232/232 gitterpunkter
(100%, grænse 95%). Output afvises, den forrige prognose bliver liggende.
```

Det tomme svar blev genforsøgt i stedet for at vælte kørslen. Da
genforsøgene ikke rakte, og den tabte batch tilfældigvis var en
flyveplads-batch, afviste dækningsgrænsen at publicere. Vagthunden fyrede,
og forsøg 2 leverede 262/262 punkter.

**Uden dagens ændringer** ville den kørsel enten være crashet som om
morgenen, eller, hvis kun tolerance-delen var lavet, være blevet grøn med en
tredjedel af klubberne manglende og ingen der opdagede det.

## Sidegevinster

**Actions væk fra Node 20.** Bevidst forskellige checkout-versioner:
`update-forecast.yml` fik kun v5, som er Node 24-bumpet uden adfærdsændring,
fordi v6 flyttede credentials til en separat fil og det er netop den
mekanisme `git push`-trinnet hviler på. `deploy-pages.yml` fik v7 plus
`configure-pages@v6`, `upload-pages-artifact@v5` og `deploy-pages@v5`, da det
workflow ikke pusher. De to breaking changes i Pages-kæden blev tjekket først
og er uden effekt her: `termik/output/` har ingen skjulte filer, og
`static_site_generator` bruges ikke. Resultat: 0 annotationer, hvor
deploy-kørslen kl. 09:56 stadig advarede om fire Node 20-actions.

**`timeout-minutes: 60`** på forecast-jobbet, fordi genforsøgene gør et
vedvarende udfald langsomt (op mod 100 min for alle 27 batches) i stedet for
hurtigt. Normale kørsler topper på 25 min, og loftet udelukker overlap med
næste cron-slot.

**Frontend-banner.** `applyCoverageNote` i `app.js` viser en dæmpet note i
sidebaren når `points.length < expected_point_count`. Tallet ligger i
`current.json` frem for `meta.json`, så de to ikke kan komme i utakt i
browserens cache, og frontenden slipper for en ekstra hentning.

## Commits

| Commit | Indhold |
|---|---|
| `0307ee5` | `fix:` dårlige API-svar må hverken vælte eller udvande prognosen |
| `7777d61` | `ci:` opgrader actions væk fra Node 20 |
| `0e98927` | `web:` sig det når prognosen er delvis |

## Opdaterede dokumenter

- `docs/PROJEKT-DOKUMENTATION.md`: dataflowet sagde "79 punkter (2 batch-kald)"
  og "3 dage frem". Rettet til 262 punkter i 27 batches og 7 dage. De tal er
  nu load-bearing for dækningsgrænsen.

## Åbne punkter

- **Genforsøg på fejlede batches til sidst** i `process_all_points`, før
  dækningen bedømmes. Kørslen kl. 12:38 tabte kun én batch ud af 27, men fordi
  flyvepladserne ligger samlet i batch 1-3, er der reelt tre batches hvor et
  enkelt uheld koster hele kørslen. Ét ekstra forsøg ville formentlig have
  reddet første forsøg og sparet en hel cyklus. **Bygget 3/9** som
  `retry_failed_batches` (commit `c9f89de`): runden kører når alle øvrige
  batches er hentet, springes over hvis mere end 5 batches er faldet (så er
  API'et nede, ikke ustabilt), og bruger et kortere retry-budget. Hændelsen
  kl. 12:38 er simuleret igennem og ender nu på exit 0 med 262/262.
- **Banneret er ikke set i en browser.** Chrome-udvidelsen var ikke forbundet
  under sessionen. Logikken er kørt igennem i node for komplet, delvis, tom og
  gammel datafil uden feltet, og noten deler CSS-regel med den eksisterende
  `#uncertainty-note`, men det visuelle er uverificeret. Kan tjekkes med
  `forecastData.expected_point_count = forecastData.points.length + 10;
  applyCoverageNote();` i konsollen.
- **`termik/tools/fetch_reference_day.py`** havde hele tiden den brede
  fejlfangst og formvalidering som produktionsstien manglede. Værd at holde
  for øje om flere sådanne uoverensstemmelser findes mellem dev-værktøj og
  cron.
