// public/js/source-panel.js
//
// Reusable source-attach panel.
//
// Mounts the Text/URL/File tabs (paste/clipboard/file/url handlers,
// validation, Attach/Cancel buttons) inside any container element.
// Used by:
//   - the concept-create modal (existing source chip)
//   - the loop-entry door (new affordance, future round)
//
// The DOM markup, tab-switching, validation, paste/upload/url handlers,
// and Cancel/Attach buttons are identical to the inline implementation
// that previously lived inside concept-create.js::beginEditSource.
//
// mountSourcePanel(targetEl, opts) -> { teardown: () => void }
//
//   targetEl: HTMLElement to mount the panel into. Existing innerHTML is
//             replaced (matching the modal's previous behavior).
//
//   opts.onAttach({type, text?, url?, filename?}): called when the
//     learner clicks the Attach button with valid input. The payload
//     shape mirrors the source object expected by concept-create's state:
//       Text tab  → { type: "text", text }
//       URL tab   → { type: "url",  url, text: "", filename: "" }
//       File tab  → { type: "file", text, filename }
//
//   opts.onCancel(): called when the learner clicks Cancel or presses
//     Escape inside the panel.
//
//   teardown(): NO-OP. Listeners attach to children of targetEl, so
//     callers clean up by replacing innerHTML on the mount point (which
//     drops the listener-bearing nodes — the GC handles the rest). Both
//     the concept-create modal and the door rely on this pattern. The
//     return shape includes teardown only so future callers that need
//     explicit cleanup can opt in by replacing the implementation.

import { AudioFX } from "./audio.js?v=4";
import { readSourceFile } from "./door-source.js?v=1";

// Same printable-key heuristic used by the door (app.js) and launch pad —
// keeps audio cues consistent across every text-entry surface.
const _isPrintableSourceKey = (e) =>
  !e.metaKey && !e.ctrlKey && !e.altKey && !e.repeat &&
  (e.key.length === 1 || e.key === "Backspace" || e.key === "Enter");

export function isBlockedVideoUrl(value) {
  try {
    const parsed = new URL(value);
    const host = parsed.hostname.toLowerCase();
    return host === "youtu.be"
      || host === "youtube.com"
      || host.endsWith(".youtube.com")
      || host === "youtube-nocookie.com"
      || host.endsWith(".youtube-nocookie.com");
  } catch {
    return false;
  }
}

export function mountSourcePanel(targetEl, opts = {}) {
  const onAttach = opts.onAttach || (() => {});
  const onCancel = opts.onCancel || (() => {});
  const readFile = opts.readFile || readSourceFile;

  targetEl.innerHTML = `
    <div class="creation-source-panel">
      <div class="overlay-tabs creation-source-tabs">
        <button class="overlay-tab active" type="button" data-tab="paste">Text</button>
        <button class="overlay-tab" type="button" data-tab="url">URL</button>
        <button class="overlay-tab" type="button" data-tab="upload">File</button>
      </div>
      <div class="overlay-panel" data-panel="paste">
        <textarea class="overlay-textarea" placeholder="Paste source material here." maxlength="500000"></textarea>
      </div>
      <div class="overlay-panel" data-panel="url" style="display:none">
        <input class="overlay-url-input" type="url" placeholder="https://example.com/article">
        <p class="overlay-dropfeedback overlay-url-feedback"></p>
      </div>
      <div class="overlay-panel" data-panel="upload" style="display:none">
        <div class="overlay-dropzone" tabindex="0" role="button" aria-label="Attach a file">
          Drop a file or click to browse<br>
          <span style="font-size:11px;opacity:0.65">.txt &nbsp; .md &nbsp; .pdf &nbsp; up to 2MB</span>
        </div>
        <input type="file" accept=".txt,.md,.pdf" style="display:none">
        <p class="overlay-dropfeedback overlay-file-feedback"></p>
      </div>
      <div class="creation-source-panel-footer">
        <button class="creation-source-panel-cancel" type="button">Cancel</button>
        <button class="creation-source-panel-attach" type="button" disabled>Attach</button>
      </div>
    </div>
  `;

  const tabs = targetEl.querySelectorAll(".overlay-tab");
  const panels = targetEl.querySelectorAll(".overlay-panel");
  let activeTab = "paste";
  let pendingFileText = "";
  let pendingFileName = "";

  const textarea = targetEl.querySelector(".overlay-textarea");
  const urlInput = targetEl.querySelector(".overlay-url-input");
  const dropzone = targetEl.querySelector(".overlay-dropzone");
  const fileInput = targetEl.querySelector('input[type="file"]');
  const fileFeedback = targetEl.querySelector(".overlay-file-feedback");
  const cancelBtn = targetEl.querySelector(".creation-source-panel-cancel");
  const attachBtn = targetEl.querySelector(".creation-source-panel-attach");
  let fileReadId = 0;

  // Reject URLs the server's /api/extract-url won't accept (non-http/https
  // schemes, malformed). Same heuristic is reused at attach time so the
  // Attach button doesn't enable on inputs that would fail downstream.
  function isValidHttpUrl(s) {
    const trimmed = String(s || "").trim();
    if (!trimmed) return false;
    try {
      const u = new URL(trimmed);
      return (u.protocol === "http:" || u.protocol === "https:") && !isBlockedVideoUrl(trimmed);
    } catch (_e) {
      return false;
    }
  }

  function panelHasContent() {
    if (activeTab === "paste") return textarea.value.trim().length > 0;
    if (activeTab === "url") return isValidHttpUrl(urlInput.value);
    return pendingFileText.length > 0;
  }
  function refreshAttachEnabled() {
    attachBtn.disabled = !panelHasContent();
  }

  tabs.forEach((tab) => {
    tab.addEventListener("click", () => {
      activeTab = tab.dataset.tab;
      tabs.forEach((t) => t.classList.toggle("active", t.dataset.tab === activeTab));
      panels.forEach((p) => {
        p.style.display = p.dataset.panel === activeTab ? "" : "none";
      });
      targetEl.querySelectorAll(".overlay-dropfeedback").forEach((f) => {
        f.textContent = "";
        f.className = "overlay-dropfeedback";
      });
      refreshAttachEnabled();
    });
  });

  textarea.addEventListener("input", refreshAttachEnabled);
  // URL validation is server-side: Task 9 hops through /api/extract-url, which
  // applies source_intake's allow-list (private-IP block, video-host block, scheme
  // checks). The client only enables Attach when the field is non-empty.
  urlInput.addEventListener("input", refreshAttachEnabled);

  const onSourcePanelEscape = (e) => {
    if (e.key === "Escape") {
      e.stopPropagation();
      e.preventDefault();
      onCancel();
    }
  };
  textarea.addEventListener("keydown", onSourcePanelEscape);
  urlInput.addEventListener("keydown", onSourcePanelEscape);
  // Also wire the panel itself so Escape consistency is preserved
  // when focus is on the Cancel/Attach buttons themselves.
  const panelEl = targetEl.querySelector(".creation-source-panel");
  if (panelEl) {
    panelEl.addEventListener("keydown", onSourcePanelEscape);
  }

  dropzone.addEventListener("click", () => fileInput.click());
  dropzone.addEventListener("keydown", (e) => {
    if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      fileInput.click();
    }
  });
  dropzone.addEventListener("dragover", (e) => {
    e.preventDefault();
    dropzone.classList.add("dragover");
  });
  dropzone.addEventListener("dragleave", () => dropzone.classList.remove("dragover"));
  dropzone.addEventListener("drop", (e) => {
    e.preventDefault();
    dropzone.classList.remove("dragover");
    const f = e.dataTransfer.files?.[0];
    if (f) handleFile(f);
  });
  fileInput.addEventListener("change", () => {
    const f = fileInput.files?.[0];
    if (f) handleFile(f);
    // Reset value so the same file can be re-selected after a cancel/error.
    fileInput.value = "";
  });

  function handleFile(file) {
    const myReadId = ++fileReadId;

    // Two-megabyte cap mirrors the form-era constraint.
    if (file.size > 2 * 1024 * 1024) {
      fileFeedback.className = "overlay-dropfeedback error";
      fileFeedback.textContent = "File is over 2MB.";
      pendingFileText = "";
      pendingFileName = "";
      refreshAttachEnabled();
      return;
    }

    const onReadOk = (text, filename) => {
      if (myReadId !== fileReadId) return; // stale; a newer file selection took priority
      pendingFileText = String(text || "");
      pendingFileName = String(filename || file.name);
      fileFeedback.className = "overlay-dropfeedback ok";
      fileFeedback.textContent = `${pendingFileName} · ${pendingFileText.length.toLocaleString()} chars`;
      refreshAttachEnabled();
    };
    const onReadError = (errMsg) => {
      if (myReadId !== fileReadId) return; // stale; a newer file selection took priority
      fileFeedback.className = "overlay-dropfeedback error";
      fileFeedback.textContent = errMsg || "Couldn't read that file.";
      pendingFileText = "";
      pendingFileName = "";
      refreshAttachEnabled();
    };

    readFile(file, onReadOk, onReadError);
  }

  // Audio cues — match the door + launch-pad pattern so the source-attach
  // surface is sonically consistent with the rest of the create flow.
  // Textboxes: focus tap on arrival + key click per printable keystroke.
  // Buttons (tabs, dropzone, Cancel, Attach): single focus tap on click.
  const _bindFieldAudio = (el) => {
    if (!el) return;
    el.addEventListener("focus", () => AudioFX.playFocusTap());
    el.addEventListener("keydown", (e) => {
      if (_isPrintableSourceKey(e)) AudioFX.playKeyClick();
    });
  };
  _bindFieldAudio(textarea);
  _bindFieldAudio(urlInput);
  tabs.forEach((tab) => tab.addEventListener("click", () => AudioFX.playFocusTap()));
  if (dropzone) dropzone.addEventListener("click", () => AudioFX.playFocusTap());
  if (cancelBtn) cancelBtn.addEventListener("click", () => AudioFX.playFocusTap());
  if (attachBtn) {
    attachBtn.addEventListener("click", () => {
      if (!attachBtn.disabled) AudioFX.playFocusTap();
    });
  }

  cancelBtn.addEventListener("click", () => onCancel());

  attachBtn.addEventListener("click", (e) => {
    e.preventDefault();
    if (attachBtn.disabled) return;
    let payload;
    if (activeTab === "paste") {
      const text = textarea.value.trim();
      if (!text) return;
      payload = { type: "text", text };
    } else if (activeTab === "url") {
      // The Plan A backend expects URL fetching to go through /api/extract-url
      // (separate endpoint). For now we capture the URL on the client; Task 9
      // routes URL submits through that endpoint. The chip stores the URL
      // and the fetched text once the URL endpoint succeeds.
      const url = urlInput.value.trim();
      // Defensive: reject non-http(s) / malformed URLs at attach time so the
      // /api/extract-url call downstream doesn't have to.
      if (!isValidHttpUrl(url)) return;
      payload = { type: "url", url, text: "", filename: "" };
    } else {
      if (!pendingFileText) return;
      payload = { type: "file", text: pendingFileText, filename: pendingFileName };
    }
    onAttach(payload);
  });

  return {
    teardown() {
      // No-op: callers release listeners by replacing this panel's container
      // innerHTML (rerenderSummary on the modal, panel collapse on the door).
    },
  };
}
