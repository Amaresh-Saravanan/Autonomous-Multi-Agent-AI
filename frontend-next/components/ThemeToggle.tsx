"use client";

import { useEffect, useState } from "react";

type Theme = "dark" | "light";

function applyTheme(theme: Theme) {
  document.documentElement.setAttribute("data-theme", theme);
}

export default function ThemeToggle() {
  const [theme, setTheme] = useState<Theme>("dark");

  // Read the persisted choice on mount (the anti-flash script in layout.tsx
  // has already applied it to <html>; this just syncs React state to it).
  useEffect(() => {
    const stored = (localStorage.getItem("theme") as Theme) || "dark";
    setTheme(stored);
  }, []);

  function toggle() {
    const next: Theme = theme === "dark" ? "light" : "dark";
    setTheme(next);
    applyTheme(next);
    try {
      localStorage.setItem("theme", next);
    } catch {
      /* localStorage unavailable — theme just won't persist */
    }
  }

  return (
    <button
      onClick={toggle}
      aria-label={theme === "dark" ? "Switch to light theme" : "Switch to dark theme"}
      title={theme === "dark" ? "Switch to light theme" : "Switch to dark theme"}
      className="cursor-pointer rounded border border-[var(--border)] bg-white/5 px-1.5 py-0.5 text-[var(--text-primary)] hover:bg-white/15"
    >
      {theme === "dark" ? "☾" : "☀"}
    </button>
  );
}
