export const DEFAULT_BASE_API = "http://127.0.0.1:8000";
export const CUSTOM_API_BASE_OPTION = "custom";
export const API_BASE_OPTIONS = [
  { value: DEFAULT_BASE_API, label: "127.0.0.1:8000" },
  { value: "http://127.0.0.1:8001", label: "127.0.0.1:8001" },
];

const API_BASE_STORAGE_KEY = "coregrid.apiBase";
const API_BASE_QUERY_PARAMS = ["api_base", "api"];

let currentBaseApi = resolveInitialBaseApi();

export function getBaseApi() {
  return currentBaseApi;
}

export function setBaseApi(value) {
  currentBaseApi = normalizeBaseApi(value);
  writeStoredBaseApi(currentBaseApi);
  return currentBaseApi;
}

export function getApiBaseSelection(value = currentBaseApi) {
  return API_BASE_OPTIONS.some((option) => option.value === value)
    ? value
    : CUSTOM_API_BASE_OPTION;
}

function resolveInitialBaseApi() {
  const queryBaseApi = readQueryBaseApi();

  if (queryBaseApi) {
    writeStoredBaseApi(queryBaseApi);
    return queryBaseApi;
  }

  return readStoredBaseApi() || DEFAULT_BASE_API;
}

function readQueryBaseApi() {
  const params = new URLSearchParams(window.location.search);

  for (const paramName of API_BASE_QUERY_PARAMS) {
    const rawValue = params.get(paramName);

    if (rawValue) {
      try {
        return normalizeBaseApi(rawValue);
      } catch {
        return "";
      }
    }
  }

  return "";
}

function readStoredBaseApi() {
  try {
    const value = window.localStorage.getItem(API_BASE_STORAGE_KEY);

    return value ? normalizeBaseApi(value) : "";
  } catch {
    return "";
  }
}

function writeStoredBaseApi(value) {
  try {
    window.localStorage.setItem(API_BASE_STORAGE_KEY, value);
  } catch {
    // localStorage may be blocked; the in-memory value still works for this page.
  }
}

function normalizeBaseApi(value) {
  const rawValue = String(value || "").trim();

  if (!rawValue) {
    throw new Error("API base URL is required.");
  }

  const url = new URL(rawValue);

  if (url.protocol !== "http:" && url.protocol !== "https:") {
    throw new Error("API base URL must use http or https.");
  }

  url.hash = "";
  url.search = "";

  const pathname = url.pathname.replace(/\/+$/, "");

  return `${url.origin}${pathname}`;
}
