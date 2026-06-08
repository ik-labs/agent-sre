import { useEffect, useRef } from "react";
import { StepCard } from "./StepCard";

interface Props {
  diff: string | null;
  active: boolean;
  canApply: boolean;
  applying: boolean;
  applied: boolean;
  onApply: () => void;
}

function DiffView({ diff }: { diff: string }) {
  return (
    <pre className="diff">
      {diff.split("\n").map((line, i) => {
        const cls = line.startsWith("+")
          ? "add"
          : line.startsWith("-")
            ? "del"
            : line.startsWith("@@")
              ? "hunk"
              : "ctx";
        return (
          <div key={i} className={`diff-line ${cls}`}>
            {line || " "}
          </div>
        );
      })}
    </pre>
  );
}

export function FixCard({ diff, active, canApply, applying, applied, onApply }: Props) {
  const isCta = canApply && !applying && !applied;
  const btnRef = useRef<HTMLButtonElement>(null);
  useEffect(() => {
    if (isCta) btnRef.current?.scrollIntoView({ behavior: "smooth", block: "center" });
  }, [isCta]);

  return (
    <StepCard step="3 · Fix" title="Patch the prompt via Phoenix MCP upsert-prompt" active={active} done={applied}>
      {diff && (
        <>
          <DiffView diff={diff} />
          <div className="cta-row">
            <button
              ref={btnRef}
              className={`apply-btn${isCta ? " cta" : ""}`}
              onClick={onApply}
              disabled={!canApply || applying || applied}
            >
              {applied ? "Fix applied ✓" : applying ? "Applying via MCP…" : "Apply Fix"}
            </button>
            {isCta && <span className="cta-hint">← your turn: apply the fix</span>}
          </div>
        </>
      )}
    </StepCard>
  );
}
