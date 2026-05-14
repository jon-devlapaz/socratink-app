export const THEME_STORAGE_KEY = 'learnops-theme';

export function normalizeThemePreference(nextPreference) {
  return nextPreference === 'dark' ? 'dark' : 'light';
}

export function getToggledTheme(currentTheme) {
  return currentTheme === 'dark' ? 'light' : 'dark';
}

export function getStoredThemePreference({ storage = localStorage, logger = console } = {}) {
  try {
    const stored = storage.getItem(THEME_STORAGE_KEY);
    return normalizeThemePreference(stored);
  } catch (err) {
    logger.warn('Theme preference unavailable.', err);
    return 'light';
  }
}

export function updateThemeToggleUi(resolvedTheme, themeToggleEl) {
  if (!themeToggleEl) return;
  const isDark = resolvedTheme === 'dark';
  const label = isDark ? 'Switch to light mode' : 'Switch to dark mode';
  themeToggleEl.dataset.theme = resolvedTheme;
  themeToggleEl.setAttribute('aria-pressed', String(isDark));
  themeToggleEl.setAttribute('aria-label', label);
  themeToggleEl.setAttribute('title', label);
}

export function applyThemePreference(
  nextPreference,
  {
    persist = true,
    documentRef = document,
    themeToggleEl = null,
    storage = localStorage,
    logger = console,
    onRemount = () => {},
  } = {},
) {
  const resolvedTheme = normalizeThemePreference(nextPreference);
  documentRef.body.classList.toggle('night', resolvedTheme === 'dark');
  documentRef.body.dataset.theme = resolvedTheme;
  documentRef.documentElement.dataset.theme = resolvedTheme;
  updateThemeToggleUi(resolvedTheme, themeToggleEl);
  onRemount();
  if (!persist) return resolvedTheme;
  try {
    storage.setItem(THEME_STORAGE_KEY, resolvedTheme);
  } catch (err) {
    logger.warn('Theme preference could not be saved.', err);
  }
  return resolvedTheme;
}
