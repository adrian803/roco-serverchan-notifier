const THEME_STORAGE_KEY = "roco-console-theme";

function themeIconSvg(theme) {
  if (theme === "dark") {
    return `
      <svg class="theme-icon" viewBox="0 0 24 24" aria-hidden="true">
        <circle cx="12" cy="12" r="4.25" fill="none" stroke="currentColor" stroke-width="1.9"/>
        <path d="M12 2.25v2.2M12 19.55v2.2M5.11 5.11l1.56 1.56M17.33 17.33l1.56 1.56M2.25 12h2.2M19.55 12h2.2M5.11 18.89l1.56-1.56M17.33 6.67l1.56-1.56" fill="none" stroke="currentColor" stroke-linecap="round" stroke-width="1.9"/>
      </svg>`;
  }
  return `
    <svg class="theme-icon" viewBox="0 0 24 24" aria-hidden="true">
      <path d="M19.2 14.72A8.5 8.5 0 0 1 9.28 4.8a8.55 8.55 0 1 0 9.92 9.92Z" fill="none" stroke="currentColor" stroke-linejoin="round" stroke-width="1.9"/>
    </svg>`;
}

export function storedTheme() {
  try {
    return localStorage.getItem(THEME_STORAGE_KEY);
  } catch {
    return "";
  }
}

export function systemPrefersDark() {
  return window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches;
}

export function resolvedTheme() {
  const theme = document.documentElement.dataset.theme || storedTheme();
  if (theme === "light" || theme === "dark") return theme;
  return systemPrefersDark() ? "dark" : "light";
}

export function renderThemeButton(button) {
  if (!button) return;
  const theme = resolvedTheme();
  button.innerHTML = themeIconSvg(theme);
  button.setAttribute("aria-pressed", theme === "dark" ? "true" : "false");
  button.setAttribute("aria-label", `切换到${theme === "dark" ? "浅色" : "深色"}模式`);
  button.setAttribute("title", theme === "dark" ? "切换到浅色模式" : "切换到深色模式");
}

export function applyTheme(theme) {
  document.documentElement.dataset.theme = theme;
  try {
    localStorage.setItem(THEME_STORAGE_KEY, theme);
  } catch {
    // Theme persistence is a convenience; the UI still works without storage.
  }
}

export function initThemeToggle(button) {
  if (!button) return;

  const render = () => renderThemeButton(button);
  button.addEventListener("click", () => {
    applyTheme(resolvedTheme() === "dark" ? "light" : "dark");
    render();
  });

  if (window.matchMedia) {
    window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change", () => {
      if (!storedTheme()) render();
    });
  }

  render();
}
