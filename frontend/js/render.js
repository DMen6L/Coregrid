function render() {
  renderTabs();
  renderDashboard();
  renderProductTable();
  renderSelectedSearchTags();
  renderProductSortControls();
  renderProductFormTags();
  renderSelects();
  renderLookupTable("company");
  renderLookupTable("supplier");
  renderMovementTable();
  renderPagination("products");
  renderPagination("companies");
  renderPagination("suppliers");
  renderPagination("stockMovements");
}

function renderTabs() {
  refs.tabButtons.forEach((button) => {
    const isActive = button.dataset.tabTarget === state.activeTab;
    button.classList.toggle("active", isActive);
    button.setAttribute("aria-selected", String(isActive));
  });

  refs.tabPanels.forEach((panel) => {
    panel.classList.toggle("hidden", panel.dataset.tabPanel !== state.activeTab);
  });
}

function renderDashboard() {
  const summary = state.productSummary || createEmptyProductSummary();
  const salesSummary = state.salesSummary || createEmptySalesSummary(
    state.salesDateFrom,
    state.salesDateTo,
  );

  refs.dashboardTotalProducts.textContent = formatNumber(summary.total_products);
  refs.dashboardLowStock.textContent = formatNumber(summary.low_stock);
  refs.dashboardOutOfStock.textContent = formatNumber(summary.out_of_stock ?? 0);
  refs.dashboardSalesDateFrom.value = state.salesDateFrom;
  refs.dashboardSalesDateTo.value = state.salesDateTo;
  refs.dashboardSalesRevenue.textContent = formatNumber(salesSummary.revenue);
  refs.dashboardSalesUnits.textContent = formatSalesQuantitySummary(salesSummary);
  refs.dashboardSalesOperations.textContent = formatNumber(
    salesSummary.sale_operations,
  );
  renderSalesChart(salesSummary);
  renderBestSellers(salesSummary.best_sellers || []);
  renderDashboardMovements();
}

function renderBestSellers(bestSellers) {
  if (!bestSellers.length) {
    refs.dashboardBestSellers.innerHTML = `
      <div class="best-sellers-empty">За выбранный период продаж нет.</div>
    `;
    return;
  }

  const maxRevenue = Math.max(...bestSellers.map((item) => item.revenue), 1);

  refs.dashboardBestSellers.innerHTML = bestSellers
    .map((item, index) => {
      const barWidth = roundChartValue((item.revenue / maxRevenue) * 100);

      return `
        <div class="best-seller-row">
          <span class="best-seller-rank">${index + 1}</span>
          <div class="best-seller-main">
            <div class="best-seller-title-row">
              <strong class="best-seller-name">${escapeHtml(item.product_name)}</strong>
              <strong class="best-seller-revenue">${formatNumber(item.revenue)}</strong>
            </div>
            <div class="best-seller-bar" aria-hidden="true">
              <span style="width: ${barWidth}%"></span>
            </div>
            <div class="best-seller-stats">
              <span>Продано: ${escapeHtml(formatQuantityGroups(item.units_sold_by_unit))}</span>
              <span>Продаж: ${formatNumber(item.sale_operations)}</span>
              <span>Остаток: ${escapeHtml(formatQuantity(item.current_quantity, item.current_quantity_unit))}</span>
              ${renderStockStatus(item)}
            </div>
          </div>
        </div>
      `;
    })
    .join("");
}

function renderSalesChart(salesSummary) {
  const isRange = salesSummary.date_from && salesSummary.date_to
    && salesSummary.date_from !== salesSummary.date_to;

  if (!isRange) {
    refs.dashboardSalesChart.innerHTML = "";
    refs.dashboardSalesChart.classList.add("hidden");
    return;
  }

  const dailyTotals = normalizeDailySalesTotals(
    salesSummary.date_from,
    salesSummary.date_to,
    salesSummary.daily_totals || [],
  );

  refs.dashboardSalesChart.classList.remove("hidden");
  refs.dashboardSalesChart.innerHTML = `
    <div class="sales-chart-header">
      <h4 class="sales-chart-title">Динамика выручки</h4>
      <span class="sales-chart-total">${formatNumber(salesSummary.revenue)} за период</span>
    </div>
    ${renderSalesChartBody(dailyTotals)}
  `;
}

function renderSalesChartBody(dailyTotals) {
  const maxRevenue = Math.max(...dailyTotals.map((item) => item.revenue), 0);

  if (maxRevenue === 0) {
    return '<div class="sales-chart-empty">Продаж за период нет.</div>';
  }

  const width = 720;
  const height = 240;
  const padding = {
    top: 28,
    right: 24,
    bottom: 46,
    left: 56,
  };
  const plotWidth = width - padding.left - padding.right;
  const plotHeight = height - padding.top - padding.bottom;
  const lastIndex = Math.max(dailyTotals.length - 1, 1);
  const points = dailyTotals.map((item, index) => {
    const x = padding.left + (plotWidth * index) / lastIndex;
    const y = padding.top + plotHeight - (item.revenue / maxRevenue) * plotHeight;

    return { ...item, x, y };
  });
  const polylinePoints = points
    .map((point) => `${roundChartValue(point.x)},${roundChartValue(point.y)}`)
    .join(" ");
  const baselineY = padding.top + plotHeight;
  const valueLabelIndexes = getSalesChartValueLabelIndexes(points);
  const dateLabelIndexes = getSalesChartDateLabelIndexes(points);

  return `
    <svg class="sales-chart-svg" viewBox="0 0 ${width} ${height}" role="img" aria-label="Выручка по дням">
      <line class="sales-chart-axis" x1="${padding.left}" y1="${baselineY}" x2="${width - padding.right}" y2="${baselineY}"></line>
      <line class="sales-chart-axis" x1="${padding.left}" y1="${padding.top}" x2="${padding.left}" y2="${baselineY}"></line>
      <polyline class="sales-chart-line" points="${polylinePoints}"></polyline>
      ${points
        .map(
          (point) => `
            <circle class="sales-chart-point" cx="${roundChartValue(point.x)}" cy="${roundChartValue(point.y)}" r="4">
              <title>${escapeHtml(formatSalesChartTitle(point))}</title>
            </circle>
          `,
        )
        .join("")}
      ${points
        .filter((_, index) => valueLabelIndexes.has(index))
        .map(
          (point) => `
            <text class="sales-chart-value" x="${roundChartValue(point.x)}" y="${roundChartValue(Math.max(point.y - 10, 12))}" text-anchor="middle">${formatNumber(point.revenue)}</text>
          `,
        )
        .join("")}
      ${points
        .filter((_, index) => dateLabelIndexes.has(index))
        .map(
          (point) => `
            <text class="sales-chart-label" x="${roundChartValue(point.x)}" y="${height - 14}" text-anchor="middle">${escapeHtml(formatShortDate(point.date))}</text>
          `,
        )
        .join("")}
    </svg>
  `;
}

function normalizeDailySalesTotals(dateFrom, dateTo, dailyTotals) {
  const totalsByDate = new Map(
    dailyTotals.map((item) => [
      item.date,
      {
        date: item.date,
        revenue: Number(item.revenue) || 0,
        units_sold: Number(item.units_sold) || 0,
        units_sold_by_unit: item.units_sold_by_unit || [],
        sale_operations: Number(item.sale_operations) || 0,
      },
    ]),
  );
  const dates = getDateInputRange(dateFrom, dateTo);

  return dates.map((dateValue) => (
    totalsByDate.get(dateValue) || {
      date: dateValue,
      revenue: 0,
      units_sold: 0,
      units_sold_by_unit: [],
      sale_operations: 0,
    }
  ));
}

function getDateInputRange(dateFrom, dateTo) {
  const startDate = parseDateInput(dateFrom);
  const endDate = parseDateInput(dateTo);

  if (!startDate || !endDate || startDate > endDate) {
    return [];
  }

  const dates = [];
  const currentDate = new Date(startDate);
  while (currentDate <= endDate) {
    dates.push(formatDateInputValue(currentDate));
    currentDate.setDate(currentDate.getDate() + 1);
  }

  return dates;
}

function getSalesChartValueLabelIndexes(points) {
  const indexes = new Set([0, points.length - 1]);
  const maxRevenue = Math.max(...points.map((point) => point.revenue));
  const maxIndex = points.findIndex((point) => point.revenue === maxRevenue);

  if (maxIndex >= 0) {
    indexes.add(maxIndex);
  }

  return indexes;
}

function getSalesChartDateLabelIndexes(points) {
  if (points.length <= 7) {
    return new Set(points.map((_, index) => index));
  }

  const step = Math.ceil((points.length - 1) / 4);
  const indexes = new Set([0, points.length - 1]);
  for (let index = step; index < points.length - 1; index += step) {
    indexes.add(index);
  }

  return indexes;
}

function formatSalesChartTitle(point) {
  return `${formatShortDate(point.date)}: ${formatNumber(point.revenue)}`;
}

function renderDashboardMovements() {
  if (state.dashboardMovements.length === 0) {
    refs.dashboardMovementList.innerHTML = `
      <div class="empty-state">Движений пока нет.</div>
    `;
    return;
  }

  refs.dashboardMovementList.innerHTML = state.dashboardMovements
    .map(
      (movement) => `
        <article class="dashboard-movement">
          <div class="dashboard-movement-header">
            <span class="status-pill">${escapeHtml(MOVEMENT_TYPE_LABELS[movement.movement_type] || movement.movement_type)}</span>
            <span class="dashboard-movement-date">${formatDate(movement.created_at)}</span>
          </div>
          ${renderMovementLines(movement.lines)}
          ${movement.note ? `<div class="dashboard-movement-note">${escapeHtml(movement.note)}</div>` : ""}
        </article>
      `,
    )
    .join("");
}

function renderProductTable() {
  if (state.products.length === 0) {
    refs.productTableBody.innerHTML = `
      <tr>
        <td colspan="10">
          <div class="empty-state">Нет товаров для текущего фильтра.</div>
        </td>
      </tr>
    `;
    return;
  }

  refs.productTableBody.innerHTML = state.products
    .map((product) => {
      const companyName = product.company_name ?? getCompanyName(product.company_id);
      const supplierName =
        product.supplier_name ?? getSupplierName(product.supplier_id);
      const productHasTags = Boolean(product.tags?.length);

      return `
        <tr class="product-main-row${productHasTags ? " has-product-tags" : ""}">
          <td>
            <div class="product-name-cell">
              <strong class="product-name">${escapeHtml(product.name)}</strong>
            </div>
          </td>
          <td>${formatNumber(product.purchase_price)}</td>
          <td>${formatNumber(product.margin_percent)}%</td>
          <td>${formatNumber(product.sale_price)}</td>
          <td>${escapeHtml(formatQuantity(product.quantity, product.quantity_unit))}</td>
          <td>${renderStockStatus(product)}</td>
          <td>${escapeHtml(companyName)}</td>
          <td>${escapeHtml(supplierName)}</td>
          <td>${formatDate(product.created_at)}</td>
          <td>
            <div class="actions">
              <button class="secondary-button" type="button" data-action="edit" data-id="${product.id}">Изменить</button>
              <button class="danger-button" type="button" data-action="delete" data-id="${product.id}">Удалить</button>
            </div>
          </td>
        </tr>
        ${renderProductTagRow(product.tags)}
      `;
    })
    .join("");
}

function renderStockStatus(product) {
  const status = getStockStatus(product);
  const label = STOCK_STATUS_LABELS[status] || status;
  const className = status === "low" || status === "out" ? ` status-${status}` : "";

  return `<span class="status-pill${className}">${escapeHtml(label)}</span>`;
}

function renderProductTagRow(tags = []) {
  if (!tags.length) {
    return "";
  }

  return `
    <tr class="product-tags-row">
      <td class="product-tags-cell" colspan="10">
        ${renderProductTags(tags)}
      </td>
    </tr>
  `;
}

function renderProductTags(tags = []) {
  if (!tags.length) {
    return "";
  }

  const visibleTags = tags.slice(0, PRODUCT_ROW_TAG_LIMIT);
  const hiddenTagCount = Math.max(tags.length - visibleTags.length, 0);
  const allTagNames = tags.map((tag) => tag.name).join(", ");

  return `
    <div class="product-tag-list" title="${escapeHtml(allTagNames)}">
      ${visibleTags.map((tag) => renderTagChip(tag.name)).join("")}
      ${hiddenTagCount > 0 ? `<span class="tag-chip tag-chip-more">+${hiddenTagCount}</span>` : ""}
    </div>
  `;
}

function renderSelectedSearchTags() {
  if (!state.selectedTagFilters.length) {
    refs.selectedSearchTags.innerHTML = "";
    refs.selectedSearchTags.classList.add("hidden");
    return;
  }

  refs.selectedSearchTags.innerHTML = state.selectedTagFilters
    .map((tagName) => renderTagChip(tagName, { removeAction: "search-tag" }))
    .join("");
  refs.selectedSearchTags.classList.remove("hidden");
}

function renderProductSortControls() {
  refs.productSort.value = state.productSort;
  refs.productSortOrder.value = state.productSortOrder;
}

function renderProductFormTags() {
  if (!state.productFormTags.length) {
    refs.productTagList.innerHTML = '<span class="tag-empty">Теги не добавлены</span>';
    return;
  }

  refs.productTagList.innerHTML = state.productFormTags
    .map((tagName) => renderTagChip(tagName, { removeAction: "product-tag" }))
    .join("");
}

function renderTagChip(tagName, options = {}) {
  if (!options.removeAction) {
    return `<span class="tag-chip">${escapeHtml(tagName)}</span>`;
  }

  const removeAttribute = options.removeAction
    ? ` data-remove-${options.removeAction}="${escapeHtml(tagName)}"`
    : "";

  return `
    <button class="tag-chip" type="button" title="Удалить тег"${removeAttribute}>
      ${escapeHtml(tagName)}
    </button>
  `;
}

function getStockStatus(product) {
  if (product.stock_status) {
    return product.stock_status;
  }

  if (product.quantity === 0) {
    return "out";
  }

  const threshold = product.low_stock_threshold ?? DEFAULT_LOW_STOCK_THRESHOLD;
  if (threshold > 0 && product.quantity <= threshold) {
    return "low";
  }

  return "available";
}

function renderSelects() {
  const editingProduct = state.products.find(
    (product) => product.id === state.editingProductId,
  );

  renderOptions(
    refs.productCompany,
    state.companies,
    "Без компании",
    editingProduct?.company_id,
    editingProduct?.company_name,
  );
  renderOptions(
    refs.productSupplier,
    state.suppliers,
    "Без поставщика",
    editingProduct?.supplier_id,
    editingProduct?.supplier_name,
  );
}

function renderOptions(select, items, emptyLabel, pinnedId = null, pinnedName = null) {
  const currentValue = select.value;
  const hasPinnedId = pinnedId !== null && pinnedId !== undefined;
  const hasPinnedItem =
    hasPinnedId && items.some((item) => item.id === pinnedId);
  const options = [
    `<option value="">${emptyLabel}</option>`,
    ...items.map(
      (item) => `<option value="${item.id}">${escapeHtml(item.name)}</option>`,
    ),
  ];

  if (hasPinnedId && !hasPinnedItem) {
    options.push(
      `<option value="${pinnedId}">${escapeHtml(pinnedName ?? `#${pinnedId}`)}</option>`,
    );
  }

  select.innerHTML = options.join("");

  if ([...select.options].some((option) => option.value === currentValue)) {
    select.value = currentValue;
  }
}

function renderLookupTable(type) {
  const items = type === "company" ? state.companies : state.suppliers;
  const body =
    type === "company" ? refs.companyTableBody : refs.supplierTableBody;
  const secondaryKey = type === "company" ? "iin" : "phone_number";
  const emptyText =
    type === "company" ? "Компаний пока нет." : "Поставщиков пока нет.";

  if (items.length === 0) {
    body.innerHTML = `
      <tr>
        <td colspan="3">
          <div class="empty-state">${emptyText}</div>
        </td>
      </tr>
    `;
    return;
  }

  body.innerHTML = items
    .map(
      (item) => `
        <tr>
          <td>
            <strong>${escapeHtml(item.name)}</strong>
            <div class="lookup-meta">#${item.id}</div>
          </td>
          <td>${escapeHtml(item[secondaryKey])}</td>
          <td>
            <div class="actions">
              <button class="danger-button" type="button" data-id="${item.id}">Удалить</button>
            </div>
          </td>
        </tr>
      `,
    )
    .join("");
}

function renderMovementTable() {
  if (state.stockMovements.length === 0) {
    refs.movementTableBody.innerHTML = `
      <tr>
        <td colspan="5">
          <div class="empty-state">Движений пока нет.</div>
        </td>
      </tr>
    `;
    return;
  }

  refs.movementTableBody.innerHTML = state.stockMovements
    .map(
      (movement) => `
        <tr>
          <td>#${movement.id}</td>
          <td>${escapeHtml(MOVEMENT_TYPE_LABELS[movement.movement_type] || movement.movement_type)}</td>
          <td>${renderMovementLines(movement.lines)}</td>
          <td>${formatDate(movement.created_at)}</td>
          <td>${escapeHtml(movement.note || "-")}</td>
        </tr>
      `,
    )
    .join("");
}

function renderMovementLines(lines) {
  return `
    <div class="movement-lines">
      ${lines
        .map((line) => {
          const quantityUnit = getMovementLineUnit(line);

          return `
            <div class="movement-line">
              <strong>${escapeHtml(getProductDisplayName(line.product_id))}</strong>:
              ${escapeHtml(formatSignedQuantity(line.quantity_delta, quantityUnit))}
              (${escapeHtml(formatQuantity(line.quantity_before, quantityUnit))} -> ${escapeHtml(formatQuantity(line.quantity_after, quantityUnit))})
            </div>
          `;
        })
        .join("")}
    </div>
  `;
}

function renderPagination(type) {
  const pagination = state.pagination[type];
  const { container, info } = getPaginationRefs(type);
  const previousButton = container.querySelector(
    '[data-pagination-action="prev"]',
  );
  const nextButton = container.querySelector('[data-pagination-action="next"]');
  const start = pagination.total === 0
    ? 0
    : (pagination.page - 1) * pagination.pageSize + 1;
  const end = Math.min(pagination.page * pagination.pageSize, pagination.total);

  info.textContent =
    pagination.total === 0
      ? "Нет записей"
      : `${formatNumber(start)}-${formatNumber(end)} из ${formatNumber(
          pagination.total,
        )}`;
  previousButton.disabled = pagination.page <= 1;
  nextButton.disabled = pagination.pages === 0 || pagination.page >= pagination.pages;
}

function getPaginationRefs(type) {
  if (type === "products") {
    return { container: refs.productPagination, info: refs.productPageInfo };
  }

  if (type === "companies") {
    return { container: refs.companyPagination, info: refs.companyPageInfo };
  }

  if (type === "suppliers") {
    return { container: refs.supplierPagination, info: refs.supplierPageInfo };
  }

  return { container: refs.movementPagination, info: refs.movementPageInfo };
}

function getCompanyName(companyId) {
  if (companyId === null) {
    return "Не указана";
  }

  return state.companies.find((company) => company.id === companyId)?.name ?? `#${companyId}`;
}

function getSupplierName(supplierId) {
  if (supplierId === null) {
    return "Не указан";
  }

  return (
    state.suppliers.find((supplier) => supplier.id === supplierId)?.name ??
    `#${supplierId}`
  );
}

function getProductDisplayName(productId) {
  const product =
    state.products.find((item) => item.id === productId) ||
    state.movementProductCache.get(productId);

  return product ? product.name : `#${productId}`;
}

function getMovementLineUnit(line) {
  if (line.quantity_unit_snapshot) {
    return line.quantity_unit_snapshot;
  }

  const product =
    state.products.find((item) => item.id === line.product_id) ||
    state.movementProductCache.get(line.product_id);

  return product?.quantity_unit || DEFAULT_QUANTITY_UNIT;
}
