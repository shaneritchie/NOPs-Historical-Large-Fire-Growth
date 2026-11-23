"""Clean-up steps applied to the historical dataset (November 23, 2026). Safe to re-run: it
only changes rows that still need it.

1. Late perimeter records: rows dated in a different year than the fire's ID year (for example
   Caldor, a 2021 fire, with a 2026 row equal to its final size). These are perimeters re-saved
   later, not fire-days. They are removed and archived in data/removed_late_perimeter_records.csv.
2. Same-day duplicates: complexes whose perimeter was split into several polygons have two or
   three rows for the same fire, PSA and date. Weather, growth % and the large growth flag are
   identical in those rows; only acres and location differ. They are merged into one row:
   acres summed, cumulative acres = largest, Lat/Long = mean, lightning counts = largest,
   everything else from the first row. The original rows are archived in
   data/merged_duplicate_rows.csv.

Then run:  python scripts/flag_large_growth.py, python scripts/compute_thresholds.py  and  python scripts/build_dashboard.py
"""
import pathlib
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[1]
CSV = ROOT / "data" / "NOPs_Large_Fire_Growth_Days_2012_2026_SIG_Weather.csv"
c = pd.read_csv(CSV)
cols = list(c.columns)
d = pd.to_datetime(c.DateText, format="mixed")

# 1. Late perimeter records
late = d.dt.year != c.Fire_ID.str[:4].astype(int)
if late.any():
    c[late].to_csv(ROOT / "data" / "removed_late_perimeter_records.csv", index=False)
c, d = c[~late].copy(), d[~late]

# 2. Same-day duplicates
c["_d"] = d.values
key = ["Fire_ID", "PSANationa", "_d"]
dup = c.duplicated(key, keep=False)
if dup.any():
    out = ROOT / "data" / "merged_duplicate_rows.csv"
    c[dup].drop(columns="_d").to_csv(out, index=False)
    agg = {col: "first" for col in cols if col not in ("Fire_ID", "PSANationa")}
    agg.update(Fire_Size="sum", Fire_Size_Cumulative="max", Lat="mean", Long="mean",
               Lightning_Day="max", Lightning_Prior3d="max", Lightning_Prior7d="max", Lightning_Cluster_Flag="max")
    merged = c[dup].groupby(key, sort=False).agg(agg).reset_index()
    c = pd.concat([c[~dup], merged], ignore_index=True)
c = c.sort_values(["_d", "PSANationa", "Fire_ID"]).drop(columns="_d")[cols]
c.to_csv(CSV, index=False)
print(f"removed {int(late.sum())} late perimeter records; merged {int(dup.sum())} duplicate rows; {len(c)} fire-days, "
      f"{int(c.LargeGrowthDayFlag.sum())} large growth days")
