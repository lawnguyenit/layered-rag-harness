/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_OIDC_AUTHORITY: string;
  readonly VITE_OIDC_CLIENT_ID?: string;
  readonly VITE_HOST_URL: string;
  /** Optional text shown on the sign-in card (the demo uses it to say which accounts to use). */
  readonly VITE_LOGIN_HINT?: string;
}
interface ImportMeta {
  readonly env: ImportMetaEnv;
}
