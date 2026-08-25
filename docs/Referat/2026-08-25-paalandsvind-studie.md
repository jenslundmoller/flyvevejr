# Pålandsvinds-studie: kan gammelt vejr + startlist afgøre rest-straffen?

Dato: 2026-08-25. Opfølgning på Slaglille 22/8-hypotesen fra
`2026-08-25-startlist-validering.md`: bør pålandsvind >= 8 kt beholde en
rest-straf, selv når land/hav-temperaturforskellen er lille?

## Metode

1. Hentede Slaglille-vejret maj-september 2023-2026 fra
   historical-forecast-endpointet (571 dage) og scorede alle dage med v2.
2. Udpegede alle weekenddage med v2-maks >= 6.5 kl. 11-17 (52 dage) plus
   kandidat/kontrol-hverdage, og hentede startlist-facit for hver
   (skolefly filtreret fra som i sæson-valideringen).
3. Klassificerede dagene efter vind i 12-16-vinduet: PÅLAND (4+ timer
   onshore, >= 8 kt), FRALAND/SVAG, MIX, og efter land/hav-diff.

Kun 9 af 57 dage havde reel aktivitet (mange gode dage er feriedage eller
stævnedage andre steder), plus den kendte 22/8. Facit ("bar" = længste
signalflyvning >= 60 min):

| Gruppe | N | Bar | Median længste |
|---|---|---|---|
| PÅLAND (alle diff), inkl. 22/8 | 5 | **1** | 27 min |
| MIX | 1 | 0 | 25 min |
| FRALAND/SVAG | 4 | **3** | 107 min |

Isoleret set støtter Slaglille-dataene hypotesen: pålandsdage bar 1 af 5,
fralandsdage 3 af 4. Bemærk også at pålandsdage med diff > 2 (hvor v2
allerede straffer 0.9-1.2) også døde (13/9-25: 27 min, 18/7-26: 10 min mod
v2 8.8), og at den ene pålandsdag der BAR, gjorde det stort (24/8-25:
175 min ved 11.7 kt onshore, diff 0.8).

## Modbeviset: v2's egne største sejre var pålandsdage

Vindtjek på de dage, der bar sæson-valideringen:

| Dag | Plads | Facit | Vind 12-16h | Onshore |
|---|---|---|---|---|
| 16/8 | Kalundborg (13 km kyst) | 315 min | 270-275 grader, 12-13 kt | **5/5 timer** |
| 2/8 | Kalundborg | 208 min | 248-262 grader, 8-10 kt | **5/5 timer** |
| 25/8 | Slaglille | 184 min | 114-121 grader, 4-5 kt | 0/5 (fraland) |
| 8/8 | Sæby | 108 min | 246-264 grader, 9-12 kt | 0/5 (fraland) |

Kalundborg fløj 5+ timer i fuld pålandsvind fra en plads tættere på kysten
end Slaglille. En generel rest-straf for pålandsvind >= 8 kt ville have
kostet ca. 1.3-2.1 point på netop de to dage, der gjorde v2 målbart bedre
end v1 (v1's faste pålandsstraf var årsagen til dens 2.8-points fejl 16/8).

## Konklusion: rest-straffen implementeres IKKE nu

Metoden virker (mønster-scan i gammelt vejr + startlist-facit er billig og
reproducerbar), men beviset er reelt splittet: Slaglille-pålandsdage dør
oftest, Kalundborg-pålandsdage leverer stort. Hverken land/hav-diff,
på/fraland eller kystafstand skiller de to grupper i det indsamlede
materiale (N = 9 aktive dage er for lidt). En blank rest-straf ville bytte
kendte gevinster for en usikker rettelse.

Hvad der kan afgøre sagen senere:

1. **Kryds-plads-udvidelse**: samme scan for alle kystnære pladser
   (Kalundborg, Kongsted, Sæby, Lolland, Frederikssund...). Startlist-siderne
   indeholder alle pladser pr. dag, så facit-hentningen genbruges; kun
   vejr-scanningen koster ekstra kald (8 pladser x 4 somre). Det giver
   formentlig 40-60 aktive facit-dage i stedet for 9.
2. **Diskriminator-hypotese til den udvidelse**: det afgørende er måske
   ikke land mod hav, men om selve havluften er ustabil (koldluft over
   varmt sensommerhav giver konvektiv luft, som bærer termik med ind over
   land). Det kan testes med 850 hPa-temperaturen mod havtemperaturen på
   de samme dage.

Rådata: scanningen og facit ligger i scratchpad-pipelinen fra denne session;
metoden er beskrevet ovenfor og kan genkøres med
`termik.tools.compare_scores` plus startlist-parseren.

## Kryds-plads-udvidelsen (samme dag): afgørelsen

Udvidet til 10 pladser (Kalundborg, Kongsted, Sæby, Gørløse, Frederikssund,
Aars, True/Aarhus, Lolland, Gesten, Slaglille; Hammer udeladt som
skrænt-plads), somrene 2024-2026 (2023 mangler 850 hPa-data), 4180
plads-dage scannet. 79 unionsweekenddage med v2 >= 6.5 gav 288 plads-dage
med startlist-sektion, heraf 128 aktive med facit (rådata:
`2026-08-25-paalandsvind-pooled.json`).

### Rest-straffen for diff <= 2 er definitivt død

| Gruppe | N | Bar (>=60 min) | Median længste |
|---|---|---|---|
| Påland, diff <= 2 | 8 | **8/8** | 174 min |
| Påland, diff > 2 | 16 | 9/16 | 106 min |
| Fraland/svag, diff <= 2 | 13 | 8/13 | 135 min |
| Fraland/svag, diff > 2 | 71 | 56/71 | 128 min |

Slaglille 22/8 var en outlier: præcis det hjørne, hypotesen ville straffe,
leverede 8 af 8 gange på tværs af pladser.

### Diskriminatoren: havluftens instabilitet (havtemp minus 850-temp)

| Pålandsdage | Bar |
|---|---|
| Instab >= 7 | **15/17 (88 %)** |
| Instab < 7 | **2/7 (29 %)** |

I fralandsgruppen er instabiliteten ligegyldig (76 mod 77 %), så effekten
er specifikt marin: pålandsvind bærer termik når havluften er konvektiv
(kold luftmasse over varmt hav, typisk sensommer, hvor land/hav-diff
samtidig er lille: derfor "hullet" aldrig var et hul), og dræber når
havluften er stabil (typisk forår, også ved moderat diff hvor v2's
diff-kurve kun gav halv straf).

### Implementeret: punkt 5b

`calculate_seabreeze_penalty_v2` tager nu `temp_850hpa`: ved pålandsvind
>= 8 kt og instab < `SEABREEZE_STABLE_MARINE_INSTAB` (7.0) løftes
drivkraften til maksimum uanset land/hav-diff. Ændringen rører præcis de
målte fejlrækker og ingen af de målte bar-rækker:

- True/Aarhus 12/5-2024 (facit 20 min): v2 6.8 -> 6.2.
- Slaglille 18/7-2026 (facit 10 min): v2 8.8 -> 8.6 (resterende overcall
  skyldes andet end søbrise).
- Sæson-valideringens 88 rækker: 0 flyttede sig (61/88 bånd, afvigelse
  51.6, uændret).
- Kalundborg 16/8 og 2/8, Slaglille 24/8-25 m.fl. (konvektive pålandsdage):
  uændrede.

Diff <= 2-hjørnet forbliver bevidst straffrit: alle målte dage der var
konvektive og bar. 347 tests grønne.
