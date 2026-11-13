import { describe, expect, it } from "vitest";
import { describeToken, HostClient } from "./api";

const jwt = (claims: object) => `h.${btoa(JSON.stringify(claims)).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "")}.s`;

function client(handler: (url: string, init?: RequestInit) => Response | Promise<Response>, token: string | undefined = "tok") {
  const calls: { url: string; init?: RequestInit }[] = [];
  const fetcher = (async (url: string, init?: RequestInit) => { calls.push({ url, init }); return handler(url, init); }) as unknown as typeof fetch;
  return { c: new HostClient("https://host.test", () => token, fetcher), calls };
}

describe("HostClient", () => {
  it("sends the bearer token and url-encodes the reference", async () => {
    const { c, calls } = client(() => new Response("{}", { status: 404 }));
    await c.lookup("order", " BM-1001/../x ");
    expect(calls[0].url).toBe("https://host.test/v1/orders/BM-1001%2F..%2Fx");
    expect((calls[0].init!.headers as Record<string, string>).Authorization).toBe("Bearer tok");
  });

  it("maps 404 to not_found without distinguishing denied from missing, and keeps the request id", async () => {
    const { c } = client(() => new Response("{}", { status: 404, headers: { "x-request-id": "abc12345" } }));
    expect(await c.lookup("invoice", "INV-2026-0451")).toEqual({ status: "not_found", requestId: "abc12345" });
  });

  it("maps 401 to unauthorized, 5xx and network errors to unavailable", async () => {
    expect((await client(() => new Response("", { status: 401 })).c.lookup("order", "BM-1001")).status).toBe("unauthorized");
    expect((await client(() => new Response("", { status: 503 })).c.search("x")).status).toBe("unavailable");
    expect((await client(() => { throw new TypeError("net"); }).c.lookup("ticket", "T01")).status).toBe("unavailable");
  });

  it("posts the query as JSON and returns hits", async () => {
    const { c, calls } = client(() => new Response(JSON.stringify({ results: [{ chunk_id: "a#0", doc_id: "a", title: "t", kind: "public", text: "x", score: 0.5 }] }), { status: 200 }));
    const r = await c.search("giao hàng", 3);
    expect(JSON.parse(calls[0].init!.body as string)).toEqual({ query: "giao hàng", top_k: 3 });
    expect(r.status === "ok" && r.hits[0].doc_id).toBe("a");
  });
});

describe("HostClient.list", () => {
  it("requests the list for the kind with the bearer token and returns what the server sent", async () => {
    const { c, calls } = client(() => new Response(JSON.stringify({ items: [{ kind: "order", ref_id: "BM-1001", title: "Đơn BM-1001" }], truncated: false }), { status: 200, headers: { "x-request-id": "rid-12345" } }));
    const r = await c.list("order");
    expect(calls[0].url).toBe("https://host.test/v1/orders");
    expect((calls[0].init!.headers as Record<string, string>).Authorization).toBe("Bearer tok");
    expect(r).toEqual({ status: "ok", items: [{ kind: "order", ref_id: "BM-1001", title: "Đơn BM-1001" }], truncated: false, requestId: "rid-12345" });
  });
  it("maps 401 to unauthorized and failures to unavailable", async () => {
    expect((await client(() => new Response("", { status: 401 })).c.list("invoice")).status).toBe("unauthorized");
    expect((await client(() => new Response("", { status: 500 })).c.list("ticket")).status).toBe("unavailable");
    expect((await client(() => { throw new TypeError("net"); }).c.list("order")).status).toBe("unavailable");
  });
});

describe("describeToken (display only)", () => {
  it("reads the single known role and customer id", () => {
    expect(describeToken(jwt({ realm_access: { roles: ["offline_access", "customer"] }, customer_id: "c001" }))).toEqual({ role: "customer", customerId: "c001" });
  });
  it("returns null for garbage or a token without a known role", () => {
    expect(describeToken("nope")).toBeNull();
    expect(describeToken(jwt({ realm_access: { roles: ["offline_access"] } }))).toBeNull();
    expect(describeToken(undefined)).toBeNull();
  });
});
