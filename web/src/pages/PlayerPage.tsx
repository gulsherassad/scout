import { Link, useParams } from "react-router-dom";
import type { PlayerProfile, SimilarResponse, ZonesResponse } from "../api";
import { PercentileBars } from "../components/PercentileBars";
import { PlayerHeader } from "../components/PlayerHeader";
import { ResultsList } from "../components/ResultsList";
import { ShotZonesPitch } from "../components/ShotZonesPitch";
import { ErrorState, Loading } from "../components/Status";
import { useApi } from "../lib/useApi";

export function PlayerPage() {
  const { id } = useParams();
  const profile = useApi<PlayerProfile>(`/players/${id}`);
  const zones = useApi<ZonesResponse>("/zones");
  const similar = useApi<SimilarResponse>(`/players/${id}/similar?limit=10`);

  if (profile.error) return <div className="page"><ErrorState message={profile.error} onRetry={profile.reload} /></div>;
  if (!profile.data) return <div className="page"><Loading label="Loading player" /></div>;
  const p = profile.data;

  return (
    <div className="page">
      <PlayerHeader player={p} distinctiveness={p.distinctiveness} lowReliability={p.low_reliability} />
      <div className="player-grid">
        <section className="card">
          <h2>Where they shoot from</h2>
          {zones.error && <ErrorState message={zones.error} onRetry={zones.reload} />}
          {zones.data ? <ShotZonesPitch zones={zones.data} weights={p.zones} /> : !zones.error && <Loading label="Loading zones" />}
        </section>
        <section className="card">
          <h2>Style vs all attackers</h2>
          <PercentileBars features={p.features} />
        </section>
      </div>
      <section className="card">
        <div className="card-head">
          <h2>Most similar players</h2>
          <Link to={`/?player=${p.id}`} className="btn-ghost">
            Filter by age, value, contract →
          </Link>
        </div>
        {similar.error && <ErrorState message={similar.error} onRetry={similar.reload} />}
        {similar.data ? <ResultsList results={similar.data.results} /> : !similar.error && <Loading label="Finding similar players" />}
      </section>
    </div>
  );
}
