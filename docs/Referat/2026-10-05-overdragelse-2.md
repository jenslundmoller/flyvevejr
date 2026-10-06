# Overdragelse 2026-10-05 (2): drift på OMV, begrænsende faktor, tre målinger

Fortsættelse af [2026-10-05-overdragelse.md](2026-10-05-overdragelse.md)
samme dag. Den session sluttede med punkt **13, 9, 1, 7** som næste skridt;
alle fire er afsluttet her, og driften er flyttet fra GitHubs runnere til
OMV-maskinen derhjemme. Prompt til at fortsætte står nederst.

## Kort fortalt

| Punkt | Resultat | Scores ændret? |
|---|---|---|
| 13 Actions-timeouts | Kaldene **hang** fra GitHub-runnerne (ikke langsomme). Ingen pause hjalp. Forecast-jobbet kører nu på OMV: 2.5 min, 0 timeouts | Nej |
| 9 Begrænsende faktor | `data.limited_by` pr. flyvepladstime og en gul linje i popup'en | Nej (verificeret på 986 timer) |
| 1 `score_solar` og cumulus | Målt, uændret: v2 har allerede løst 8/8, ingen variant slår støjen | Nej |
| 7 Lavniveaudata (ICON/DMI) | Målt, ikke implementeret: lille gevinst mod dobbelt så mange kald | Nej |
| Kørselsplan og parametre | 5 kørsler kl. 05-17 UTC, 32 i stedet for 41 variable | 6 af 700 dagtimer på 10 sydlige punkter (op til 3) |

Ingen scoringsregel er ændret i denne session.

## Commits (alle pushet til main)

| Commit | Indhold |
|---|---|
| `9fa8a98` | Probe-værktøj og -workflow til droslingen |
| `14f3e67` | Punkt 9: `dealbreaker_caps_v2`, `dealbreakers_v2`, `limited_by`, popup-linje |
| `d77bc98` | Punkt 1 dokumenteret (uændret) |
| `673dd18` | Probe-resultat og punkt 7 dokumenteret |
| `2b1c566` | Selvhostet runner + `forecast-fallback.yml` + `forecast_watchdog.py` |
| `401db80` | OMV-tilpasning: Python 3.13, deploy-trigger uden gh (`dispatch_workflow.py`) |
| `2f81047` | Kørselsplan 05-17 UTC, 32 variable |

Bemærk: en anden session i **samme arbejdsmappe** committede oven på mine
lokale commits og pushede dem med (`15c5753`, Jylland juli-september). Det
gik godt, men to sessioner i samme mappe deler commits. Brug separate git
worktrees, hvis to sessioner skal arbejde samtidig.

## Punkt 13: GitHub-runnerne drosles

Detaljer: [2026-09-02-api-robusthed.md](2026-09-02-api-robusthed.md),
opfølgning 5/10.

- 33 kørsler 1-5/10: vellykkede kald median 0.8 s, p90 1.5 s; 730 af 738
  fejlede sluttede på præcis 30.0-30.5 s uden svar. Højere timeout hjælper ikke.
- Fejlraten afhang af tiden siden forrige succes i loggene (5 s: 50 %,
  50 s: 61 %, 110 s: 2 %), men proben på en GitHub-runner modsagde en simpel
  vindue-forklaring: 11 af 15 kald ved 20-100 s hang, 0 af 21 ved 5 s eller
  efter >= 150 s stilhed. Ingen overkommelig pause virker.
- Hjemmefra (Zorin og OMV) hænger intet: 0.1-0.4 s pr. batch.

## Driften nu

**Runner på OMV** (verificeret 5/10):

| | |
|---|---|
| Sti | `/opt/gh-runner`, systembruger `gh-runner` (nologin) |
| Unit | `actions.runner.jenslundmoller-flyvevejr.omv.service`, enabled |
| Hærdning | drop-in `10-hardening.conf`: `NoNewPrivileges`, `PrivateTmp`, `ProtectSystem=strict`, `ReadWritePaths=/opt/gh-runner`, `ProtectHome`, `InaccessiblePaths=` for `/srv`, `/opt/flightradar`, `/opt/hue-poller`, `/etc/flightradar`, `/etc/cloudflared` (tjekket med nsenter: tomme `d---------`) |
| Runner | v2.337.0 (SHA-256 tjekket), navn `omv`, labels `self-hosted, Linux, X64, flyvevejr` |
| Python | maskinens 3.13 i en venv pr. job (`$RUNNER_TEMP/venv`); testsuiten består på 3.12 og 3.13 |
| Deploy | `termik/tools/dispatch_workflow.py` via REST-API, fordi OMV ikke har gh |

OMV-referencen (driftsdokumentet for maskinen) er opdateret som rev. 5:
`~/Downloads/omv-webhosting-reference-rev5.html`. Læg den hvor rev. 4 bor.

**Reserve:** `forecast-fallback.yml` kører på GitHub hver halve time kl.
05-18 UTC. En forecast-kørsel der har stået 15 min i kø (OMV nede), aflyses
og erstattes af én kørsel på `ubuntu-latest` (langsom, men den lykkes).
Reservekørsler har "(ubuntu-latest)" i titlen og aflyses aldrig. Manuelt
testet: grøn, "Ingen hængende kørsler".

**Kørselsplan:** `15 5-17/3 * * *`, altså 05:15, 08:15, 11:15, 14:15, 17:15
UTC (07:15-19:15 dansk sommertid). Ingen kørsler om natten; morgenkørslen
giver en frisk prognose. GitHub starter cron-kørsler 15-30 min forsinket.

**Open-Meteo-forbrug:** gratis grænse 10.000 kald/døgn, hver påbegyndte 10
variable tæller som et kald pr. punkt. Før: 41 variable x 8 kørsler = ~9.900
(lige ved grænsen). Nu: 32 variable x 5 kørsler = ~5.000. De 9 fjernede
(80/120/180 m-temperatur, 950/900/800 hPa med højder) var tomme for 252 af
262 punkter. **Hjemme-IP'en deler kvoten** med analysekald hjemmefra.

**Målt efter omlægningen** (manuel kørsel 16:04 UTC): forecast 2 min 24 s,
0 fejlede kald, 262/262 punkter, `limited_by` på 5040/5040 flyvepladstimer,
deploy grøn, flyvevejr.dk viser data fra 16:06.

**GitHub-indstillinger** (sat 5/10 via API, Settings → Actions → General):
godkendelse af fork-workflows for alle eksterne bidragydere; kun GitHubs
egne actions. Repoet forbliver offentligt, fordi Pages fra et privat repo
kræver en betalt plan. Ingen workflow må få en `pull_request`-trigger.

## Punkt 9: begrænsende faktor

`dealbreaker_caps_v2` giver alle lofter som (kode, loft); `dealbreakers_v2`
giver scoren plus koderne for de lofter der satte den (laveste loft under
scoren efter overskyet-straffen, alle ved lige lofter). Koder: `radiation`,
`shallow_bl`, `stable`, `surface_stable`, `overcast`, `cirrus`, `mid_cloud`,
`rain`, `wind`, `cold`, `cape`, `low_top`. Popup: "Holdes nede af ...
(højst N)." med tekster i `LIMIT_TEXT` i `app.js`. Kun lofter vises (valgt
af brugeren); de 71 lave timer uden loft viser intet. `airfields.json` +1 %
gzippet; gitterpunkterne er uændrede.

Målt: et loft satte scoren i 451 af 986 timer, oftest cirrus (131),
mellemhøj sky (70) og overskyet (59).

## Punkt 1 og 7: målt, ikke ændret

Tal og tabeller i [startlist-referatet](2026-10-05-startlist-weekend-oktober.md),
afsnittene om punkt 1 og punkt 7. Det vigtigste fund fra punkt 7:
**produktionens egen lapse_rate og termiktop sorterer stadig bar fra kort
inden for scorebåndene (AUC 0.705 / 0.733)**, så scoren udnytter information
den allerede har for dårligt. Det er næste kandidat til en reel forbedring.

## Faldgruber fra i dag

- **To sessioner i samme mappe** deler commits (se ovenfor).
- **Heredocs i SSH-sessioner** kan hænge (prompt `>`); brug en
  `printf ... | sudo tee`-linje. Samme fælde står i OMV-referencen afsnit 09.
- **Open-Meteos kvote er delt** mellem OMV-produktionen og alt andet på
  hjemme-IP'en. Store analysehentninger kan tømme den for produktionen.
- **Lapse 2-180 m-cappet (`surface_stable`) er nu reelt død kode:**
  `temperature_180m` hentes ikke længere. Det havde kun data for 10 punkter
  og ramte 7 af 873 facit-timer, alle korte.
- **Proben modsagde loggenes mønster.** Konklusioner fra én datakilde om
  netværksadfærd skal efterprøves, før de bruges til et design.

## Åbne punkter

Videreført fra [morgenens overdragelse](2026-10-05-overdragelse.md)
(numrene er bevaret): 2, 3, 4, 5, 6, 8, 10, 11, 12, 14, 15, 16, 17, 18.
Det planlagte live-tjek af weekenden 10.-11. oktober (cloud-rutinen
mandag 12/10) står uændret dér; dens "morgenkørsel" er nu 05:15 UTC.

Nye:

19. **Repoets størrelse: ~920 MB.** Hver kørsel committer ~14 MB JSON (5 om
    dagen nu). GitHub anbefaler under 1 GB. Løsning: publicér data uden at
    committe dem (fx Pages-artefakt direkte fra jobbet) eller ryd historikken.
20. **Overvej at gøre repoet privat og flytte siden væk fra GitHub Pages**
    (Cloudflare Pages, eller OMV via den eksisterende Cloudflare Tunnel), så
    den selvhostede runner ikke hænger på et offentligt repo. Hænger
    naturligt sammen med 19. Besluttet 5/10 at vente.
21. **Mellemhøj sky-cappet (2)** har den dårligste træfsikkerhed af de
    hyppige lofter: 18 af 56 facit-timer bar alligevel. Kandidat til samme
    time-for-time-forsøg som cirrus-skjoldet.
22. ~~**Probe-workflowet**~~ Slettet 6/10 (workflow, værktøj og tests);
    koden findes i commit `9fa8a98`, resultatet i api-robusthed-referatet.
23. **`surface_stable`-cappet**: fjern det eller dokumentér det som inaktivt
    (se faldgruber).
24. **Redningsrunden og fallback til `ubuntu-latest`** er ikke set i
    produktion endnu. Test ved at stoppe runneren på OMV i et kvarter
    (`sudo systemctl stop actions.runner.jenslundmoller-flyvevejr.omv.service`)
    lige før en planlagt kørsel, og start den igen bagefter.

Forslag til næste session: **3 + 5 (vægtningen af lapse og termiktop)**,
derefter **21**, og **18** når weekendens data er inde.

## Prompt til at fortsætte

```
Continue the Flyvevejr work from docs/Referat/2026-10-05-overdragelse-2.md.
Read it first, then the earlier handover it links to and
docs/Referat/2026-10-05-startlist-weekend-oktober.md for the numbers.
Reusable analysis scripts are in docs/Referat/2026-10-05-analyse/ (see its
README); lowlevel7.py and solarvar.py are the closest templates.

Work through these one at a time. For each, show me the findings before
changing production code, validate any scoring change against the startlist
facit (day level and hour level, as in the referat), write tests first,
update the referat/PROJEKT-DOKUMENTATION, and commit. Ask before pushing.
Note that the forecast now runs on a self-hosted runner on the OMV box and
shares Open-Meteo's free quota with analysis calls from home: keep pulls small.

3+5. Weighting of lapse rate and thermal top: production's own lapse_rate
     and thermal_top still separate flown from short hours within score
     bands (AUC 0.705 / 0.733). Test reweighting variants (lapse weight,
     a thermal-top term) hour by hour and day by day.

21.  Mid-level cloud cap (2): 18 of 56 facit hours were flown anyway. Test it
     hour by hour like the cirrus shield.

18.  Fix 3 over a lid: once the 10-11 Oct weekend PR from the cloud routine
     is in, re-check the candidate rule against the new days.
```
