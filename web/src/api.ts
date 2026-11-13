/** Host API client. Every access decision is made by the server; nothing here filters or hides data. */

export type Kind = "order" | "ticket" | "invoice";
export const KIND_PATH: Record<Kind, string> = { order: "orders", ticket: "tickets", invoice: "invoices" };

export interface RecordView {
  kind: Kind;
  ref_id: string;
  title: string;
  body: string;
}
export interface Hit {
  chunk_id: string;
  doc_id: string;
  title: string;
  kind: string;
  text: string;
  score: number;
}

/** `not_found` covers both "does not exist" and "not allowed": the server answers them identically. */
export type LookupResult =
  | { status: "ok"; record: RecordView; requestId: string | null }
  | { status: "not_found"; requestId: string | null }
  | { status: "unauthorized" }
  | { status: "unavailable"; requestId: string | null };

export type SearchResult =
  | { status: "ok"; hits: Hit[]; requestId: string | null }
  | { status: "unauthorized" }
  | { status: "unavailable"; requestId: string | null };

export class HostClient {
  constructor(
    private baseUrl: string,
    private token: () => string | undefined,
    private fetcher: typeof fetch = (...a) => fetch(...a),
  ) {}

  private headers(extra: Record<string, string> = {}): Record<string, string> {
    const t = this.token();
    return { ...(t ? { Authorization: `Bearer ${t}` } : {}), ...extra };
  }

  async lookup(kind: Kind, refId: string): Promise<LookupResult> {
    let r: Response;
    try {
      r = await this.fetcher(`${this.baseUrl}/v1/${KIND_PATH[kind]}/${encodeURIComponent(refId.trim())}`, { headers: this.headers() });
    } catch {
      return { status: "unavailable", requestId: null };
    }
    const requestId = r.headers.get("x-request-id");
    if (r.status === 401) return { status: "unauthorized" };
    if (r.status === 404) return { status: "not_found", requestId };
    if (!r.ok) return { status: "unavailable", requestId };
    return { status: "ok", record: (await r.json()) as RecordView, requestId };
  }

  async search(query: string, topK = 5): Promise<SearchResult> {
    let r: Response;
    try {
      r = await this.fetcher(`${this.baseUrl}/v1/search`, {
        method: "POST",
        headers: this.headers({ "Content-Type": "application/json" }),
        body: JSON.stringify({ query, top_k: topK }),
      });
    } catch {
      return { status: "unavailable", requestId: null };
    }
    const requestId = r.headers.get("x-request-id");
    if (r.status === 401) return { status: "unauthorized" };
    if (!r.ok) return { status: "unavailable", requestId };
    return { status: "ok", hits: ((await r.json()) as { results: Hit[] }).results, requestId };
  }
}

/** Display only. The server verifies the token; this just shows the signed-in user who they are to the system. */
export function describeToken(jwt: string | undefined): { role: string; customerId: string | null } | null {
  if (!jwt) return null;
  try {
    const part = jwt.split(".")[1].replace(/-/g, "+").replace(/_/g, "/");
    const claims = JSON.parse(decodeURIComponent(escape(atob(part)))) as {
      realm_access?: { roles?: string[] };
      customer_id?: string;
    };
    const known = ["visitor", "customer", "support", "finance", "manager"];
    const role = (claims.realm_access?.roles ?? []).find((r) => known.includes(r));
    return role ? { role, customerId: claims.customer_id ?? null } : null;
  } catch {
    return null;
  }
}
