#!/usr/bin/env python3
"""
Builds data.json for the Dixon-Coles dashboard.

Sources (both public, no API key):
  1. openfootball/football.json  -> full fixture list + results (may lag ~1 matchweek)
  2. football-data.co.uk E0.csv  -> authoritative results, updated within hours of each round

Strategy: take the fixture list from openfootball, then overlay football-data.co.uk
results on top so the site is current even when openfootball lags.

Usage:  python3 scripts/build_data.py
Writes: data.json
"""

import csv
import io
import json
import sys
import urllib.request
from datetime import datetime, timezone

SEASON = "2026-27"          # openfootball folder
FD_CODE = "2627"            # football-data.co.uk season code
PREV_SEASON = "2025-26"
LEAGUE_JSON = "en.1"        # English Premier League
FD_LEAGUE = "E0"

OF_URL = "https://raw.githubusercontent.com/openfootball/football.json/master/{s}/{l}.json"
FD_URL = "https://www.football-data.co.uk/mmz4281/{c}/{l}.csv"

# Map every source's naming to one canonical name.
NORM = {
    "Manchester United": "Man Utd", "Man United": "Man Utd", "Manchester Utd": "Man Utd",
    "Manchester City": "Man City",
    "Nottingham Forest": "Nott'm Forest", "Nott'ham Forest": "Nott'm Forest",
    "Tottenham Hotspur": "Tottenham", "Spurs": "Tottenham",
    "Brighton & Hove Albion": "Brighton", "Brighton and Hove Albion": "Brighton",
    "Newcastle United": "Newcastle",
    "West Ham United": "West Ham",
    "Wolverhampton Wanderers": "Wolves", "Wolverhampton": "Wolves",
    "AFC Bournemouth": "Bournemouth",
    "Leeds United": "Leeds",
    "Coventry City": "Coventry",
    "Hull City": "Hull",
    "Ipswich Town": "Ipswich",
    "Leicester City": "Leicester",
    "Sheffield United": "Sheffield Utd",
    "West Bromwich Albion": "West Brom",
}


def clean(name):
    n = (name or "").strip()
    for suf in (" FC", " AFC"):
        if n.endswith(suf):
            n = n[: -len(suf)].strip()
    return NORM.get(n, n)


def get(url, timeout=45):
    req = urllib.request.Request(url, headers={"User-Agent": "dc-model/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def load_openfootball(season):
    """Return [[date, home, away, hg, ag], ...]; goals are None for unplayed."""
    raw = json.loads(get(OF_URL.format(s=season, l=LEAGUE_JSON)).decode("utf-8"))
    out = []
    for m in raw["matches"]:
        s = m.get("score")
        ft = s.get("ft") if isinstance(s, dict) else (s if isinstance(s, list) else None)
        out.append([
            m["date"], clean(m["team1"]), clean(m["team2"]),
            ft[0] if ft else None, ft[1] if ft else None,
        ])
    return out


def load_footballdata(code):
    """Return {(home, away): (hg, ag, date)} from football-data.co.uk. [] on failure."""
    try:
        raw = get(FD_URL.format(c=code, l=FD_LEAGUE)).decode("utf-8-sig", errors="replace")
    except Exception as e:
        print(f"  ! football-data.co.uk unavailable ({e}) - using openfootball only", file=sys.stderr)
        return {}
    out = {}
    for row in csv.DictReader(io.StringIO(raw)):
        h, a = clean(row.get("HomeTeam")), clean(row.get("AwayTeam"))
        hg, ag = row.get("FTHG"), row.get("FTAG")
        if not h or not a or hg in (None, "") or ag in (None, ""):
            continue
        d = (row.get("Date") or "").strip()
        iso = ""
        for fmt in ("%d/%m/%Y", "%d/%m/%y"):
            try:
                iso = datetime.strptime(d, fmt).strftime("%Y-%m-%d")
                break
            except ValueError:
                pass
        out[(h, a)] = (int(float(hg)), int(float(ag)), iso)
    return out


def main():
    print(f"Fetching {SEASON} fixtures from openfootball ...")
    cur = load_openfootball(SEASON)
    print(f"  {len(cur)} fixtures, {sum(1 for r in cur if r[3] is not None)} with results")

    print(f"Fetching {SEASON} results from football-data.co.uk ...")
    fd = load_footballdata(FD_CODE)
    print(f"  {len(fd)} played matches")

    added = 0
    for r in cur:
        key = (r[1], r[2])
        if key in fd:
            hg, ag, iso = fd[key]
            if r[3] is None:
                added += 1
            r[3], r[4] = hg, ag
            if iso:
                r[0] = iso
    print(f"  overlaid {added} result(s) openfootball did not yet have")

    # Unmatched football-data rows mean a name normalisation gap - fail loudly.
    fixture_keys = {(r[1], r[2]) for r in cur}
    unmatched = [k for k in fd if k not in fixture_keys]
    if unmatched:
        print(f"  ! {len(unmatched)} result(s) did not match a fixture: {unmatched[:5]}", file=sys.stderr)
        print("    -> add the offending names to NORM in this script.", file=sys.stderr)

    print(f"Fetching {PREV_SEASON} (prior-season strength) ...")
    prev = load_openfootball(PREV_SEASON)
    prev = [r for r in prev if r[3] is not None]
    print(f"  {len(prev)} completed matches")

    teams = sorted({r[1] for r in cur} | {r[2] for r in cur})
    prev_teams = {r[1] for r in prev} | {r[2] for r in prev}
    promoted = [t for t in teams if t not in prev_teams]

    played = sum(1 for r in cur if r[3] is not None)
    if len(teams) != 20:
        print(f"  ! expected 20 teams, found {len(teams)}: {teams}", file=sys.stderr)

    data = {
        "season": SEASON.replace("-", "/"),
        "prevSeason": PREV_SEASON.replace("-", "/"),
        "league": "English Premier League",
        "updated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "teams": teams,
        "promoted": promoted,
        # Prior for promoted sides, from how the last promoted cohort actually performed.
        # The app recomputes this from prevMatches; these are the fallback values.
        "promotedPrior": {"a": -0.1648, "d": 0.2889},
        "matches": cur,
        "prevMatches": prev,
    }
    with open("data.json", "w") as f:
        json.dump(data, f, separators=(",", ":"))

    print(f"\nWrote data.json - {played}/{len(cur)} played, {len(teams)} teams, promoted: {promoted}")


if __name__ == "__main__":
    main()
