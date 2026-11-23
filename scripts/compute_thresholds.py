"""Recompute everything derived from the historical dataset, then write it back.

Run from the repo root after changing data/NOPs_Large_Fire_Growth_Days_2012_2026_SIG_Weather.csv:

    python scripts/compute_thresholds.py
    python scripts/build_dashboard.py

Steps
1. Dataset columns that depend on other rows:
   - Large_Fire_Starts_PSA_Day: number of fires whose first date in the data falls on that
     PSA-day (a fire whose first date spans two PSAs counts in both).
   - Multi_Large_Fire_Start_Flag: 1 when that count is 3 or more.
   - Wind_Event_Threshold_mph: the PSA's 90th percentile of GSpd over all fire-days.
   - Large_Wind_Event_Flag: 1 when GSpd reaches it.
2. Scoring thresholds for the 8 variables: the median on the PSA's large growth days. PSAs with
   fewer than 40 large growth days are blended toward the PSA's 60th percentile (40th for MxRH and
   F100) of all fire-days, weighted 30 days.
3. Fuel gate: 5th percentile of ERC and 95th percentile of 100-hr FM on the PSA's large growth days.
4. HIST_LGD_RATE: % of fire-days at each concern level (fuel gate applied) that were large growth days.

Writes the CSV, data/psa_thresholds.json, and the THRESHOLDS and HIST_LGD_RATE blocks in
scripts/nops_psa_conditions_update.py.
"""
import json, pathlib, re
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[1]
CSV = ROOT / "data" / "NOPs_Large_Fire_Growth_Days_2012_2026_SIG_Weather.csv"
UPDATE = ROOT / "scripts" / "nops_psa_conditions_update.py"
VARS = {"ERC": ">=", "BI": ">=", "IC": ">=", "FFWI": ">=", "GSpd": ">=", "VPDA": ">=", "MxRH": "<=", "F100": "<="}
LEVELS = [(0, "Low"), (2, "Moderate"), (4, "High"), (6, "Very High")]
BLEND_N, BLEND_K = 40, 30

c = pd.read_csv(CSV)
d = pd.to_datetime(c.DateText, format="mixed")

# 1. Derived dataset columns
first = c.assign(d=d).groupby("Fire_ID").d.transform("min")
starts = c[d == first].assign(d=d[d == first]).groupby(["PSANationa", "d"]).Fire_ID.nunique()
c["Large_Fire_Starts_PSA_Day"] = [int(starts.get((p, x), 0)) for p, x in zip(c.PSANationa, d)]
c["Multi_Large_Fire_Start_Flag"] = (c.Large_Fire_Starts_PSA_Day >= 3).astype(int)
wthr = c.groupby("PSANationa").GSpd.quantile(0.9).round(1)
c["Wind_Event_Threshold_mph"] = c.PSANationa.map(wthr)
c["Large_Wind_Event_Flag"] = (c.GSpd >= c.Wind_Event_Threshold_mph).astype(int)
c.to_csv(CSV, index=False)

# 2-3. Thresholds and fuel gate
L = c[c.LargeGrowthDayFlag == 1]
TH = {}
for p in sorted(c.PSANationa.unique()):
    g, a = L[L.PSANationa == p], c[c.PSANationa == p]
    t = {}
    for v, op in VARS.items():
        med = g[v].median()
        if len(g) < BLEND_N:
            q = a[v].quantile(0.6 if op == ">=" else 0.4)
            med = (len(g) * med + BLEND_K * q) / (len(g) + BLEND_K)
        t[v] = (op, round(float(med), 1))
    t["_wind_event"] = (">=", float(wthr[p]))
    t["_gate_ERC"] = ("<", round(float(g.ERC.quantile(0.05)), 1))
    t["_gate_F100"] = (">", round(float(g.F100.quantile(0.95)), 1))
    TH[p] = t

# 4. Historical large-growth rate by (gated) level
score = sum(((c[v] >= c.PSANationa.map(lambda p: TH[p][v][1])) if op == ">=" else
             (c[v] <= c.PSANationa.map(lambda p: TH[p][v][1]))).astype(int) for v, op in VARS.items())
gate = (c.ERC < c.PSANationa.map(lambda p: TH[p]["_gate_ERC"][1])) | (c.F100 > c.PSANationa.map(lambda p: TH[p]["_gate_F100"][1]))
level = pd.cut(score, [-1, 1, 3, 5, 8], labels=[l for _, l in LEVELS]).astype(str).where(~gate, "Low")
HR = {}
for p, g in c.groupby("PSANationa"):
    lv = level[g.index]
    HR[p] = {l: (int(round(g[lv == l].LargeGrowthDayFlag.mean() * 100)) if (lv == l).any() else None) for _, l in LEVELS}

# Write psa_thresholds.json
json.dump({p: {k: v[1] for k, v in t.items()} for p, t in TH.items()},
          open(ROOT / "data" / "psa_thresholds.json", "w"), indent=1)

# Rewrite the blocks in the update script
src = UPDATE.read_text()
lines = ["THRESHOLDS = {"]
for p, t in TH.items():
    main = ", ".join(f'"{v}": ("{t[v][0]}", {t[v][1]})' for v in VARS)
    lines.append(f'    "{p}": {{{main},\n             "_wind_event": (">=", {t["_wind_event"][1]}),\n'
                 f'             "_gate_ERC": ("<", {t["_gate_ERC"][1]}), "_gate_F100": (">", {t["_gate_F100"][1]})}},')
lines.append("}")
src = re.sub(r"THRESHOLDS = \{.*?\n\}\n", "\n".join(lines) + "\n", src, count=1, flags=re.S)
hr = "HIST_LGD_RATE = {  # % of fire-days at each level (fuel gate applied) that were large growth days, 2012-2026\n" + \
     "".join(f'    "{p}": {json.dumps(v)},\n' for p, v in HR.items()) + "}\n"
src = re.sub(r"HIST_LGD_RATE = \{.*?\n\}\n", hr, src, count=1, flags=re.S)
UPDATE.write_text(src)

print(f"{len(c)} fire-days, {len(L)} large growth days")
for p, t in TH.items():
    print(p, {k: v[1] for k, v in t.items()})
print("HIST_LGD_RATE", HR)
