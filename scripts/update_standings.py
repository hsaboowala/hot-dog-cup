"""Fetch current NBA standings and update data/standings.json and data/history.json.

Runs daily from GitHub Actions. Primary source is Basketball Reference; ESPN's
public standings API is the fallback. Writes nothing unless all 30 teams parse.
"""
import html
import json
import re
import sys
import urllib.request
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

SEASON_END_YEAR = 2027  # 2026-27 season
BREF_URL = f"https://www.basketball-reference.com/leagues/NBA_{SEASON_END_YEAR}_standings.html"
ESPN_URL = f"https://site.api.espn.com/apis/v2/sports/basketball/nba/standings?season={SEASON_END_YEAR}"
DATA = Path(__file__).resolve().parent.parent / "data"
UA = {"User-Agent": "Mozilla/5.0 (hot-dog-cup standings tracker; one request per day)"}

# Names as used in data/picks.json; ESPN uses "LA Clippers".
ALIASES = {"LA Clippers": "Los Angeles Clippers"}


def get(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8", "replace")


def from_bref():
    page = get(BREF_URL)
    out = {}
    for table_id, conf in (("confs_standings_E", "East"), ("confs_standings_W", "West")):
        m = re.search(rf'<table[^>]*id="{table_id}".*?</table>', page, re.S)
        if not m:
            raise ValueError(f"table {table_id} not found")
        for row in re.findall(r"<tr[^>]*>(.*?)</tr>", m.group(0), re.S):
            name = re.search(r'data-stat="team_name"[^>]*>.*?<a[^>]*>(.*?)</a>', row, re.S)
            w = re.search(r'data-stat="wins"[^>]*>(\d+)<', row)
            l = re.search(r'data-stat="losses"[^>]*>(\d+)<', row)
            if name and w and l:
                team = html.unescape(name.group(1)).strip()
                out[team] = {"team": team, "conference": conf, "wins": int(w.group(1)), "losses": int(l.group(1))}
    return list(out.values())


def from_espn():
    data = json.loads(get(ESPN_URL))
    out = {}
    for child in data.get("children", []):
        conf = "East" if "East" in child.get("name", "") else "West"
        for e in child.get("standings", {}).get("entries", []):
            team = ALIASES.get(e["team"]["displayName"], e["team"]["displayName"])
            stats = {s.get("name"): s.get("value") for s in e.get("stats", [])}
            out[team] = {"team": team, "conference": conf, "wins": int(stats["wins"]), "losses": int(stats["losses"])}
    return list(out.values())


def main():
    picks = json.loads((DATA / "picks.json").read_text())
    standings, errors = None, []
    for name, fn in (("Basketball Reference", from_bref), ("ESPN", from_espn)):
        try:
            rows = fn()
            if len(rows) != 30:
                raise ValueError(f"got {len(rows)} teams, expected 30")
            missing = {p["team"] for p in picks} - {r["team"] for r in rows}
            if missing:
                raise ValueError(f"picked teams not found: {sorted(missing)}")
            standings = rows
            print(f"Standings from {name}")
            break
        except Exception as exc:  # try the next source
            errors.append(f"{name}: {exc}")
    if standings is None:
        print("No usable standings source:\n  " + "\n  ".join(errors))
        sys.exit(1)

    standings.sort(key=lambda r: (r["conference"], -r["wins"], r["losses"]))
    (DATA / "standings.json").write_text(json.dumps(standings, indent=1) + "\n")

    today = datetime.now(ZoneInfo("America/Chicago")).date().isoformat()
    hist_path = DATA / "history.json"
    history = json.loads(hist_path.read_text()) if hist_path.exists() else []
    history = [h for h in history if h["date"] != today]
    history += [{"date": today, "team": r["team"], "wins": r["wins"], "losses": r["losses"]} for r in standings]
    hist_path.write_text(json.dumps(history, separators=(",", ":")) + "\n")

    wins = {r["team"]: r["wins"] for r in standings}
    totals = {}
    for p in picks:
        totals[p["player"]] = totals.get(p["player"], 0) + wins[p["team"]]
    print(" | ".join(f"{k} {v}" for k, v in sorted(totals.items(), key=lambda kv: -kv[1])))


if __name__ == "__main__":
    main()
