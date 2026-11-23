# NOPs Large Fire Growth Days, 2012–2026 — SIG Weather, Lightning and Event Flags

**File:** `NOPs_Large_Fire_Growth_Days_2012_2026_SIG_Weather.csv`
**Last updated:** November 23, 2026
**Rows:** 4,623 fire-days (one row per fire, per day, per PSA)
**Columns:** 45
**Companion files:** `NOPs_2012_2020_FireFamilyPlus_SIG_Values_Archive.csv` (original FireFamily+ values), `nops_psa_conditions_notebook.py` (ArcGIS Online update script)
**Coverage:** North Ops (ONCC) PSAs NC01–NC08, 2012 through October 2026

## Purpose

This table pairs every day of growth on North Ops large fires with the weather, fire danger, lightning and regional activity in that fire's PSA on that day. It's meant for finding which conditions separate large growth days from other fire-days, and for setting thresholds for an ONCC dashboard.

## How the data were built

| Piece | 2012–2020 (3,243 rows) | 2021–2026 (1,380 rows) |
|---|---|---|
| Fire days and sizes | VIIRS daily fire perimeters (user-provided) | VIIRS daily fire perimeters (user-provided) |
| Location (Lat/Long) | Centroid of that day's perimeter | Point of origin from WFIGS incident locations (same for every day of a fire) |
| Elevation | User-provided, binned to 1,000 ft | USGS 3DEP elevation at point of origin, rounded to nearest 1,000 ft (minimum 1,000) |
| SIG weather and indices | FEMS hourly observations, averaged across the PSA's RAWS (re-pulled Nov 2026; the original FireFamily+ values are in the archive file) | FEMS hourly observations, averaged across the PSA's RAWS |
| Wind / gust direction | FEMS hourly observations, averaged across the PSA's RAWS | FEMS hourly observations, averaged across the PSA's RAWS |
| Lightning | NOAA NCEI NLDN daily 0.1° tile counts | NOAA NCEI NLDN daily 0.1° tile counts |

**RAWS used:** the "2025 Winner Analysis for both" stations and WIMS IDs on the NOPS tab of `Winter_2025_RAWS.xlsx` (6–26 stations per PSA).

**Fuel model:** Y (NFDRS 2016) for all fire danger indices.

**Observation time:** 1300 LST (21:00 UTC) for observation-time values. The "day" for daily max/min/average values runs midnight to midnight LST.

## Column reference

### Fire identification and growth

| Column | Description |
|---|---|
| FID | Row ID from the source perimeter data. |
| Fire_ID | Fire identifier. In 2021–2026 it's the year plus the IRWIN ID. |
| DateText | Date of the fire-day. |
| FireName | Incident name. |
| PSANAME | PSA name from the perimeter data. |
| GACCUnitID | GACC unit (blank for 2012–2020). |
| PSANationa | PSA code (NC01–NC08) used to match weather, thresholds and fire-start counts. See the known issues for rows where this disagrees with PSANAME. |
| Lat, Long | Fire location in decimal degrees (WGS84). See "How the data were built" for the source by period. |
| Elevation_FT | Elevation in feet, binned to the nearest 1,000 ft. |
| Fire_Size | Acres burned on this day, rounded to a whole number. |
| Fire_Size_Cumulative | Total fire size through this day, in acres, rounded. |
| LargeFireFlag | 1 = the fire meets the large-fire definition (every row in this file is 1). |
| GrowthPercent | Percent growth from the prior day, rounded, as supplied. Blank on a fire's first day, and blank or 0 on many 2020–2026 rows; the dashboard computes growth % from Fire_Size and Fire_Size_Cumulative instead. |
| LGD_Cutoff_Acres | Acres of growth needed that day to count as a large growth day, from the ONCC threshold chart (see known issue 11). |
| LargeGrowthDayFlag | 1 = large fire growth day: Fire_Size at or above LGD_Cutoff_Acres. This is the target variable for analysis. |
| LargeGrowthDayFlag_Original | The flag as supplied with the perimeter data, before re-flagging on November 23, 2026. Kept for reference only. |

### SIG weather and fire danger (PSA averages)

Categories follow the WIMS SIG Daily Listing. Each value is the average across the PSA's RAWS.

| Column | Description |
|---|---|
| Temp | Dry bulb temperature at 1300, °F. |
| MaxT | Daily maximum temperature, °F. |
| RH | Relative humidity at 1300, %. |
| MxRH | Daily maximum RH, %. |
| Rain | Precipitation amount, inches, for the 24 hours from 1300 the day before to 1300 that day. |
| RnDr | Precipitation duration, hours with measurable rain in the same window. |
| Wind | Wind speed at 1300, mph (20-ft, 10-minute average). |
| SC | Spread Component, fuel model Y. |
| ERC | Energy Release Component, fuel model Y. |
| BI | Burning Index, fuel model Y. |
| IC | Ignition Component, fuel model Y. |
| F100 | 100-hour fuel moisture, %. |
| F1000 | 1000-hour fuel moisture, %. |
| WDIR | Wind direction code at 1300: 1 = NE, 2 = E, 3 = SE, 4 = S, 5 = SW, 6 = W, 7 = NW, 8 = N. |
| WDIR_deg | Wind direction at 1300, degrees, averaged across stations as compass directions. Calm stations are excluded. |
| GDir | Direction of each station's strongest gust of the day, degrees, averaged across stations as compass directions. |
| GSpd | Daily peak gust speed, mph, averaged across stations. |
| VPDM | Daily maximum vapor pressure deficit, Pa. |
| VPDA | Daily average vapor pressure deficit, Pa. |
| FFWI | Fosberg Fire Weather Index, calculated from 1300 temperature, RH and wind. |

### Lightning (NLDN cloud-to-ground strikes within 20 miles of Lat/Long)

| Column | Description |
|---|---|
| Lightning_Day | Strikes on the fire date (UTC day). |
| Lightning_Prior3d | Strikes over the 3 days before the fire date (not including it). |
| Lightning_Prior7d | Strikes over the 7 days before the fire date (not including it). |
| Lightning_Cluster_Flag | 1 = 3 or more strikes within 20 miles on the fire date. |

### Event flags

| Column | Description |
|---|---|
| Wind_Event_Threshold_mph | That PSA's 90th percentile of GSpd across all fire-days in this file (NC01 16.3, NC02 23.8, NC03A 25.3, NC03B 33.1, NC04 19.0, NC05 24.0, NC06 27.0, NC07 22.0, NC08 29.0 mph). |
| Large_Wind_Event_Flag | 1 = GSpd at or above that PSA's threshold. |
| Large_Fire_Starts_PSA_Day | Number of large fires that started in that PSA on that date. A fire's start is its first date in the perimeter data. |
| Multi_Large_Fire_Start_Flag | 1 = 3 or more large fires started in that PSA on that date. |

## Known issues and caveats

1. **The full 2012–2026 record now comes from one source (FEMS),** so all weather and fire danger values can be compared across years. FireFamily+ ran about 10–15 points higher on ERC, about 1.5× on BI, about 2× on SC and 2–4 mph higher on Wind than FEMS for the same days. Those FireFamily+ values are kept in `NOPs_2012_2020_FireFamilyPlus_SIG_Values_Archive.csv` (matched by FID).
2. **Wind and gust direction for 2012–2020 come from FEMS,** not the FireFamily+ listings. The original listings had directions limited to 211–359°.
3. **2021–2026 locations and elevations** come from each fire's point of origin and don't change from day to day. 2012–2020 uses each day's perimeter centroid.
4. **Lightning counts:**
   - They use UTC days, so an evening storm in Pacific time can fall on the next date.
   - Strikes are counted by 0.1° tile (roughly 4 × 7 mi), and the 20-mile radius is measured to each tile's center.
   - The cluster flag can't confirm that strikes landed close to each other, only that there were 3 or more within 20 miles.
5. **Fire start dates** come from the first VIIRS perimeter, which can trail actual ignition by a day or more.
6. **PSA code and name disagree on 326 rows from 2012–2020.** These are mostly fires crossing a PSA boundary, where PSANationa and PSANAME differ. Weather on those rows comes from the PSANationa PSA.
7. **The wind event thresholds come from fire-days only,** not the full climatology, so they show how windy a day was compared with other fire-days in that PSA.
8. **One bad rain value was removed.** NC07 on 9/4/2019 showed 4.08 in with 0 hours of rain duration (a single-station spike), so Rain is blank on that row.
9. **20 off-season fire-days were removed as Rx or pile burns** (November 23, 2026). The rule removed every fire-day with both of these:
   - a date in December–March
   - ERC below 10

   One was a large growth day: "Shelly" on 1/2/2025, 15,520 ac at ERC 0.5. Most of these were winter dates attached to summer wildfires, such as Shelly (July 2024) and SCOTT, Deep, Diamond and HEAD (August 2023). That fits burning inside the old footprints, or late perimeter updates, rather than wildfire growth. The summer days of those fires were kept. The removed rows are in `removed_rx_pile_burn_fire_days.csv`. Fire-start counts, wind event thresholds, scoring thresholds, the fuel gate and the historical rates were all recomputed with `scripts/compute_thresholds.py`. The thresholds moved by 0.1 at most.

10. **Late perimeter records were removed and split fire-days merged** (November 23, 2026, `scripts/clean_dataset.py`).
    - **47 rows were dated years after their fire,** for example Caldor (2021) on 8/24/2026 at its final 221,786 ac, and Antelope (2021) on 2/4/2026. These are final perimeters re-saved later, not fire-days, so they were removed (`removed_late_perimeter_records.csv`).
    - **228 fire-days were split across 2–3 rows** (488 rows) for complexes mapped as several polygons. Examples are Doe/August Complex, Carr, Ranch, Hennessey, the SCU and CZU Lightning Complexes, and Claremont/North Complex. Each fire-day was merged into one row:
      - acres summed (Claremont on 9/9/2020 became 116,678 ac)
      - cumulative acres taken as the largest
      - Lat/Long averaged
      - lightning counts taken as the largest
      - weather and flags kept, since they were identical

      The original rows are in `merged_duplicate_rows.csv`.
    - Before this, those fire-days counted two or three times in every statistic. Thresholds moved by 0–1 point in most PSAs. NC03A moved more, because the SCU and CZU duplicates were concentrated there: max RH went from ≤ 74.5 to ≤ 82.5%, average VPD from ≥ 1,500 to ≥ 1,341 Pa, and gust from ≥ 22.8 to ≥ 21.5 mph. NC03A then had 32 large growth days, so it gets small-sample blending.

11. **Large growth days were re-flagged with the ONCC threshold chart** (November 23, 2026, `scripts/flag_large_growth.py`, from `Large_Fire_Growth_Threshold_Working.xlsx`).
    - **The rule:** the cutoff is 25% of the fire's to-date acres before that day's growth, with a PSA minimum (NC01 50, NC02 75, NC03A 50, NC03B 150, NC04 75, NC05 150, NC06 150 then 100 once the fire reaches 150 ac, NC07 50, NC08 400 ac), capped at 10,000 ac. The minimum applies while 20% of to-date acres is at or below it, and on a fire's first perimeter day.
    - **Why:** the supplied flag matched the chart on nearly every 2012–2019 row, but missed many runs from 2020 on (2021: 34 flagged, 143 by the chart). Missed examples include Doe (August Complex) 135,193 ac on 9/9/2020, Sugar 39,238 ac on 7/9/2021, Caldor 18,372 ac on 8/17/2021 and Dixie 58,874 ac on 8/5/2021. 37 small 2012–2017 days had been flagged below their PSA minimum and are no longer flagged. One perimeter artifact is never flagged: Haypress (River Complex) on 9/19/2021 shows 193,414 ac in a day at max RH 98% and ERC 29, doubling its to-date acres when other River Complex fires were merged into its perimeter.
    - **Effect:** 1,227 large growth days became 1,455 (265 added, 37 removed); they now hold 69% of all growth acres, up from 41%. NC04 gained 95, NC07 73 and NC06 24. Thresholds moved by about 1 point at most. The score separates days better: Low 22% vs Very High 47%, up from 20% vs 36%. The original flag is kept in `LargeGrowthDayFlag_Original`.

## Large growth day analysis and dashboard thresholds

The comparison is large growth days against other days when the same large fires were burning. Because every row is already a fire-day, the gaps are smaller than they would be against all summer days.

- **Weather separates large growth days only modestly.** The best single variables (SC, BI, IC, FFWI, GSpd, F100) have an AUC of about 0.62–0.65 across North Ops, where 0.5 means no skill and 1.0 means perfect.
- **The strongest signal is regional activity.** On days when 3 or more large fires started in a PSA, 67% of fire-days were large growth days, compared with 29% otherwise. A lightning cluster raised the rate from 30% to 47%, and a large wind event from 30% to 40%.
- **The PSAs behave differently:**
  - NC01, NC02, NC03A and NC04 respond most to fire weather (best single-variable AUC 0.66–0.77).
  - NC03A shows the clearest separation (AUC about 0.75–0.77 on F100, SC, GSpd and BI).
  - In NC05, NC06 and NC07 weather separates large growth days poorly (best AUC 0.58–0.60). Growth there tracks lightning (in NC06) and multiple starts (in NC07).

**Dashboard score.** Each PSA-day gets one point per variable that meets that PSA's threshold, for 8 variables in total. Thresholds are the median value on the PSA's large growth days, 2012–2026. PSAs with fewer than 40 large growth days (NC01, NC03A, NC03B, NC08) are blended toward the PSA's 60th percentile of all fire-days. MxRH and F100 count when at or below the threshold.

| PSA | ERC | BI | IC | FFWI | GSpd | VPDA | MxRH | F100 |
|---|---|---|---|---|---|---|---|---|
| NC01 | 28.8 | 18.0 | 14.7 | 9.4 | 14.0 | 1005 | 86.8 | 15.0 |
| NC02 | 46.2 | 28.1 | 32.8 | 17.5 | 20.0 | 1904 | 58.9 | 10.4 |
| NC03A | 35.4 | 21.8 | 18.7 | 13.5 | 21.6 | 1319 | 82.9 | 13.2 |
| NC03B | 51.4 | 32.5 | 36.2 | 23.4 | 25.1 | 2301 | 48.9 | 8.8 |
| NC04 | 47.5 | 24.1 | 28.2 | 9.9 | 16.1 | 1956 | 64.0 | 10.5 |
| NC05 | 53.4 | 29.2 | 40.1 | 15.4 | 18.0 | 2587 | 49.0 | 9.1 |
| NC06 | 52.7 | 29.3 | 36.9 | 16.2 | 21.7 | 2157 | 51.0 | 9.0 |
| NC07 | 53.9 | 28.0 | 35.1 | 13.8 | 18.0 | 2028 | 50.0 | 9.2 |
| NC08 | 54.1 | 29.3 | 37.3 | 17.4 | 24.0 | 2154 | 53.0 | 8.9 |

Concern levels are based on the score:
- Low: 0–1
- Moderate: 2–3
- High: 4–5
- Very High: 6–8

Across North Ops, 22% of fire-days at Low were large growth days, compared with 28% at Moderate, 34% at High and 47% at Very High (base rate 31%). The dashboard builds forecast days from FEMS hourly forecasts, read at 1300 and over each day exactly like the history, so all 8 variables are scored every day.

This replaced FEMS daily forecast summaries on November 23, 2026. Those summaries give daily peak values, which run well above 1300 values. On 10 August 2025 days at 8 NC04 stations, the peaks were higher by:

- ERC: +3
- BI: +6, about 28%
- IC: +14, about 57%

100-hr fuel moisture ran 0.7 points lower. As a result, forecast days had cleared thresholds more easily than observed days.

**Weak-guide PSAs.** In PSAs where the large growth rate at Very High is less than 10 points above Low, the dashboard adds a ⚠ note. Since the November 23, 2026 re-flagging that is only NC06 (36% at Low, 42% at Very High). NC07 (47% → 58%) and NC08 (27% → 40%) no longer qualify. NC08 has few fire-days per level (0 of 11 at High), so read its rates loosely.

**Fuel gate (added November 23, 2026).** If ERC is below the 5th percentile of the PSA's large growth days, or 100-hr fuel moisture is above the 95th percentile, the level is capped at Low whatever the score. The dashboard marks these days with ⊘.

The gate was added because wind and humidity alone could raise off-season days. For example, NC01 on November 23, 2026 had a 36 mph east wind forecast but ERC of 6, and scored Moderate.

| PSA | NC01 | NC02 | NC03A | NC03B | NC04 | NC05 | NC06 | NC07 | NC08 |
|---|---|---|---|---|---|---|---|---|---|
| ERC below | 20.0 | 35.4 | 26.3 | 35.6 | 29.3 | 43.0 | 44.1 | 35.4 | 44.5 |
| 100-hr FM above (%) | 18.1 | 13.7 | 16.2 | 13.2 | 15.6 | 12.0 | 12.1 | 13.7 | 12.6 |

How the cutoffs were chosen, tested on 2012–2026:

- **5th/95th percentile gate:** caps 26 of the 1,455 large growth days that had scored Moderate or higher, which is 0.5% of large-growth acres. None of them had scored Very High. The largest is Kelly on 8/24/2023 (Moderate, 12,086 ac). (Before re-flagging: 24 of 1,227, 0.8% of acres.)
- **10th/90th percentile gate:** rejected. It would have capped 58 such days, including Zogg and Doe on 9/28/2020 and Kincade on 10/24/2019, all wind-driven High days.

The large growth rates by level barely change with the gate, because the historical record holds few fire-days with wet fuels. The gate matters mostly outside fire season.

## Sources

- FEMS ext-climatology web services: https://fems.fs2c.usda.gov/api/ext-climatology/
- NOAA NCEI SWDI NLDN lightning tile summaries: https://www.ncei.noaa.gov/pub/data/swdi/database-csv/v2/
- WFIGS Incident Locations (NIFC): https://services3.arcgis.com/T4QMspbfLg3qTGWY/arcgis/rest/services/WFIGS_Incident_Locations/FeatureServer/0
- USGS Elevation Point Query Service (3DEP): https://epqs.nationalmap.gov/
- User-provided files: VIIRS fire perimeter exports, FireFamily+ SIG daily listings for each PSA (2012–2020, archived), `Winter_2025_RAWS.xlsx`, `SIG_Daily_Listing.docx`
