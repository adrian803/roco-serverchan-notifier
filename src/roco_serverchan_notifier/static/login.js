    import {initThemeToggle} from "./theme.js";

    const form = document.getElementById("loginForm");
    const button = document.getElementById("loginBtn");
    const message = document.getElementById("message");
    const themeButton = document.getElementById("themeBtn");

    function nextUrl() {
      const params = new URLSearchParams(window.location.search);
      const next = params.get("next") || "/";
      return next.startsWith("/") ? next : "/";
    }

    initThemeToggle(themeButton);

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
