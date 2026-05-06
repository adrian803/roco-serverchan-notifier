    const form = document.getElementById("loginForm");
    const button = document.getElementById("loginBtn");
    const message = document.getElementById("message");
    const themeButton = document.getElementById("themeBtn");
    const themeStorageKey = "roco-console-theme";

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

    function storedTheme() {
      try {
        return localStorage.getItem(themeStorageKey);
      } catch {
        return "";
      }
    }

    function systemPrefersDark() {
      return window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches;
    }

    function resolvedTheme() {
      const theme = document.documentElement.dataset.theme || storedTheme();
      if (theme === "light" || theme === "dark") return theme;
      return systemPrefersDark() ? "dark" : "light";
    }

    function renderThemeButton() {
      const theme = resolvedTheme();
      themeButton.innerHTML = themeIconSvg(theme);
      themeButton.setAttribute("aria-pressed", theme === "dark" ? "true" : "false");
      themeButton.setAttribute("aria-label", `切换到${theme === "dark" ? "浅色" : "深色"}模式`);
      themeButton.setAttribute("title", theme === "dark" ? "切换到浅色模式" : "切换到深色模式");
    }

    function applyTheme(theme) {
      document.documentElement.dataset.theme = theme;
      try {
        localStorage.setItem(themeStorageKey, theme);
      } catch {
        // Theme persistence is optional; rendering still works without storage.
      }
      renderThemeButton();
    }

    function nextUrl() {
      const params = new URLSearchParams(window.location.search);
      const next = params.get("next") || "/";
      return next.startsWith("/") ? next : "/";
    }

    themeButton.addEventListener("click", () => {
      applyTheme(resolvedTheme() === "dark" ? "light" : "dark");
    });

    if (window.matchMedia) {
      window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change", () => {
        if (!storedTheme()) renderThemeButton();
      });
    }

    renderThemeButton();

    form.addEventListener("submit", async event => {
      event.preventDefault();
      button.disabled = true;
      message.textContent = "";
      try {
        const response = await fetch("/api/login", {
          method: "POST",
          headers: {"Content-Type": "application/json"},
          body: JSON.stringify({
            username: document.getElementById("username").value.trim(),
            password: document.getElementById("password").value,
          }),
        });
        const data = await response.json().catch(() => ({}));
        if (!response.ok) throw new Error(data.detail || data.message || "登录失败");
        window.location.assign(nextUrl());
      } catch (error) {
        message.textContent = error.message;
      } finally {
        button.disabled = false;
      }
    });
