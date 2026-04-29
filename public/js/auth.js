function safeReturnTo() {
  const next = `${window.location.pathname}${window.location.search}${window.location.hash}`;
  return next.startsWith('/') ? next : '/';
}

export function buildLoginHref(returnTo = safeReturnTo()) {
  return `/login?return_to=${encodeURIComponent(returnTo)}`;
}

export function redirectToLogin(returnTo = safeReturnTo()) {
  window.location.assign(buildLoginHref(returnTo));
}

export function isGuestSession(session) {
  return Boolean(session?.guest_mode);
}

export function isIdentifiedUserSession(session) {
  return Boolean(session?.authenticated && !session?.guest_mode && session?.user);
}

// Module-scoped session cache. First caller fetches; subsequent callers
// await the same in-flight promise OR the resolved value. Cleared on
// logout so the next fetch reflects the new anonymous state.
let __sessionPromise = null;

export async function fetchAuthSession({ force = false } = {}) {
  if (force || !__sessionPromise) {
    __sessionPromise = (async () => {
      const response = await fetch('/api/me', {
        method: 'GET',
        credentials: 'same-origin',
        headers: {
          Accept: 'application/json',
        },
      });
      if (!response.ok) {
        throw new Error(`Auth bootstrap failed with status ${response.status}`);
      }
      return response.json();
    })().catch((err) => {
      // Null the cache on failure so next call retries instead of
      // permanently returning a rejection.
      __sessionPromise = null;
      throw err;
    });
  }
  return __sessionPromise;
}

export function invalidateAuthSession() {
  __sessionPromise = null;
}

export async function logout() {
  const response = await fetch('/api/auth/logout', {
    method: 'POST',
    credentials: 'same-origin',
    headers: {
      Accept: 'application/json',
    },
  });
  invalidateAuthSession();
  if (!response.ok) {
    throw new Error(`Logout failed with status ${response.status}`);
  }
  return response.json();
}

// Admin Surface gate: server-side check at /admin/todo is the canonical
// authority. This client-side comparison only decides whether to RENDER
// the link; a wrong email here just hides a button (and the server would
// 404 anyway).
const ADMIN_EMAIL = 'jonathan10620@gmail.com';

function applyAuthUi(session) {
  const controls = document.getElementById('auth-controls');
  const loginLink = document.getElementById('auth-login-link');
  const logoutBtn = document.getElementById('auth-logout-btn');
  const status = document.getElementById('auth-status');
  const adminLink = document.getElementById('auth-admin-todo-link');
  if (!controls || !loginLink || !logoutBtn || !status) return;

  controls.hidden = false;
  loginLink.href = buildLoginHref();
  loginLink.textContent = 'Save & Sync';
  logoutBtn.textContent = 'Log Out';

  const isAdmin =
    isIdentifiedUserSession(session) &&
    session.user?.email?.toLowerCase() === ADMIN_EMAIL;
  if (adminLink) adminLink.hidden = !isAdmin;

  if (isGuestSession(session)) {
    status.hidden = false;
    status.textContent = 'Guest mode';
    logoutBtn.hidden = false;
    logoutBtn.textContent = 'Exit Guest';
    loginLink.hidden = !session?.auth_enabled;
  } else if (isIdentifiedUserSession(session)) {
    const label = session.user.first_name || session.user.email || 'Signed in';
    status.hidden = false;
    status.textContent = label;
    logoutBtn.hidden = false;
    loginLink.hidden = true;
  } else {
    status.hidden = false;
    status.textContent = 'Login required';
    logoutBtn.hidden = true;
    loginLink.hidden = false;
  }
}

export async function bootstrapAuthUi() {
  const logoutBtn = document.getElementById('auth-logout-btn');
  if (logoutBtn && !logoutBtn.dataset.bound) {
    logoutBtn.dataset.bound = 'true';
    logoutBtn.addEventListener('click', async () => {
      logoutBtn.disabled = true;
      try {
        await logout();
        redirectToLogin('/');
      } catch (err) {
        console.warn('Logout failed.', err);
      } finally {
        logoutBtn.disabled = false;
      }
    });
  }

  try {
    const session = await fetchAuthSession();
    applyAuthUi(session);
  } catch (err) {
    console.warn('Auth UI bootstrap unavailable.', err);
  }
}
