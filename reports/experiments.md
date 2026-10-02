# Experiment log

Split-half self-retrieval on 2025/26 data for all 5 leagues: 493 pool player-seasons, 20 splits (seeds 0–19), features "rates + style". Values are mean ± std across splits. Random guess: recall@1 0.002, recall@5 0.010, recall@10 0.020, MRR 0.014.

Every row can be re-run with `python -m scout.evaluate <flags>` at the commit shown; each non-baseline run writes its full report to `reports/experiments/`. Flags are relative to the defaults at that commit: from f7890f4 the default features include 6 shot-location zones, so the earlier baseline is `--zones 0` there. "Hardest 10" is the average mean rank of the no-zones baseline's 10 hardest players (out of 493; random ≈ 247).

| date | commit | flags | description | recall@1 | recall@5 | recall@10 | MRR | recall@10 (<20 shots) | hardest 10 |
|---|---|---|---|---|---|---|---|---|---|
| 2026-10-02 | 7e2115d | *(none)* | Baseline: random split, cosine, no shrinkage | 0.042 ± 0.008 | 0.132 ± 0.011 | 0.205 ± 0.015 | 0.099 ± 0.007 | 0.081 ± 0.028 | 339.2 |
| 2026-10-02 | 7e2115d | `--split stratified` | Stratified split. **Not adopted** (note 1) | 0.043 ± 0.008 | 0.138 ± 0.016 | 0.204 ± 0.016 | 0.102 ± 0.008 | 0.084 ± 0.031 | 333.2 |
| 2026-10-02 | 7e2115d | `--metric euclidean` | Euclidean distance instead of cosine. **Not adopted** (note 1) | 0.041 ± 0.008 | 0.130 ± 0.012 | 0.201 ± 0.014 | 0.098 ± 0.008 | 0.054 ± 0.033 | 241.6 |
| 2026-10-02 | 7e2115d | `--shrinkage-k 0` | Shot-style share shrinkage, k = 0 (= baseline) | 0.042 ± 0.008 | 0.132 ± 0.011 | 0.205 ± 0.015 | 0.099 ± 0.007 | 0.081 ± 0.028 | 339.2 |
| 2026-10-02 | 7e2115d | `--shrinkage-k 5` | Shrinkage, k = 5 | 0.038 ± 0.008 | 0.127 ± 0.011 | 0.199 ± 0.014 | 0.095 ± 0.008 | 0.099 ± 0.032 | 341.0 |
| 2026-10-02 | 7e2115d | `--shrinkage-k 10` | Shrinkage, k = 10 | 0.037 ± 0.006 | 0.124 ± 0.010 | 0.197 ± 0.015 | 0.093 ± 0.007 | 0.116 ± 0.037 | 341.0 |
| 2026-10-02 | 7e2115d | `--shrinkage-k 20` | Shrinkage, k = 20 | 0.035 ± 0.007 | 0.123 ± 0.009 | 0.196 ± 0.014 | 0.092 ± 0.007 | 0.123 ± 0.042 | 339.9 |
| 2026-10-02 | 7e2115d | `--shrinkage-k 40` | Shrinkage, k = 40 (note 2) | 0.035 ± 0.008 | 0.120 ± 0.009 | 0.195 ± 0.013 | 0.091 ± 0.008 | 0.143 ± 0.050 | 338.3 |
| 2026-10-02 | 77d4c83 | `--zones 4` | Shot-location zones (NMF on shot heatmaps), k = 4, all features (note 3) | 0.056 ± 0.006 | 0.170 ± 0.011 | 0.252 ± 0.014 | 0.123 ± 0.006 | 0.116 ± 0.037 | 335.3 |
| 2026-10-02 | 77d4c83 | `--zones 6` | Zones, k = 6, all features. **Adopted** (note 3) | 0.059 ± 0.009 | 0.178 ± 0.012 | 0.258 ± 0.011 | 0.128 ± 0.008 | 0.118 ± 0.033 | 342.2 |
| 2026-10-02 | 77d4c83 | `--zones 8` | Zones, k = 8, all features | 0.058 ± 0.010 | 0.175 ± 0.012 | 0.258 ± 0.014 | 0.127 ± 0.009 | 0.123 ± 0.039 | 335.2 |
| 2026-10-02 | 77d4c83 | `--zones 10` | Zones, k = 10, all features | 0.056 ± 0.008 | 0.178 ± 0.014 | 0.258 ± 0.013 | 0.127 ± 0.008 | 0.114 ± 0.034 | 333.3 |
| 2026-10-02 | 77d4c83 | `--zones 6` | Zones only, k = 6 ("zones only" set of the run above) | 0.016 ± 0.005 | 0.065 ± 0.008 | 0.118 ± 0.012 | 0.055 ± 0.004 | 0.078 ± 0.030 | — |
| 2026-10-02 | f7890f4 | *(none)* | **New baseline**: default features now include 6 zones (same numbers as `--zones 6` above) | 0.059 ± 0.009 | 0.178 ± 0.012 | 0.258 ± 0.011 | 0.128 ± 0.008 | 0.118 ± 0.033 | 342.2 |
| 2026-10-02 | 5823926 | `--mode recent` | Recent-form profiles: each player's newest 2,000 league minutes across 2025/26 and 2026/27, window split in half; own pool of 522 (random recall@10 0.019) (note 4) | 0.058 ± 0.009 | 0.166 ± 0.013 | 0.249 ± 0.018 | 0.125 ± 0.009 | 0.118 ± 0.045 | — |

## Notes

1. **Stratified split and Euclidean distance (2026-10-02).** Hypothesis: the worst-ranked players (mean rank ~300–400, worse than the random ~247) fail because one half gets mostly sub appearances. Rejected:
   - Within a player, |difference in starts share between halves| does not predict rank (Spearman 0.008, p = 0.42, 9,860 player-splits). Pooled across players it is 0.06.
   - The 10 hardest players have balanced halves on average (starts-share difference 0.07–0.18, similar to the rest of the pool), and stay hardest under the stratified split.

   What does explain it: players whose full-season profile is close to the pool average. Their z-scored profile is mostly noise, and because the two halves split one fixed set of matches, one half's deviations from the player's own average mirror the other's. So the halves point in opposite directions.
   - Distance from the pool average vs mean rank: Spearman −0.47. The 20% of players closest to the average have mean rank 151; the furthest 20% have 57.
   - Own A–B cosine is negative for all 10 hardest players (−0.07 to −0.27; pool median 0.38). 9 of the 10 are in the 35% of players closest to the average.
   - Euclidean distance brings the hardest 10 to about random (241.6) but does not improve overall recall@10 (0.201) and lowers recall@10 for <20 shots (0.054).

2. **Shot-style share shrinkage (2026-10-02).** lastAction and shotType shares become (count + k · prior) / (n_shots + k), with priors = pool-wide shares across all players' style shots (not position-specific, which would leak full-season information into both halves). **k is tuned on this same evaluation, so the best value is slightly optimistic.**
   - Paired by split (same seeds), shrinkage helps players with <20 shots consistently (k = 40: +0.061 recall@10, better on 19 of 20 splits, worse on 0) but hurts players with 40+ shots just as consistently (k = 40: −0.032, worse on 19 of 20). Overall recall@10 falls at every k (k = 40: −0.010, worse on 18 of 20).
   - The <20 bucket is 54 players, the 40+ bucket 231, so the net effect is negative.
   - It does nothing for the hardest 10 (338–341 vs 339.2): their problem is closeness to the pool average, and shrinkage pulls players further towards it.
   - In this evaluation each half has about half a player's shots, so a given k shrinks twice as hard here as it would on full-season profiles.

3. **Shot-location zones (2026-10-02).** Following Decroos et al., "Player Vectors": each player's style shots (no own goals, penalties or direct free kicks) become a 2D histogram over the attacking area (70–105 m, full width, 10 × 20 cells of 3.5 × 3.4 m; shots from further out go in the first row; not mirrored), smoothed (Gaussian, σ = 1 cell) and normalised to sum to 1. NMF on the player × cell matrix gives k zone weights per player, normalised to sum to 1. In the evaluation, NMF is fitted on the A-half grids only within each split and applied to both halves. **k is tuned on this same evaluation, so the best value is slightly optimistic.**
   - Paired by split against the no-zones baseline, recall@10 change (splits better / worse, of 20):

     | k | all (493) | <20 shots (54) | 20–39 shots (208) | 40+ shots (231) |
     |---|---|---|---|---|
     | 4 | +0.047 (20 / 0) | +0.034 (17 / 1) | +0.039 (19 / 0) | +0.056 (20 / 0) |
     | 6 | +0.053 (20 / 0) | +0.036 (16 / 1) | +0.046 (20 / 0) | +0.064 (20 / 0) |
     | 8 | +0.053 (20 / 0) | +0.042 (14 / 1) | +0.049 (20 / 0) | +0.058 (20 / 0) |
     | 10 | +0.053 (20 / 0) | +0.032 (13 / 3) | +0.053 (20 / 0) | +0.059 (20 / 0) |

   - Unlike shrinkage, zones help every shot-count group. k = 6, 8 and 10 tie on recall@10 (0.258); k = 6 has the best recall@1 and MRR with the fewest components, so it was adopted.
   - Zones alone (0.118) are about as informative as rates alone (0.124) or style shares alone (0.112), and add to them.
   - They do not help the hardest players (333–342 vs 339.2): see note 1.
   - Components: `reports/figures/shot_zones_k6.png` (`python -m scout.figures --zones 6`).
4. **Recent-form profiles (2026-10-02).** One profile per player from their newest league appearances, newest first across seasons, up to and including the one that reaches 2,000 minutes; same pool thresholds (5 starts, 900 minutes) applied to the window. 522 players, of whom 119 have no 2026/27 league minutes yet, so their window lies in 2025/26.
   - Not directly comparable with the season baseline: a different pool (522 vs 493, random recall@10 0.019 vs 0.020), and windows are capped near 2,000 minutes where season profiles use up to a full season, so each half has fewer matches for regular starters.
   - Even so, recall@10 is close (0.249 ± 0.018 vs 0.258 ± 0.011), as is recall@10 for <20 shots (0.118 for both). Recent form identifies players about as well as a full season.
