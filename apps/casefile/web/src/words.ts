// The surface's own words, the few the configuration does not carry. German first (the demo), English second.
export type Lang = "de" | "en";

const W = {
  de: {
    nothing: "Nichts wartet auf dich.",
    one: "Eine Sache wartet auf dich.",
    many: (n: number) => `${n} Dinge warten auf dich.`,
    oneCase: "Eine Akte wartet auf dich.",
    manyCases: (n: number) => `${n} Akten warten auf dich.`,
    nice: "Schön.",
    others: "Andere sind dran",
    coming: "Demnächst",
    workshop: "Werkstatt",
    stages: "Stufen",
    dropIn: "+ Etwas hineinlegen",
    askClaude: (a: string) => `${a} fragen`,
    onDesk: "In der Akte",
    missing: "Fehlt noch",
    conversation: "Verlauf",
    notePlaceholder: (a: string) => `Notiz, oder frag ${a} …`,
    since: "seit",
    yourMove: "Du bist dran",
    answer: "Antworten",
    done: "Erledigt",
    undo: "Rückgängig",
    doneMoved: (to: string) => `Erledigt · jetzt ${to}`,
    firstHere: "Erst",
    dropHere: "hier ablegen",
    tapToAdd: "antippen und Datei wählen",
    version: (n: number) => (n > 1 ? `Fassung ${n}` : "Fassung 1"),
    keeps: "frühere Fassungen bleiben erhalten",
    open: "Öffnen",
    signIn: "Wer bist du?",
    signOut: "Abmelden",
    switchHand: "Menü auf die andere Seite",
    menu: "Menü",
    amount: "Betrag",
    date: "Termin",
    link: "Link",
    byHand: "von Hand",
    waitingFor: (who: string) => `wartet auf ${who}`,
    waitingForYou: "wartet auf dich",
    isWorking: (who: string) => `${who} arbeitet gerade`,
    you: "Du",
    moved: "Weiter",
    sample: (what: string) => `Beispiel einlegen: ${what}`,
  },
  en: {
    nothing: "Nothing waits for you.",
    one: "One thing waits for you.",
    many: (n: number) => `${n} things wait for you.`,
    oneCase: "One case waits for you.",
    manyCases: (n: number) => `${n} cases wait for you.`,
    nice: "Nice.",
    others: "Others are on it",
    coming: "Coming up",
    workshop: "Workshop",
    stages: "stages",
    dropIn: "+ Drop something in",
    askClaude: (a: string) => `Ask ${a}`,
    onDesk: "On the desk",
    missing: "Still missing",
    conversation: "Conversation",
    notePlaceholder: (a: string) => `Note, or ask ${a}…`,
    since: "since",
    yourMove: "Your move",
    answer: "Answer",
    done: "Done",
    undo: "Undo",
    doneMoved: (to: string) => `Done · now ${to}`,
    firstHere: "First",
    dropHere: "drop it here",
    tapToAdd: "tap to add a file",
    version: (n: number) => (n > 1 ? `version ${n}` : "version 1"),
    keeps: "earlier versions stay",
    open: "Open",
    signIn: "Who are you?",
    signOut: "Sign out",
    switchHand: "Move the menu to the other side",
    menu: "Menu",
    amount: "Amount",
    date: "Date",
    link: "Link",
    byHand: "by hand",
    waitingFor: (who: string) => `waiting for ${who}`,
    waitingForYou: "waiting for you",
    isWorking: (who: string) => `${who} is working`,
    you: "You",
    moved: "Moved",
    sample: (what: string) => `Put in a sample ${what.toLowerCase()}`,
  },
};

export function words(lang: string) {
  return W[(lang === "de" ? "de" : "en") as Lang];
}

export function ago(iso: string, lang: string): string {
  if (!iso) return "";
  const d = new Date(iso.replace(" ", "T"));
  if (Number.isNaN(d.getTime())) return iso;
  const diff = Date.now() - d.getTime();
  const m = Math.round(diff / 60000);
  const de = lang === "de";
  if (m < 1) return de ? "gerade eben" : "just now";
  if (m < 60) return de ? `${m} Min.` : `${m} min`;
  const h = Math.round(m / 60);
  if (h < 24) return de ? `${h} Std.` : `${h} h`;
  const days = Math.round(h / 24);
  if (days < 7) return de ? `${days} Tag${days > 1 ? "en" : ""}` : `${days} day${days > 1 ? "s" : ""}`;
  return d.toLocaleDateString(de ? "de-DE" : "en-GB", { day: "numeric", month: "short" });
}

export function dateWords(iso: string, lang: string): string {
  if (!iso) return "";
  const d = new Date(iso.slice(0, 10));
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleDateString(lang === "de" ? "de-DE" : "en-GB", { weekday: "short", day: "numeric", month: "short" });
}
