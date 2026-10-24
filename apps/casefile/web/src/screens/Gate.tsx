// Who are you: one button per person. Open identity (development, demo). When the identity comes from outside
// (the cockpit's login) and matches nobody here, the gate says so instead of offering a picker.
import { useState } from "react";
import { api, type ConfigView, type MeOut } from "../api";
import { words } from "../words";

export function Gate({ config, me, onSignedIn }: { config: ConfigView; me?: MeOut; onSignedIn: () => void }) {
  const w = words(config.lang);
  const [busy, setBusy] = useState<string | null>(null);
  const humans = config.people.filter((p) => p.kind === "human");
  if (me && !me.open_identity) {
    return (
      <div className="gate">
        <form onSubmit={(e) => e.preventDefault()}>
          <h1>{config.product}</h1>
          <p className="hint">{me.identity ? `${me.identity}: ${w.notAPersonHere}` : w.signIn}</p>
          <p className="hint">{humans.map((p) => p.name).join(" · ")}</p>
        </form>
      </div>
    );
  }
  return (
    <div className="gate">
      <form onSubmit={(e) => e.preventDefault()}>
        <h1>{config.product}</h1>
        <p className="hint">{w.signIn}</p>
        {humans.map((p) => (
          <button key={p.id} type="button" className="person" disabled={busy !== null}
                  onClick={async () => { setBusy(p.id); try { await api.signIn(p.id); onSignedIn(); } finally { setBusy(null); } }}>
            <span className="avatar">{p.name.slice(0, 2).toUpperCase()}</span>
            <span>{p.name}</span>
            <span className="mono hint" style={{ marginLeft: "auto" }}>{p.roles.join(" · ")}</span>
          </button>
        ))}
      </form>
    </div>
  );
}
