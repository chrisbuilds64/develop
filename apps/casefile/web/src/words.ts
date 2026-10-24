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
    otherLang: "English", language: "Sprache",
    views: "Ansicht", casesView: "Akten", board: "Kanban", stacked: "Liste", filter: "Filtern …",
    colNumber: "Nummer", colTitle: "Titel", colTurn: "Am Zug", colSince: "Seit", colDate: "Termin",
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
    notAPersonHere: "ist in diesem Workspace nicht als Person eingetragen. Hier arbeiten:",
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
    startOver: "Neu starten",
    theme: "Darstellung", light: "Hell", dark: "Dunkel",
    notHere: "Diese Akte gibt es hier nicht mehr.", unreachable: "Der Kern antwortet nicht.",
    openTab: "In neuem Tab öffnen", close: "Schließen", backToDesk: "Zurück zur Akte", versions: "Fassungen", popOut: "Als Fenster lösen", prev: "Voriges Dokument", next: "Nächstes Dokument",
    world: (k: string) => (k === "claims" ? "Zur Schadenakte" : k === "pressroom" ? "Zum PressRoom" : k === "egutachten" ? "Zur Gutachtenakte" : k),
    signals: "Muster", signalsHint: (a: string) => `was ${a} über alle Akten hinweg aufgefallen ist · Hinweise, keine Feststellungen`, signalsNone: "Nichts aufgefallen.",
    rules: "Regelwerk", rulesHint: "Stufen, Helfer, Regeln und Bausteine, jeweils in der gültigen Fassung", rulesStages: "Stufen und Übergänge", rulesSkills: "Was die KI tut und nie tut",
    rulesSkill: "Helfer", rulesDoes: "Tut", rulesNever: "Tut nie", rulesBy: "Darf bestellen", rulesOrders: "bestellt", rulesNeeds: "braucht", rulesAuto: "automatisch bei", rulesRules: "Regeln", rulesModules: "Textbausteine", rulesConnectors: "Schnittstellen", rulesSystem: "System", rulesStandard: "Standard", rulesCarries: "Trägt",
    fictional: "Fiktive Demo. Jeder Name ist erfunden.",
    shape: (k: string) => (k.startsWith("image") ? "ein Bild" : k.startsWith("video") ? "ein Video" : k === "pdf" ? "ein PDF" : k),
    fillFrames: (what: string) => `Leg ${what} in den Rahmen. Mehr braucht es nicht.`,
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
    otherLang: "Deutsch", language: "Language",
    views: "View", casesView: "Cases", board: "Board", stacked: "List", filter: "Filter …",
    colNumber: "Number", colTitle: "Title", colTurn: "Whose move", colSince: "Since", colDate: "Date",
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
    notAPersonHere: "is not a person in this workspace. Who works here:",
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
    startOver: "Start over",
    theme: "Appearance", light: "Light", dark: "Dark",
    notHere: "This case is not here any more.", unreachable: "The core does not answer.",
    openTab: "Open in a new tab", close: "Close", backToDesk: "Back to the case", versions: "Versions", popOut: "Pop out as a window", prev: "Previous document", next: "Next document",
    world: (k: string) => (k === "claims" ? "To the claims file" : k === "pressroom" ? "To PressRoom" : k === "egutachten" ? "To the assessment file" : k),
    signals: "Patterns", signalsHint: (a: string) => `what ${a} noticed across all files · hints, never findings`, signalsNone: "Nothing noticed.",
    rules: "Rulebook", rulesHint: "Stages, helpers, rules and modules, each in its current version", rulesStages: "Stages and hand-offs", rulesSkills: "What the AI does and never does",
    rulesSkill: "Helper", rulesDoes: "Does", rulesNever: "Never does", rulesBy: "May order", rulesOrders: "orders", rulesNeeds: "needs", rulesAuto: "automatically on", rulesRules: "Rules", rulesModules: "Text modules", rulesConnectors: "Connectors", rulesSystem: "System", rulesStandard: "Standard", rulesCarries: "Carries",
    fictional: "Fictional demo. Every name is invented.",
    shape: (k: string) => (k.startsWith("image") ? "an image" : k.startsWith("video") ? "a video" : k === "pdf" ? "a PDF" : k),
    fillFrames: (what: string) => `Put ${what} into the frame. That is all it needs.`,
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
