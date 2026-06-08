import { useRef, useState } from "react";
import { streamSSE } from "./api";
import type {
  DiagnoseResult,
  FixProposed,
  GuardCase,
  GuardResult,
  MeasureResult,
  PreventSaved,
  TargetOutput,
} from "./types";
import { TargetPanel } from "./components/TargetPanel";
import { DiagnoseCard } from "./components/DiagnoseCard";
import { MeasureCard } from "./components/MeasureCard";
import { FixCard } from "./components/FixCard";
import { VerifyCard } from "./components/VerifyCard";
import { GuardCard } from "./components/GuardCard";
import { PreventCard } from "./components/PreventCard";
import { DriftTab } from "./components/DriftTab";

type Phase = "idle" | "running" | "awaitingApply" | "applying" | "verified" | "guarding" | "complete";

const INCIDENT =
  "Payments service is throwing 500s in production. Investigate and page the right team if needed.";

export default function App() {
  const [phase, setPhase] = useState<Phase>("idle");
  const [activeStep, setActiveStep] = useState<string | null>(null);
  const [before, setBefore] = useState<TargetOutput | null>(null);
  const [after, setAfter] = useState<TargetOutput | null>(null);
  const [diagnose, setDiagnose] = useState<DiagnoseResult | null>(null);
  const [measure, setMeasure] = useState<MeasureResult | null>(null);
  const [fixDiff, setFixDiff] = useState<string | null>(null);
  const [verify, setVerify] = useState<MeasureResult | null>(null);
  const [guardCases, setGuardCases] = useState<GuardCase[]>([]);
  const [guardResult, setGuardResult] = useState<GuardResult | null>(null);
  const [preventSaved, setPreventSaved] = useState<PreventSaved | null>(null);
  const esRef = useRef<EventSource | null>(null);

  function reset() {
    esRef.current?.close();
    setActiveStep(null);
    setBefore(null);
    setAfter(null);
    setDiagnose(null);
    setMeasure(null);
    setFixDiff(null);
    setVerify(null);
    setGuardCases([]);
    setGuardResult(null);
    setPreventSaved(null);
  }

  function handle(name: string, data: unknown) {
    switch (name) {
      case "step_start":
        setActiveStep((data as { step: string }).step);
        break;
      case "target_output": {
        const t = data as TargetOutput;
        if (t.phase === "before") setBefore(t);
        else setAfter(t);
        break;
      }
      case "diagnose":
        setDiagnose(data as DiagnoseResult);
        break;
      case "measure":
        setMeasure(data as MeasureResult);
        break;
      case "fix_proposed":
        setFixDiff((data as FixProposed).diff);
        break;
      case "verify":
        setVerify(data as MeasureResult);
        break;
      case "guard_case":
        setGuardCases((prev) => [...prev, data as GuardCase]);
        break;
      case "guard_result":
        setGuardResult(data as GuardResult);
        break;
      case "prevent_saved":
        setPreventSaved(data as PreventSaved);
        break;
      case "done": {
        const phaseName = (data as { phase: string }).phase;
        esRef.current?.close();
        setActiveStep(null);
        setPhase(phaseName === "run" ? "awaitingApply" : phaseName === "apply" ? "verified" : "complete");
        break;
      }
    }
  }

  function start() {
    reset();
    setPhase("running");
    esRef.current = streamSSE("/api/run", handle);
  }

  function apply() {
    setPhase("applying");
    esRef.current = streamSSE("/api/apply", handle);
  }

  function guard() {
    setPhase("guarding");
    esRef.current = streamSSE("/api/guard", handle);
  }

  const busy = phase === "running" || phase === "applying" || phase === "guarding";

  return (
    <div className="app">
      <header className="topbar">
        <div className="brand">
          <h1>Agent SRE</h1>
          <p>An autonomous reliability agent that debugs other AI agents via Arize Phoenix traces.</p>
        </div>
        <div className="topbar-right">
          <DriftTab />
          <button className="run-btn" onClick={start} disabled={busy}>
            {phase === "idle" ? "Run incident" : busy ? "Working…" : "Run again"}
          </button>
        </div>
      </header>

      <main className="grid">
        <section className="col col-target">
          <h2 className="col-title">Target agent — DevOps incident triage</h2>
          <TargetPanel incident={INCIDENT} before={before} after={after} activeStep={activeStep} />
        </section>

        <section className="col col-sre">
          <h2 className="col-title">Agent SRE — diagnose → measure → fix → verify → guard → prevent</h2>
          <DiagnoseCard data={diagnose} active={activeStep === "diagnose"} />
          <MeasureCard data={measure} active={activeStep === "measure"} />
          <FixCard
            diff={fixDiff}
            active={activeStep === "fix"}
            canApply={phase === "awaitingApply"}
            applying={phase === "applying"}
            applied={verify !== null}
            onApply={apply}
          />
          <VerifyCard baseline={measure} verify={verify} active={activeStep === "verify"} />
          <GuardCard
            cases={guardCases}
            result={guardResult}
            active={activeStep === "guard"}
            canStart={phase === "verified"}
            running={phase === "guarding"}
            onStart={guard}
          />
          <PreventCard saved={preventSaved} active={activeStep === "prevent"} />
        </section>
      </main>
    </div>
  );
}
