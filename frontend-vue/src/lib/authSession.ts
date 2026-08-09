import type { TokenResponse } from "../types/api";
import { clearWorkspaceSession } from "./workspaceSession";

const AUTH_TOKEN_STORAGE_KEY = "coregrid.authToken";
export const AUTH_SESSION_CHANGE_EVENT = "coregrid-auth-session-change";

export function getAuthToken() {
  return localStorage.getItem(AUTH_TOKEN_STORAGE_KEY);
}

export function saveAuthToken(token: TokenResponse) {
  localStorage.setItem(AUTH_TOKEN_STORAGE_KEY, token.access_token);
  window.dispatchEvent(new Event(AUTH_SESSION_CHANGE_EVENT));
}

export function clearAuthToken() {
  localStorage.removeItem(AUTH_TOKEN_STORAGE_KEY);
  clearWorkspaceSession();
  window.dispatchEvent(new Event(AUTH_SESSION_CHANGE_EVENT));
}
