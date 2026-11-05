export function currentTheme() {
  return document.documentElement.dataset.theme === "light" ? "light" : "dark";
}

export function applyTheme(theme) {
  document.documentElement.dataset.theme = theme;
  try {
    localStorage.setItem("theme", theme);
  } catch {
    /* navegador sem localStorage: a escolha vale só nesta visita */
  }
}
