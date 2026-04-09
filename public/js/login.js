function qs(name) {
  return new URLSearchParams(window.location.search).get(name);
}

function safeReturnTo() {
  const raw = qs("return_to") || "/";
  return raw.startsWith("/") && !raw.startsWith("//") ? raw : "/";
}

function setBanner(message, kind = "default") {
  const banner = document.getElementById("auth-status-banner");
  if (!banner) return;
  if (!message) {
    banner.hidden = true;
    banner.textContent = "";
    banner.className = "auth-status-banner";
    return;
  }
  banner.hidden = false;
  banner.textContent = message;
  banner.className = `auth-status-banner${kind === "error" ? " is-error" : kind === "success" ? " is-success" : ""}`;
}

function setMode(mode) {
  const body = document.body;
  const modeCopy = document.getElementById("mode-copy-text");
  if (!body || !modeCopy) return;

  const resolved = mode === "signup" ? "signup" : "signin";
  body.dataset.mode = resolved;
  if (resolved === "signup") {
    modeCopy.textContent = "Use your Google account to create an account.";
  } else {
    modeCopy.textContent = "Use your Google account to sign in or create an account.";
  }
}

function applyAuthErrorFromQuery() {
  const authError = qs("auth_error");
  if (!authError) return;
  const messages = {
    access_denied: "Google sign-in was cancelled. You can try again.",
    user_cancelled: "Google sign-in was cancelled. You can try again.",
    authentication_failed: "We couldn't complete sign-in. Please try again.",
    missing_code: "Sign-in did not complete. Please try again.",
    invalid_state: "Sign-in could not be verified safely. Please try again.",
  };
  setBanner(messages[authError] || "Sign-in was interrupted. Please try again.", "error");
}

function initStardust() {
  const container = document.getElementById("stardust-container");
  if (!container) return;
  container.innerHTML = "";
  for (let i = 0; i < 50; i += 1) {
    const star = document.createElement("div");
    const size = (Math.random() * 2 + 1).toFixed(2);
    star.className = "star";
    star.style.width = `${size}px`;
    star.style.height = `${size}px`;
    star.style.left = `${(Math.random() * 100).toFixed(3)}%`;
    star.style.top = `${(Math.random() * 100).toFixed(3)}%`;
    star.style.setProperty("--duration", `${(Math.random() * 3 + 2).toFixed(3)}s`);
    container.appendChild(star);
  }
}

function initParallax() {
  document.addEventListener("mousemove", (event) => {
    const moveX = event.clientX - window.innerWidth / 2;
    const moveY = event.clientY - window.innerHeight / 2;
    document.querySelectorAll("[data-parallax]").forEach((element) => {
      const factor = Number(element.getAttribute("data-parallax") || "0");
      element.style.transform = `translate(${moveX * factor}px, ${moveY * factor}px)`;
    });
  });
}

async function fetchSession() {
  const response = await fetch("/api/me", {
    method: "GET",
    credentials: "same-origin",
    headers: { Accept: "application/json" },
  });
  if (!response.ok) {
    throw new Error(`Auth session fetch failed with status ${response.status}`);
  }
  return response.json();
}

async function postJson(url, payload) {
  const response = await fetch(url, {
    method: "POST",
    credentials: "same-origin",
    headers: {
      "Content-Type": "application/json",
      Accept: "application/json",
    },
    body: JSON.stringify(payload),
  });
  const text = await response.text();
  let data = {};
  try {
    data = text ? JSON.parse(text) : {};
  } catch (err) {
    data = {};
  }
  if (!response.ok) {
    const detail = typeof data.detail === "string" ? data.detail : `Request failed with status ${response.status}`;
    throw new Error(detail);
  }
  return data;
}

async function bootstrap() {
  initStardust();
  initParallax();
  setMode(qs("mode"));
  applyAuthErrorFromQuery();

  const googleLink = document.getElementById("google-login-link");
  const googleLabel = document.getElementById("google-label");

  if (googleLink && googleLabel) {
    googleLink.href = `/auth/google?return_to=${encodeURIComponent(safeReturnTo())}`;
    googleLink.addEventListener("click", () => {
      googleLink.classList.add("is-loading");
      googleLabel.textContent = "Connecting to Google...";
    });
  }

  try {
    const session = await fetchSession();
    if (session.auth_enabled === false) {
      setBanner("Authentication is not enabled in this environment yet.", "error");
    } else if (session.authenticated) {
      setBanner("You are already signed in. Redirecting...", "success");
      window.location.assign(safeReturnTo());
      return;
    }
  } catch (err) {
    setBanner("Authentication is temporarily unavailable.", "error");
  }
}

void bootstrap();
