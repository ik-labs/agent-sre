import { StepCard } from "./StepCard";

interface Props {
  diff: string | null;
  active: boolean;
  applied: boolean;
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

export function FixCard({ diff, active, applied }: Props) {
  return (
    <StepCard step="3 · Fix" title="Patch the prompt via Phoenix MCP upsert-prompt" active={active} done={applied}>
      {diff && (
        <>
          <DiffView diff={diff} />
          {applied && <div className="applied-tag">Applied via MCP `upsert-prompt` ✓</div>}
        </>
      )}
    </StepCard>
  );
}
