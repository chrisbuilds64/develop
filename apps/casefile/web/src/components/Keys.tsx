// Keyboard shortcuts (design hand-back, 2026-11-05): one sheet, opened with "?" anywhere (not while typing), from the
// Guides menu or from Home. It lists only what this surface really does; the shortcuts themselves live where they act.
import { useEffect, useState } from "react";
import type { words } from "../words";

export const openKeys = () => window.dispatchEvent(new CustomEvent("cf:keys"));

const typing = (t: EventTarget | null) => {
  const el = t as HTMLElement | null;
  return !!el && (el.tagName === "INPUT" || el.tagName === "TEXTAREA" || el.tagName === "SELECT" || el.isContentEditable);
};

export function Keys({ w, onTheme }: { w: ReturnType<typeof words>; onTheme: () => void }) {
  const [open, setOpen] = useState(false);
  const mac = /Mac|iPhone|iPad/.test(navigator.platform);
  const cmd = mac ? "⌘" : "Ctrl";
  useEffect(() => {
    const show = () => setOpen(true);
    const key = (e: KeyboardEvent) => {
      if (e.metaKey || e.ctrlKey || e.altKey) return;
      if (e.key === "Escape" && open) { e.preventDefault(); setOpen(false); return; }
      if (typing(e.target)) return;
      if (e.key === "?") { e.preventDefault(); setOpen((o) => !o); }
      else if ((e.key === "t" || e.key === "T") && !open) onTheme();
    };
    window.addEventListener("cf:keys", show);
    window.addEventListener("keydown", key);
    return () => { window.removeEventListener("cf:keys", show); window.removeEventListener("keydown", key); };
  }, [open, onTheme]);
  if (!open) return null;
  const K = ({ k }: { k: string[] }) => <span className="ks-k">{k.map((x, i) => (x === "/" ? <span key={i} className="ks-or">/</span> : <span key={i} className="kbd">{x}</span>))}</span>;
  const groups: [string, [string, string[]][]][] = [
    [w.ksAnywhere, [[w.ksSearch, [cmd, "K"]], [w.ksTheme, ["T"]], [w.ksThis, ["?"]]]],
    [w.ksHome, [[w.ksOpenNext, ["⏎"]]]],
    [w.ksCase, [[w.ksConfirm, ["⏎"]], [w.ksNextPrev, ["J", "/", "K"]], [w.ksAsk, [cmd, "J"]], [w.ksBack, ["Esc"]]]],
  ];
  return (
    <div className="ks-scrim" role="presentation" onClick={() => setOpen(false)}>
      <div className="ks" role="dialog" aria-label={w.keysTitle} onClick={(e) => e.stopPropagation()}>
        <div className="ks-t">{w.keysTitle}<button type="button" className="ks-x" data-help-skip="closes the shortcuts" aria-label={w.close} onClick={() => setOpen(false)}>✕</button></div>
        <div className="ks-grid">
          {groups.map(([title, rows]) => (
            <div key={title} className="ks-g">
              <div className="ks-gh">{title}</div>
              {rows.map(([label, k]) => <div key={label} className="ks-r"><span>{label}</span><K k={k} /></div>)}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
