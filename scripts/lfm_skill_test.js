// Live fuel moisture (LFM) skill test for NOPs large growth days.
// Runs in a browser console on the GitHub Pages site (FEMS GraphQL allows cross-origin).
// Step 1: pull every FEMS field-sample site in/near North Ops and its full sample history.
// Step 2: for each fire-day, find live samples (shrub/tree) within RAD miles taken in the
//         LAG days before the date; compute each sample's percentile vs that site+species'
//         samples within +-15 days of the same calendar date (all years), plus raw values.
// Step 3: compare large growth day (LGD) rates and test whether LFM adds skill beyond the
//         weather/dead-fuel variables (fire-grouped 5-fold cross-validated logistic regression).
// Usage: paste into the console on https://shaneritchie.github.io/NOPs-Historical-Large-Fire-Growth/
//        then: const R = await lfmTest(); console.log(JSON.stringify(R, null, 1));

async function lfmTest({RAD = 30, LAG = 21} = {}) {
  const U = 'https://fems.fs2c.usda.gov/fuelmodel/apis/graphql', DAY = 864e5;
  const q = async (query, variables) => {
    for (let a = 0; a < 4; a++) {
      try {
        const r = await fetch(U, {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({query, variables})});
        if (r.ok) { const j = await r.json(); if (!j.errors) return j; }
      } catch (e) {}
      await new Promise(r => setTimeout(r, 1500 * (a + 1)));
    }
    return null;
  };
  // ---- 1. sites, fuels, samples
  const S = (await q('{getSites(returnAll:true){sites{siteId siteName latitude longitude active}}}')).data.getSites.sites;
  const Fz = (await q('query{getFuels(returnAll:true){fuel_id category fuel_type scientific_name}}')).data.getFuels;
  const fm = {}; (Array.isArray(Fz) ? Fz : Object.values(Fz)[0]).forEach(f => fm[f.fuel_id] = f);
  const sites = S.filter(s => s.latitude >= 36.5 && s.latitude <= 42.3 && s.longitude <= -119.3 && s.longitude >= -124.6);
  const SQ = 'query($siteId:String!){getFuelSamples(returnAll:false,sampleId:null,siteId:$siteId,startDate:"1980-01-01T00:00+00",endDate:"2050-01-01T00:00+00",filterBySampleType:"All",filterByStatus:"All",filterByCategory:"All",filterBySubCategory:"All",filterByMethod:"All"){fuelSamples{fuel_id sample status sample_average_value}}}';
  const series = {}; let i = 0;
  const w = async () => { while (i < sites.length) { const s = sites[i++]; const j = await q(SQ, {siteId: String(s.siteId)}); series[s.siteId] = j?.data?.getFuelSamples?.fuelSamples || []; } };
  await Promise.all([w(), w(), w(), w()]);
  return lfmAnalyze({sites, series, fm, RAD, LAG});
}

async function lfmAnalyze({sites, series, fm, RAD = 30, LAG = 21}) {
  const DAY = 864e5;
  const doy = t => { const d = new Date(t); return Math.floor((t - Date.UTC(d.getUTCFullYear(), 0, 1)) / DAY); };
  const site = {}; sites.forEach(s => site[s.siteId] = s);
  const SER = [];
  for (const [sid, fs] of Object.entries(series)) {
    const by = {};
    for (const x of fs) {
      const f = fm[x.fuel_id]; if (!f || !(f.category === 'Shrub' || f.category === 'Tree')) continue;
      if (x.status === 'Draft') continue;
      const v = x.sample_average_value; if (v == null || v < 30 || v > 400) continue;
      (by[x.fuel_id] = by[x.fuel_id] || []).push([Date.parse(x.sample.slice(0, 10) + 'T00:00Z'), v]);
    }
    for (const [fid, arr] of Object.entries(by)) {
      arr.sort((a, b) => a[0] - b[0]);
      SER.push({sid: +sid, fid: +fid, lat: site[sid].latitude, lon: site[sid].longitude,
        cham: /^Chamise/.test(fm[fid].fuel_type), arr, d: arr.map(a => doy(a[0])), y: arr.map(a => new Date(a[0]).getUTCFullYear())});
    }
  }
  // ---- 2. fire-days
  const txt = await (await fetch('data/NOPs_Large_Fire_Growth_Days_2012_2026_SIG_Weather.csv')).text();
  const split = l => { const o = []; let c = '', qq = false; for (const ch of l) { if (ch == '"') qq = !qq; else if (ch == ',' && !qq) { o.push(c); c = ''; } else c += ch; } o.push(c); return o; };
  const lines = txt.trim().split(/\r?\n/), H = split(lines[0]);
  const num = v => v === '' || v == null ? null : +v;
  const rows = lines.slice(1).map(split).map(r => Object.fromEntries(H.map((h, k) => [h, r[k]])));
  const mi = (a, b, c, d) => { const R = 3958.8, r = Math.PI / 180; const x = (d - b) * r * Math.cos((a + c) / 2 * r), y = (c - a) * r; return R * Math.sqrt(x * x + y * y); };
  const med = a => { if (!a.length) return null; const s = [...a].sort((x, y) => x - y), m = s.length >> 1; return s.length % 2 ? s[m] : (s[m - 1] + s[m]) / 2; };
  for (const r of rows) {
    const [m, d, y] = r.DateText.split('/').map(Number), T = Date.UTC(y, m - 1, d);
    const P = [], RAW = [], CH = [];
    for (const s of SER) {
      if (mi(+r.Lat, +r.Long, s.lat, s.lon) > RAD) continue;
      let k = -1; for (let j = s.arr.length - 1; j >= 0; j--) { if (s.arr[j][0] <= T) { if (s.arr[j][0] >= T - LAG * DAY) k = j; break; } }
      if (k < 0) continue;
      const v = s.arr[k][1], dk = s.d[k]; RAW.push(v); if (s.cham) CH.push(v);
      const win = [], ys = new Set();
      for (let j = 0; j < s.arr.length; j++) { let dd = Math.abs(s.d[j] - dk); dd = Math.min(dd, 365 - dd); if (dd <= 15) { win.push(s.arr[j][1]); ys.add(s.y[j]); } }
      if (win.length >= 8 && ys.size >= 4) P.push(100 * (win.filter(x => x < v).length + 0.5 * win.filter(x => x === v).length) / win.length);
    }
    r.LFM_N = RAW.length; r.LFM_PCT = med(P); r.LFM_RAW = med(RAW); r.LFM_CHAM = CH.length ? med(CH) : null;
    r.LGD = +r.LargeGrowthDayFlag; r.MONTH = m;
  }
  // ---- 3. analysis
  const rate = a => a.length ? {n: a.length, lgd: a.filter(r => r.LGD).length, rate: Math.round(1000 * a.filter(r => r.LGD).length / a.length) / 10} : {n: 0};
  const bins = (a, key, edges) => edges.slice(0, -1).map((lo, k) => [`${lo}-${edges[k + 1]}`, rate(a.filter(r => r[key] != null && r[key] >= lo && r[key] < edges[k + 1]))]);
  const M = rows.filter(r => r.LFM_PCT != null);
  const res = {coverage: {fire_days: rows.length, with_sample: rows.filter(r => r.LFM_N > 0).length, with_pct: M.length, all: rate(rows), matched: rate(M)}};
  res.by_pct = bins(M, 'LFM_PCT', [0, 20, 40, 60, 80, 101]);
  res.by_raw = bins(rows.filter(r => r.LFM_RAW != null), 'LFM_RAW', [0, 80, 100, 120, 150, 1000]);
  res.by_chamise = bins(rows.filter(r => r.LFM_CHAM != null), 'LFM_CHAM', [0, 60, 80, 100, 1000]);
  // within ERC terciles
  const ercs = M.map(r => num(r.ERC)).filter(v => v != null).sort((a, b) => a - b);
  const t1 = ercs[Math.floor(ercs.length / 3)], t2 = ercs[Math.floor(2 * ercs.length / 3)];
  res.erc_terciles = {cuts: [t1, t2]};
  for (const [nm, f] of [['low', r => num(r.ERC) < t1], ['mid', r => num(r.ERC) >= t1 && num(r.ERC) < t2], ['high', r => num(r.ERC) >= t2]]) {
    const a = M.filter(r => num(r.ERC) != null && f(r));
    res.erc_terciles[nm] = {dry_lfm_lt33: rate(a.filter(r => r.LFM_PCT < 33)), mid: rate(a.filter(r => r.LFM_PCT >= 33 && r.LFM_PCT < 67)), moist_lfm_ge67: rate(a.filter(r => r.LFM_PCT >= 67))};
  }
  // logistic regression, fire-grouped 5-fold CV
  const base = ['ERC', 'F100', 'BI', 'FFWI', 'GSpd', 'MxRH', 'VPDA'];
  const D = M.filter(r => base.every(k => num(r[k]) != null) && r.LFM_RAW != null);
  const fold = r => { let h = 0; for (const c of r.Fire_ID) h = (h * 31 + c.charCodeAt(0)) >>> 0; return h % 5; };
  const fitPred = (cols) => {
    const X = D.map(r => [1, ...cols.map(k => num(r[k]))]), Y = D.map(r => r.LGD), F = D.map(fold);
    const pred = new Array(D.length);
    for (let f = 0; f < 5; f++) {
      const tr = [], te = []; F.forEach((v, k) => (v === f ? te : tr).push(k));
      const p = X[0].length, mu = new Array(p).fill(0), sd = new Array(p).fill(1);
      for (let j = 1; j < p; j++) { const v = tr.map(k => X[k][j]); mu[j] = v.reduce((a, b) => a + b, 0) / v.length; sd[j] = Math.sqrt(v.reduce((a, b) => a + (b - mu[j]) ** 2, 0) / v.length) || 1; }
      const Z = k => X[k].map((x, j) => j ? (x - mu[j]) / sd[j] : 1);
      let b = new Array(p).fill(0);
      for (let it = 0; it < 25; it++) { // Newton with small ridge
        const g = new Array(p).fill(0), Hm = Array.from({length: p}, () => new Array(p).fill(0));
        for (const k of tr) { const z = Z(k), e = 1 / (1 + Math.exp(-z.reduce((a, x, j) => a + x * b[j], 0))); for (let a = 0; a < p; a++) { g[a] += (Y[k] - e) * z[a]; for (let c = 0; c < p; c++) Hm[a][c] += e * (1 - e) * z[a] * z[c]; } }
        for (let a = 1; a < p; a++) { g[a] -= 1 * b[a]; Hm[a][a] += 1; }
        // solve Hm * delta = g
        const A = Hm.map((row, a) => [...row, g[a]]);
        for (let c = 0; c < p; c++) { let piv = c; for (let a = c + 1; a < p; a++) if (Math.abs(A[a][c]) > Math.abs(A[piv][c])) piv = a; [A[c], A[piv]] = [A[piv], A[c]]; for (let a = 0; a < p; a++) if (a !== c) { const fct = A[a][c] / A[c][c]; for (let cc = c; cc <= p; cc++) A[a][cc] -= fct * A[c][cc]; } }
        b = b.map((x, a) => x + A[a][p] / A[a][a]);
      }
      for (const k of te) { const z = Z(k); pred[k] = 1 / (1 + Math.exp(-z.reduce((a, x, j) => a + x * b[j], 0))); }
    }
    let ll = 0; pred.forEach((pp, k) => { const e = Math.min(Math.max(pp, 1e-6), 1 - 1e-6); ll -= Y[k] ? Math.log(e) : Math.log(1 - e); });
    const pos = [], neg = []; pred.forEach((pp, k) => (Y[k] ? pos : neg).push(pp));
    const all = pred.map((pp, k) => [pp, Y[k]]).sort((a, b) => a[0] - b[0]); let rs = 0; all.forEach((x, k) => { if (x[1]) rs += k + 1; });
    const auc = (rs - pos.length * (pos.length + 1) / 2) / (pos.length * neg.length);
    return {logloss: +(ll / D.length).toFixed(4), auc: +auc.toFixed(3)};
  };
  D.forEach(r => { r.LFM_PCT_ = r.LFM_PCT; r.LFM_RAW_ = r.LFM_RAW; });
  res.cv = {n: D.length, lgd: D.filter(r => r.LGD).length,
    climatology: fitPred([]), lfm_pct_only: fitPred(['LFM_PCT_']), lfm_raw_only: fitPred(['LFM_RAW_']),
    weather: fitPred(base), weather_plus_lfm_pct: fitPred([...base, 'LFM_PCT_']), weather_plus_lfm_raw: fitPred([...base, 'LFM_RAW_']),
    weather_plus_both: fitPred([...base, 'LFM_PCT_', 'LFM_RAW_'])};
  // ---- 4. control for fire age (day of fire) and month, which dominate LGD rates
  const T = r => { const [m, d, y] = r.DateText.split('/').map(Number); return Date.UTC(y, m - 1, d); };
  const first = {}; rows.forEach(r => { const t = T(r); if (!(r.Fire_ID in first) || t < first[r.Fire_ID]) first[r.Fire_ID] = t; });
  rows.forEach(r => { r.AGE = Math.round((T(r) - first[r.Fire_ID]) / DAY) + 1; });
  const ageB = [[1, 1], [2, 2], [3, 5], [6, 14], [15, 999]];
  res.by_fire_age = ageB.map(([a, b]) => [`day ${a}-${b}`, rate(rows.filter(r => r.AGE >= a && r.AGE <= b))]);
  res.by_month = [5, 6, 7, 8, 9, 10, 11].map(m => [m, rate(rows.filter(r => r.MONTH == m))]);
  // rate below vs above a cut, averaged over fire-age x month strata (harmonic-mean weights)
  const strat = (get, cut) => {
    const st = [];
    for (const [a, b] of ageB) for (const m of [6, 7, 8, 9, 10]) {
      const s = M.filter(r => r.AGE >= a && r.AGE <= b && r.MONTH == m && get(r) != null);
      const L = s.filter(r => get(r) < cut), Hh = s.filter(r => get(r) >= cut);
      if (L.length >= 10 && Hh.length >= 10) st.push([L.length, L.filter(r => r.LGD).length / L.length, Hh.length, Hh.filter(r => r.LGD).length / Hh.length]);
    }
    const wt = st.map(x => 2 / (1 / x[0] + 1 / x[2])), W = wt.reduce((a, b) => a + b, 0);
    return {strata: st.length, rate_below: +(100 * st.reduce((a, x, k) => a + wt[k] * x[1], 0) / W).toFixed(1), rate_above: +(100 * st.reduce((a, x, k) => a + wt[k] * x[3], 0) / W).toFixed(1)};
  };
  const q3 = k => { const s = M.map(r => num(r[k])).filter(v => v != null).sort((a, b) => a - b); return s[Math.floor(2 * s.length / 3)]; };
  res.top_third_vs_rest_controlled = {
    ERC: strat(r => num(r.ERC), q3('ERC')), FFWI: strat(r => num(r.FFWI), q3('FFWI')), VPDA: strat(r => num(r.VPDA), q3('VPDA')),
    GSpd: strat(r => num(r.GSpd), q3('GSpd')), LFM_pct: strat(r => r.LFM_PCT, 67), LFM_raw: strat(r => r.LFM_RAW, q3('LFM_RAW'))};
  D.forEach(r => { r.a1 = +(r.AGE == 1); r.a2 = +(r.AGE == 2); r.a35 = +(r.AGE >= 3 && r.AGE <= 5); r.a614 = +(r.AGE >= 6 && r.AGE <= 14); r.mo = r.MONTH; r.mo2 = r.MONTH * r.MONTH; });
  const ctl = ['a1', 'a2', 'a35', 'a614', 'mo', 'mo2'];
  res.cv_controlled = {controls_only: fitPred(ctl), controls_lfm: fitPred([...ctl, 'LFM_PCT_', 'LFM_RAW_']),
    controls_weather: fitPred([...ctl, ...base]), controls_weather_lfm: fitPred([...ctl, ...base, 'LFM_PCT_', 'LFM_RAW_'])};
  res.rows = rows; // matched rows kept for follow-up checks
  return res;
}
