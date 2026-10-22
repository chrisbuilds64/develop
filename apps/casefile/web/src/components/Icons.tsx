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
export const Back = () => <svg {...base}><path d="M19 12H6M12 6l-6 6 6 6" /></svg>;
export const Prev = () => <svg {...base}><path d="M15 6l-6 6 6 6" /></svg>;
export const Next = () => <svg {...base}><path d="M9 6l6 6-6 6" /></svg>;
export const PopOut = () => <svg {...base}><path d="M14 4h6v6M20 4l-8 8M18 14v5H5V6h5" /></svg>;
export const ViewCases = () => <svg {...base}><path d="M4 5h16v14H4zM4 10h16M9 10v9" /></svg>;
export const ViewBoard = () => <svg {...base}><path d="M4 4h4v16H4zM10 4h4v10h-4zM16 4h4v7h-4z" /></svg>;
export const ViewList = () => <svg {...base}><path d="M4 6h16M4 12h16M4 18h16" /></svg>;
export const Globe = () => <svg {...base}><circle cx="12" cy="12" r="9" /><path d="M3 12h18M12 3a14 14 0 0 1 0 18M12 3a14 14 0 0 0 0 18" /></svg>;
export const Book = () => <svg {...base}><path d="M4 4h7a3 3 0 0 1 3 3v13a2 2 0 0 0-2-2H4zM20 4h-7a3 3 0 0 0-3 3v13a2 2 0 0 1 2-2h8z" /></svg>;
