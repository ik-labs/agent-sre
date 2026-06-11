import { useEffect, useState, type ReactNode } from "react";
import { checkAuth, setAuthKey } from "../api";

// Shows a password screen when the demo is gated. Renders children once authorized. The password is
// never in the bundle — the user types it and the server validates (/api/check).
export function Gate({ children }: { children: ReactNode }) {
  const [status, setStatus] = useState<"loading" | "open" | "locked" | "authed">("loading");
  const [pw, setPw] = useState("");
  const [error, setError] = useState(false);

  useEffect(() => {
    // Accept the password from the URL (?key= / ?password=) so a shared link auto-authenticates,
    // else fall back to a previously stored key. Decide whether to gate.
    const params = new URLSearchParams(window.location.search);
    const urlKey = params.get("key") || params.get("password") || params.get("pw");
    const candidate = urlKey || sessionStorage.getItem("demo_key") || undefined;
    checkAuth(candidate).then((r) => {
      if (!r.gated) setStatus("open");
      else if (r.ok) {
        if (urlKey) {
          setAuthKey(urlKey); // persist for the SSE calls
          // strip the password from the address bar so it isn't left visible / copied
          window.history.replaceState({}, "", window.location.pathname);
        }
        setStatus("authed");
      } else setStatus("locked");
    });
  }, []);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError(false);
    const r = await checkAuth(pw);
    if (r.ok) {
      setAuthKey(pw);
      setStatus("authed");
    } else {
      setError(true);
    }
  }

  if (status === "loading") return <div className="gate-loading" />;
  if (status === "open" || status === "authed") return <>{children}</>;

  return (
    <div className="gate">
      <form className="gate-card" onSubmit={submit}>
        <h1>Agent SRE</h1>
        <p>This demo is password-protected. Enter the password to continue.</p>
        <input
          type="password"
          value={pw}
          autoFocus
          placeholder="Password"
          onChange={(e) => setPw(e.target.value)}
        />
        {error && <div className="gate-error">Incorrect password.</div>}
        <button type="submit" disabled={!pw}>
          Enter
        </button>
      </form>
    </div>
  );
}
