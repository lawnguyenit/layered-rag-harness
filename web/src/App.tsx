import { useEffect, useMemo, useRef, useState } from "react";
import type { User } from "oidc-client-ts";
import { completeLoginIfNeeded, createUserManager } from "./auth";
import { describeToken, HostClient, type Hit, type Kind, type LookupResult, type SearchResult } from "./api";

const KIND_LABEL: Record<Kind, string> = { order: "Đơn hàng", ticket: "Phiếu hỗ trợ", invoice: "Hóa đơn" };
const KIND_HINT: Record<Kind, string> = { order: "BM-1001", ticket: "T01", invoice: "INV-2026-0451" };
const ROLE_LABEL: Record<string, string> = {
  visitor: "khách vãng lai", customer: "khách hàng", support: "hỗ trợ", finance: "tài chính", manager: "quản lý",
};

export function App() {
  const mgr = useMemo(() => createUserManager(), []);
  const [user, setUser] = useState<User | null>(null);
  const [ready, setReady] = useState(false);
  const [authError, setAuthError] = useState<string | null>(null);
  const tokenRef = useRef<string | undefined>(undefined);
  tokenRef.current = user?.access_token;
  const host = useMemo(() => new HostClient(import.meta.env.VITE_HOST_URL, () => tokenRef.current), []);
  const [tab, setTab] = useState<"lookup" | "search">("lookup");

  useEffect(() => {
    let alive = true;
    completeLoginIfNeeded(mgr)
      .then((u) => alive && setUser(u))
      .catch((e: Error) => alive && setAuthError(e.message))
      .finally(() => alive && setReady(true));
    return () => { alive = false; };
  }, [mgr]);

  const who = describeToken(user?.access_token);
  const expire = () => { void mgr.removeUser(); setUser(null); setAuthError("Phiên đã hết hạn, hãy đăng nhập lại."); };

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

      {ready && user && (
        <>
          <nav role="tablist">
            <button role="tab" aria-selected={tab === "lookup"} onClick={() => setTab("lookup")}>Tra cứu theo mã</button>
            <button role="tab" aria-selected={tab === "search"} onClick={() => setTab("search")}>Tìm tài liệu</button>
          </nav>
          {tab === "lookup" ? <Lookup host={host} onExpire={expire} /> : <Search host={host} onExpire={expire} />}
          <section className="card pending">
            <h2>Hỏi đáp qua harness</h2>
            <p className="muted">Chưa nối. Phần này (câu hỏi → route plan → công cụ) thuộc giai đoạn harness; giao diện sẽ gọi nó khi harness có bước thực thi.</p>
          </section>
        </>
      )}
    </main>
  );
}

function TraceId({ id }: { id: string | null }) {
  return id ? <p className="muted trace">Mã vết: <code data-testid="request-id">{id}</code></p> : null;
}

function Lookup({ host, onExpire }: { host: HostClient; onExpire: () => void }) {
  const [kind, setKind] = useState<Kind>("order");
  const [ref, setRef] = useState("");
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<LookupResult | null>(null);

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
      <h2>Tra cứu theo mã</h2>
      <form onSubmit={submit}>
        <label>Loại
          <select value={kind} onChange={(e) => { setKind(e.target.value as Kind); setResult(null); }}>
            {(Object.keys(KIND_LABEL) as Kind[]).map((k) => <option key={k} value={k}>{KIND_LABEL[k]}</option>)}
          </select>
        </label>
        <label>Mã
          <input value={ref} onChange={(e) => setRef(e.target.value)} placeholder={`ví dụ ${KIND_HINT[kind]}`} autoComplete="off" />
        </label>
        <button disabled={busy || !ref.trim()}>{busy ? "Đang tra…" : "Tra cứu"}</button>
      </form>
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
