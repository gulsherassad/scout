import type { PlayerSummary } from "../api";
import { formatDate, formatMonth, formatValue, roleClass } from "../lib/format";

type Props = {
  player: PlayerSummary;
  distinctiveness: number;
  lowReliability: boolean;
  windowMinutes?: number;
};

export function PlayerHeader({ player, distinctiveness, lowReliability, windowMinutes }: Props) {
  return (
    <header className="player-header">
      <div className="player-title">
        <span className={`role-dot ${roleClass(player.position)}`} aria-hidden="true" />
        <h1>{player.name}</h1>
        {player.active === false && (
          <span className="badge badge-inactive" title="No league appearance in the current season">
            Inactive
          </span>
        )}
      </div>
      <p className="player-sub">
        {player.team} · {player.league.replace("_", " ")} · {player.position}
      </p>
      <dl className="facts">
        <div>
          <dt>Age</dt>
          <dd>{player.age ?? "—"}</dd>
        </div>
        <div>
          <dt>Value</dt>
          <dd>{formatValue(player.market_value_m)}</dd>
        </div>
        <div>
          <dt>Contract to</dt>
          <dd>{formatMonth(player.contract_end)}</dd>
        </div>
        <div>
          <dt>Profile window</dt>
          <dd className="small">
            {formatDate(player.window_start)} – {formatDate(player.window_end)}
            {windowMinutes ? <span className="muted"> · {player.minutes ?? "?"} of last {windowMinutes} min</span> : null}
          </dd>
        </div>
        <div>
          <dt>Distinctiveness</dt>
          <dd>
            <span className="num">{Math.round(distinctiveness)}</span>
            <span className="muted small"> / 100</span>
          </dd>
        </div>
      </dl>
      {lowReliability && (
        <p className="warning" role="note">
          <strong>Low reliability.</strong> This profile is close to the average attacker (more distinctive than only{" "}
          {Math.round(distinctiveness)}% of the pool), so the similar players below are less trustworthy.
        </p>
      )}
    </header>
  );
}
