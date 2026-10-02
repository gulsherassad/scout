# Split-half self-retrieval: stratified (starts and sub appearances halved separately) split, cosine similarity, no shrinkage

Generated 2026-10-02 by `python -m scout.evaluate --split stratified`.

## Setup
- **Population:** 493 player-seasons from `profiles.parquet` (EPL 116, La_liga 109, Serie_A 93, Ligue_1 88, Bundesliga 87).
- **Method:** each player's appearances are split into halves A and B. Profiles built on B are matched against all 493 A profiles on z-scored features (fitted on A); we record where the player's own A profile ranks.
- **Configuration:** stratified (starts and sub appearances halved separately) split, cosine similarity, no shrinkage.
- **Splits:** 20 (seeds 0–19); metrics are mean ± std across splits.
- **Imputed values** (NaN replaced by A's mean, all features): 5.1 per split on average, out of 23664.
- The single-feature baseline uses minus the absolute difference instead of cosine, which is always ±1 in one dimension. Ties count against the player.

## Retrieval metrics
| features | recall@1 | recall@5 | recall@10 | MRR |
|---|---|---|---|---|
| rates + style | 0.043 ± 0.008 | 0.138 ± 0.016 | 0.204 ± 0.016 | 0.102 ± 0.008 |
| rates only | 0.019 ± 0.005 | 0.075 ± 0.009 | 0.130 ± 0.011 | 0.061 ± 0.004 |
| style only | 0.017 ± 0.006 | 0.069 ± 0.012 | 0.111 ± 0.013 | 0.056 ± 0.006 |
| npxG per 90 only | 0.004 ± 0.002 | 0.019 ± 0.006 | 0.041 ± 0.011 | 0.024 ± 0.003 |
| random guess | 0.002 | 0.010 | 0.020 | 0.014 |

## Recall@10 by full-season shot count (rates + style)
Shots exclude own goals, penalties and direct free kicks. Random guess is 0.020 in every bucket.

| shot_bucket | players | recall@10 |
|---|---|---|
| <20 | 54 | 0.084 ± 0.031 |
| 20–39 | 208 | 0.141 ± 0.021 |
| 40+ | 231 | 0.290 ± 0.026 |

## Recall@10 by primary position (rates + style)
| primary_position | players | recall@10 |
|---|---|---|
| AMC | 114 | 0.200 ± 0.026 |
| AML | 54 | 0.161 ± 0.038 |
| AMR | 44 | 0.234 ± 0.044 |
| FW | 207 | 0.220 ± 0.021 |
| FWL | 20 | 0.185 ± 0.059 |
| FWR | 20 | 0.203 ± 0.070 |
| ML | 16 | 0.103 ± 0.062 |
| MR | 18 | 0.219 ± 0.084 |

## Hardest players to re-identify (rates + style)
The 10 players with the worst mean rank across splits (out of 493).

| player | teams | position | shots | minutes | mean rank | best / worst rank |
|---|---|---|---|---|---|---|
| Benedict Hollerbach | Mainz 05 | FW | 22 | 903 | 395.2 | 324 / 470 |
| Shuto Machino | Borussia M.Gladbach | FW | 25 | 1046 | 370.1 | 207 / 464 |
| Lovro Majer | Wolfsburg | AMC | 25 | 1390 | 343.4 | 70 / 491 |
| Santiago Hidalgo | Toulouse | AMC | 34 | 1387 | 338.2 | 89 / 474 |
| Amin Sarr | Verona | FW | 19 | 1046 | 337.6 | 160 / 455 |
| Amine Adli | Bournemouth | AML | 19 | 1036 | 328.7 | 161 / 439 |
| Maximilian Beier | Borussia Dortmund | AMC | 49 | 2069 | 316.2 | 137 / 455 |
| Tom Louchet | Nice | AML | 21 | 1344 | 311.4 | 78 / 438 |
| Arnaud Kalimuendo Muinga | Eintracht Frankfurt, Nottingham Forest | FW | 34 | 1506 | 311.4 | 24 / 457 |
| Danny Namaso | Auxerre | ML | 59 | 2544 | 309.6 | 75 / 443 |

## Baseline's hardest players under this configuration
Average of the mean ranks: 339.2 in the baseline, 333.2 here.

| player | baseline mean rank | mean rank here |
|---|---|---|
| Shuto Machino | 401.4 | 370.1 |
| Benedict Hollerbach | 397.3 | 395.2 |
| Santiago Hidalgo | 351.7 | 338.2 |
| Amin Sarr | 349.4 | 337.6 |
| Lovro Majer | 345.2 | 343.4 |
| Amine Adli | 326.0 | 328.7 |
| Danny Namaso | 314.2 | 309.6 |
| Maximilian Beier | 312.0 | 316.2 |
| Arnaud Kalimuendo Muinga | 299.2 | 311.4 |
| Tijjani Noslin | 295.4 | 281.6 |
