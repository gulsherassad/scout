# Experiment log

Split-half self-retrieval on 2025/26 data for all 5 leagues: 493 pool player-seasons, 20 splits (seeds 0–19), features "rates + style" unless noted. Values are mean ± std across splits. Random guess: recall@1 0.002, recall@5 0.010, recall@10 0.020, MRR 0.014.

| date | commit | description | recall@1 | recall@5 | recall@10 | MRR | recall@10 (<20 shots) |
|---|---|---|---|---|---|---|---|
| 2026-10-02 | 57fb62c | Baseline: random split of each player's appearances | 0.042 ± 0.008 | 0.132 ± 0.011 | 0.205 ± 0.015 | 0.099 ± 0.007 | 0.081 ± 0.028 |
| 2026-10-02 | 57fb62c + scratch patch | Stratified split: starts and sub appearances halved separately. **Not adopted**: no meaningful change, see note 1 | 0.043 ± 0.008 | 0.138 ± 0.016 | 0.204 ± 0.016 | 0.102 ± 0.008 | 0.084 ± 0.031 |

## Notes

1. **Stratified split (2026-10-02).** Hypothesis: the worst-ranked players (mean rank ~300–400, worse than the random ~247) fail because one half gets mostly sub appearances. Rejected:
   - Within a player, |difference in starts share between halves| does not predict rank (Spearman 0.008, p = 0.42, 9,860 player-splits). Pooled across players it is 0.06.
   - The 10 hardest players have balanced halves on average (starts-share difference 0.07–0.18, similar to the rest of the pool), and stay hardest under the stratified split (mean rank 282–395).
   - The split function was patched only for this run and is not in the code.

   What does explain it: players whose full-season profile is close to the pool average. Their z-scored profile is mostly noise, and because the two halves split one fixed set of matches, one half's deviations from the player's own average mirror the other's. So the halves point in opposite directions.
   - Distance from the pool average vs mean rank: Spearman −0.47. The 20% of players closest to the average have mean rank 151; the furthest 20% have 57.
   - Own A–B cosine is negative for all 10 hardest players (−0.07 to −0.27; pool median 0.38). 9 of the 10 are in the 35% of players closest to the average.
   - Euclidean distance instead of cosine helps some of them (e.g. Namaso 314 → 72) but leaves overall recall@10 unchanged (0.201). Not adopted; reference only.
