import { UserManager, WebStorageStateStore, type User } from "oidc-client-ts";

/** Authorization Code + PKCE (S256, the library default for a public client). Tokens live in sessionStorage:
 *  they vanish with the tab, at the cost of being readable by any script on this origin; there is no refresh token. */
export function createUserManager(): UserManager {
  const origin = window.location.origin;
  return new UserManager({
    authority: import.meta.env.VITE_OIDC_AUTHORITY,
    client_id: import.meta.env.VITE_OIDC_CLIENT_ID ?? "bepmay-spa",
    redirect_uri: `${origin}/`,
    post_logout_redirect_uri: `${origin}/`,
    response_type: "code",
    scope: "openid",
    automaticSilentRenew: false,
    userStore: new WebStorageStateStore({ store: window.sessionStorage }),
  });
}

let pending: Promise<User | null> | null = null;

/** Completes the redirect if the URL carries an authorization response; returns the user (or null).
 *  An authorization code is single use, and React StrictMode runs effects twice in development, so the work
 *  is memoised per page load: a second call returns the first call's result instead of replaying the code. */
export function completeLoginIfNeeded(mgr: UserManager): Promise<User | null> {
  pending ??= (async () => {
    const q = new URLSearchParams(window.location.search);
    if (q.has("code") && q.has("state")) {
      const user = await mgr.signinCallback();
      window.history.replaceState({}, document.title, window.location.pathname);
      return user ?? null;
    }
    const user = await mgr.getUser();
    return user && !user.expired ? user : null;
  })();
  return pending;
}
