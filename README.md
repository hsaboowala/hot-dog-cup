# Hot Dog Cup 26/27

Live standings for the 2026-27 NBA wins bet. Six players, four teams each. Most wins collects $25 from everyone else, and fewest wins eats 69 hot dogs.

- `index.html` is the whole site. It reads the three files in `data/`.
- `data/picks.json` holds the draft picks and Vegas totals. Edit this if a pick ever changes.
- `data/standings.json` and `data/history.json` are rewritten every morning by `.github/workflows/update-standings.yml`, which runs `scripts/update_standings.py`.

Standings come from Basketball Reference, with ESPN as a backup. If neither source returns all 30 teams, the run fails and leaves the data alone. GitHub emails the repo owner when a run fails.

To refresh by hand, go to the **Actions** tab, open **Update standings** and click **Run workflow**.
