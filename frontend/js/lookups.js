async function handleCompanySubmit(event) {
  event.preventDefault();

  setBusy(true);

  try {
    await request("/companies", {
      method: "POST",
      body: JSON.stringify({
        name: refs.companyName.value.trim(),
        iin: refs.companyIin.value.trim(),
      }),
    });

    refs.companyForm.reset();
    closeDrawer();
    await loadAll({ quiet: true });
    showNotice("Компания добавлена.");
  } catch (error) {
    showNotice(error.message, true);
  } finally {
    setBusy(false);
  }
}

function handleCompanyTableClick(event) {
  const button = event.target.closest("button[data-id]");

  if (button) {
    deleteLookup("company", Number(button.dataset.id));
  }
}

async function handleSupplierSubmit(event) {
  event.preventDefault();

  setBusy(true);

  try {
    await request("/suppliers", {
      method: "POST",
      body: JSON.stringify({
        name: refs.supplierName.value.trim(),
        phone_number: refs.supplierPhone.value.trim(),
      }),
    });

    refs.supplierForm.reset();
    closeDrawer();
    await loadAll({ quiet: true });
    showNotice("Поставщик добавлен.");
  } catch (error) {
    showNotice(error.message, true);
  } finally {
    setBusy(false);
  }
}

function handleSupplierTableClick(event) {
  const button = event.target.closest("button[data-id]");

  if (button) {
    deleteLookup("supplier", Number(button.dataset.id));
  }
}

async function deleteLookup(type, id) {
  const items = type === "company" ? state.companies : state.suppliers;
  const item = items.find((candidate) => candidate.id === id);
  const label = type === "company" ? "компанию" : "поставщика";
  const successMessage =
    type === "company" ? "Компания удалена." : "Поставщик удален.";
  const endpoint = type === "company" ? "companies" : "suppliers";
  const name = item ? item.name : `#${id}`;

  if (!window.confirm(`Удалить ${label} "${name}"? Связанные товары останутся.`)) {
    return;
  }

  try {
    await request(`/${endpoint}/${id}`, { method: "DELETE" });
    resetProductForm();
    await loadAll({ quiet: true });
    showNotice(successMessage);
  } catch (error) {
    showNotice(error.message, true);
  }
}
