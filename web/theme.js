(() => {
  // Light by default. A saved choice from the header toggle wins over the default;
  // ?clawpilotTheme=light|dark wins over both.
  const KEY = "arxiv.theme";
  const valid = (t) => (t === "light" || t === "dark" ? t : null);
  const read = () => { try { return valid(localStorage.getItem(KEY)); } catch { return null; } };
  const param = () => valid(new URLSearchParams(location.search).get("clawpilotTheme"));
  const root = document.documentElement;
  root.setAttribute("data-theme", param() || read() || "light");

  const label = (btn) => {
    const next = root.getAttribute("data-theme") === "dark" ? "light" : "dark";
    btn.setAttribute("aria-label", `Switch to ${next} mode`);
    btn.title = `Switch to ${next} mode`;
  };
  document.addEventListener("DOMContentLoaded", () => {
    const btn = document.getElementById("theme-toggle");
    if (!btn) return;
    label(btn);
    btn.addEventListener("click", () => {
      const next = root.getAttribute("data-theme") === "dark" ? "light" : "dark";
      root.setAttribute("data-theme", next);
      try { localStorage.setItem(KEY, next); } catch {}
      if (param()) {
        const url = new URL(location.href);
        url.searchParams.set("clawpilotTheme", next);
        history.replaceState(history.state, "", url);
      }
      label(btn);
    });
  });
})();
