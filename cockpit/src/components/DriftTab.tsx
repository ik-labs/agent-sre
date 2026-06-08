import { useEffect, useState } from "react";
import { withKey } from "../api";

interface Drift {
  n_traces: number;
  n_affected: number;
  summary: string;
  phoenix_url?: string | null;
}

// LIVE (per spec it was "shown"; we upgraded it): the SRE's continuous drift watch over real
// traces of a second, intermittently-buggy agent. Triage only — no live fix.
export function DriftTab() {
  const [d, setD] = useState<Drift | null>(null);

  useEffect(() => {
    fetch(withKey("/api/drift"))
      .then((r) => r.json())
      .then(setD)
      .catch(() => {});
  }, []);

  const text = d
    ? `2nd agent watch · ${d.n_affected}/${d.n_traces} runs skipped log inspection — flagged, not yet fixed`
    : "2nd agent watch · scanning traces…";

  return (
    <div className="drift-wrap">
      <div
        className="drift"
        title="A separate, intermittently-buggy agent the SRE monitors. Read live from real Phoenix traces; surfaced (triaged) but NOT fixed in this demo — unlike the payments incident on the left."
      >
        <span className="drift-dot" />
        {text}
      </div>
      {d?.phoenix_url && (
        <a className="exp-link" href={d.phoenix_url} target="_blank" rel="noreferrer">
          open Phoenix ↗
        </a>
      )}
    </div>
  );
}
