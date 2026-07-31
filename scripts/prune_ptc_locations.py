#!/usr/bin/env python3
"""Prune the predtimechart Location dropdown to locations that actually have
forecasts.

predtimechart builds the Location options from the hub's tasks.json (every
forecastable location), not from the forecasts that exist. This rewrites the
generated predtimechart-options.json so each target's `location` options are
limited to locations that appear in the generated forecast files, and fixes
`initial_task_ids` so the opening view lands on a location that has data.

Run it against the built data directory (the checked-out `ptc/data` branch):

    python prune_ptc_locations.py <data_dir>

where <data_dir> contains predtimechart-options.json and forecasts/.
It is data-driven: as more models/states submit, the list grows on its own.
Assumes `location` is the only task-id in the forecast filenames
(<target-slug>_<location>_<reference-date>.json), which is this hub's layout.
"""
import json, sys, pathlib, collections

data_dir = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else ".")
opts_path = data_dir / "predtimechart-options.json"
forecasts_dir = data_dir / "forecasts"

opts = json.loads(opts_path.read_text())

# target-slug -> set of locations that have >=1 forecast file
locs_by_slug = collections.defaultdict(set)
for f in forecasts_dir.glob("*.json"):
    parts = f.stem.split("_")            # [slug, location, reference_date]
    if len(parts) < 3:
        continue
    slug, location = parts[0], "_".join(parts[1:-1])
    locs_by_slug[slug].add(location)

changed = False
for target_key, task_ids in opts.get("task_ids", {}).items():
    if "location" not in task_ids:
        continue
    slug = target_key.replace(" ", "-")
    have = locs_by_slug.get(slug, set())
    kept = [o for o in task_ids["location"] if o["value"] in have]
    if kept and len(kept) != len(task_ids["location"]):
        task_ids["location"] = kept
        changed = True
    # make sure the opening view points at a location with data
    init = opts.get("initial_task_ids", {})
    if kept and init.get("location") not in {o["value"] for o in kept}:
        init["location"] = kept[0]["value"]
        changed = True

if changed:
    opts_path.write_text(json.dumps(opts, indent=2))
    print(f"pruned locations -> { {k: sorted(v) for k, v in locs_by_slug.items()} }")
else:
    print("no change (every location already has forecasts, or none to prune)")
