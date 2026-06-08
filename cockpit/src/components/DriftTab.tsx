import { useEffect, useState } from "react";

interface Drift {
  n_traces: number;
  n_affected: number;
  summary: string;
}

// LIVE (per spec it was "shown"; we upgraded it): the SRE's continuous drift watch over real
// traces of a second, intermittently-buggy agent. Triage only — no live fix.
export function DriftTab() {
  const [d, setD] = useState<Drift | null>(null);

  useEffect(() => {
    fetch("/api/drift")
      .then((r) => r.json())
      .then(setD)
      .catch(() => {});
  }, []);

  const text = d
    ? `Drift watch: ${d.n_affected}/${d.n_traces} traces skipped log inspection (triage only)`
    : "Drift watch: scanning traces…";

  return (
    <div className="drift" title="Live triage of an intermittent 2nd bug — diagnose only">
      <span className="drift-dot" />
      {text}
    </div>
  );
}
