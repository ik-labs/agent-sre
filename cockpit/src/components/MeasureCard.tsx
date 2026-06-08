import type { MeasureResult } from "../types";
import { StepCard } from "./StepCard";

export function MeasureCard({ data, active }: { data: MeasureResult | null; active: boolean }) {
  return (
    <StepCard
      step="2 · Measure"
      title="Prove the bug with an eval (baseline)"
      active={active}
      done={!!data}
      tone={data ? (data.score === 1 ? "pass" : "fail") : "neutral"}
    >
      {data && (
        <>
          <div className="score-line">
            <span className={`score-badge ${data.score === 1 ? "pass" : "fail"}`}>
              {data.score}/1 {data.verdict}
            </span>
          </div>
          <p className="reason">{data.reason}</p>
        </>
      )}
    </StepCard>
  );
}
