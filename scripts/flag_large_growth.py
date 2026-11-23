"""Set LargeGrowthDayFlag from the ONCC large fire growth threshold chart
(Large_Fire_Growth_Threshold_Working.xlsx, "PSA Thresholds" sheet).

The cutoff for a fire-day comes from the fire's to-date acres before that day's growth
(Fire_Size_Cumulative - Fire_Size):

    cutoff = PSA minimum             if 20% of to-date acres <= PSA minimum
           = 25% of to-date acres    otherwise, capped at 10,000 acres

PSA minimums: NC01 50, NC02 75, NC03A 50, NC03B 150, NC04 75, NC05 150, NC06 150
(100 once the fire is 150 acres or more, as in the chart), NC07 50, NC08 400.
A fire-day is a large growth day when that day's growth (Fire_Size) is at or above the cutoff.
On a fire's first perimeter day the to-date acres are 0, so the PSA minimum applies.

Why: the flag supplied with the 2012-2019 perimeters matches this chart on 99% of rows, but the
2020-2026 flag missed many large runs (2021: 34 flagged vs 143 by the chart; e.g. Sugar
7/9/2021 39,238 ac, Doe 9/9/2020 135,193 ac). Re-flagging every year with one rule keeps the
record consistent. The flag as originally supplied is kept in LargeGrowthDayFlag_Original.

Safe to re-run. Pipeline: clean_dataset.py -> flag_large_growth.py -> compute_thresholds.py
-> build_dashboard.py
"""
import pathlib
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[1]
CSV = ROOT / "data" / "NOPs_Large_Fire_Growth_Days_2012_2026_SIG_Weather.csv"
PSA_MIN = {"NC01": 50, "NC02": 75, "NC03A": 50, "NC03B": 150, "NC04": 75,
           "NC05": 150, "NC06": 150, "NC07": 50, "NC08": 400}
CAP = 10000
# Fire-days whose "growth" is a perimeter artifact, not fire spread. Never flagged.
#   Haypress (River Complex) 9/19/2021: 193,414 ac in one day at max RH 98% and ERC 29, which
#   doubles the fire's to-date acres; other River Complex fires' area was merged into its perimeter.
ARTIFACTS = {("Haypress (River Complex)", "9/19/2021")}


def cutoff(to_date, psa):
    mn = PSA_MIN.get(psa, 50)
    if psa == "NC06" and to_date >= 150:
        mn = 100
    return mn if 0.2 * to_date <= mn else min(0.25 * to_date, CAP)


c = pd.read_csv(CSV)
if "LargeGrowthDayFlag_Original" not in c.columns:
    c.insert(c.columns.get_loc("LargeGrowthDayFlag") + 1, "LargeGrowthDayFlag_Original", c.LargeGrowthDayFlag)
to_date = (c.Fire_Size_Cumulative - c.Fire_Size).clip(lower=0)
c["LGD_Cutoff_Acres"] = [round(cutoff(t, p)) for t, p in zip(to_date, c.PSANationa)]
c["LargeGrowthDayFlag"] = (c.Fire_Size >= c.LGD_Cutoff_Acres).astype(int)
c.loc[[(n, d) in ARTIFACTS for n, d in zip(c.FireName, c.DateText)], "LargeGrowthDayFlag"] = 0
cols = [k for k in c.columns if k != "LGD_Cutoff_Acres"]
cols.insert(cols.index("LargeGrowthDayFlag"), "LGD_Cutoff_Acres")
c = c[cols]
c.to_csv(CSV, index=False)

o = c.LargeGrowthDayFlag_Original
print(f"Large growth days: {int(c.LargeGrowthDayFlag.sum())} (originally {int(o.sum())}); "
      f"added {int(((c.LargeGrowthDayFlag == 1) & (o == 0)).sum())}, "
      f"removed {int(((c.LargeGrowthDayFlag == 0) & (o == 1)).sum())}")
