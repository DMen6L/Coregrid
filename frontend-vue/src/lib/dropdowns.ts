type BootstrapDropdownInstance = {
  hide: () => void;
};

type BootstrapDropdownApi = {
  getOrCreateInstance: (element: HTMLElement) => BootstrapDropdownInstance;
};

type BootstrapWindow = Window & typeof globalThis & {
  bootstrap?: {
    Dropdown?: BootstrapDropdownApi;
  };
};

export function closeOpenDropdowns(exceptToggle: HTMLElement | null = null) {
  document.querySelectorAll<HTMLElement>('[data-bs-toggle="dropdown"].show').forEach((toggle) => {
    if (toggle !== exceptToggle) {
      closeDropdownToggle(toggle);
    }
  });
}

export function closeDropdownToggle(toggle: HTMLElement | null | undefined) {
  if (!toggle) {
    return;
  }

  const dropdown = (window as BootstrapWindow).bootstrap?.Dropdown?.getOrCreateInstance(toggle);

  if (dropdown) {
    dropdown.hide();
    return;
  }

  closeDropdownByClass(toggle);
}

function closeDropdownByClass(toggle: HTMLElement) {
  toggle.classList.remove("show");
  toggle.setAttribute("aria-expanded", "false");

  const menu = toggle.closest(".dropdown")?.querySelector<HTMLElement>(".dropdown-menu.show");

  menu?.classList.remove("show");
}
