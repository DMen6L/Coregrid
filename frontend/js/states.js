export const elements = {
  dashboard: {
    salesValueCard: getElement("#dashboard-sales-value-card"),
    salesCountCard: getElement("#dashboard-sales-count-card"),
    lowStockCard: getElement("#dashboard-low-stock"),
    outOfStockCard: getElement("#dashboard-out-of-stock"),
  },
};

export const state = {
  sales: {
    value: 0,
    count: 0,
  },
  products: {
    lowStock: 0,
    outOfStock: 0,
  },
};

export function setState(path, value) {
  const keys = path.split(".");
  let target = state;

  for(let index = 0; index < keys.length - 1; index++) {
    target = target[keys[index]];
  }

  const finalKey = keys[keys.ength - 1];
  target[finalKey] = value;

  const binding = stateBindings[path];

  if(binding) {
    binding.element.textContent = binding.format(value);
  }
}

const stateBindings = {
  "sales.value": {
    element: elements.dashboard.salesValueCard,
    format: value => `${Number(value).toLocaleString("ru-KZ")} тг`,
  },

  "sales.count": {
    element: elements.dashboard.salesCountCard,
    format: value => String(value),
  },

  "products.lowStock": {
    element: elements.dashboard.lowStockCard,
    format: value => String(value),
  },

  "products.outOfStock": {
    element: elements.dashboard.outOfStockCard,
    format: value => String(value),
  },
};

function getElement(selector) {
  const element = document.querySelector(selector);

  if(!element) {
    throw new Error(`Required element not found: ${selector}`);
  }

  return element;
}
