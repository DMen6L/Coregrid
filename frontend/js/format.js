export const DEFAULT_QUANTITY_UNIT = "шт";

export function formatCount(value) {
  return Number(value || 0).toLocaleString("ru-KZ");
}

export function formatCurrency(value) {
  return `${formatCount(value)} тг`;
}

export function formatQuantity(quantity, unit = DEFAULT_QUANTITY_UNIT) {
  return `${formatCount(quantity)} ${unit || DEFAULT_QUANTITY_UNIT}`;
}

export function formatDateTime(value) {
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

export function getRequestErrorMessage(error, label) {
  if (error?.status) {
    return `Не удалось загрузить ${label}. API вернул статус ${error.status}.`;
  }

  return `Не удалось загрузить ${label}. Проверьте, что API запущен.`;
}

export function getCreateErrorMessage(error, label) {
  const detail = error?.data?.detail;

  if (Array.isArray(detail)) {
    return detail
      .map((item) => {
        const field = Array.isArray(item.loc) ? item.loc.slice(1).join(".") : "";
        return field ? `${field}: ${item.msg}` : item.msg;
      })
      .filter(Boolean)
      .join(" ");
  }

  if (typeof detail === "string") {
    return detail;
  }

  if (typeof detail?.message === "string") {
    return detail.message;
  }

  if (error?.status) {
    return `Не удалось создать ${label}. API вернул статус ${error.status}.`;
  }

  return `Не удалось создать ${label}. Проверьте, что API запущен.`;
}
