/* Guarda exclusivamente la apariencia; nunca datos de acceso. */
(() => {
  const key = 'crece.appearance';
  let theme = 'dark';
  try { if (localStorage.getItem(key) === 'light') theme = 'light'; } catch (_) {}
  function apply(value, persist = false) {
    theme = value === 'light' ? 'light' : 'dark';
    document.documentElement.dataset.theme = theme;
    document.documentElement.style.colorScheme = theme;
    document.querySelector('meta[name="theme-color"]')?.setAttribute('content', theme === 'light' ? '#E0F5EA' : '#001F3F');
    for (const link of document.querySelectorAll('link[data-theme-sheet]')) {
      link.disabled = link.dataset.themeSheet !== theme;
    }
    for (const button of document.querySelectorAll('[data-theme-toggle]')) {
      const next = theme === 'dark' ? 'claro' : 'oscuro';
      button.setAttribute('aria-label', `Usar tema ${next}`);
      button.title = `Usar tema ${next}`;
      button.querySelector('[data-theme-label]').textContent = next === 'claro' ? 'Claro' : 'Oscuro';
      const symbol = button.querySelector('svg');
      if (symbol) symbol.innerHTML = theme === 'light'
        ? '<path d="M20.5 14A8.5 8.5 0 0 1 10 3.5 8.5 8.5 0 1 0 20.5 14Z"/>'
        : '<circle cx="12" cy="12" r="4"/><path d="M12 2v2m0 16v2M2 12h2m16 0h2M5 5l1.5 1.5m11 11L19 19M5 19l1.5-1.5m11-11L19 5"/>';
    }
    for (const mark of document.querySelectorAll('[data-logo-light]')) {
      mark.setAttribute('href', theme === 'light' ? mark.dataset.logoLight : mark.dataset.logoDark);
    }
    if (persist) { try { localStorage.setItem(key, theme); } catch (_) {} }
  }
  apply(theme);
  document.addEventListener('DOMContentLoaded', () => {
    apply(theme);
    document.querySelectorAll('[data-theme-toggle]').forEach(button => {
      button.addEventListener('click', () => apply(theme === 'dark' ? 'light' : 'dark', true));
    });
  });
  window.addEventListener('storage', event => {
    if (event.key === key) apply(event.newValue === 'light' ? 'light' : 'dark');
  });
})();
