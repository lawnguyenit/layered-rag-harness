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
  await page.getByLabel("Loại").selectOption(kind);
  await page.getByLabel("Mã").fill(ref);
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
  await expect(page.getByLabel("Mã")).toHaveCount(0);
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
