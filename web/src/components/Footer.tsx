import type { Meta } from "../api";
import { useApi } from "../lib/useApi";

export const EVALUATION_URL = "https://github.com/gulsherassad/scout#evaluation";

export function Footer() {
  const { data } = useApi<Meta>("/meta");
  return (
    <footer className="site-footer">
      <p>
        Data: Understat (match events, window to {data?.data_window_end ?? "…"}) · Transfermarkt via{" "}
        <a href="https://github.com/dcaribou/transfermarkt-datasets">transfermarkt-datasets</a>, CC0 (market snapshot{" "}
        {data?.market_snapshot ?? "…"})
      </p>
      <p>
        Self-retrieval recall@10: <span className="num">{data?.recall_at_10?.toFixed(3) ?? "…"}</span>{" "}
        <a href={EVALUATION_URL}>how this is measured</a>
        {data ? <span className="muted"> · {data.pool_size} attackers</span> : null}
      </p>
    </footer>
  );
}
