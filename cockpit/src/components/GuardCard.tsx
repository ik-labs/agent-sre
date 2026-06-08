import { useEffect, useRef } from "react";
import type { GuardCase, GuardResult } from "../types";
import { StepCard } from "./StepCard";

interface Props {
  cases: GuardCase[];
  result: GuardResult | null;
  active: boolean;
  canStart: boolean;
  running: boolean;
  onStart: () => void;
}

export function GuardCard({ cases, result, active, canStart, running, onStart }: Props) {
  const started = cases.length > 0 || result !== null || running;
  const isCta = !started && canStart;
  const btnRef = useRef<HTMLButtonElement>(null);
  useEffect(() => {
    if (isCta) btnRef.current?.scrollIntoView({ behavior: "smooth", block: "center" });
  }, [isCta]);
  return (
    <StepCard
      step="5 · Guard"
      title="Replay the golden set — no regressions"
      active={active}
      done={!!result}
      tone={result ? (result.all_pass ? "pass" : "fail") : "neutral"}
    >
      {isCta && (
        <div className="cta-row">
          <button ref={btnRef} className="apply-btn cta" onClick={onStart}>
            Guard &amp; Prevent
          </button>
          <span className="cta-hint">← next: replay the golden set &amp; save the regression</span>
        </div>
      )}
      {started && (
        <>
          <ul className="golden">
            {cases.map((c) => (
              <li key={c.label} className={c.passed ? "ok" : "bad"}>
                <span className="g-mark">{c.passed ? "✓" : "✗"}</span>
                <span className="g-label">{c.label}</span>
                <span className="g-team">{c.paged_team}</span>
              </li>
            ))}
          </ul>
          {result && (
            <div className="guard-result">
              <span className={`score-badge ${result.all_pass ? "pass" : "fail"}`}>
                {result.passed}/{result.total} {result.all_pass ? "all green" : "REGRESSION"}
              </span>
              {result.url && (
                <a className="exp-link" href={result.url} target="_blank" rel="noreferrer">
                  view Phoenix experiment ↗
                </a>
              )}
            </div>
          )}
        </>
      )}
    </StepCard>
  );
}
