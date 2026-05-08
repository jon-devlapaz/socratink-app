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
//   teardown(): removes event listeners. For v1, the modal does not call
//     this (it relies on the chip being re-rendered via rerenderSummary).
//     The door surface uses teardown to collapse the panel cleanly.

export function mountSourcePanel(targetEl, opts = {}) {
  const onAttach = opts.onAttach || (() => {});
  const onCancel = opts.onCancel || (() => {});

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
        <div class="overlay-dropzone">
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

  function panelHasContent() {
    if (activeTab === "paste") return textarea.value.trim().length > 0;
    if (activeTab === "url") return urlInput.value.trim().length > 0;
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
      pendingFileText = String(text || "");
      pendingFileName = String(filename || file.name);
      fileFeedback.className = "overlay-dropfeedback ok";
      fileFeedback.textContent = `${pendingFileName} · ${pendingFileText.length.toLocaleString()} chars`;
      refreshAttachEnabled();
    };
    const onReadError = (errMsg) => {
      fileFeedback.className = "overlay-dropfeedback error";
      fileFeedback.textContent = errMsg || "Couldn't read that file.";
      pendingFileText = "";
      pendingFileName = "";
      refreshAttachEnabled();
    };

    // Prefer the app-level _readFile helper (handles PDFs via pdf.js, txt/md via
    // readAsText). Falls back to readAsText for text files only when the helper
    // isn't available (e.g., test harness loading source-panel in isolation).
    const appReadFile = (typeof window !== "undefined" && window.App && typeof window.App._readFile === "function")
      ? window.App._readFile
      : null;
    if (appReadFile) {
      appReadFile(file, onReadOk, onReadError);
      return;
    }

    // Fallback: only safe for text files. Reject PDFs explicitly so we never
    // produce garbage extracted text.
    if (/\.pdf$/i.test(file.name)) {
      onReadError("PDF reader unavailable.");
      return;
    }
    const reader = new FileReader();
    reader.onload = () => onReadOk(reader.result, file.name);
    reader.onerror = () => onReadError("Couldn't read that file.");
    reader.readAsText(file);
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
      if (!url) return;
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
