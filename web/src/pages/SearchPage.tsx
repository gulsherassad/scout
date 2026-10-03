import { useNavigate, useSearchParams } from "react-router-dom";
import type { SimilarResponse } from "../api";
import { FiltersPanel } from "../components/FiltersPanel";
import { PlayerHeader } from "../components/PlayerHeader";
import { ResultsList } from "../components/ResultsList";
import { SearchBox } from "../components/SearchBox";
import { ErrorState, Loading } from "../components/Status";
import { buildSimilarQuery, parseFilters, type Filters } from "../lib/format";
import { useApi } from "../lib/useApi";

/** Home: search a player, then their most similar players. The selected player and the
 * filters live in the URL, so a search can be bookmarked or shared. */
export function SearchPage() {
  const [params, setParams] = useSearchParams();
  const navigate = useNavigate();
  const playerId = params.get("player");
  const filters = parseFilters(params);
  const { data, error, loading, reload } = useApi<SimilarResponse>(
    playerId ? `/players/${playerId}/similar${buildSimilarQuery(filters)}` : null,
  );

  const setFilters = (f: Filters) => {
    const query = new URLSearchParams(buildSimilarQuery(f));
    if (playerId) query.set("player", playerId);
    setParams(query, { replace: true });
  };

  return (
    <div className="page">
      <section className={playerId ? "hero hero-compact" : "hero"}>
        {!playerId && (
          <>
            <p className="eyebrow">Style scouting · Europe's top five leagues</p>
            <h1 className="hero-title">Who plays like them?</h1>
            <p className="hero-lede">
              Search an attacker to find players with a similar style: where they shoot from, how their chances are created and
              how involved they are in attacks. Then narrow by age, value and contract.
            </p>
          </>
        )}
        <SearchBox autoFocus={!playerId} onSelect={(hit) => setParams(new URLSearchParams({ player: String(hit.id) }))} />
      </section>

      {playerId && error && <ErrorState message={error} onRetry={reload} />}
      {playerId && !data && loading && <Loading label="Finding similar players" />}
      {playerId && data && (
        <div className={loading ? "results-area is-updating" : "results-area"} aria-busy={loading}>
          <PlayerHeader player={data.player} distinctiveness={data.distinctiveness} lowReliability={data.low_reliability} />
          <div className="toolbar">
            <FiltersPanel key={playerId} value={filters} onChange={setFilters} />
            <button type="button" className="btn" onClick={() => navigate(`/player/${data.player.id}`)}>
              Full profile →
            </button>
          </div>
          <p className="result-count muted">
            {data.results.length} shown of {data.candidates} candidates
            {data.removed_by_filters > 0 && ` · ${data.removed_by_filters} removed by filters`}
            {data.inactive_excluded > 0 && ` · ${data.inactive_excluded} inactive players hidden`}
          </p>
          <ResultsList results={data.results} />
        </div>
      )}
    </div>
  );
}
