# Flyvevejr: instruktioner til Claude Code

## Start altid i en separat worktree

Før du ændrer, committer eller pusher noget, så opret en git worktree til
sessionen og arbejd i den. Rør ikke hovedmappen `/home/jens/AI/Flyvevejr`.

```bash
git -C /home/jens/AI/Flyvevejr fetch origin
git -C /home/jens/AI/Flyvevejr worktree add .claude/worktrees/<emne> -b <emne> origin/main
cd /home/jens/AI/Flyvevejr/.claude/worktrees/<emne>
```

(Eller Claude Codes egen worktree-funktion, som også lægger dem i
`.claude/worktrees/`, der er i `.gitignore`.)

**Hvorfor:** flere sessioner arbejder ofte samtidig i dette repo. Deler de
samme mappe, deler de også commits: 5. og 6. oktober 2026 pushede én session
to gange en anden sessions lokale commits med, før brugeren var blevet
spurgt, og en session kunne ikke pulle, fordi en anden havde ucommittede
ændringer liggende.

**Sådan:**
- Commit på worktreens egen gren. Spørg brugeren før push.
- Ved push til main: `git fetch origin && git rebase origin/main`, derefter
  `git push origin HEAD:main`. main flytter sig hele tiden, fordi
  forecast-kørslen committer data (`termik/output/data/`) seks gange om
  dagen; den rebase er altid ren, fordi datacommits kun rører de filer.
- Testene kører med system-Python fra worktreen: `python3 -m pytest termik/tests -q`.
- Ryd op når arbejdet er pushet: `git worktree remove .claude/worktrees/<emne>`
  og `git branch -d <emne>`.

## Hvor tingene står

- Projektet: `docs/PROJEKT-DOKUMENTATION.md`.
- Seneste status og åbne punkter: den nyeste `docs/Referat/*-overdragelse*.md`.
- Driften (selvhostet runner på OMV, kørselsplan, Open-Meteo-kvote):
  `docs/Referat/2026-09-02-api-robusthed.md` og PROJEKT-DOKUMENTATION,
  afsnittet GitHub Actions. Ingen workflow må få en `pull_request`-trigger:
  repoet er offentligt, og forecast-jobbet kører på en maskine derhjemme.
