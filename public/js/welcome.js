const WELCOME_STORAGE_PREFIX = 'socratink:firstSeenAt:v1';

const FRAMES = [
  {
    state: 'instantiated',
    kicker: 'welcome',
    title: 'socratink is a reading room, not a dashboard.',
    description: 'Bring what you have. The first room stays quiet until you begin.',
    action: 'enter the first room',
  },
];

function escapeHtml(value) {
  return String(value)
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#39;');
}

function storageKeyForSession(session) {
  if (session?.guest_mode) return `${WELCOME_STORAGE_PREFIX}:guest`;
  if (session?.authenticated && !session?.guest_mode && session?.user?.id) {
    return `${WELCOME_STORAGE_PREFIX}:user:${session.user.id}`;
  }
  return `${WELCOME_STORAGE_PREFIX}:browser`;
}

function hasSeenWelcome(session) {
  try {
    return Boolean(localStorage.getItem(storageKeyForSession(session)));
  } catch {
    return false;
  }
}

function markWelcomeSeen(session) {
  try {
    const key = storageKeyForSession(session);
    if (!localStorage.getItem(key)) {
      localStorage.setItem(key, new Date().toISOString());
    }
  } catch (err) {
    console.warn('Welcome state could not be saved.', err);
  }
}

function prefersReducedMotion() {
  return window.matchMedia?.('(prefers-reduced-motion: reduce)').matches === true;
}

function focusThresholdComposer() {
  const field = document.getElementById('hero-single-input-field');
  if (!field) return;
  field.focus({ preventScroll: false });
}

function buildCrystalSvg() {
  return `
    <svg class="first-run-welcome__crystal" data-state="instantiated" viewBox="0 0 200 280" aria-hidden="true" focusable="false">
      <polygon class="first-run-welcome__crystal-face first-run-welcome__crystal-face--top" points="100,18 145,72 100,96 55,72"></polygon>
      <polygon class="first-run-welcome__crystal-face first-run-welcome__crystal-face--upper-left" points="55,72 100,96 100,168 40,132"></polygon>
      <polygon class="first-run-welcome__crystal-face first-run-welcome__crystal-face--upper-right" points="145,72 160,132 100,168 100,96"></polygon>
      <polygon class="first-run-welcome__crystal-face first-run-welcome__crystal-face--lower-left" points="40,132 100,168 100,246 60,198"></polygon>
      <polygon class="first-run-welcome__crystal-face first-run-welcome__crystal-face--lower-right" points="160,132 140,198 100,246 100,168"></polygon>
      <polygon class="first-run-welcome__crystal-face first-run-welcome__crystal-face--bottom-tip" points="60,198 100,246 140,198 100,268"></polygon>
      <path class="first-run-welcome__crystal-face first-run-welcome__crystal-face--specular" d="M76 70 99 36 121 70 101 82Z"></path>
    </svg>
  `;
}

function buildFrameMarkup(frame, index) {
  const titleId = `first-run-welcome-title-${index}`;
  const descId = `first-run-welcome-desc-${index}`;
  const isActive = index === 0 ? 'true' : 'false';
  const inertAttr = index === 0 ? '' : ' inert';
  const tabIndex = index === 0 ? '0' : '-1';

  return `
    <section class="first-run-welcome__frame" data-frame="${index}" data-active="${isActive}" aria-hidden="${index === 0 ? 'false' : 'true'}"${inertAttr}>
      <p class="first-run-welcome__kicker">${escapeHtml(frame.kicker)}</p>
      <h2 class="first-run-welcome__title" id="${titleId}">${escapeHtml(frame.title)}</h2>
      <p class="first-run-welcome__lede" id="${descId}">${escapeHtml(frame.description)}</p>
      <button class="first-run-welcome__primary" type="button" data-primary-action tabindex="${tabIndex}">
        ${escapeHtml(frame.action)}
      </button>
    </section>
  `;
}

function buildWelcomeDialog() {
  const root = document.createElement('div');
  root.className = 'first-run-welcome';
  root.setAttribute('role', 'presentation');
  root.innerHTML = `
    <div class="first-run-welcome__card"
         role="dialog"
         aria-modal="true"
         aria-labelledby="first-run-welcome-title-0"
         aria-describedby="first-run-welcome-desc-0">
      <button class="first-run-welcome__skip" type="button">skip</button>
      <div class="first-run-welcome__crystal-stage">
        ${buildCrystalSvg()}
      </div>
      <div class="first-run-welcome__frames">
        ${FRAMES.map(buildFrameMarkup).join('')}
      </div>
    </div>
  `;
  return root;
}

function getFocusableElements(root) {
  return Array.from(root.querySelectorAll('button:not([disabled]), [href], input, textarea, select, [tabindex]:not([tabindex="-1"])'))
    .filter((el) => !el.closest('[inert]'));
}

function setFrame(root, nextIndex) {
  const clampedIndex = Math.max(0, Math.min(FRAMES.length - 1, nextIndex));
  const dialog = root.querySelector('[role="dialog"]');
  const crystal = root.querySelector('.first-run-welcome__crystal');

  root.dataset.frame = String(clampedIndex);
  if (crystal) crystal.dataset.state = FRAMES[clampedIndex].state;

  root.querySelectorAll('.first-run-welcome__frame').forEach((frameEl, index) => {
    const isActive = index === clampedIndex;
    frameEl.dataset.active = String(isActive);
    frameEl.setAttribute('aria-hidden', String(!isActive));
    frameEl.inert = !isActive;
    frameEl.querySelectorAll('[data-primary-action]').forEach((button) => {
      button.tabIndex = isActive ? 0 : -1;
    });
  });

  if (dialog) {
    dialog.setAttribute('aria-labelledby', `first-run-welcome-title-${clampedIndex}`);
    dialog.setAttribute('aria-describedby', `first-run-welcome-desc-${clampedIndex}`);
  }
}

function mountWelcomeOverlay(session) {
  if (document.querySelector('.first-run-welcome')) return;

  const root = buildWelcomeDialog();
  let frameIndex = 0;
  let closing = false;

  const close = ({ focusComposer = false } = {}) => {
    if (closing) return;
    closing = true;
    markWelcomeSeen(session);

    const finish = () => {
      root.remove();
      if (focusComposer) focusThresholdComposer();
    };

    if (prefersReducedMotion()) {
      finish();
      return;
    }

    root.dataset.closing = 'true';
    window.setTimeout(finish, 220);
  };

  const advance = () => {
    if (frameIndex >= FRAMES.length - 1) {
      close({ focusComposer: true });
      return;
    }
    frameIndex += 1;
    setFrame(root, frameIndex);
    root.querySelector('.first-run-welcome__frame[data-active="true"] [data-primary-action]')?.focus();
  };

  const retreat = () => {
    if (frameIndex <= 0) return;
    frameIndex -= 1;
    setFrame(root, frameIndex);
    root.querySelector('.first-run-welcome__frame[data-active="true"] [data-primary-action]')?.focus();
  };

  root.querySelector('.first-run-welcome__skip')?.addEventListener('click', () => close());
  root.querySelectorAll('[data-primary-action]').forEach((button) => {
    button.addEventListener('click', advance);
  });

  root.addEventListener('keydown', (event) => {
    if (event.key === 'Escape') {
      event.preventDefault();
      close();
      return;
    }

    if (event.key === 'ArrowRight') {
      event.preventDefault();
      advance();
      return;
    }

    if (event.key === 'ArrowLeft') {
      event.preventDefault();
      retreat();
      return;
    }

    if (event.key !== 'Tab') return;

    const focusable = getFocusableElements(root);
    if (!focusable.length) return;
    const first = focusable[0];
    const last = focusable[focusable.length - 1];

    if (event.shiftKey && document.activeElement === first) {
      event.preventDefault();
      last.focus();
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault();
      first.focus();
    }
  });

  document.body.appendChild(root);
  setFrame(root, frameIndex);
  requestAnimationFrame(() => {
    root.querySelector('.first-run-welcome__frame[data-active="true"] [data-primary-action]')?.focus();
  });
}

export async function maybeShowFirstRunWelcome({ getSession, shouldShow } = {}) {
  if (typeof shouldShow === 'function' && !shouldShow()) return;

  let session = null;
  try {
    session = typeof getSession === 'function' ? await getSession() : null;
  } catch (err) {
    console.warn('Welcome account gate unavailable.', err);
  }

  if (typeof shouldShow === 'function' && !shouldShow()) return;
  if (hasSeenWelcome(session)) return;

  mountWelcomeOverlay(session);
}
