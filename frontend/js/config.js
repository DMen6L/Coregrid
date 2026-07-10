const DEFAULT_API_BASE = "http://127.0.0.1:8000";
const API_BASE_STORAGE_KEY = "coregrid.apiBase";
const DEFAULT_LOW_STOCK_THRESHOLD = 5;
const DEFAULT_PRODUCT_PAGE_SIZE = 25;
const DEFAULT_LOOKUP_PAGE_SIZE = 10;
const DEFAULT_MOVEMENT_PAGE_SIZE = 25;
const DEFAULT_DASHBOARD_MOVEMENT_PAGE_SIZE = 5;
const DEFAULT_MOVEMENT_PRODUCT_SEARCH_PAGE_SIZE = 10;
const DEFAULT_QUANTITY_UNIT = "шт";
const MOVEMENT_PRODUCT_SEARCH_DELAY_MS = 300;
const DEFAULT_TAG_SEARCH_PAGE_SIZE = 10;
const TAG_SEARCH_DELAY_MS = 250;
const PRODUCT_ROW_TAG_LIMIT = 6;
const DEFAULT_PRODUCT_SORT = "created_at";
const DEFAULT_PRODUCT_SORT_ORDER = "asc";

const PRODUCT_SORT_LABELS = {
  name: "Название",
  quantity: "Количество",
  stock_status: "Статус",
  inventory_value: "Стоимость остатков",
  company: "Компания",
  supplier: "Поставщик",
  created_at: "Дата создания",
};

const PRODUCT_SORT_ORDER_LABELS = {
  asc: "По возрастанию",
  desc: "По убыванию",
};

const STOCK_STATUS_LABELS = {
  available: "В наличии",
  low: "Мало",
  out: "Нет на складе",
};

const MOVEMENT_TYPE_LABELS = {
  in: "Приход",
  out: "Списание",
  adjustment: "Корректировка",
};

const BACKEND_ERROR_MESSAGES = {
  "Duplicate value conflicts existing row": "Такое значение уже используется.",
  "Referenced row does not exist or was changed":
    "Связанная запись не существует или была изменена.",
  "Company not found": "Компания не найдена.",
  "Supplier not found": "Поставщик не найден.",
  "Product not found": "Товар не найден.",
  "Stock movement would make product quantity negative":
    "Движение не может сделать остаток товара отрицательным.",
  "Sale would make product quantity negative":
    "Продажа не может сделать остаток товара отрицательным.",
  "sale_price cannot be lower than floor_price":
    "Цена продажи не может быть ниже минимальной цены.",
  "date_from cannot be after date_to":
    "Дата начала не может быть позже даты окончания.",
};

const FIELD_LABELS = {
  name: "Название",
  iin: "ИИН",
  phone_number: "Телефон",
  purchase_price: "Цена закупки",
  margin_percent: "Маржа",
  sale_price: "Цена продажи",
  quantity: "Количество",
  quantity_unit: "Ед. изм.",
  low_stock_threshold: "Порог малого остатка",
  company_id: "Компания",
  supplier_id: "Поставщик",
  movement_type: "Тип движения",
  product_id: "Товар",
  quantity_delta: "Изменение",
  unit_price: "Цена",
  note: "Заметка",
};
