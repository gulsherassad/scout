# Experiment log

Split-half self-retrieval on 2025/26 data for all 5 leagues: 493 pool player-seasons, 20 splits (seeds 0–19), features "rates + style". Values are mean ± std across splits. Random guess: recall@1 0.002, recall@5 0.010, recall@10 0.020, MRR 0.014.

Every row can be re-run with `python -m scout.evaluate <flags>` at the commit shown; each non-baseline run writes its full report to `reports/experiments/`. "Hardest 10" is the average mean rank of the baseline's 10 hardest players (out of 493; random ≈ 247).

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
