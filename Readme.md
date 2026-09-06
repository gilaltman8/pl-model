# Premier League 2026/27 — Dixon–Coles model

Live league table, model-based team ratings, match predictions, and a Monte Carlo
projection of the season — refreshed automatically after every matchweek.

```
index.html                     the whole app — no build step, no dependencies
data.json                      match data, rewritten automatically by the Action
scripts/build_data.py          fetches results, writes data.json
.github/workflows/update.yml   cron: refresh data + deploy to GitHub Pages
```

---

## Setup

Everything runs in the browser — no terminal, no git, no local Python. The full
click-by-click walkthrough with verification checkpoints is in
**[SETUP.md](SETUP.md)**.

The short version, if you've done this before:

1. Create a **public** repo on github.com.
2. **Add file → Create new file**, type the path `.github/workflows/update.yml`,
   paste the workflow, commit. (Typing the path is how you create folders;
   drag-and-drop drops hidden `.github` folders.)
3. Same again for `scripts/build_data.py`, then **Upload files** for
   `index.html`, `data.json` and `README.md`.
4. **Settings → Actions → General → Workflow permissions → Read and write.**
5. **Settings → Pages → Source → GitHub Actions.**
6. **Actions → Update data and deploy → Run workflow.**

Live at `https://YOUR_USER.github.io/YOUR_REPO/` about a minute later.

---

## Weekly operation

Nothing. After a matchweek finishes, the night's run picks up the results,
commits `data.json`, and redeploys. Check the **Actions** tab if the site looks
stale; force a refresh any time with **Run workflow**.

## Things you'll want to do eventually

**Update it right now instead of waiting for the cron** — Actions → "Update data
and deploy" → **Run workflow**. Nothing to run locally.

**Change league or season** — edit the constants at the top of
`scripts/build_data.py`:

```python
SEASON      = "2026-27"   # openfootball folder name
FD_CODE     = "2627"      # football-data.co.uk season code
PREV_SEASON = "2025-26"
LEAGUE_JSON = "en.1"      # en.1 EPL · es.1 La Liga · it.1 Serie A · de.1 Bundesliga
FD_LEAGUE   = "E0"        # E0  EPL · SP1 La Liga  · I1  Serie A  · D1  Bundesliga
```

Next summer that means bumping the three season constants — a two-minute job.

**Tune the model defaults** — the sliders in the UI are per-visitor. To change
what visitors see by default, edit the two `value="..."` attributes of `#hl`
(last-season half-life, days) and `#rg` (shrinkage) in `index.html`.

**Edit any file in the browser** — open the file on github.com and click the
pencil, or press `.` anywhere in the repo to get VS Code in the browser
(github.dev). Committing to `main` redeploys automatically.

**Preview before deploying?** You don't need a local server — the deployed page
IS the preview; every commit redeploys in ~1 minute. (If you ever do want it
locally: `python3 -m http.server 8000` in the folder, because browsers block
`fetch` on `file://`.)

## Troubleshooting

| Symptom | Cause / fix |
|---|---|
| Action fails on `git push` (403) | Step 4 skipped — enable Read and write permissions |
| Site 404s | Step 5 — Pages source must be "GitHub Actions" |
| `X result(s) did not match a fixture` in the log | A team-name spelling differs between sources; add it to `NORM` in `build_data.py` |
| Results a matchweek behind | football-data.co.uk not updated yet (rare, hours after a round) — rerun later |
| Ratings look insane | Shrinkage slider at 0 early in the season — that's the identifiability demo, move it back up |

## The model, briefly

Home goals ~ Poisson(λ), away ~ Poisson(μ), λ = α_home·β_away·γ, μ = α_away·β_home;
Dixon & Coles (1997) low-score correction τ(ρ); all 42 parameters by maximum
likelihood (Adam on the exact log-likelihood), attack centred for identifiability.
Early-season identifiability is handled by exponentially time-decayed
previous-season matches plus a ridge penalty toward league average, and promoted
teams start from a prior measured from the previous promoted cohort. Full write-up
in the "How this works" section at the bottom of the page.
