import type { TargetOutput } from "../types";

interface Props {
  incident: string;
  before: TargetOutput | null;
  after: TargetOutput | null;
  activeStep: string | null;
}

function OutputBlock({ data, label }: { data: TargetOutput; label: string }) {
  const bad = data.verdict === "healthy";
  return (
    <div className={`target-output ${bad ? "is-bad" : "is-good"}`}>
      <div className="target-output-label">{label}</div>
      <ul className="toolcalls">
        {data.calls.map((c, i) => (
          <li key={i}>
            <code>{c}</code>
          </li>
        ))}
      </ul>
      <div className="verdict">
        {bad ? "healthy ❌" : "paged ✅"}
        <span className="verdict-detail">{lastLine(data.final)}</span>
      </div>
    </div>
  );
}

function lastLine(final: string): string {
  const lines = (final || "").trim().split("\n");
  return lines[lines.length - 1] || "";
}

export function TargetPanel({ incident, before, after, activeStep }: Props) {
  const running = activeStep === "target_before" || activeStep === "target_after";
  return (
    <div className="target-panel">
      <div className="incident">
        <div className="incident-label">Incident report</div>
        <p>“{incident}”</p>
      </div>

      {before ? (
        <OutputBlock data={before} label="Agent's answer (before fix)" />
      ) : (
        <div className="placeholder">{running ? "Running the agent…" : "Press “Run incident”."}</div>
      )}

      {after && <OutputBlock data={after} label="Agent's answer (after fix)" />}
    </div>
  );
}
