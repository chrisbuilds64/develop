// Stroke icons, 2 px, from one hand. No glyphs, no emoji.
const base = { width: 18, height: 18, viewBox: "0 0 24 24", fill: "none", stroke: "currentColor", strokeWidth: 2, strokeLinecap: "round" as const, strokeLinejoin: "round" as const, "aria-hidden": true };
export const Swap = () => <svg {...base}><path d="M7 7h11l-3-3M17 17H6l3 3" /></svg>;
export const Restart = () => <svg {...base}><path d="M4 12a8 8 0 1 0 3-6.2M4 4v5h5" /></svg>;
export const Send = () => <svg {...base}><path d="M5 12h13M13 6l6 6-6 6" /></svg>;
export const Worlds = () => <svg {...base}><path d="M4 7h16M4 12h16M4 17h10" /></svg>;
export const Sun = () => <svg {...base}><circle cx="12" cy="12" r="4" /><path d="M12 2v2M12 20v2M2 12h2M20 12h2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4" /></svg>;
export const Moon = () => <svg {...base}><path d="M20 14.5A8 8 0 0 1 9.5 4a8 8 0 1 0 10.5 10.5z" /></svg>;
export const MenuIcon = () => <svg {...base}><path d="M4 7h16M4 12h16M4 17h16" /></svg>;
export const Close = () => <svg {...base}><path d="M6 6l12 12M18 6L6 18" /></svg>;
