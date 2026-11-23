# NOPs Large Fire Growth Days

Weather on large fire growth days in North Ops (ONCC) Predictive Service Areas NC01–NC08, 2012–2026, and a live dashboard that scores current and forecast conditions against what large growth days have looked like in the past.

## The dashboard

`index.html` is a static web page (with its data in `dashboard_data.js`). Each time it opens, it pulls RAWS observations, FEMS daily forecasts and NFDRS fuel model Y indices straight from the public [FEMS](https://fems.fs2c.usda.gov/) climatology services. It needs no server, scheduler, API key or ArcGIS license.

It shows:

- **Concern by PSA.** A map of the 9 PSAs colored by concern level for the selected day: today's observation or one of the next 6 forecast days.
- **7-day outlook.** A grid of PSAs by day, with concern level and score. ▲ marks a large wind event.
- **PSA detail.** Each variable's value against that PSA's threshold, plus other conditions.
- **Where this day sits in history.** The selected day's values plotted against the typical ranges on large growth days and on other fire-days in that PSA.
- **History for the PSA.** The large growth rate at each concern level, large growth days by month, and the biggest growth days.

### How the score works

Each PSA has a threshold for 8 variables: ERC, BI, IC, FFWI, peak gust, average VPD, max RH and 100-hr fuel moisture. Each threshold is the median value on that PSA's large growth days, 2012–2026. A day gets one point for each threshold it meets, and the total sets the concern level:

- Low: 0–1
- Moderate: 2–3
- High: 4–5
- Very High: 6–8

Forecast days don't include FFWI or average VPD, so their score is scaled to 8 from the 6 variables available.

Across North Ops, 19% of fire-days at Low were large growth days, compared with 36% at Very High. The score works best in NC01–NC05. In NC06–NC08 weather alone separates large growth days poorly. See `data/DATA_DICTIONARY.md` for the full analysis and caveats.

Concern levels describe how similar conditions are to past large growth days. They are not a forecast of fire behavior.

### Viewing it

- **GitHub Pages:** in repo Settings → Pages, choose "Deploy from a branch", then `main` and `/ (root)`. The dashboard is then served at `https://<owner>.github.io/<repo>/`.
- **Locally:** download `index.html` and `dashboard_data.js` into one folder and open `index.html`.

## Repository layout

| Path | What it is |
|---|---|
| `index.html` | The dashboard page |
| `dashboard_data.js` | Station lists, thresholds and historical statistics the page loads (generated) |
| `scripts/build_dashboard.py` | Rebuilds `dashboard_data.js` from the historical CSV and the thresholds in the update script |
| `scripts/nops_psa_conditions_update.py` | Updates the ArcGIS Online layer "NOPs PSA Fire Weather Conditions" (NIFC org) with the same calculations. Holds the PSA station lists and thresholds. |
| `data/NOPs_Large_Fire_Growth_Days_2012_2026_SIG_Weather.csv` | 4,950 large fire-days with PSA SIG weather, lightning and event flags |
| `data/NOPs_2012_2020_FireFamilyPlus_SIG_Values_Archive.csv` | Original FireFamily+ values for 2012–2020, replaced in the main file by FEMS values |
| `data/psa_thresholds.json` | Per-PSA thresholds used for scoring |
| `data/DATA_DICTIONARY.md` | Column reference, methods, analysis and known issues |
| `.github/workflows/update-agol-layer.yml` | Optional GitHub Actions job to run the ArcGIS Online update on a schedule (off by default) |

## Updating

- **Changing stations or thresholds:** edit `PSA_STATIONS`, `THRESHOLDS` and `HIST_LGD_RATE` in `scripts/nops_psa_conditions_update.py`, then run `python scripts/build_dashboard.py` (needs `pandas`) to regenerate `dashboard_data.js`.
- **Adding a season of fire data:** update the CSV in `data/`, recompute the thresholds, and rebuild.

## ArcGIS Online layer (optional)

`scripts/nops_psa_conditions_update.py` writes the same PSA scores to a hosted feature layer, so an ArcGIS Dashboard can use them. It can run in two ways:

- In an ArcGIS Notebook.
- Anywhere with Python 3 and `pip install arcgis pandas requests`, with the account set in the `AGOL_USER` and `AGOL_PASS` environment variables.

The GitHub Actions workflow is one way to schedule it. Check with your ArcGIS admin before storing a shared account's password as a repository secret.

## Data sources

- FEMS ext-climatology web services (RAWS observations, forecasts, NFDRS indices)
- NOAA NCEI NLDN lightning tile summaries
- WFIGS incident locations and NIFC PSA boundaries
- USGS 3DEP elevation
- VIIRS fire perimeters and FireFamily+ SIG listings supplied by ONCC Predictive Services
