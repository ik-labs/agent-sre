import type { PreventSaved } from "../types";
import { StepCard } from "./StepCard";

export function PreventCard({ saved, active }: { saved: PreventSaved | null; active: boolean }) {
  return (
    <StepCard
      step="6 · Prevent"
      title="Save the failure as a permanent test"
      active={active}
      done={!!saved}
      tone={saved ? "pass" : "neutral"}
    >
      {saved && (
        <p className="prevent-line">
          Saved the failing case to dataset <code className="chip">{saved.dataset}</code> via MCP{" "}
          <code className="chip">add-dataset-examples</code>
          {saved.count > 0 && <> — {saved.count} regression example{saved.count > 1 ? "s" : ""} on file</>}.
        </p>
      )}
    </StepCard>
  );
}
