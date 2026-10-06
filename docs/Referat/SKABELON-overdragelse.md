# Skabelon: overdragelse

En overdragelse skrives sidst i hver session, så næste session (menneske
eller Claude) kan fortsætte uden at spørge. Den er kort; tal og
begrundelser står i emne-referatet, som overdragelsen linker til.

**Filnavn:** `docs/Referat/YYYY-MM-DD-overdragelse[-emne].md`. Flere samme
dag: `-2`, eller et emne-suffiks (`-termikfarver`).

**Regler:**
- Dansk, ingen tankestreg. Prompten nederst er på engelsk.
- Hvert tal har enhed og datum: m QNH / m QFE, W/m², kt, UTC.
- Skriv også det der blev undersøgt og **ikke** ændret, og hvorfor.
- Åbne punkter opdateres i `docs/AABNE-PUNKTER.md`; overdragelsen nævner
  kun numrene der blev rørt og de nye.
- Commits i tabellen skal være pushet. Er noget ikke pushet, så sig det.

Kopiér herfra:

````markdown
# Overdragelse YYYY-MM-DD: <emne>

Fortsættelse af [<forrige overdragelse>](<fil>). Tal og begrundelser står i
[<referat>](<fil>). Analysescripts i [YYYY-MM-DD-analyse/](YYYY-MM-DD-analyse/README.md).
Prompt til at fortsætte står nederst.

## Kort fortalt

| Emne | Resultat | Scores ændret? |
|---|---|---|
| | | Ja (n timer) / Nej |

<Én til tre sætninger: hvad er ændret i produktion, og hvad er kun analyse.>

## Commits

| Commit | Indhold |
|---|---|
| `abc1234` | |

Pushet til main: ja / nej (hvorfor).

## 1. <Emne>

<Data, metode, resultat. Valideret på hvilke dage, og var de med i
tilpasningen? Hvad blev afvist, og hvorfor?>

## Data og værktøjer

<Nye datakilder, hentninger, hvor mange API-kald det kostede, kommandoer
brugeren selv skal køre.>

## Faldgruber fra i dag

- <Det der kostede tid og vil gøre det igen. Varige faldgruber flyttes også
  til CLAUDE.md eller `.claude/rules/`.>

## Åbne punkter

Ændret status: <numre og hvad der skete>. Nye: <numre>. Se
[AABNE-PUNKTER.md](../AABNE-PUNKTER.md).

Forslag til næste session: **<numre>**.

## Prompt til at fortsætte

```
Continue the Flyvevejr work from docs/Referat/YYYY-MM-DD-overdragelse.md.
Read it first, then docs/AABNE-PUNKTER.md.

Work through these one at a time. For each, show me the findings before
changing production code, validate any scoring change on days the rule was
not fitted on, write tests first, update the referat, PROJEKT-DOKUMENTATION
and AABNE-PUNKTER, and commit. Ask before pushing.

<nr>. <Opgaven, konkret nok til at starte uden spørgsmål.>
```
````
