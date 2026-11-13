import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { User } from "oidc-client-ts";
import { completeLoginIfNeeded, createUserManager } from "./auth";
import { describeToken, HostClient, type Hit, type Kind, type ListResult, type LookupResult, type SearchResult, type Summary } from "./api";

const KINDS: Kind[] = ["order", "ticket", "invoice"];
const KIND_LABEL: Record<Kind, string> = { order: "Đơn hàng", ticket: "Phiếu hỗ trợ", invoice: "Hóa đơn" };
const KIND_HINT: Record<Kind, string> = { order: "BM-1001", ticket: "T01", invoice: "INV-2026-0451" };
const ROLE_LABEL: Record<string, string> = {
  visitor: "khách vãng lai", customer: "khách hàng", support: "hỗ trợ", finance: "tài chính", manager: "quản lý",
};

type Mode = "detail" | "lookup" | "search";
type Lists = Partial<Record<Kind, ListResult>>;
interface Selection { kind: Kind; ref: string }

export function App() {
  const mgr = useMemo(() => createUserManager(), []);
  const [user, setUser] = useState<User | null>(null);
  const [ready, setReady] = useState(false);
  const [authError, setAuthError] = useState<string | null>(null);
  const tokenRef = useRef<string | undefined>(undefined);
  tokenRef.current = user?.access_token;
  const host = useMemo(() => new HostClient(import.meta.env.VITE_HOST_URL, () => tokenRef.current), []);

  useEffect(() => {
    let alive = true;
    completeLoginIfNeeded(mgr)
      .then((u) => alive && setUser(u))
      .catch((e: Error) => alive && setAuthError(e.message))
      .finally(() => alive && setReady(true));
    return () => { alive = false; };
  }, [mgr]);

  const who = describeToken(user?.access_token);
  const expire = useCallback(() => { void mgr.removeUser(); setUser(null); setAuthError("Phiên đã hết hạn, hãy đăng nhập lại."); }, [mgr]);

  return (
    <main>
      <header>
        <h1>Bếp Mây <span>hệ thống chủ (dữ liệu tổng hợp)</span></h1>
        {user && who && (
          <div className="who" data-testid="identity">
            <b>{ROLE_LABEL[who.role] ?? who.role}</b>{who.customerId ? ` · ${who.customerId}` : ""}
            <button className="link" onClick={() => void mgr.signoutRedirect()}>Đăng xuất</button>
          </div>
        )}
      </header>

      {!ready && <p className="muted">Đang tải…</p>}
      {ready && !user && (
        <section className="card">
          <h2>Đăng nhập</h2>
          <p>Mọi quyết định xem hay không xem một bản ghi do máy chủ quyết định theo vai trò trong token của bạn. Giao diện này không lọc gì.</p>
          {import.meta.env.VITE_LOGIN_HINT && <p className="notice" data-testid="login-hint">{import.meta.env.VITE_LOGIN_HINT}</p>}
          {authError && <p role="alert" className="error">{authError}</p>}
          <button onClick={() => void mgr.signinRedirect()}>Đăng nhập bằng Keycloak</button>
        </section>
      )}
      {ready && user && <Workspace host={host} onExpire={expire} />}
    </main>
  );
}

/** Two panes: what this user may see (left, from the server) and what to do with it (right). */
function Workspace({ host, onExpire }: { host: HostClient; onExpire: () => void }) {
  const [lists, setLists] = useState<Lists>({});
  const [listKind, setListKind] = useState<Kind>("order");
  const [selected, setSelected] = useState<Selection | null>(null);
  const [mode, setMode] = useState<Mode>("detail");
  const [lookupSeed, setLookupSeed] = useState<{ kind: Kind; ref: string } | null>(null);

  useEffect(() => {
    let alive = true;
    void Promise.all(KINDS.map((k) => host.list(k))).then((results) => {
      if (!alive) return;
      if (results.some((r) => r.status === "unauthorized")) return onExpire();
      setLists(Object.fromEntries(KINDS.map((k, i) => [k, results[i]])) as Lists);
      // Open on something real: the first record the server lists, so the screen is never empty after sign-in.
      const first = KINDS.map((k, i) => ({ k, r: results[i] })).find(({ r }) => r.status === "ok" && r.items.length > 0);
      if (first && first.r.status === "ok") {
        const kind = first.k;
        const ref = first.r.items[0].ref_id;
        setListKind(kind);
        setSelected((cur) => cur ?? { kind, ref });
      }
    });
    return () => { alive = false; };
  }, [host, onExpire]);

  const pick = (kind: Kind, ref: string) => { setSelected({ kind, ref }); setMode("detail"); };

  return (
    <div className="workspace">
      <aside className="card list-pane" aria-label="Dữ liệu của bạn">
        <h2>Dữ liệu của bạn</h2>
        <p className="muted small">Danh sách do máy chủ trả về theo quyền của bạn. Bấm một mục để xem chi tiết.</p>
        <div role="tablist" aria-label="Loại bản ghi" className="kind-tabs">
          {KINDS.map((k) => {
            const r = lists[k];
            return (
              <button key={k} role="tab" aria-selected={listKind === k} onClick={() => setListKind(k)}>
                {KIND_LABEL[k]} <span className="count" data-testid={`count-${k}`}>{r?.status === "ok" ? r.items.length : "…"}</span>
              </button>
            );
          })}
        </div>
        <ItemList kind={listKind} result={lists[listKind]} selected={selected} onPick={pick} />
      </aside>

      <section className="main-pane" aria-label="Chi tiết và công cụ">
        <nav role="tablist" aria-label="Chế độ xem" className="mode-tabs">
          <button role="tab" aria-selected={mode === "detail"} onClick={() => setMode("detail")}>Chi tiết</button>
          <button role="tab" aria-selected={mode === "lookup"} onClick={() => setMode("lookup")}>Tra theo mã</button>
          <button role="tab" aria-selected={mode === "search"} onClick={() => setMode("search")}>Tìm tài liệu</button>
        </nav>
        {mode === "detail" && <Detail host={host} selected={selected} onExpire={onExpire} onLookup={() => setMode("lookup")} />}
        {mode === "lookup" && (
          <Lookup host={host} lists={lists} seed={lookupSeed} onSeedUsed={() => setLookupSeed(null)} onExpire={onExpire}
                  onUseRef={(kind, ref) => setLookupSeed({ kind, ref })} />
        )}
        {mode === "search" && <Search host={host} onExpire={onExpire} />}
        <section className="card pending">
          <h2>Hỏi đáp qua harness</h2>
          <p className="muted">Chưa nối. Phần này (câu hỏi → route plan → công cụ) thuộc giai đoạn harness; khi có, người dùng chỉ cần hỏi bằng lời và harness sẽ tra theo mã hoặc tìm tài liệu thay họ.</p>
        </section>
      </section>
    </div>
  );
}

function ItemList({ kind, result, selected, onPick }: {
  kind: Kind; result: ListResult | undefined; selected: Selection | null; onPick: (k: Kind, ref: string) => void;
}) {
  if (!result) return <p className="muted">Đang tải…</p>;
  if (result.status === "unavailable") return <p className="error" role="alert">Không tải được danh sách. Thử lại sau.</p>;
  if (result.status === "unauthorized") return null;
  if (result.items.length === 0) {
    return <p className="notice" data-testid={`empty-${kind}`}>Vai trò của bạn không có {KIND_LABEL[kind].toLowerCase()} nào để xem.</p>;
  }
  return (
    <>
      <ul className="items" data-testid={`list-${kind}`}>
        {result.items.map((it: Summary) => (
          <li key={it.ref_id}>
            <button data-ref={it.ref_id} aria-current={selected?.kind === kind && selected.ref === it.ref_id ? "true" : undefined}
                    onClick={() => onPick(kind, it.ref_id)}>
              <code>{it.ref_id}</code>
              <span>{it.title}</span>
            </button>
          </li>
        ))}
      </ul>
      {result.truncated && <p className="muted small">Chỉ hiện các mục đầu tiên; còn nhiều hơn.</p>}
    </>
  );
}

function TraceId({ id }: { id: string | null }) {
  return id ? <p className="muted trace">Mã vết: <code data-testid="request-id">{id}</code></p> : null;
}

function Detail({ host, selected, onExpire, onLookup }: {
  host: HostClient; selected: Selection | null; onExpire: () => void; onLookup: () => void;
}) {
  const [result, setResult] = useState<LookupResult | null>(null);
  useEffect(() => {
    if (!selected) { setResult(null); return; }
    let alive = true;
    setResult(null);
    void host.lookup(selected.kind, selected.ref).then((r) => {
      if (!alive) return;
      if (r.status === "unauthorized") return onExpire();
      setResult(r);
    });
    return () => { alive = false; };
  }, [host, selected, onExpire]);

  if (!selected) {
    return (
      <section className="card">
        <h2>Chi tiết</h2>
        <p className="muted">Chọn một mục ở danh sách. Cần xem một mã không có trong danh sách? Dùng <button className="link" onClick={onLookup}>Tra theo mã</button> để xem máy chủ trả lời thế nào.</p>
      </section>
    );
  }
  return (
    <section className="card" data-testid="detail">
      <h2>{KIND_LABEL[selected.kind]} <code>{selected.ref}</code></h2>
      {!result && <p className="muted">Đang tải…</p>}
      {result?.status === "ok" && (
        <article className="record">
          <h3>{result.record.title}</h3>
          <pre>{result.record.body}</pre>
          <TraceId id={result.requestId} />
        </article>
      )}
      {result?.status === "not_found" && <div className="notice"><p>Không tìm thấy bản ghi này hoặc bạn không có quyền xem.</p><TraceId id={result.requestId} /></div>}
      {result?.status === "unavailable" && <p className="error" role="alert">Hệ thống tạm thời không phản hồi. Thử lại sau.</p>}
    </section>
  );
}

function Lookup({ host, lists, seed, onSeedUsed, onExpire, onUseRef }: {
  host: HostClient; lists: Lists; seed: { kind: Kind; ref: string } | null; onSeedUsed: () => void;
  onExpire: () => void; onUseRef: (kind: Kind, ref: string) => void;
}) {
  const [kind, setKind] = useState<Kind>(seed?.kind ?? "order");
  const [ref, setRef] = useState(seed?.ref ?? "");
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<LookupResult | null>(null);

  useEffect(() => { if (seed) { setKind(seed.kind); setRef(seed.ref); onSeedUsed(); } }, [seed, onSeedUsed]);

  const mine = lists[kind]?.status === "ok" ? (lists[kind] as Extract<ListResult, { status: "ok" }>).items : [];

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    const r = await host.lookup(kind, ref);
    setBusy(false);
    if (r.status === "unauthorized") return onExpire();
    setResult(r);
  }

  return (
    <section className="card">
      <h2>Tra theo mã <span className="badge">thử quyền</span></h2>
      <p className="muted small">Dùng để thử một mã bất kỳ, kể cả mã của người khác hoặc mã không có thật: máy chủ trả lời hai trường hợp đó giống hệt nhau.</p>
      <form onSubmit={submit}>
        <label>Loại
          <select value={kind} onChange={(e) => { setKind(e.target.value as Kind); setResult(null); }}>
            {KINDS.map((k) => <option key={k} value={k}>{KIND_LABEL[k]}</option>)}
          </select>
        </label>
        <label>Mã
          <input value={ref} onChange={(e) => setRef(e.target.value)} placeholder={`ví dụ ${KIND_HINT[kind]}`} autoComplete="off" />
        </label>
        <button disabled={busy || !ref.trim()}>{busy ? "Đang tra…" : "Tra cứu"}</button>
      </form>
      <div className="chips" data-testid="ref-hints">
        <span className="muted small">Mã của bạn ({KIND_LABEL[kind].toLowerCase()}):</span>
        {mine.length === 0 && <span className="muted small">không có</span>}
        {mine.map((it) => <button key={it.ref_id} type="button" className="chip" onClick={() => onUseRef(kind, it.ref_id)}>{it.ref_id}</button>)}
      </div>
      <div aria-live="polite" data-testid="lookup-result">
        {result?.status === "ok" && (
          <article className="record">
            <h3>{result.record.title}</h3>
            <pre>{result.record.body}</pre>
            <TraceId id={result.requestId} />
          </article>
        )}
        {result?.status === "not_found" && (
          <div className="notice">
            <p>Không tìm thấy bản ghi này hoặc bạn không có quyền xem.</p>
            <TraceId id={result.requestId} />
          </div>
        )}
        {result?.status === "unavailable" && <p className="error" role="alert">Hệ thống tạm thời không phản hồi. Thử lại sau.</p>}
      </div>
    </section>
  );
}

function Search({ host, onExpire }: { host: HostClient; onExpire: () => void }) {
  const [q, setQ] = useState("");
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<SearchResult | null>(null);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    const r = await host.search(q.trim(), 5);
    setBusy(false);
    if (r.status === "unauthorized") return onExpire();
    setResult(r);
  }

  return (
    <section className="card">
      <h2>Tìm tài liệu</h2>
      <form onSubmit={submit}>
        <label className="grow">Câu hỏi
          <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="ví dụ: giao hàng khi nào" maxLength={1000} />
        </label>
        <button disabled={busy || !q.trim()}>{busy ? "Đang tìm…" : "Tìm"}</button>
      </form>
      <div aria-live="polite" data-testid="search-result">
        {result?.status === "ok" && (
          <>
            {result.hits.length === 0 && <div className="notice"><p>Không có đoạn nào bạn được phép xem khớp với câu hỏi.</p></div>}
            <ol className="hits">{result.hits.map((h: Hit) => (
              <li key={h.chunk_id} data-doc={h.doc_id}>
                <header><h3>{h.title}</h3><span className="badge">{h.kind}</span><span className="score">{h.score.toFixed(3)}</span></header>
                <p>{h.text}</p>
              </li>
            ))}</ol>
            <TraceId id={result.requestId} />
          </>
        )}
        {result?.status === "unavailable" && <p className="error" role="alert">Tìm kiếm tạm thời không khả dụng. Thử lại sau.</p>}
      </div>
    </section>
  );
}
