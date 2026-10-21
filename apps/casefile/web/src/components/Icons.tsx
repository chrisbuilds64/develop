// Stroke icons, 2 px, from one hand. No glyphs, no emoji.
const base = { width: 18, height: 18, viewBox: "0 0 24 24", fill: "none", stroke: "currentColor", strokeWidth: 2, strokeLinecap: "round" as const, strokeLinejoin: "round" as const, "aria-hidden": true };
export const Swap = () => <svg {...base}><path d="M7 7h11l-3-3M17 17H6l3 3" /></svg>;
export const Restart = () => <svg {...base}><path d="M4 12a8 8 0 1 0 3-6.2M4 4v5h5" /></svg>;
export const Send = () => <svg {...base}><path d="M5 12h13M13 6l6 6-6 6" /></svg>;
export const Worlds = () => <svg {...base}><path d="M4 7h16M4 12h16M4 17h10" /></svg>;
