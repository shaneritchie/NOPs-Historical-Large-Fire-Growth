# Live fuel moisture vs. large growth days — test results (2026-11-23)

Script: `scripts/lfm_skill_test.js` (runs in a browser console on the GitHub Pages site).

## Data
- **Source:** FEMS Field Sample database (measured live fuel moisture), public GraphQL at
  `https://fems.fs2c.usda.gov/fuelmodel/apis/graphql`.
- **Sites:** 274 sample sites in/near North Ops, about 46,500 samples. Live shrub/tree samples only; draft samples dropped.
- **Matching to fire-days:** each fire-day uses the live samples within 30 mi of the fire, taken in the 21 days up to the date.
  - Each sample is ranked against that site and species' samples within ±15 days of the same calendar date (all years; needs at least 8 samples from at least 4 years).
  - The fire-day gets the median rank (LFM percentile) and the median raw value.
- **Coverage:** 4,200 of 4,623 fire-days (91%) have a sample, and 4,081 (88%) have a percentile.

## Results
### Raw comparison, no controls
| Raw LFM (%) | Fire-days | Large growth rate |
|---|---|---|
| < 80 | 593 | 29% |
| 80–100 | 1,807 | 18% |
| 100–120 | 1,279 | 29% |
| 120–150 | 458 | 44% |
| ≥ 150 | 63 | 49% |

The rate goes *up* as fuels get wetter, which is the opposite of the physical expectation. The seasonal percentile shows no pattern (23–30% in every bin).

### Why: fire age and month dominate
**By fire age:**

| Day of fire | Large growth rate |
|---|---|
| Day 1 | 59% |
| Day 2 | 71% |
| Days 3–5 | 38% |
| Days 6–14 | 12% |
| Day 15+ | 3% |

**By month:** June 56%, July 42%, August 25%, September 19%, October 18%.

Live fuel moisture is high early in the season and on young fires, so raw LFM is mostly standing in for "early in the fire / early in the season".

### Controlled for fire age × month
Large growth rate, top third vs. the rest, averaged within fire-age × month groups:

| Variable | Rest | Top third |
|---|---|---|
| ERC | 28.5% | 31.7% |
| VPD (afternoon) | 28.1% | 32.2% |
| FFWI | 29.2% | 31.1% |
| Peak gust | 28.8% | 28.8% |
| LFM percentile (wettest third) | 25.3% | 28.2% |
| Raw LFM (wettest third) | 30.0% | 32.1% |

Even after controls, wetter live fuels go with slightly *more* large growth, so the dataset shows no drying signal.

### Cross-validated logistic regression
5 folds, grouped by fire.

| Model | AUC | Log loss |
|---|---|---|
| Fire age + month | 0.848 | 0.3998 |
| + LFM | 0.854 | 0.3992 |
| + weather/dead fuels | 0.858 | 0.3973 |
| + weather/dead fuels + LFM | 0.859 | 0.3968 |

## Conclusion
- Measured LFM does **not** add useful skill for predicting which days a burning North Ops fire makes a large run, beyond what the weather and dead-fuel variables already give.
- What signal there is points the wrong way, and it comes from seasonality.
- **Not recommended** as a scoring input. It could still be shown as context (season-to-date curing), clearly labeled as not part of the score.

## Caveats
- Samples are 1–3 weeks old and taken up to 30 mi from the fire, often in a different species or at a different elevation.
- The dataset holds only days when a fire was already burning. LFM may matter more for whether a new start becomes large than for which day it grows.
- Chamise-only matches are too few (564 fire-days) to test on their own.
