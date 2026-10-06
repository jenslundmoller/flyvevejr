# Overdragelse 2026-10-06: nye farver på kortlaget Termik-tophøjde

Kort session om farveskalaen på kortlaget **Termik-tophøjde**. Ingen
scoringsregel eller beregning er ændret; kun farver, legende og
service-worker-cache. Prompt til at fortsætte står nederst.

## Kort fortalt

| Emne | Resultat |
|---|---|
| Problem | 0-1500 m havde næsten samme farve, selvom forskellen i flyvning er størst netop her |
| Ny palet | Grå → lilla → magenta → orange → gul → grøn med et skift hver 300 m op til 1500 m, derefter mørkere grønne |
| Legende | Ikke-equidistante CSS-stop som matcher paletten, etiketter for hver 500 m |
| Deploy | Live på flyvevejr.dk via `deploy-pages.yml`, service-worker-cache talt op |
| Dokumentation | `PROJEKT-DOKUMENTATION.md`: afsnittet om kortlaget og en note om `CACHE_VERSION` under `deploy-pages.yml` |

## Problemet

Brugerens ønske: farven skal vise den store forskel i flyvning mellem 0 og
1500 m.

Den gamle palet (fra [2026-05-28](2026-05-28-termik-top.md)) var
viridis-lignende med stop ved 0/500/1000/1500/2000/2500 m: mørk lilla,
lilla-blå, blågrøn, grøn, gul-orange, orange-rød. 0-1000 m var derfor mørke,
ens lilla nuancer, og laget vises med 55 % gennemsigtighed oven på kortet.

Data fra `current.json` 6/10: 2.718 timer med top > 0 lå på 46-849 m
(median 410 m, 90 %-fraktil 566 m). Hele dagens kort lå altså i det lilla
område.

## Den nye palet

`THERMAL_TOP_STOPS` i `termik/output/app.js`, lineær interpolation mellem
stoppene som før:

| Højde | RGB | Farve | Betydning |
|---|---|---|---|
| 0 m | 110,110,120 | grå | ingen termik |
| 300 m | 120,60,170 | lilla | for lavt til at holde sig oppe |
| 600 m | 215,55,150 | magenta | marginalt, kun platrunde |
| 900 m | 245,125,40 | orange | lokal termikflyvning |
| 1200 m | 245,215,50 | gul | strækflyvning mulig |
| 1500 m | 110,200,70 | grøn | god dag |
| 2000 m | 35,150,75 | mørkegrøn | kraftig |
| 2500 m+ | 15,95,60 | dybgrøn | fremragende |

Valg:

- Både farvetone og lysstyrke skifter mellem hvert stop under 1500 m, så
  forskellen kan ses ved 55 % gennemsigtighed.
- Score-lagets blå → rød er bevidst undgået (samme krav som i maj), så de to
  lag ikke forveksles.
- Grøn som "godt" i toppen er intuitivt. Blå blev fravalgt i toppen, fordi
  mørkeblå betyder dårligt i score-laget.
- `thermalTopToRgb(null)` giver stadig neutral grå (200,200,200) for ukendt.

Legenden i `style.css` (`.legend-thermal`) har stop ved 0/12/24/36/48/60/80/100 %
(= 0-2500 m), og `updateLegend()` viser etiketterne
0, 500, 1000, 1500, 2000, 2500m+.

Grænserne er sat ud fra almindelig svæveflyvererfaring, ikke fra målinger.
Højderne er `thermal_top_m` som i resten af laget.

## Verifikation

- Syntakstjek af `app.js` med node.
- Lokalt (`python3 -m http.server` i `termik/output/`) og i Chrome kl. 14 i
  dag: Sønderjylland og øerne grå (0 m), Midt- og Nordjylland lilla og
  magenta. Før så det hele ens mørkt lilla ud.
- Live: `https://flyvevejr.dk/app.js` indeholder de nye stop, `sw.js` havde
  `termik-v21` efter deploy.

## Deploy og service worker

`deploy-pages.yml` kører ved push til `main`, der rører `termik/output/**`,
så farverne var live ca. et minut efter push. Men `sw.js` serverer app-skallen
**cache-first**, så tilbagevendende besøgende (og PWA'en) ville have beholdt de
gamle farver. `CACHE_VERSION` blev derfor talt op fra `termik-v20` til
`termik-v21`. Reglen er nu skrevet ind i `PROJEKT-DOKUMENTATION.md`: tæl
`CACHE_VERSION` op i samme push som en UI-ændring.

## Commits (alle pushet til main)

| Commit | Indhold |
|---|---|
| `2739ede` | Ny palet og legende (`app.js`, `style.css`) |
| `e44f65f` | `PROJEKT-DOKUMENTATION.md`: afsnittet om kortlaget |
| `f902580` | `sw.js`: `CACHE_VERSION` til `termik-v21` |
| (denne) | Overdragelsen her og noten om `CACHE_VERSION` i dokumentationen |

Det første push tog også fire lokale commits med, som endnu ikke var pushet
(`6731ca7`..`929afbd`, bl.a. aftenkørslen kl. 20:15 UTC).

Bemærk: en anden session arbejdede samtidig i **samme arbejdsmappe** og
pushede `60b5575` (Hcrit-margin følger solskin), `838b92e` og `b8d0af4`
(QNH/QFE i højdeteksterne, `CACHE_VERSION` nu `termik-v23`). Ingen konflikt,
men som nævnt i [overdragelsen 2026-10-05 (2)](2026-10-05-overdragelse-2.md):
brug separate git worktrees, når to sessioner arbejder samtidig.

## Åbne punkter

1. **Se paletten på en god sommerdag.** Dagens data går kun til 849 m, så den
   øvre del (gul, grøn) er kun set i legenden. Tjek næste dag med toppe over
   1500 m, at grøn ikke flyder sammen med OSM-basekortets grønne skove og
   parker ved 55 % gennemsigtighed.
2. **Farveblindhed.** Orange (900 m) og grøn (1500 m) adskilles mest af
   lysstyrke. Kunne tjekkes med en simulator (deuteranopi).
3. **Grænserne er skøn.** 300/600/900/1200 m kunne afstemmes mod
   FlightRadar-materialet i
   [2026-10-06-termiktop-mod-flightradar.md](2026-10-06-termiktop-mod-flightradar.md),
   f.eks. hvilken top der typisk giver flyvninger over 60 min.
4. De åbne punkter i [overdragelsen 2026-10-05 (2)](2026-10-05-overdragelse-2.md)
   gælder uændret.

## Prompt til at fortsætte

```
Continue the Flyvevejr work from docs/Referat/2026-10-06-overdragelse-termikfarver.md.
Read it first. The thermal-top map layer got a new palette on 6 Oct
(THERMAL_TOP_STOPS in termik/output/app.js, .legend-thermal in style.css).

1. On the next forecast day with thermal tops above 1500 m, look at the layer
   on flyvevejr.dk (or locally with python3 -m http.server in termik/output)
   and check that the yellow/green part reads well over the OSM base map.
2. Optionally check the palette for deuteranopia.
3. Optionally use the FlightRadar data from
   docs/Referat/2026-10-06-termiktop-mod-flightradar.md to tune the
   300/600/900/1200 m stops.

Any change to files in termik/output/ must bump CACHE_VERSION in sw.js in the
same push. Show me before pushing.
```
