# DMA-PRIME Model Challenge Dashboard

The dashboard for the [DMA-PRIME Model
Challenge](https://github.com/bleicham/DMA-PRIME-Model-Challenge-Sandbox), built with
[hub-dashboard-control-room](https://github.com/hubverse-org/hub-dashboard-control-room).

It renders two pages from the hub's data: a **forecast** page
([predtimechart](https://github.com/hubverse-org/hub-dashboard-predtimechart)) and an
**evaluation** page
([hubPredEvalsData](https://github.com/hubverse-org/hubPredEvalsData)).

## Configuration

| File | Purpose |
|---|---|
| `site-config.yml` | Which hub to read, and the site title |
| `predtimechart-config.yml` | Forecast page: round, column names, initial view |
| `predevals-config.yml` | Evaluation page: targets, metrics, evaluation sets |
| `pages/index.qmd` | Landing page content |

> [!IMPORTANT]
> `site-config.yml > hub` must match `hub-config/admin.json > repository` in the hub
> repo (`owner/name`). If they disagree, the build fails or reads the wrong hub.

### Forecast page

All six hub targets appear in the target dropdown. This works because the hub uses a
**single round** in `tasks.json`: predtimechart can only plot one `rounds` entry, so
splitting seasons into separate rounds would hide every season but one.

`initial_checked_models` is currently empty, since no models have submitted yet. Add
model ids there once teams begin submitting, so the plot is populated on load.

### Evaluation page

Configured for all six targets with WIS, absolute error of the median, and 50% / 95%
interval coverage, disaggregated by location, reference date, horizon, and target end
date. Evaluation sets are defined per respiratory virus season.

> [!WARNING]
> Do not compare WIS across the hospitalization and ED visit targets. Counts and
> proportions differ by orders of magnitude, so an average across both is
> meaningless. Compare within a target, or use relative WIS against a common
> baseline.

Reference dates in `predevals-config.yml` are generated from the hub's `tasks.json`
rather than typed by hand. When a season is added to the hub, regenerate them rather
than editing the lists.

## Builds

| Workflow | Trigger | Purpose |
|---|---|---|
| `build-data.yaml` | Thursdays 17:33 UTC, on config push, manual | Rebuild forecast and evaluation data |
| `build-site.yaml` | Push to main, manual | Rebuild the Quarto site |

The hub refreshes its target data on **Wednesdays at 18:00 UTC**, so the Thursday
build picks up the new week.

> [!NOTE]
> The forecast page builds **incrementally** by default. A model added mid-season
> only appears for reference dates built after it was added, unless you run
> `build-data.yaml` manually with **regenerate** checked. The evaluation page
> recomputes in full every run, so it is not affected.

Generated pages (`pages/forecast.qmd`, `pages/evaluation.qmd`, and friends) are
gitignored: they are produced during the build, not stored here.
