function safeReturnTo() {
  const next = `${window.location.pathname}${window.location.search}${window.location.hash}`;
  return next.startsWith('/') ? next : '/';
}

function loginHref() {
  return `/login?return_to=${encodeURIComponent(safeReturnTo())}`;
}

export async function fetchAuthSession() {
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
}

export async function logout() {
  const response = await fetch('/api/auth/logout', {
    method: 'POST',
    credentials: 'same-origin',
    headers: {
      Accept: 'application/json',
    },
  });
  if (!response.ok) {
    throw new Error(`Logout failed with status ${response.status}`);
  }
  return response.json();
}

function applyAuthUi(session) {
  const controls = document.getElementById('auth-controls');
  const loginLink = document.getElementById('auth-login-link');
  const logoutBtn = document.getElementById('auth-logout-btn');
  const status = document.getElementById('auth-status');
  if (!controls || !loginLink || !logoutBtn || !status) return;

  if (!session?.auth_enabled) {
    controls.hidden = true;
    return;
  }

  controls.hidden = false;
  loginLink.href = loginHref();

  if (session.authenticated && session.user) {
    const label = session.user.first_name || session.user.email || 'Signed in';
    status.hidden = false;
    status.textContent = label;
    logoutBtn.hidden = false;
    loginLink.hidden = true;
  } else {
    status.hidden = false;
    status.textContent = 'Guest mode';
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
        window.location.reload();
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
