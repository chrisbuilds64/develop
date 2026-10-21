// The cover: a small coloured poster on every case, the colour from the domain's theme (one meta key), label and number on it.
// What the old cockpit had, kept on the calm cards as the one place colour means "which kind". A long number shows its last segment.
export function Cover({ label, number, tint, size = "s" }: { label: string; number: string; tint: string; size?: "s" | "m" }) {
  return (
    <span className={`cover ${size}`} style={{ "--tint": tint || "var(--hairline-2)" } as React.CSSProperties} aria-hidden="true">
      <small>{label}</small>
      <b>{number.includes("-") ? number.split("-").pop() : number}</b>
    </span>
  );
}
