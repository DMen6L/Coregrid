import { readonly, ref } from "vue";

export const DEFAULT_BASE_API = normalizeBaseApi(
  import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000",
);
export const CUSTOM_API_BASE_OPTION = "custom";
export const API_BASE_OPTIONS = [
  { value: DEFAULT_BASE_API, label: new URL(DEFAULT_BASE_API).host },
  { value: "http://127.0.0.1:8001", label: "127.0.0.1:8001" },
] as const;

const API_BASE_STORAGE_KEY = "coregrid.vue.apiBase";
const API_BASE_QUERY_PARAMS = ["api_base", "api"];

const currentBaseApi = ref(resolveInitialBaseApi());

export function useApiBase() {
  return {
    apiBase: readonly(currentBaseApi),
    setBaseApi,
    getApiBaseSelection,
  };
}

export function getBaseApi() {
  return currentBaseApi.value;
}

export function setBaseApi(value: string) {
  currentBaseApi.value = normalizeBaseApi(value);
  writeStoredBaseApi(currentBaseApi.value);
  return currentBaseApi.value;
}

export function getApiBaseSelection(value = currentBaseApi.value) {
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

    if (!rawValue) {
      continue;
    }

    try {
      return normalizeBaseApi(rawValue);
    } catch {
      return "";
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

function writeStoredBaseApi(value: string) {
  try {
    window.localStorage.setItem(API_BASE_STORAGE_KEY, value);
  } catch {
    // localStorage may be blocked; the in-memory value still works for this page.
  }
}

function normalizeBaseApi(value: string) {
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
