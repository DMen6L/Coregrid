import { ApiRequestError } from "./api";

export const DEFAULT_QUANTITY_UNIT = "шт";

export function formatCount(value: number | null | undefined) {
  return Number(value || 0).toLocaleString("ru-KZ");
}

export function formatCurrency(value: number | null | undefined) {
  return `${formatCount(value)} тг`;
}

export function formatQuantity(quantity: number | null | undefined, unit = DEFAULT_QUANTITY_UNIT) {
  return `${formatCount(quantity)} ${unit || DEFAULT_QUANTITY_UNIT}`;
}

export function formatDateTime(value: string | null | undefined) {
  if (!value) {
    return "Не указано";
  }

  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return String(value);
  }

  return date.toLocaleString("ru-KZ", {
    dateStyle: "medium",
    timeStyle: "short",
  });
}

export function formatFullDate(value: string) {
  const date = new Date(`${value}T00:00:00`);

  return Number.isNaN(date.getTime())
    ? value
    : date.toLocaleDateString("ru-KZ", { dateStyle: "medium" });
}

export function formatShortDate(value: string) {
  const date = new Date(`${value}T00:00:00`);

  return Number.isNaN(date.getTime())
    ? ""
    : date.toLocaleDateString("ru-KZ", { day: "2-digit", month: "2-digit" });
}

export function getRequestErrorMessage(error: unknown, label: string) {
  if (error instanceof ApiRequestError) {
    return `Не удалось загрузить ${label}. API вернул статус ${error.status}.`;
  }

  return `Не удалось загрузить ${label}. Проверьте, что API запущен.`;
}

export function getCreateErrorMessage(error: unknown, label: string) {
  const detail = getErrorDetail(error);

  if (Array.isArray(detail)) {
    return detail
      .map((item) => {
        const location = Array.isArray(item?.loc) ? item.loc.slice(1).join(".") : "";
        const message = typeof item?.msg === "string" ? item.msg : "";

        return location && message ? `${location}: ${message}` : message;
      })
      .filter(Boolean)
      .join(" ");
  }

  if (typeof detail === "string") {
    return detail;
  }

  if (hasMessage(detail)) {
    return detail.message;
  }

  if (error instanceof ApiRequestError) {
    return `Не удалось создать ${label}. API вернул статус ${error.status}.`;
  }

  return `Не удалось создать ${label}. Проверьте, что API запущен.`;
}

export function getDeleteErrorMessage(error: unknown, label: string) {
  const detail = getErrorDetail(error);

  if (Array.isArray(detail)) {
    return detail
      .map((item) => {
        const location = Array.isArray(item?.loc) ? item.loc.slice(1).join(".") : "";
        const message = typeof item?.msg === "string" ? item.msg : "";

        return location && message ? `${location}: ${message}` : message;
      })
      .filter(Boolean)
      .join(" ");
  }

  if (typeof detail === "string") {
    return detail;
  }

  if (hasMessage(detail)) {
    return detail.message;
  }

  if (error instanceof ApiRequestError) {
    return `Не удалось удалить ${label}. API вернул статус ${error.status}.`;
  }

  return `Не удалось удалить ${label}. Проверьте, что API запущен.`;
}

function getErrorDetail(error: unknown) {
  if (error instanceof ApiRequestError) {
    return error.data && typeof error.data === "object"
      ? (error.data as { detail?: unknown }).detail
      : undefined;
  }

  if (error && typeof error === "object" && "data" in error) {
    const data = (error as { data?: unknown }).data;

    return data && typeof data === "object"
      ? (data as { detail?: unknown }).detail
      : undefined;
  }

  return undefined;
}

function hasMessage(value: unknown): value is { message: string } {
  return Boolean(
    value
      && typeof value === "object"
      && "message" in value
      && typeof (value as { message?: unknown }).message === "string",
  );
}
