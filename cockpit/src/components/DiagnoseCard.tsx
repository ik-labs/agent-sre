import type { DiagnoseResult } from "../types";
import { StepCard } from "./StepCard";

export function DiagnoseCard({ data, active }: { data: DiagnoseResult | null; active: boolean }) {
  return (
    <StepCard step="1 · Diagnose" title="Read the traces via Phoenix MCP" active={active} done={!!data}>
      {data && (
        <>
          <div className="mcp-tools">
            MCP tools used:{" "}
            {data.tools.map((t) => (
              <code key={t} className="chip">
                {t}
              </code>
            ))}
          </div>
          <pre className="diagnosis">{data.text}</pre>
          {data.url && (
            <a className="exp-link" href={data.url} target="_blank" rel="noreferrer">
              view traces in Phoenix ↗
            </a>
          )}
        </>
      )}
    </StepCard>
  );
}
