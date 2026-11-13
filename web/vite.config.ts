import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

export default defineConfig({
  plugins: [react()],
  // Unit tests only; the Playwright specs in e2e/ need running services and are run with `npm run e2e`.
  test: { include: ["src/**/*.test.ts"] },
});
