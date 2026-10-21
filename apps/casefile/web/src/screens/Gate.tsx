// Who are you: one button per person. Open identity (development, demo); a login replaces this later.
import { useState } from "react";
import { api, type ConfigView } from "../api";
import { words } from "../words";

export function Gate({ config, onSignedIn }: { config: ConfigView; onSignedIn: () => void }) {
  const w = words(config.lang);
  const [busy, setBusy] = useState<string | null>(null);
  const humans = config.people.filter((p) => p.kind === "human");
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
