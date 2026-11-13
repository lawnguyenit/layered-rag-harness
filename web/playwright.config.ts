import { defineConfig } from "@playwright/test";

// Runs against services you start yourself (see web/README.md): Keycloak dev realm, host API, `npm run dev`.
// Uses the installed Chrome (`channel: "chrome"`), so no browser download is needed.
export default defineConfig({
  testDir: "e2e",
  timeout: 60_000,
  retries: 0,
  workers: 1,
  reporter: [["list"]],
  outputDir: "e2e-results",
  use: { baseURL: "http://localhost:5173", channel: "chrome", headless: true, screenshot: "only-on-failure", trace: "off" },
});
