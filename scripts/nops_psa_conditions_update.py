# =============================================================================
# NOPs PSA Fire Weather Conditions - ArcGIS Online Notebook update script
# -----------------------------------------------------------------------------
# What it does (each run):
#   1. Pulls RAWS observations (last 36 h) and forecasts (next 7 days) from FEMS
#      for every RAWS in each North Ops PSA.
#   2. Builds PSA "SIG" values the same way as the historical dataset
#      (1300 LST obs, daily max/min, PSA averages, fuel model Y).
#   3. Scores each PSA against the large-growth-day thresholds (from the
#      historical analysis) and assigns a concern level.
#   4. Overwrites the "current" hosted feature layer (one PSA polygon per PSA per
#      day: today + 6 forecast days) and appends today's row to a history table.
#
# Where it writes (already created in the oncc_oscc_scripting account, NIFC org,
# folder "NOPs Large Fire Growth Days"):
#   NOPs_PSA_Fire_Weather_Conditions feature service
#     layer 0  PSA_Conditions          - today's obs + 6 forecast days, overwritten each run
#     table 1  PSA_Conditions_History  - one observed row per PSA per day, kept
#
# How to run:
#   - ArcGIS Notebook: paste into a cell and schedule it as a task (signs in as
#     the notebook owner automatically).
#   - Anywhere else (server / PC with Python 3 and `pip install arcgis pandas requests`):
#     set environment variables AGOL_USER and AGOL_PASS for the account, then run
#     `python nops_psa_conditions_notebook.py` from Task Scheduler / cron every few hours.
#
# FEMS endpoints used are public (no API key needed). FEMS rejects long station
# lists in one GET, so requests are made one PSA at a time.
# =============================================================================

import io, os, math, datetime as dt
import requests
import numpy as np
import pandas as pd
from arcgis.gis import GIS
from arcgis.features import FeatureLayer

PORTAL = "https://nifc.maps.arcgis.com"
SERVICE_URL = ("https://services3.arcgis.com/T4QMspbfLg3qTGWY/arcgis/rest/services/"
               "NOPs_PSA_Fire_Weather_Conditions/FeatureServer")
FEMS = "https://fems.fs2c.usda.gov/api/ext-climatology/"
PSA_SERVICE = ("https://services3.arcgis.com/T4QMspbfLg3qTGWY/ArcGIS/rest/services/"
               "DMP_Predictive_Service_Area__PSA_Boundaries_Public/FeatureServer/0")
LST_OFFSET_H = 8                       # PST; RAWS obs time is 1300 LST = 21Z
FORECAST_DAYS = 6

# --- RAWS used for each PSA (Winter_2025_RAWS.xlsx, NOPS tab) -----------------
PSA_STATIONS = {
    "NC01": ["40102","40421","40425","40427","40428","40429"],
    "NC02": ["41001","41005","41015","41018","41101","41402","41406","42010","42108","41411"],
    "NC03A": ["42308","42309","42310","42312","43009","43304","43309","43402","43403","43802"],
    "NC03B": ["43008","43011","43013","43404","43407","43502","43809"],
    "NC04": ["40105","40203","40217","40218","40222","40225","40231","40237","40239","40244",
             "40245","40246","40408","40501","40503","40507","40508","40511","40512","40516",
             "40517","40518","40519","40520","40614","40618"],
    "NC05": ["40611","40615","40802","40812","40814","40816","41201","41211","41410","41503","41907","42202"],
    "NC06": ["40221","40228","40233","40240","40242","40243","40247","40302","40306","40308",
             "40309","40312","40313","40314","40630"],
    "NC07": ["40609","40635","40703","40719","40723","40730","40801","40904","40910","40915",
             "40916","40921","41213","41214","41304","41701","41806","41908","42601","42603",
             "42608","42611","42615"],
    "NC08": ["40709","40714","40724","40725","40727","40728","41302","41310","41311","260111","260112","260113"],
}

# --- Thresholds from the historical analysis -----------------------------------
# THRESHOLDS[psa][var] = (direction, value). ">=" means higher is worse.
# Value = median of that variable on the PSA's large growth days, 2012-2026
# (PSAs with < 40 large growth days are blended toward the PSA's 60th percentile
# of all fire-days). _wind_event = PSA 90th percentile of daily peak gust.
# Fuel gate: if ERC < _gate_ERC (5th percentile of ERC on the PSA's large growth
# days) or 100-hr FM > _gate_F100 (95th percentile), fuels are not receptive and
# the concern level is capped at Low, whatever the score. Checked on 2012-2026:
# it caps 24 of 1,292 large growth days that scored Moderate or higher (0.9% of
# large-growth acres) and none that scored Very High.
THRESHOLDS = {
    "NC01": {"ERC": (">=", 29.1), "BI": (">=", 18.2), "IC": (">=", 14.7), "FFWI": (">=", 9.5), "GSpd": (">=", 14.3), "VPDA": (">=", 1044.6), "MxRH": ("<=", 87.0), "F100": ("<=", 15.2),
             "_wind_event": (">=", 16.2),
             "_gate_ERC": ("<", 19.6), "_gate_F100": (">", 18.1)},
    "NC02": {"ERC": (">=", 45.4), "BI": (">=", 27.9), "IC": (">=", 31.4), "FFWI": (">=", 17.0), "GSpd": (">=", 20.0), "VPDA": (">=", 1846.5), "MxRH": ("<=", 59.4), "F100": ("<=", 10.6),
             "_wind_event": (">=", 23.8),
             "_gate_ERC": ("<", 35.4), "_gate_F100": (">", 13.7)},
    "NC03A": {"ERC": (">=", 35.9), "BI": (">=", 22.4), "IC": (">=", 19.0), "FFWI": (">=", 14.6), "GSpd": (">=", 22.8), "VPDA": (">=", 1499.5), "MxRH": ("<=", 74.6), "F100": ("<=", 12.7),
             "_wind_event": (">=", 26.4),
             "_gate_ERC": ("<", 26.8), "_gate_F100": (">", 16.2)},
    "NC03B": {"ERC": (">=", 50.5), "BI": (">=", 31.9), "IC": (">=", 36.3), "FFWI": (">=", 22.7), "GSpd": (">=", 24.9), "VPDA": (">=", 2248.2), "MxRH": ("<=", 50.2), "F100": ("<=", 8.9),
             "_wind_event": (">=", 33.1),
             "_gate_ERC": ("<", 29.7), "_gate_F100": (">", 13.9)},
    "NC04": {"ERC": (">=", 47.4), "BI": (">=", 24.0), "IC": (">=", 28.3), "FFWI": (">=", 10.0), "GSpd": (">=", 16.0), "VPDA": (">=", 1944.0), "MxRH": ("<=", 64.0), "F100": ("<=", 10.6),
             "_wind_event": (">=", 19.0),
             "_gate_ERC": ("<", 29.3), "_gate_F100": (">", 15.7)},
    "NC05": {"ERC": (">=", 53.3), "BI": (">=", 29.2), "IC": (">=", 40.0), "FFWI": (">=", 15.1), "GSpd": (">=", 18.0), "VPDA": (">=", 2588.5), "MxRH": ("<=", 49.0), "F100": ("<=", 9.0),
             "_wind_event": (">=", 23.9),
             "_gate_ERC": ("<", 43.0), "_gate_F100": (">", 12.1)},
    "NC06": {"ERC": (">=", 52.4), "BI": (">=", 29.1), "IC": (">=", 36.0), "FFWI": (">=", 15.9), "GSpd": (">=", 21.0), "VPDA": (">=", 2132.0), "MxRH": ("<=", 52.0), "F100": ("<=", 9.6),
             "_wind_event": (">=", 27.0),
             "_gate_ERC": ("<", 46.2), "_gate_F100": (">", 11.7)},
    "NC07": {"ERC": (">=", 52.3), "BI": (">=", 27.6), "IC": (">=", 33.7), "FFWI": (">=", 13.5), "GSpd": (">=", 17.9), "VPDA": (">=", 1969.0), "MxRH": ("<=", 51.0), "F100": ("<=", 9.5),
             "_wind_event": (">=", 22.0),
             "_gate_ERC": ("<", 34.1), "_gate_F100": (">", 13.9)},
    "NC08": {"ERC": (">=", 53.6), "BI": (">=", 29.4), "IC": (">=", 37.4), "FFWI": (">=", 17.7), "GSpd": (">=", 24.0), "VPDA": (">=", 2174.3), "MxRH": ("<=", 53.7), "F100": ("<=", 9.0),
             "_wind_event": (">=", 29.0),
             "_gate_ERC": ("<", 43.8), "_gate_F100": (">", 13.1)},
}

HIST_LGD_RATE = {  # % of fire-days at each level (fuel gate applied) that were large growth days, 2012-2026
    "NC01": {"Low": 22, "Moderate": 33, "High": 43, "Very High": 53},
    "NC02": {"Low": 24, "Moderate": 24, "High": 29, "Very High": 48},
    "NC03A": {"Low": 24, "Moderate": 75, "High": 64, "Very High": 75},
    "NC03B": {"Low": 38, "Moderate": 50, "High": 54, "Very High": 62},
    "NC04": {"Low": 13, "Moderate": 16, "High": 17, "Very High": 31},
    "NC05": {"Low": 27, "Moderate": 41, "High": 38, "Very High": 48},
    "NC06": {"Low": 21, "Moderate": 32, "High": 39, "Very High": 29},
    "NC07": {"Low": 43, "Moderate": 44, "High": 38, "Very High": 40},
    "NC08": {"Low": 24, "Moderate": 30, "High": 8, "Very High": 31},
}
CONCERN_LEVELS = [(0, "Low"), (2, "Moderate"), (4, "High"), (6, "Very High")]

# =============================================================================
def fems_csv(path, **params):
    """GET one FEMS CSV. FEMS sometimes answers "Download Failed" (HTTP 400) when
    busy, so retry up to 3 times with a growing pause."""
    import time
    for attempt in range(1, 5):
        r = requests.get(FEMS + path, params=params, timeout=120)
        if r.ok:
            return pd.read_csv(io.StringIO(r.text))
        if attempt == 4:
            r.raise_for_status()
        time.sleep(2 * attempt)

def fems_by_psa(path, **params):
    """Same request for each PSA's stations (keeps URLs short), concatenated."""
    parts = []
    for sts in PSA_STATIONS.values():
        df = fems_csv(path, stationIds=",".join(sts), **params)
        if len(df):
            parts.append(df)
    return pd.concat(parts, ignore_index=True) if parts else pd.DataFrame()

def zulu(t):
    return t.strftime("%Y-%m-%dT%H:%M:%SZ")

def circ_mean(deg):
    deg = [d for d in deg if pd.notna(d)]
    if not deg:
        return None
    s = sum(math.sin(math.radians(d)) for d in deg)
    c = sum(math.cos(math.radians(d)) for d in deg)
    v = round(math.degrees(math.atan2(s, c))) % 360
    return 360 if v == 0 else v

def ffwi(T, H, U):
    if any(pd.isna(x) for x in (T, H, U)):
        return None
    if H < 10:   m = 0.03229 + 0.281073*H - 0.000578*H*T
    elif H < 50: m = 2.22749 + 0.160107*H - 0.01478*T
    else:        m = 21.0606 + 0.005565*H*H - 0.00035*H*T - 0.483199*H
    x = m / 30
    return (1 - 2*x + 1.5*x*x - 0.5*x**3) * math.sqrt(1 + U*U) / 0.3002

def observed_sig(now_utc):
    """PSA SIG values for the most recent complete 1300 LST observation."""
    obs = now_utc.replace(minute=0, second=0, microsecond=0, hour=13 + LST_OFFSET_H)
    if obs > now_utc:
        obs -= dt.timedelta(days=1)
    start, end = obs - dt.timedelta(hours=23), obs + dt.timedelta(hours=10)
    wx = fems_by_psa("download-weather", startDate=zulu(start),
                     endDate=zulu(end), dataset="observation", dataFormat="csv", dataIncrement="hourly")
    nf = fems_by_psa("download-nfdr", startDate=zulu(obs - dt.timedelta(hours=1)),
                  endDate=zulu(obs + dt.timedelta(hours=1)), dataset="observation", dataFormat="csv",
                  fuelModels="Y", dateTimeFormat="UTC")
    wx["t"] = pd.to_datetime(wx["DateTime"], utc=True)
    nf["t"] = pd.to_datetime(nf["observationTime"], utc=True)
    obs_ts = pd.Timestamp(obs)
    day0, day1 = obs_ts - pd.Timedelta(hours=13), obs_ts + pd.Timedelta(hours=11)
    rows = []
    for psa, sts in PSA_STATIONS.items():
        per = []
        for s in map(int, sts):
            w = wx[wx.StationId == s]
            if w.empty or w["Temperature(F)"].isna().all():
                continue
            o = w[w.t == obs_ts]
            day = w[(w.t >= day0) & (w.t < day1)]
            rain = w[(w.t > obs_ts - pd.Timedelta(hours=24)) & (w.t <= obs_ts)]["Precipitation(in)"].dropna()
            n = nf[(nf.stationId == s) & (nf.t == obs_ts)]
            T = o["Temperature(F)"].iloc[0] if len(o) else None
            H = o["RelativeHumidity(%)"].iloc[0] if len(o) else None
            U = o["WindSpeed(mph)"].iloc[0] if len(o) else None
            g = day.loc[day["GustSpeed(mph)"].idxmax()] if day["GustSpeed(mph)"].notna().any() else None
            per.append(dict(
                Temp=T, MaxT=day["Temperature(F)"].max(), RH=H, MxRH=day["RelativeHumidity(%)"].max(),
                Rain=rain.sum() if len(rain) else None, RnDr=(rain > 0).sum() if len(rain) else None,
                Wind=U, WDIR_deg=(o["WindAzimuth(degrees)"].iloc[0] if len(o) and U and U > 0 else None),
                GSpd=g["GustSpeed(mph)"] if g is not None else None,
                GDir=g["GustAzimuth(degrees)"] if g is not None else None,
                VPDM=day["VPD(Pa)"].max(), VPDA=day["VPD(Pa)"].mean(), FFWI=ffwi(T, H, U),
                SC=n.spreadComponent.mean() if len(n) else None,
                ERC=n.energyReleaseComponent.mean() if len(n) else None,
                BI=n.burningIndex.mean() if len(n) else None,
                IC=n.ignitionComponent.mean() if len(n) else None,
                F100=n.hundredHR_TL_FuelMoisture.mean() if len(n) else None,
                F1000=n.thousandHR_TL_FuelMoisture.mean() if len(n) else None))
        if not per:
            continue
        d = pd.DataFrame(per)
        row = {k: d[k].mean() for k in d.columns if k not in ("WDIR_deg", "GDir")}
        row.update(WDIR_deg=circ_mean(d.WDIR_deg), GDir=circ_mean(d.GDir),
                   PSA=psa, Date=(obs - dt.timedelta(hours=LST_OFFSET_H)).date(),
                   DataType="Observed", Stations=len(per))
        rows.append(row)
    return pd.DataFrame(rows)

def forecast_sig(today):
    """PSA daily forecast values (FEMS station forecasts) for the next days."""
    s, e = (today + dt.timedelta(days=1)).isoformat(), (today + dt.timedelta(days=FORECAST_DAYS)).isoformat()
    wx = fems_by_psa("download-wx-daily-summary/", dataset="forecast", startDate=s, endDate=e,
                     dataFormat="csv")
    nf = fems_by_psa("download-nfdr-daily-summary/", dataset="forecast", startDate=s, endDate=e,
                     dataFormat="csv", fuelModels="Y")
    nf = nf.rename(columns={"ObservationTime": "Date"})
    rows = []
    for psa, sts in PSA_STATIONS.items():
        ids = list(map(int, sts))
        w, n = wx[wx.StationId.isin(ids)], nf[nf.StationId.isin(ids)]
        for d in sorted(set(w.Date) | set(n.Date)):
            wd, nd = w[w.Date == d], n[n.Date == d]
            rows.append(dict(
                PSA=psa, Date=pd.to_datetime(d).date(), DataType="Forecast", Stations=len(wd),
                MaxT=wd["TemperatureMax(F)"].mean(), RH=wd["RelativeHumidityMin(%)"].mean(),
                MxRH=wd["RelativeHumidityMax(%)"].mean(), Rain=wd["Precipitation24hr(in)"].mean(),
                Wind=wd["WindSpeedMax(mph)"].mean(), GSpd=wd["GustSpeedMax(mph)"].mean(),
                GDir=circ_mean(wd["GustDirection(degrees)"]), VPDM=wd["VPDMax(Pa)"].mean(),
                SC=nd.SC.mean(), ERC=nd.ERC.mean(), BI=nd.BI.mean(), IC=nd.IC.mean(),
                F100=nd["100HrFM"].mean(), F1000=nd["1000HrFM"].mean()))
    return pd.DataFrame(rows)

def score(df):
    """Count how many large-growth thresholds each PSA-day meets.
    Forecast days lack some variables (FFWI, VPDA), so the count is scaled
    to an 8-point score before assigning the concern level."""
    hits, poss, names = [], [], []
    for _, r in df.iterrows():
        t, met, n = THRESHOLDS.get(r.PSA, {}), [], 0
        for var, (op, val) in t.items():
            if var.startswith("_"):
                continue
            x = r.get(var)
            if x is None or pd.isna(x):
                continue
            n += 1
            if (op == ">=" and x >= val) or (op == "<=" and x <= val):
                met.append(var)
        hits.append(len(met)); poss.append(n); names.append(", ".join(met))
    df["Thresholds_Met"] = hits
    df["Thresholds_Possible"] = poss
    df["Score_8"] = [round(h / p * 8) if p else None for h, p in zip(hits, poss)]
    df["Vars_Met"] = names
    gate = []
    for _, r in df.iterrows():
        t = THRESHOLDS.get(r.PSA, {})
        erc, f100 = r.get("ERC"), r.get("F100")
        gate.append(int((pd.notna(erc) and erc < t["_gate_ERC"][1]) or (pd.notna(f100) and f100 > t["_gate_F100"][1])))
    df["Fuel_Gate"] = gate
    df["Concern"] = [None if s is None else ("Low" if g else [lbl for n0, lbl in CONCERN_LEVELS if s >= n0][-1])
                     for s, g in zip(df["Score_8"], gate)]
    # Share of past fire-days at this level that were large growth days, counting only days
    # when a large fire was already burning. Left blank on fuel-gated days (no comparable history).
    df["Hist_LGD_Rate_Pct"] = [None if g else HIST_LGD_RATE.get(p, {}).get(c) for p, c, g in zip(df.PSA, df.Concern, gate)]
    df["Wind_Event"] = [int(r.GSpd >= THRESHOLDS.get(r.PSA, {}).get("_wind_event", (None, 999))[1])
                        if pd.notna(r.get("GSpd")) else 0 for _, r in df.iterrows()]
    return df

# =============================================================================
if os.environ.get("AGOL_USER"):
    gis = GIS(PORTAL, os.environ["AGOL_USER"], os.environ["AGOL_PASS"])
else:
    gis = GIS("home")                     # inside an ArcGIS Notebook
now = dt.datetime.now(dt.timezone.utc)
today = (now - dt.timedelta(hours=LST_OFFSET_H)).date()

obs_df = observed_sig(now)
base = obs_df.Date.iloc[0] if len(obs_df) else today   # before 1300 PST the latest obs is yesterday's
cur = pd.concat([obs_df, forecast_sig(base)], ignore_index=True)
cur = score(cur)
cur["Day_Offset"] = [(d - base).days for d in cur.Date]
cur["Date"] = cur.Date.astype(str)
cur["Updated_UTC"] = now.strftime("%Y-%m-%d %H:%M")
num = cur.select_dtypes("number").columns
cur[num] = cur[num].round(1)
for c in ("Stations", "Thresholds_Met", "Thresholds_Possible", "Score_8", "Hist_LGD_Rate_Pct",
          "Wind_Event", "Fuel_Gate", "Day_Offset"):
    cur[c] = cur[c].astype("Int64")

psa_geo = FeatureLayer(PSA_SERVICE).query(
    where="PSANationalCode IN ('" + "','".join(PSA_STATIONS) + "')",
    out_fields="PSANationalCode,PSANAME", out_sr=4326)
geom = {f.attributes["PSANationalCode"]: f.geometry for f in psa_geo.features}
names = {f.attributes["PSANationalCode"]: f.attributes["PSANAME"] for f in psa_geo.features}

def to_features(df, with_geom=True):
    out = []
    for _, r in df.iterrows():
        a = {}
        for k, v in r.items():
            if pd.isna(v):
                a[k] = None
            elif isinstance(v, np.integer):
                a[k] = int(v)
            elif isinstance(v, np.floating):
                a[k] = float(v)
            else:
                a[k] = v
        a["PSA_Name"] = names.get(r.PSA)
        f = {"attributes": a}
        if with_geom:
            f["geometry"] = geom.get(r.PSA)
        out.append(f)
    return out

lyr = FeatureLayer(SERVICE_URL + "/0", gis=gis)
htab = FeatureLayer(SERVICE_URL + "/1", gis=gis)
FIELDS = {f["name"] for f in lyr.properties.fields}
cur = cur[[c for c in cur.columns if c in FIELDS or c == "PSA"]]

# Current layer: replace everything
lyr.delete_features(where="1=1")
res = lyr.edit_features(adds=to_features(cur))
ok = sum(1 for x in res["addResults"] if x.get("success"))

# History table: replace today's observed rows
obs = cur[cur.DataType == "Observed"]
if len(obs):
    htab.delete_features(where=f"Date = '{obs.Date.iloc[0]}'")
    htab.edit_features(adds=to_features(obs, with_geom=False))
print(f"Updated {ok}/{len(cur)} PSA-days and {len(obs)} history rows at {cur.Updated_UTC.iloc[0]} UTC")
