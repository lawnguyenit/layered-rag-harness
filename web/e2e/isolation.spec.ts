import { expect, test, type Page } from "@playwright/test";
import { readFileSync } from "node:fs";

const PASSWORD = process.env.DEV_USER_PASSWORD ?? "";
const TRACE_FILE = process.env.HOST_TRACE_FILE ?? "";
const NOT_FOUND = "Không tìm thấy bản ghi này hoặc bạn không có quyền xem.";
// The staffing plan is an English document and the dev embedder matches words, so the query shares its vocabulary:
// the manager case is the positive control that makes the "not visible to others" cases meaningful.
const STAFFING_QUERY = "staffing plan hire support agents extend hours";

test.skip(!PASSWORD, "DEV_USER_PASSWORD is required (the shared password of the synthetic dev users)");

async function login(page: Page, user: string) {
  await page.goto("/");
  await page.getByRole("button", { name: /Đăng nhập bằng Keycloak/ }).click();
  await page.locator("#username").fill(user);
  await page.locator("#password").fill(PASSWORD);
  await page.locator("#kc-login").click();
  await expect(page.getByTestId("identity")).toBeVisible();
}

async function lookup(page: Page, kind: string, ref: string) {
  await page.getByRole("tab", { name: "Tra theo mã" }).click();
  await page.getByRole("combobox").selectOption(kind);
  await page.getByLabel("Mã", { exact: true }).fill(ref);
  await page.getByRole("button", { name: "Tra cứu" }).click();
  const box = page.getByTestId("lookup-result");
  await expect(box.locator("article, .notice, .error")).toBeVisible();
  return box;
}

async function search(page: Page, query: string) {
  await page.getByRole("tab", { name: "Tìm tài liệu" }).click();
  await page.getByLabel("Câu hỏi").fill(query);
  await page.getByRole("button", { name: "Tìm", exact: true }).click();
  const box = page.getByTestId("search-result");
  await expect(box.locator(".hits, .notice")).toBeVisible();
  return box;
}

test("signed-out visitors see only the login prompt", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("button", { name: /Đăng nhập bằng Keycloak/ })).toBeVisible();
  await expect(page.getByRole("tab", { name: "Tra theo mã" })).toHaveCount(0);
});

test("the demo sign-in card says which accounts to use (demo build only)", async ({ page }) => {
  test.skip(!process.env.EXPECT_LOGIN_HINT, "set EXPECT_LOGIN_HINT=1 when testing a build made with VITE_LOGIN_HINT");
  await page.goto("/");
  const hint = page.getByTestId("login-hint");
  await expect(hint).toContainText("alice");
  await expect(hint).toContainText("admin");
});

test("login uses authorization code + PKCE S256 and keeps tokens out of localStorage", async ({ page }) => {
  const authRequests: string[] = [];
  page.on("request", (r) => { if (r.url().includes("/protocol/openid-connect/auth")) authRequests.push(r.url()); });
  await login(page, "alice");
  const u = new URL(authRequests[0]);
  expect(u.searchParams.get("response_type")).toBe("code");
  expect(u.searchParams.get("code_challenge_method")).toBe("S256");
  expect(u.searchParams.get("code_challenge")).toMatch(/^[A-Za-z0-9_-]{43}$/);
  expect(u.searchParams.has("client_secret")).toBe(false);
  const { local, session } = await page.evaluate(() => ({
    local: Object.keys(localStorage).filter((k) => k.includes("oidc")),
    session: Object.keys(sessionStorage).filter((k) => k.startsWith("oidc.user")),
  }));
  expect(local).toEqual([]);
  expect(session.length).toBe(1);
});

test("customer A reads own records; another customer's record looks exactly like a missing one", async ({ page }) => {
  await login(page, "alice");
  await expect(page.getByTestId("identity")).toContainText("khách hàng · c001");
  await expect(await lookup(page, "order", "BM-1001")).toContainText("BM-1001");
  const denied = await lookup(page, "order", "BM-1002"); // exists, belongs to c002
  await expect(denied).toContainText(NOT_FOUND);
  await expect(denied.locator("article")).toHaveCount(0);
  const deniedText = await denied.innerText();
  const missing = await lookup(page, "order", "BM-9999"); // does not exist
  expect((await missing.innerText()).replace(/Mã vết:.*/s, "")).toBe(deniedText.replace(/Mã vết:.*/s, ""));
  await expect(await lookup(page, "ticket", "T02")).toContainText(NOT_FOUND);
});

test("customer B sees the mirror image", async ({ page }) => {
  await login(page, "bob");
  await expect(page.getByTestId("identity")).toContainText("c002");
  await expect(await lookup(page, "order", "BM-1001")).toContainText(NOT_FOUND);
  await expect(await lookup(page, "order", "BM-1002")).toContainText("BM-1002");
});

test("search never returns another customer's document or an internal one", async ({ page }) => {
  await login(page, "alice");
  const mine = await search(page, "hóa đơn INV-2026-0451 tổng tiền thanh toán");
  await expect(mine.locator('[data-doc="invoice-c001-inv01"]')).toHaveCount(1);
  await expect(mine.locator('[data-doc="invoice-c002-inv02"]')).toHaveCount(0);
  const staffing = await search(page, STAFFING_QUERY);
  await expect(staffing.locator('[data-doc="mgmt-staffing-plan"]')).toHaveCount(0);
});

test("a manager sees the internal document that support does not", async ({ browser }) => {
  const mia = await (await browser.newContext()).newPage();
  await login(mia, "mia");
  await expect((await search(mia, STAFFING_QUERY)).locator('[data-doc="mgmt-staffing-plan"]')).toHaveCount(1);
  const sam = await (await browser.newContext()).newPage();
  await login(sam, "sam");
  await expect((await search(sam, STAFFING_QUERY)).locator('[data-doc="mgmt-staffing-plan"]')).toHaveCount(0);
});

test("the trace id shown to the user matches a host trace line without the query or token", async ({ page }) => {
  test.skip(!TRACE_FILE, "HOST_TRACE_FILE not set");
  await login(page, "alice");
  const secret = "một truy vấn riêng tư để kiểm tra nhật ký";
  const box = await search(page, secret);
  const id = (await box.getByTestId("request-id").innerText()).trim();
  const lines = readFileSync(TRACE_FILE, "utf-8").trim().split("\n").map((l) => JSON.parse(l));
  const line = lines.find((l) => l.request_id === id);
  expect(line).toBeTruthy();
  expect([line.route, line.outcome, line.actor_role, line.kind]).toEqual(["/v1/search", "ok", "customer", "search"]);
  expect(JSON.stringify(line)).not.toContain("riêng tư");
  expect(readFileSync(TRACE_FILE, "utf-8")).not.toContain("eyJ"); // no JWT anywhere in the trace file
});


async function listed(page: Page, kind: "order" | "ticket" | "invoice") {
  await page.getByRole("tab", { name: new RegExp({ order: "Đơn hàng", ticket: "Phiếu hỗ trợ", invoice: "Hóa đơn" }[kind]) }).click();
  const empty = page.getByTestId(`empty-${kind}`);
  const list = page.getByTestId(`list-${kind}`);
  await expect(empty.or(list)).toBeVisible();
  return (await list.locator("button[data-ref]").evaluateAll((els) => els.map((e) => (e as HTMLElement).dataset.ref!)));
}

test("the list shows a customer exactly their own records, and the other customer sees the mirror", async ({ browser }) => {
  const alice = await (await browser.newContext()).newPage();
  await login(alice, "alice");
  expect(await listed(alice, "order")).toEqual(["BM-1001"]);
  expect(await listed(alice, "ticket")).toEqual(["T01"]);
  expect(await listed(alice, "invoice")).toEqual(["INV-2026-0451"]);
  await expect(alice.getByTestId("count-order")).toHaveText("1");
  const bob = await (await browser.newContext()).newPage();
  await login(bob, "bob");
  expect(await listed(bob, "order")).toEqual(["BM-1002"]);
  expect(await listed(bob, "order")).not.toContain("BM-1001");
});

test("clicking a listed item opens its details, and every listed item can be opened", async ({ page }) => {
  await login(page, "alice");
  for (const kind of ["order", "ticket", "invoice"] as const) {
    for (const ref of await listed(page, kind)) {
      await page.getByTestId(`list-${kind}`).locator(`button[data-ref="${ref}"]`).click();
      await expect(page.getByTestId("detail")).toContainText(ref);
      await expect(page.getByTestId("detail").locator("article")).toBeVisible();
    }
  }
});

test("internal roles see what the matrix allows: support has no invoices, finance no tickets, manager everything", async ({ browser }) => {
  const sam = await (await browser.newContext()).newPage();
  await login(sam, "sam");
  expect((await listed(sam, "order")).length).toBe(3);
  expect((await listed(sam, "ticket")).length).toBe(3);
  expect(await listed(sam, "invoice")).toEqual([]);
  await expect(sam.getByTestId("empty-invoice")).toBeVisible();
  const fin = await (await browser.newContext()).newPage();
  await login(fin, "fin");
  expect((await listed(fin, "invoice")).length).toBe(2);
  expect(await listed(fin, "ticket")).toEqual([]);
  const mia = await (await browser.newContext()).newPage();
  await login(mia, "mia");
  expect([(await listed(mia, "order")).length, (await listed(mia, "ticket")).length, (await listed(mia, "invoice")).length]).toEqual([3, 3, 2]);
});

test("the lookup tab offers the user's own codes as one-click references", async ({ page }) => {
  await login(page, "alice");
  await page.getByRole("tab", { name: "Tra theo mã" }).click();
  const hints = page.getByTestId("ref-hints");
  await expect(hints).toContainText("BM-1001");
  await expect(hints).not.toContainText("BM-1002");
  await hints.getByRole("button", { name: "BM-1001" }).click();
  await expect(page.getByLabel("Mã", { exact: true })).toHaveValue("BM-1001");
  await page.getByRole("button", { name: "Tra cứu" }).click();
  await expect(page.getByTestId("lookup-result")).toContainText("BM-1001");
});
