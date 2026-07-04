export const SETTINGS_HTML = `
      <div class="settings-shell">
        <header class="settings-page-header">
          <span class="settings-page-kicker">
            <span class="crystal-glyph" aria-hidden="true"></span> Settings
          </span>
          <h2 class="settings-page-title">Your reading room</h2>
          <p class="settings-page-copy">Quiet preferences for how socratink looks and sounds. Saved to this browser.</p>
        </header>

        <div class="settings-identity-row" id="settings-identity-row">
          <div class="settings-avatar" id="settings-avatar"></div>
          <div class="settings-identity-text">
            <span class="settings-identity-email" id="settings-identity-email">…</span>
            <span class="settings-identity-meta" id="settings-identity-meta"></span>
          </div>
          <span id="settings-identity-action-host"></span>
        </div>

        <section class="settings-display">
          <h3 class="settings-section-heading">Display</h3>

          <div class="settings-row">
            <div>
              <div class="settings-row-label">Theme</div>
              <div class="settings-row-meta">Cream paper or obsidian sky</div>
            </div>
            <div class="settings-pill-group" role="radiogroup" aria-label="Theme">
              <button type="button" class="settings-pill" role="radio" data-theme-value="light" aria-checked="false">Light</button>
              <button type="button" class="settings-pill" role="radio" data-theme-value="dark" aria-checked="false">Dark</button>
            </div>
          </div>

          <div class="settings-row">
            <div>
              <div class="settings-row-label">Reduced motion</div>
              <div class="settings-row-meta">Calm transitions, no settle bloom</div>
            </div>
            <button type="button" class="settings-toggle" id="settings-motion-toggle"
                    role="switch" aria-checked="false" aria-label="Reduced motion"></button>
          </div>
        </section>

        <section class="settings-display">
          <h3 class="settings-section-heading">Sound</h3>

          <div class="settings-row">
            <div>
              <div class="settings-row-label">Threshold sounds</div>
              <div class="settings-row-meta">Soft cues at focus and submit</div>
            </div>
            <button type="button" class="settings-toggle" id="settings-sound-toggle"
                    role="switch" aria-checked="false" aria-label="Threshold sounds"></button>
          </div>

          <div class="settings-row">
            <div>
              <div class="settings-row-label">Mic input</div>
              <div class="settings-row-meta">Dictate answers in drill sessions</div>
            </div>
            <button type="button" class="settings-toggle" id="settings-mic-toggle"
                    role="switch" aria-checked="false" aria-label="Mic input"></button>
          </div>

          <div class="settings-row">
            <div>
              <div class="settings-row-label">Tutor voice</div>
              <div class="settings-row-meta">Read the active prompt aloud</div>
            </div>
            <button type="button" class="settings-toggle" id="settings-tutor-voice-toggle"
                    role="switch" aria-checked="false" aria-label="Tutor voice"></button>
          </div>
        </section>
      </div>
    `;

export const MIC_INPUT_PREF_KEY = 'socratink.loop.micInput';
export const TUTOR_VOICE_PREF_KEY = 'socratink.loop.tutorVoice';

let settingsCornerSyncBound = false;

export async function renderSettingsView({
  documentRef = document,
  fetchAuthSession,
  isGuestSession,
  isIdentifiedUserSession,
  buildLoginHref,
  logout,
  redirectToLogin,
  getStoredThemePreference,
  setTheme,
  AudioFX,
} = {}) {
  const settingsContent = documentRef.getElementById('settings-content');
  if (!settingsContent) return;

  settingsContent.innerHTML = SETTINGS_HTML;

  await wireSettingsIdentity(settingsContent, {
    documentRef,
    fetchAuthSession,
    isGuestSession,
    isIdentifiedUserSession,
    buildLoginHref,
    logout,
    redirectToLogin,
  });
  wireSettingsTheme(settingsContent, { documentRef, getStoredThemePreference, setTheme });
  wireSettingsMotion(settingsContent, { documentRef });
  wireSettingsSounds(settingsContent, { AudioFX });
  wireVoiceSettings(settingsContent);
}

async function wireSettingsIdentity(root, {
  documentRef,
  fetchAuthSession,
  isGuestSession,
  isIdentifiedUserSession,
  buildLoginHref,
  logout,
  redirectToLogin,
}) {
  const row = root.querySelector('#settings-identity-row');
  const avatar = root.querySelector('#settings-avatar');
  const emailEl = root.querySelector('#settings-identity-email');
  const metaEl = root.querySelector('#settings-identity-meta');
  const actionHost = root.querySelector('#settings-identity-action-host');
  if (!row || !avatar || !emailEl || !metaEl || !actionHost) return;

  let session;
  try {
    session = await fetchAuthSession();
  } catch (err) {
    console.warn('Settings identity: /api/me unavailable', err);
    row.hidden = true;
    return;
  }

  if (session && session.auth_enabled === false) {
    row.hidden = true;
    return;
  }

  if (isGuestSession(session)) {
    avatar.classList.add('is-guest');
    emailEl.textContent = 'Guest';
    metaEl.textContent = 'Not signed in';
    const link = documentRef.createElement('a');
    link.className = 'settings-identity-action';
    link.href = buildLoginHref();
    link.textContent = 'Sign in';
    actionHost.replaceChildren(link);
    return;
  }

  if (isIdentifiedUserSession(session)) {
    const email = session.user?.email || '…';
    emailEl.textContent = email;
    metaEl.textContent = 'Signed in';
    const btn = documentRef.createElement('button');
    btn.type = 'button';
    btn.className = 'settings-identity-action';
    btn.textContent = 'Log out';
    btn.addEventListener('click', async () => {
      btn.disabled = true;
      try {
        await logout();
        redirectToLogin('/');
      } catch (err) {
        console.warn('Logout failed', err);
        btn.disabled = false;
      }
    });
    actionHost.replaceChildren(btn);
    return;
  }

  row.hidden = true;
}

function wireSettingsTheme(root, { documentRef, getStoredThemePreference, setTheme }) {
  const pills = root.querySelectorAll('.settings-pill[data-theme-value]');
  if (!pills.length) return;

  const syncPills = () => {
    const current = getStoredThemePreference();
    pills.forEach(p => {
      p.setAttribute('aria-checked', String(p.dataset.themeValue === current));
    });
  };

  pills.forEach(pill => {
    pill.addEventListener('click', () => {
      const next = pill.dataset.themeValue === 'dark' ? 'dark' : 'light';
      setTheme(next);
      syncPills();
    });
  });

  syncPills();

  if (!settingsCornerSyncBound) {
    const corner = documentRef.getElementById('theme-toggle');
    if (corner) {
      corner.addEventListener('click', () => {
        setTimeout(() => {
          const livePills = documentRef.querySelectorAll('.settings-pill[data-theme-value]');
          if (!livePills.length) return;
          const current = getStoredThemePreference();
          livePills.forEach(p => {
            p.setAttribute('aria-checked', String(p.dataset.themeValue === current));
          });
        }, 0);
      });
      settingsCornerSyncBound = true;
    }
  }
}

function wireSettingsMotion(root, { documentRef }) {
  const toggle = root.querySelector('#settings-motion-toggle');
  if (!toggle) return;

  const readStored = () => {
    try {
      return localStorage.getItem('socratink.motion') === 'reduced';
    } catch {
      return false;
    }
  };

  const apply = (isReduced) => {
    if (isReduced) {
      documentRef.documentElement.dataset.motion = 'reduced';
      try { localStorage.setItem('socratink.motion', 'reduced'); } catch {}
    } else {
      delete documentRef.documentElement.dataset.motion;
      try { localStorage.setItem('socratink.motion', 'system'); } catch {}
    }
    toggle.setAttribute('aria-checked', String(isReduced));
  };

  apply(readStored());

  toggle.addEventListener('click', () => {
    const next = toggle.getAttribute('aria-checked') !== 'true';
    apply(next);
  });
}

function wireSettingsSounds(root, { AudioFX }) {
  const toggle = root.querySelector('#settings-sound-toggle');
  if (!toggle) return;

  toggle.setAttribute('aria-checked', String(Boolean(AudioFX.enabled)));

  toggle.addEventListener('click', () => {
    const next = toggle.getAttribute('aria-checked') !== 'true';
    AudioFX.setEnabled(next);
    toggle.setAttribute('aria-checked', String(next));
    if (next) {
      AudioFX.playFocusTap();
    }
  });
}

function wireVoiceSettings(root) {
  wireStoredSwitch(root.querySelector('#settings-mic-toggle'), {
    key: MIC_INPUT_PREF_KEY,
    defaultEnabled: true,
  });
  wireStoredSwitch(root.querySelector('#settings-tutor-voice-toggle'), {
    key: TUTOR_VOICE_PREF_KEY,
    defaultEnabled: false,
  });
}

function wireStoredSwitch(toggle, { key, defaultEnabled }) {
  if (!toggle) return;

  const read = () => {
    try {
      const value = localStorage.getItem(key);
      if (value === '1') return true;
      if (value === '0') return false;
    } catch {
      /* storage unavailable */
    }
    return defaultEnabled;
  };

  const write = (enabled) => {
    toggle.setAttribute('aria-checked', String(enabled));
    try {
      localStorage.setItem(key, enabled ? '1' : '0');
    } catch {
      /* preference just won't stick */
    }
  };

  write(read());
  toggle.addEventListener('click', () => {
    /* c8 ignore next -- settings toggles are clicked in browser smoke; helper coverage only imports this module. */
    write(toggle.getAttribute('aria-checked') !== 'true');
  });
}
