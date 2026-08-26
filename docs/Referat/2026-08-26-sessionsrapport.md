# Sessionsrapport 25.-26. august 2026: DSvU-hæftet, scoring v2, validering og popup-redesign

Én sammenhængende session fra "kan du læse denne PDF?" til ny scoringsmodel i
produktion, valideret mod virkelige flyvninger, plus redesignet frontend.
Detaljerne ligger i de enkelte referater og planen; dette er det samlede
overblik. En designet udgave findes som Claude-artifact (privat link hos
Jens).

## Del 1: Fra hæfte til scoring v2 (25/8)

**Grundlag.** DSvU-hæftet "Svæveflyvningen og vejret" (47 sider) blev læst
og holdt op mod `termik/scoring.py`. Meget var allerede på plads
(125 m-formlen, nedbørs- og sky-caps, shear-modifiers); syv punkter kunne
rettes til: vind-idealbånd, cu-allowance, cirrus-fradrag, basehøjde-kobling,
søbrise-skalering, varmehukommelse ved koldluft, temperaturvægt.

**Implementering.** Ny `termik/scoring_v2.py`; v1 urørt som rollback via
`SCORING_VERSION` i config. To hæfte-punkter blev justeret under
kalibrering mod referencedagene 8.-9. august: varme-malussen på hukommelsen
droppet (piloten fløj kl. 18-19 ved trend +1.0), og basehøjde-cappet fik
sol-gate (SW ≥ 400) plus krav om positiv lcl/ti_zero-dom. Sidegevinst: v1's
dokumenterede 19:00-hul (strict xfail) lukkedes af cu-allowancen.
Plan: `docs/plans/2026-08-25-scoring-v2-dsvu-haefte.md`.

**Validering mod startlist.club.** Nøglen var skolefly-filteret (samme fly
med 3+ forskellige forsædepiloter samme dag tæller ikke; lette fly som
M1/M4/MF flyver i svagere termik end fx PL). 18 dage, 88 plads-dage med
facit: v2 61/88 i forventet bånd mod v1's 57/88, samlet afvigelse 51.6 mod
55.0, største enkeltfejl 1.6 mod 3.3. Referat:
`2026-08-25-startlist-saeson-validering.md`.

**Tre evidensdrevne efterjusteringer:**

1. **Sæby-dagene**: basehøjde-båndene testes mod den ukorrigerede base
   (Hcrit-marginen fik cappet til at ramme baser op til ~850 m), og fuldt
   cirrus-fradrag flyttet fra 60 til 70 % ("op til 1 m/s").
2. **Pålandsvinds-studiet**: 571 Slaglille-dage scannet; hypotesen om
   rest-straf ved lille land/hav-diff blev AFVIST af kryds-plads-udvidelsen
   (4180 plads-dage, 128 facit-dage: 8/8 pålandsdage med lille diff bar,
   median 174 min; Kalundborgs 315/208-min sejre var fuld pålandsvind).
3. **Punkt 5b i stedet**: diskriminatoren er havluftens instabilitet
   (havtemp minus 850-temp): påland-dage med instab ≥ 7 bar 15/17, under 7
   kun 2/7, og i fraland er instab ligegyldig. Ved påland ≥ 8 kt og stabil
   havluft løftes drivkraften til maksimum. Referat:
   `2026-08-25-paalandsvind-studie.md`.

**Merge**: `scoring-v2-dsvu` → main (49623d9), 347 tests grønne.
Kendte rest-sager: Slaglille 22/8 (outlier) og 18/7 (delvis); Hammer
undtages fra termik-facit (skrænt/bølge).

## Del 2: Frontend og drift (25.-26/8)

**Termik-tophøjde-laget** renderes nu glat som score-laget (samme 0,2°-grid;
forskellen var kun `imageSmoothingEnabled`). Null-celler udfyldes med
nærmeste reelle værdi før interpolationen; højde-labels bevaret.

**Hæfte-tjek af termikhøjden**: kapitlet "Højde af termik" matcher
beregningen. Hæftets 125 m-regel og vores Bolton-LCL afviger 2-23 m under
danske forhold; tørtermik-tilfældet (stop ved inversion) er automatiseret
som TI-nul på modellens trykprofil; min(LCL, TI-nul) forener kapitlets to
tilfælde. Vores Hcrit-margin (brugshøjde) er en tilføjelse ud over hæftet.

**Popup-redesign** (designforslag i artifact, tre varianter, brugervalgt
kombination): score-ring med dagens gennemsnit kl. 10-18 (samme tal som
favorit-panelet) + termikvindue beregnet af dagsforløbet; dagsforløb rykket
op; tre heltetal; højdeakse med cirrusbånd/base/top/blandingslag;
lapse-måler; spread-termometer (°C); vindkompas med drejningsvifte og
knob-søjler med stødmærke; skylag-bjælker. Popup-højden følger skærmen.

**Ny tekstgenerator** (`comments.py`): bindende faktor først (fra
`limited_by`), derefter op til to prioriterede observationer; felt-tal
gentages ikke; ingen tankestreger. Efterfølgende rettelse: "inversion"- og
"saturated"-domme oversættes ikke ved brugbar score (falsk dom hen over
superadiabatisk overfladelag gav "Jordinversion" ved score 8.1).

**Opdater-knap + auto-genhentning**: PWA'en genoptages fra hukommelsen på
mobil med timegamle data. Knappen henter med `cache: no-cache` og genbygger
markører/lag; `visibilitychange` genhenter automatisk efter 30 min.
Service worker bumpet til v18 undervejs.

**CI-racen opklaret**: datakørslen tager ~20 min fra checkout til push; et
kode-push i vinduet fik datapushet afvist, og reruns kunne aldrig reparere
det (de kører på det oprindelige SHA). Tre kørsler fejlede i træk 26/8
morgen. Fix: rebase-retry i push-trinnet. `rerun-failed-forecast.yml` er
en vagthund fra tidligere session; dens mange "skipped"-rækker i Actions er
workflow_run-mekanik og harmløse.

## Opdaterede dokumenter

- `docs/PROJEKT-DOKUMENTATION.md`: scoringsmodel (v2), søbrise (5b),
  validering (startlist), kommentargenerering, kortlag, popup, Actions.
- `docs/scoring-scenarios.md`: markeret som v1-reference med v2-henvisninger.
- Referater og plan fra 25/8 (fem dokumenter) plus denne rapport.

## Åbne punkter

1. Efterårs-efterprøvning: genkør startlist-pipelinen med
   september-oktober som frisk facit, når sæsonen er slut.
2. Rest-sagerne Slaglille 22/8 og 18/7 overvåges; ingen ændring uden mere
   facit.
3. Termiktop-heltetallet i popup'en kan vise "0 m · jordinversion" på timer
   med den falske parcel-dom (kendt begrænsning, dokumenteret i
   maj-referatet); teksten stoler ikke længere på dommen, tallet gør.
