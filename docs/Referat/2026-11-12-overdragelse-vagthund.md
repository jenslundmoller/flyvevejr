# Overdragelse 2026-11-12: vagthunden og spøgelseskørslen

Fortsættelse af [2026-10-06-overdragelse.md](2026-10-06-overdragelse.md). Tal
og begrundelser står i
[2026-11-12-vagthund-spoegelseskoersel.md](2026-11-12-vagthund-spoegelseskoersel.md).
Prompt til at fortsætte står nederst.

## Kort fortalt

| Emne | Resultat | Scores ændret? |
|---|---|---|
| Forecast Fallback fejlede hele dagen | Kørsel 43097108052 hænger hos GitHub som "queued" uden jobs og kan ikke aflyses eller slettes. Vagthunden ignorerer nu kørsler over 6 timer og tåler en afvist aflysning | Nej |

Kun drift er ændret (vagthund og fallback-workflow). Prognosen var ikke berørt,
bortset fra at 20:15-kørslen 11/11 udeblev.

## Commits

Se `git log` for grenen `watchdog-ghost`. Pushet til main: afhænger af brugerens ja.

## Faldgruber fra i dag

- GitHub kan efterlade en kørsel som "queued" med 0 jobs, som hverken cancel,
  force-cancel eller delete kan fjerne. Kode der aflyser kørsler skal tåle det.

## Åbne punkter

Ingen ændret status. Punkt 24 (fallback ikke set i produktion) står stadig åbent.

## Prompt til at fortsætte

```
Continue the Flyvevejr work from docs/Referat/2026-11-12-overdragelse-vagthund.md.
Read it first, then docs/AABNE-PUNKTER.md. Check that the Forecast Fallback
runs since the fix are green.
```
