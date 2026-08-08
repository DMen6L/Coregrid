export const DEFAULT_BASE_API = normalizeBaseApi(
  import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000",
);

export function getBaseApi() {
  return DEFAULT_BASE_API;
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
