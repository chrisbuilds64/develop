// A thread entry as a person reads it: paragraphs, bullet and numbered lists, `code`, **bold**, *italic*, [links](url)
// and ![images](name) of the case's own files (REQ-001 S-18). Small on purpose and safe by construction: it builds React
// elements, never HTML from the text, and an image shows only where `img` gives the name an address. Anything it does not
// know stays plain text, so a helper's older entries read as before.
import type { ReactNode } from "react";

type Img = (name: string) => string | undefined;
const INLINE = /(!\[([^\]]*)\]\(([^)\s]+)\))|(`[^`]+`)|(\*\*[^*]+\*\*)|(\*[^*\s][^*]*\*)|(\[[^\]]+\]\((https?:\/\/[^)\s]+)\))/g;

function inline(text: string, key: string, img?: Img): ReactNode[] {
  const out: ReactNode[] = [];
  let last = 0;
  let n = 0;
  for (const m of text.matchAll(INLINE)) {
    const at = m.index ?? 0;
    if (at > last) out.push(text.slice(last, at));
    const k = `${key}-${n++}`;
    const src = m[1] ? img?.(m[3]) : undefined;
    if (m[1]) out.push(src ? <img key={k} className="md-img" src={src} alt={m[2] || m[3]} loading="lazy" /> : m[0]);
    else if (m[4]) out.push(<code key={k}>{m[4].slice(1, -1)}</code>);
    else if (m[5]) out.push(<b key={k}>{m[5].slice(2, -2)}</b>);
    else if (m[6]) out.push(<i key={k}>{m[6].slice(1, -1)}</i>);
    else if (m[7]) out.push(<a key={k} href={m[8]} target="_blank" rel="noreferrer">{m[7].slice(1, m[7].indexOf("]"))}</a>);
    last = at + m[0].length;
  }
  if (last < text.length) out.push(text.slice(last));
  return out;
}

const BULLET = /^\s*[-*•]\s+/;
const NUMBER = /^\s*(?:\d+[.)]|\(?[a-z]\))\s+/;

export function Md({ text, className, img }: { text: string; className?: string; img?: Img }) {
  const blocks: ReactNode[] = [];
  const lines = text.replace(/\r\n/g, "\n").split("\n");
  let i = 0;
  while (i < lines.length) {
    if (!lines[i].trim()) { i++; continue; }
    const k = `b${blocks.length}`;
    if (BULLET.test(lines[i]) || NUMBER.test(lines[i])) {
      const ordered = NUMBER.test(lines[i]);
      const re = ordered ? NUMBER : BULLET;
      const items: string[] = [];
      while (i < lines.length && lines[i].trim()) {
        if (re.test(lines[i])) items.push(lines[i].replace(re, ""));
        else if (items.length) items[items.length - 1] += " " + lines[i].trim();   // a wrapped item
        i++;
      }
      const lis = items.map((x, j) => <li key={j}>{inline(x, `${k}-${j}`, img)}</li>);
      blocks.push(ordered ? <ol key={k}>{lis}</ol> : <ul key={k}>{lis}</ul>);
      continue;
    }
    const para: string[] = [];
    while (i < lines.length && lines[i].trim() && !BULLET.test(lines[i]) && !NUMBER.test(lines[i])) para.push(lines[i++].trim());
    blocks.push(<p key={k}>{inline(para.join(" "), k, img)}</p>);
  }
  return <div className={`md${className ? ` ${className}` : ""}`}>{blocks}</div>;
}
