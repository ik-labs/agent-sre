import type { MeasureResult } from "../types";
import { StepCard } from "./StepCard";

interface Props {
  baseline: MeasureResult | null;
  verify: MeasureResult | null;
  active: boolean;
}

// The climax: same case, re-run live after the fix. eval flips 0/1 -> 1/1, output healthy -> paged.
export function VerifyCard({ baseline, verify, active }: Props) {
  return (
    <StepCard
      step="4 · Verify"
      title="Re-run live — did the fix work?"
      active={active}
      done={!!verify}
      tone={verify ? "pass" : "neutral"}
    >
      {!verify && active && (
        <p className="working">Re-running the same incident live with the fixed prompt… (~30s)</p>
      )}
      {verify && baseline && (
        <div className="flip">
          <div className="flip-row">
            <span className="flip-label">Eval</span>
            <span className="score-badge fail">{baseline.score}/1 FAIL</span>
            <span className="arrow">→</span>
            <span className="score-badge pass big">{verify.score}/1 PASS</span>
          </div>
          <div className="flip-row">
            <span className="flip-label">Output</span>
            <span className="pill bad">healthy ❌</span>
            <span className="arrow">→</span>
            <span className="pill good big">paged ✅</span>
          </div>
          <p className="reason">{verify.reason}</p>
        </div>
      )}
    </StepCard>
  );
}
