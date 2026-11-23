# NOPs Large Fire Growth Days

Weather on large fire growth days in North Ops (ONCC) Predictive Service Areas NC01–NC08, 2012–2026, and a live dashboard that scores current and forecast conditions against what large growth days have looked like in the past.

## The dashboard

`index.html` is a static web page (with its data in `dashboard_data.js`). Each time it opens, it pulls RAWS observations, FEMS daily forecasts and NFDRS fuel model Y indices straight from the public [FEMS](https://fems.fs2c.usda.gov/) climatology services. It needs no server, scheduler, API key or ArcGIS license.

It has four tabs:

- **Outlook** (live):
  - a map of the 9 PSAs colored by concern level for today's observation or any of the next 6 forecast days
  - a 7-day outlook grid of concern level and score
  - a **wind outlook** of each PSA's peak gust and direction against its large wind event threshold
  - PSA detail, where the selected day sits in that PSA's history, and the PSA's large growth history
- **Large growth days:** weather on large growth days compared with other fire-days for 16 variables, filterable by PSA, years, months and event type (wind events, lightning clusters, 50+ strikes in the prior 3 days, 3+ large fire starts). It includes:
  - a table ranking which variables separate large growth days best
  - peak gust direction roses for large growth days and other fire-days
  - a sortable table of every large growth day and its weather
- **Wind events** (days the PSA-average peak gust reached the PSA's 90th percentile threshold):
  - the live wind outlook
  - the large growth rate on wind event days compared with other days, by PSA
  - gust direction roses, with offshore events showing up as north–east gusts
  - wind event days by month
  - a table of wind event days
- **Lightning:**
  - the large growth rate by the number of strikes in the prior 3 days
  - large growth days after lightning, by year
  - a table of large growth days that followed lightning

  This is historical NLDN data; the dashboard doesn't include live lightning.

The history tabs read `data/history_rows.json`, or `data/history_rows.js` when `index.html` is opened as a local file, so keep the `data` folder next to `index.html`.

### How the score works

Each PSA has a threshold for 8 variables: ERC, BI, IC, FFWI, peak gust, average VPD, max RH and 100-hr fuel moisture. Each threshold is the median value on that PSA's large growth days, 2012–2026. A day gets one point for each threshold it meets, and the total sets the concern level:

- Low: 0–1
- Moderate: 2–3
- High: 4–5
- Very High: 6–8

**How each day is built.** Every column, observed or forecast, is built the same way as the history the thresholds come from:

- values at 1300 LST for temperature, RH, wind and the fire danger indices
- daily max and average over the LST day for max temperature, max RH, peak gust and VPD
- rain over the 24 hours to 1300

The page uses FEMS hourly observations where they exist, and FEMS hourly forecasts for the hours after them. Between 1 PM Pacific and midnight, the observed column's daily values include forecast hours for the rest of the day, and the PSA detail panel says so.

**Where the level is a weak guide.** In PSAs where the large growth rate at Very High is less than 10 points above Low (currently NC06), the PSA detail panel and map pop-up add a ⚠ note. In that PSA lightning and new large fire starts have mattered more than the weather score.

**Fuel gate.** A day can't score above Low if either of these is true:

- ERC is below the 5th percentile of that PSA's large growth days.
- 100-hr fuel moisture is above the 95th percentile.

Such days are marked ⊘, meaning fuels are not receptive. This stops wind or dry air alone from raising the level when the fuels can't carry fire, for example a November east wind event. Tested on 2012–2026, it capped 26 of 1,456 large growth days that had scored Moderate or higher, which is 0.5% of large-growth acres. None of those had scored Very High. The gate values are in `data/psa_thresholds.json` (`_gate_ERC`, `_gate_F100`).

Across North Ops, 22% of fire-days at Low were large growth days, compared with 47% at Very High. The score works best in NC01–NC04. In NC05–NC07 weather alone separates large growth days less well. See `data/DATA_DICTIONARY.md` for the full analysis and caveats.

Concern levels describe how similar conditions are to past large growth days. They are not a forecast of fire behavior.

### Viewing it

- **GitHub Pages:** in repo Settings → Pages, choose "Deploy from a branch", then `main` and `/ (root)`. The dashboard is then served at `https://<owner>.github.io/<repo>/`.
- **Locally:** download or clone the repo and open `index.html`. Keep `dashboard_data.js` and the `data` folder beside it.

## Repository layout

| Path | What it is |
|---|---|
| `index.html` | The dashboard page |
| `dashboard_data.js` | Station lists, thresholds and historical statistics the page loads (generated) |
| `data/history_rows.json`, `data/history_rows.js` | One row per fire-day with the fields the history tabs use; the `.js` copy is for opening the page as a local file (generated) |
| `scripts/build_dashboard.py` | Rebuilds `dashboard_data.js` and the `data/history_rows` files from the historical CSV and the thresholds in the update script |
| `scripts/nops_psa_conditions_update.py` | Updates the ArcGIS Online layer "NOPs PSA Fire Weather Conditions" (NIFC org) with the same calculations. Holds the PSA station lists and thresholds. |
| `data/NOPs_Large_Fire_Growth_Days_2012_2026_SIG_Weather.csv` | 4,623 large fire-days with PSA SIG weather, lightning and event flags |
| `data/NOPs_2012_2020_FireFamilyPlus_SIG_Values_Archive.csv` | Original FireFamily+ values for 2012–2020, replaced in the main file by FEMS values |
| `data/removed_late_perimeter_records.csv` | 47 rows dated years after their fire (final perimeters re-saved later), removed |
| `data/merged_duplicate_rows.csv` | The original rows of 228 fire-days that were split across 2–3 rows and merged |
| `scripts/clean_dataset.py` | The clean-up that removed late perimeter records and merged same-day duplicate rows (safe to re-run) |
| `scripts/flag_large_growth.py` | Sets the large growth day flag from the ONCC threshold chart: 25% of to-date acres, PSA minimums, capped at 10,000 ac (safe to re-run) |
| `scripts/lfm_skill_test.js` | Live fuel moisture test (browser console); results in `data/LFM_TEST_RESULTS.md` |
| `data/removed_rx_pile_burn_fire_days.csv` | 20 off-season fire-days removed as Rx or pile burns (see the data dictionary) |
| `scripts/compute_thresholds.py` | Recomputes fire-start counts, wind event thresholds, scoring thresholds, the fuel gate and historical rates from the dataset |
| `data/psa_thresholds.json` | Per-PSA thresholds used for scoring |
| `data/DATA_DICTIONARY.md` | Column reference, methods, analysis and known issues |
| `.github/workflows/update-agol-layer.yml` | Optional GitHub Actions job to run the ArcGIS Online update on a schedule (off by default) |

## Updating

- **Changing stations or thresholds:** edit `PSA_STATIONS`, `THRESHOLDS` and `HIST_LGD_RATE` in `scripts/nops_psa_conditions_update.py`, then run `python scripts/build_dashboard.py` (needs `pandas`) to regenerate `dashboard_data.js`.
- **Adding a season of fire data, or removing rows:** update the CSV in `data/`, then run `python scripts/clean_dataset.py`, `python scripts/flag_large_growth.py`, `python scripts/compute_thresholds.py` and `python scripts/build_dashboard.py`.

## ArcGIS Online layer (not maintained)

`scripts/nops_psa_conditions_update.py` and the GitHub Actions workflow were written to push the same scores to a hosted feature layer in ArcGIS Online, "NOPs PSA Fire Weather Conditions" in the `oncc_oscc_scripting` account, for an ArcGIS Dashboard.

That route was set aside on November 23, 2026 in favor of this GitHub Pages dashboard, so the layer isn't updated. The script still scores forecast days from FEMS daily summaries, which run higher than 1300 values. If the ArcGIS route is picked up again, the script should first be brought in line with the page's hourly method.

## Data sources

- FEMS ext-climatology web services (RAWS observations, forecasts, NFDRS indices)
- NOAA NCEI NLDN lightning tile summaries
- WFIGS incident locations and NIFC PSA boundaries
- USGS 3DEP elevation
- VIIRS fire perimeters and FireFamily+ SIG listings supplied by ONCC Predictive Services
