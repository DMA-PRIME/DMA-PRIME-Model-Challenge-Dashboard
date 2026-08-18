#!/usr/bin/env python3
"""Point the dashboard's "Current" truth line at the latest ACTUAL data week.

hub-dashboard-predtimechart only generates target-data (truth) json files up
through the latest FORECAST reference date, and sets `current_date` from
forecast dates too. When submissions pause (e.g. the off-season), the "Current"
line freezes at the last submitted week even though the hub's target data keeps
updating weekly.

This script fixes that by reading the hub's versioned time-series target data
directly:

1. Finds the latest data snapshot date (max `as_of` in
   target-data/time-series.parquet).
2. Generates the missing truth json files for that date -- one per
   (target, location) pair already present in the built `targets/` dir -- in
   the exact upstream format: {"date": [iso...], "y": [...]} sorted by date,
   filtered to that snapshot.
3. Sets `current_date` in predtimechart-options.json to that date, so the
   legend reads "Current (<latest data week>)" and the plot fetches the truth
   files written in step 2.

Run AFTER fix_ptc_initial_as_of.py (which manages `initial_as_of`; this script
only ever advances `current_date`):

    python extend_ptc_targets.py <hub_dir> <data_dir>

where <hub_dir> is a checkout of the hub repo (contains
target-data/time-series.parquet) and <data_dir> is the checked-out `ptc/data`
branch (contains predtimechart-options.json and targets/). Idempotent and
data-driven: no hardcoded dates.
"""
import json
import pathlib
import sys

import polars as pl

hub_dir = pathlib.Path(sys.argv[1])
data_dir = pathlib.Path(sys.argv[2])
ts_path = hub_dir / "target-data" / "time-series.parquet"
targets_dir = data_dir / "targets"
opts_path = data_dir / "predtimechart-options.json"

if not ts_path.exists():
    print(f"{ts_path} not found; nothing to do")
    sys.exit(0)

df = pl.read_parquet(ts_path)
latest = df["as_of"].max()  # newest data snapshot
latest_iso = latest.isoformat() if not isinstance(latest, str) else latest
snapshot = df.filter(pl.col("as_of") == latest)

# (target slug, location) pairs the dashboard already knows about, from the
# built targets dir. File names are {target-slug}_{location}_{date}.json;
# slug = target id with spaces replaced by "-".
pairs = set()
for f in targets_dir.glob("*.json"):
    parts = f.stem.rsplit("_", 2)
    if len(parts) == 3:
        pairs.add((parts[0], parts[1]))

written, skipped = 0, 0
for slug, loc in sorted(pairs):
    out = targets_dir / f"{slug}_{loc}_{latest_iso}.json"
    if out.exists():
        skipped += 1
        continue
    target_id = slug.replace("-", " ")
    sub = (snapshot
           .filter(pl.col("target") == target_id)
           .filter(pl.col("location") == loc)
           .sort("target_end_date"))
    if len(sub) == 0:
        continue  # no data for this pair in the snapshot (e.g. PR for NSSP)
    out.write_text(json.dumps({
        "date": [d if isinstance(d, str) else d.isoformat()
                 for d in sub["target_end_date"].to_list()],
        "y": sub["observation"].to_list(),
    }, indent=4))
    written += 1

print(f"truth files for {latest_iso}: wrote {written}, "
      f"already present {skipped}")

opts = json.loads(opts_path.read_text())
current = opts.get("current_date")
# only ever move current_date FORWARD to the data snapshot; never backward
if current is None or str(current) < latest_iso:
    print(f"current_date: {current!r} -> {latest_iso!r} (latest data snapshot)")
    opts["current_date"] = latest_iso
    opts_path.write_text(json.dumps(opts, indent=2))
else:
    print(f"current_date already {current!r}; no change")
