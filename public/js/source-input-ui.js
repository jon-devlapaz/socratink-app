export function isBlockedVideoUrl(value) {
  try {
    const parsed = new URL(value);
    const host = parsed.hostname.toLowerCase();
    return host === 'youtu.be'
      || host === 'youtube.com'
      || host.endsWith('.youtube.com')
      || host === 'youtube-nocookie.com'
      || host.endsWith('.youtube-nocookie.com');
  } catch {
    return false;
  }
}

export function shortOnboardingText(value, maxLength = 180) {
  const text = String(value || '').replace(/\s+/g, ' ').trim();
  if (text.length <= maxLength) return text;
  return `${text.slice(0, maxLength - 3).trimEnd()}...`;
}

export function hasStudyEvidence(node = {}) {
  return node.drill_status === 'primed'
    || node.drill_status === 'drilled'
    || node.drill_status === 'solidified'
    || node.drill_status === 'solid'
    || Boolean(node.gap_type);
}

export function SOURCE_INPUT_HTML(showClipboard) {
  return `
      <div class="overlay-tabs creation-source-tabs">
        <button class="overlay-tab active" data-tab="paste">Paste</button>
        <button class="overlay-tab" data-tab="url">URL</button>
        <button class="overlay-tab" data-tab="upload">Upload</button>
      </div>
      <div class="overlay-panel" data-panel="paste">
        <textarea class="overlay-textarea" placeholder="Paste source material here."></textarea>
        ${showClipboard ? '<div class="paste-actions"><button class="paste-clipboard-btn" type="button">Paste from clipboard</button></div>' : ''}
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
      <div class="overlay-footer">
        <button class="overlay-cancel">Cancel</button>
        <button class="overlay-extract" disabled>Extract</button>
      </div>
    `;
}

export function buildContentInputUI(container, { onSubmit, onCancel, showClipboard, readFile }) {
  let uploadedText = '';
  let uploadedFilename = '';
  let fetchedUrlText = '';
  let fetchedUrlTitle = '';
  let fetchedUrl = '';
  let activeTab = 'paste';

  container.innerHTML = SOURCE_INPUT_HTML(showClipboard);

  const tabs = container.querySelectorAll('.overlay-tab');
  const panels = container.querySelectorAll('.overlay-panel');
  const textarea = container.querySelector('.overlay-textarea');
  const dropzone = container.querySelector('.overlay-dropzone');
  const fileInput = container.querySelector('input[type="file"]');
  const feedback = container.querySelector('.overlay-file-feedback');
  const urlInput = container.querySelector('.overlay-url-input');
  const urlFeedback = container.querySelector('.overlay-url-feedback');
  const pasteClipBtn = container.querySelector('.paste-clipboard-btn');
  const cancelBtn = container.querySelector('.overlay-cancel');
  const submitBtn = container.querySelector('.overlay-extract');

  function hasContent() {
    if (activeTab === 'paste') return textarea.value.trim().length > 0;
    if (activeTab === 'url') {
      const rawUrl = urlInput.value.trim();
      return rawUrl.length > 0 && !isBlockedVideoUrl(rawUrl);
    }
    return uploadedText.length > 0;
  }
  function checkSubmitEnabled() {
    const blockedVideoUrl = activeTab === 'url' && isBlockedVideoUrl(urlInput.value.trim());
    submitBtn.disabled = !(hasContent() && !blockedVideoUrl);
    if (urlFeedback) {
      const rawUrl = urlInput.value.trim();
      urlFeedback.className = 'overlay-dropfeedback overlay-url-feedback';
      if (rawUrl && isBlockedVideoUrl(rawUrl)) {
        urlFeedback.classList.add('error');
        urlFeedback.textContent = 'Video links are not supported in this build. Paste notes or transcript text instead.';
      } else {
        urlFeedback.textContent = '';
      }
    }
  }

  tabs.forEach(tab => {
    tab.addEventListener('click', () => {
      activeTab = tab.dataset.tab;
      tabs.forEach(t => t.classList.toggle('active', t.dataset.tab === activeTab));
      panels.forEach(p => { p.style.display = p.dataset.panel === activeTab ? '' : 'none'; });
      checkSubmitEnabled();
    });
  });

  if (showClipboard && pasteClipBtn) {
    pasteClipBtn.addEventListener('click', () => {
      navigator.clipboard.readText().then(text => {
        textarea.value = text;
        textarea.focus();
        checkSubmitEnabled();
      }).catch(() => {
        textarea.focus();
        document.execCommand('paste');
      });
    });
  }

  textarea.addEventListener('input', checkSubmitEnabled);
  if (urlInput) {
    urlInput.addEventListener('input', () => {
      fetchedUrlText = '';
      fetchedUrlTitle = '';
      fetchedUrl = '';
      checkSubmitEnabled();
    });
    urlInput.addEventListener('keydown', e => {
      if (e.key === 'Enter' && !submitBtn.disabled) { e.preventDefault(); doSubmit(); }
    });
  }

  dropzone.addEventListener('click', () => fileInput.click());
  dropzone.addEventListener('dragover', e => { e.preventDefault(); dropzone.classList.add('dragover'); });
  dropzone.addEventListener('dragleave', () => dropzone.classList.remove('dragover'));
  dropzone.addEventListener('drop', e => {
    e.preventDefault();
    dropzone.classList.remove('dragover');
    if (e.dataTransfer.files[0]) processUpload(e.dataTransfer.files[0]);
  });
  fileInput.addEventListener('change', () => {
    if (fileInput.files[0]) processUpload(fileInput.files[0]);
  });

  function processUpload(file) {
    uploadedText = '';
    uploadedFilename = '';
    feedback.className = 'overlay-dropfeedback';
    feedback.textContent = '';
    submitBtn.disabled = true;
    readFile(
      file,
      (text, filename) => {
        uploadedText = text; uploadedFilename = filename;
        feedback.className = 'overlay-dropfeedback ok';
        feedback.textContent = `${filename} · ${text.length.toLocaleString()} chars`;
        checkSubmitEnabled();
      },
      (errMsg, fallbackText, filename) => {
        feedback.className = 'overlay-dropfeedback error';
        feedback.textContent = errMsg;
        uploadedText = '';
        uploadedFilename = '';
        checkSubmitEnabled();
      }
    );
  }

  cancelBtn.addEventListener('click', () => {
    onCancel();
  });

  submitBtn.addEventListener('mousedown', e => {
    e.preventDefault();
    doSubmit();
  });

  function doSubmit() {
    let text, type, filename, url;
    if (activeTab === 'paste') {
      text = textarea.value.trim();
      type = 'text';
      filename = null;
      url = null;
    } else if (activeTab === 'url') {
      url = urlInput.value.trim();
      text = fetchedUrlText || url;
      type = 'url';
      filename = fetchedUrlTitle || null;
    } else {
      text = uploadedText;
      type = 'file';
      filename = uploadedFilename;
      url = null;
    }
    onSubmit({
      text,
      type,
      filename,
      url,
    });
  }

  textarea.focus();
  checkSubmitEnabled();
  return {
    destroy() {
      container.innerHTML = '';
    }
  };
}
