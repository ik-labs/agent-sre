import type { ReactNode } from "react";

interface Props {
  step: string;
  title: string;
  active: boolean;
  done: boolean;
  children?: ReactNode;
  tone?: "neutral" | "fail" | "pass";
}

export function StepCard({ step, title, active, done, children, tone = "neutral" }: Props) {
  const state = active ? "active" : done ? "done" : "pending";
  return (
    <div className={`card card-${state} tone-${tone}`}>
      <div className="card-head">
        <span className="card-step">{step}</span>
        <span className="card-title">{title}</span>
        <span className="card-status">
          {active ? <span className="spinner" aria-label="working" /> : done ? "✓" : "•"}
        </span>
      </div>
      {children && <div className="card-body">{children}</div>}
    </div>
  );
}
