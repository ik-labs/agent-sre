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
  return (
    <StepCard step="3 · Fix" title="Patch the prompt via Phoenix MCP upsert-prompt" active={active} done={applied}>
      {diff && (
        <>
          <DiffView diff={diff} />
          <button className="apply-btn" onClick={onApply} disabled={!canApply || applying || applied}>
            {applied ? "Fix applied ✓" : applying ? "Applying via MCP…" : "Apply Fix"}
          </button>
        </>
      )}
    </StepCard>
  );
}
