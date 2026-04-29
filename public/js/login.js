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

function applyAuthErrorFromQuery() {
  const authError = qs("auth_error");
  if (!authError) return;
  const messages = {
    access_denied: "Google sign-in was cancelled. You can try again.",
    user_cancelled: "Google sign-in was cancelled. You can try again.",
    authentication_failed: "We couldn't complete sign-in. Please try again.",
    authentication_unavailable: "Google sign-in is not configured correctly right now. Continue as guest or try again later.",
    guest_unavailable: "Guest mode is not configured correctly right now. Try again later.",
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
  applyAuthErrorFromQuery();

  const googleLink = document.getElementById("google-login-link");
  const googleLabel = document.getElementById("google-label");
  const guestLink = document.getElementById("guest-continue-link");

  if (googleLink && googleLabel) {
    googleLink.href = `/auth/google?return_to=${encodeURIComponent(safeReturnTo())}`;
    googleLink.addEventListener("click", () => {
      googleLink.classList.add("is-loading");
      googleLabel.textContent = "Connecting to Google...";
    });
  }

  if (guestLink) {
    guestLink.href = `/auth/guest?return_to=${encodeURIComponent(safeReturnTo())}`;
  }

  try {
    const session = await fetchSession();
    if (session.guest_mode) {
      setBanner("Guest mode is active. Continue with Google to save and sync, or return to the app.", "default");
      if (guestLink) {
        guestLink.href = safeReturnTo();
        guestLink.textContent = "return to app";
      }
      return;
    }
    if (session.authenticated && !session.guest_mode) {
      setBanner("You are already signed in. Redirecting...", "success");
      window.location.assign(safeReturnTo());
      return;
    }
    if (session.auth_enabled === false) {
      if (googleLink) {
        googleLink.setAttribute("aria-disabled", "true");
        googleLink.classList.add("is-disabled");
        googleLink.removeAttribute("href");
      }
      if (guestLink) {
        guestLink.setAttribute("aria-disabled", "true");
        guestLink.classList.add("is-disabled");
        guestLink.removeAttribute("href");
      }
      setBanner("Authentication is not configured here right now. Try again later.", "error");
    }
  } catch (err) {
    setBanner("Authentication is temporarily unavailable. Continue as guest or try Google sign-in again.", "error");
  }
}

void bootstrap();
