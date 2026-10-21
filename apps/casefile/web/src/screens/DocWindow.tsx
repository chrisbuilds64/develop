// The reader as its own window: one case, its documents, no menu. Opened by "pop out" from the case; the chips and ← → still walk the documents.
import { useQuery } from "@tanstack/react-query";
import { api, ApiError, BASE, type ConfigView } from "../api";
import { Reader } from "../components/Reader";
import { docsOf } from "./Case";
import type { words } from "../words";

export function DocWindow({ id, name, config, w }: { id: string; name: string; config: ConfigView; w: ReturnType<typeof words> }) {
  const q = useQuery({ queryKey: ["case", id], queryFn: () => api.case(id), retry: false, refetchInterval: 25_000 });
  if (q.isLoading) return <main className="main doc-window"><p className="empty">…</p></main>;
  if (!q.data) return <main className="main doc-window"><p className="empty">{q.error instanceof ApiError && q.error.status === 404 ? w.notHere : w.unreachable}</p></main>;
  const docs = docsOf(q.data);
  const index = Math.max(0, docs.findIndex((d) => d.versions.some((v) => v.name === name)));
  const setIndex = (i: number) => {
    window.history.replaceState(null, "", `${BASE}/doc/${encodeURIComponent(id)}/${encodeURIComponent(docs[i].versions[docs[i].versions.length - 1].name)}`);
    window.dispatchEvent(new PopStateEvent("popstate"));
  };
  document.title = `${docs[index]?.word ?? name} · ${q.data.title} · ${config.product}`;
  return (
    <main className="main doc-window">
      <p className="ref mono hint">{q.data.label_word} · {q.data.external_id ?? q.data.id} · {q.data.title}</p>
      <Reader docs={docs} index={index} caseId={id} onIndex={setIndex} onClose={() => window.close()} standalone startAt={name} w={w} />
    </main>
  );
}
