#!/usr/bin/env python3
"""Make the predtimechart opening view robust to targets with uneven coverage.

hub-dashboard-predtimechart computes `initial_as_of` as the maximum reference
date across ALL targets, but predtimechart validates that value against only
`available_as_ofs[initial_target_var]` (the FIRST target). If any other target
has a forecast for a later reference date than the first target, the page fails
to load with:

    initial_as_of not in available_as_ofs: <date>

This rewrites the generated predtimechart-options.json so the opening view is
always self-consistent:

1. If `initial_target_var` has no forecasts at all, switch it (and
   `initial_task_ids`) to the target with the most recent forecast.
2. Snap `initial_as_of` to the latest date in the initial target's own
   `available_as_ofs`.
3. Ensure `current_date` is the latest date across ALL targets. It is NOT
   validated against any per-target list and must NOT be snapped down: it
   selects which snapshot of truth/target data is drawn as the "Current" line
   (legend shows "Current (<date>)"), and truth files are generated for every
   reference date regardless of forecast submissions. Snapping it down would
   show stale surveillance data.

Run it against the built data directory (the checked-out `ptc/data` branch),
AFTER prune_ptc_locations.py:

    python fix_ptc_initial_as_of.py <data_dir>

where <data_dir> contains predtimechart-options.json. Data-driven and
idempotent: it never hardcodes dates, so it stays correct as seasons roll over.
"""
import json, sys, pathlib

data_dir = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else ".")
opts_path = data_dir / "predtimechart-options.json"

opts = json.loads(opts_path.read_text())

available = opts.get("available_as_ofs", {})  # target_id -> [iso dates]
initial_tv = opts.get("initial_target_var")
changed = False

all_dates = [d for dates in available.values() for d in dates]
if not all_dates:
    print("no target has any forecasts; nothing to fix")
    sys.exit(0)
global_max = max(all_dates)

# 1. If the initial target has no forecasts, fall back to the target whose
#    latest forecast is most recent (ties broken by target order in the file).
if not available.get(initial_tv):
    initial_tv = max((max(dates), tv) for tv, dates in available.items()
                     if dates)[1]
    opts["initial_target_var"] = initial_tv
    # rebuild initial_task_ids from the new target's own task options
    new_task_ids = opts.get("task_ids", {}).get(initial_tv, {})
    opts["initial_task_ids"] = {task_id: options[0]["value"]
                                for task_id, options in new_task_ids.items()
                                if options}
    changed = True
    print(f"initial_target_var had no forecasts; switched to {initial_tv!r}")

# 2. Snap initial_as_of (the only field predtimechart validates per-target)
#    to a date the initial target actually has.
valid = set(available[initial_tv])
if opts.get("initial_as_of") not in valid:
    latest = max(valid)
    print(f"initial_as_of: {opts.get('initial_as_of')!r} not in "
          f"{initial_tv!r}'s available_as_ofs; snapping to {latest!r}")
    opts["initial_as_of"] = latest
    changed = True

# 3. current_date must track the GLOBAL latest date (freshest truth snapshot).
#    Do not snap it down with initial_as_of; it is not validated per-target.
if opts.get("current_date") != global_max:
    print(f"current_date: {opts.get('current_date')!r} -> {global_max!r} "
          "(latest date across all targets)")
    opts["current_date"] = global_max
    changed = True

if changed:
    opts_path.write_text(json.dumps(opts, indent=2))
    print("wrote", opts_path)
else:
    print("no change (opening view already consistent)")
