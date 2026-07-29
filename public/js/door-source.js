import { AudioFX } from './audio.js?v=4';

export const FILE_SOURCE_TOO_LARGE =
  'This file contains too much text for one session. Choose a shorter file or paste a focused passage.';
export const PASTED_SOURCE_TOO_LARGE =
  'This source contains too much text for one session. Paste a shorter, more focused passage.';

export function readSourceFile(file, onSuccess, onError) {
  const ext = file.name.split('.').pop().toLowerCase();
  if (!['txt', 'md', 'pdf'].includes(ext)) return onError('Unsupported file type. Use .txt, .md, or .pdf.');
  if (file.size > 2 * 1024 * 1024) return onError('File too large. Maximum size is 2MB.');
  if (ext === 'pdf') {
    if (typeof pdfjsLib === 'undefined') return onError('PDF engine failed to load. Please check your connection.');
    pdfjsLib.GlobalWorkerOptions.workerSrc = 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js';
    const reader = new FileReader();
    reader.onerror = () => onError('This PDF could not be read. Choose another file.');
    reader.onload = async (event) => {
      try {
        const pdf = await pdfjsLib.getDocument({ data: new Uint8Array(event.target.result) }).promise;
        let text = '';
        for (let pageNumber = 1; pageNumber <= pdf.numPages; pageNumber += 1) {
          const page = await pdf.getPage(pageNumber);
          const content = await page.getTextContent();
          text += `${content.items.map((item) => item.str).join(' ')}\n`;
        }
        if (text.trim().length < 50) throw new Error('Scanned image or empty PDF.');
        onSuccess(text.trim(), file.name);
      } catch {
        onError('Could not natively extract text from this PDF. Try pasting the content manually.');
      }
    };
    return reader.readAsArrayBuffer(file);
  }
  const reader = new FileReader();
  reader.onerror = () => onError('This file could not be read. Choose another file.');
  reader.onload = (event) => {
    const text = String(event.target.result || '').trim();
    if (!text) return onError('This file does not contain readable text. Choose another file.');
    onSuccess(text, file.name);
  };
  reader.readAsText(file);
}

export function createDoorSourceController({ sourceFits, normalizationVersion, onChange }) {
  let fileBusy = false;
  let fileReadName = '';
  let fileSource = null;
  let intakeKey = null;
  let readGeneration = 0;
  let step = 'source';
  let getBusy = () => false;
  let getSession = () => null;

  const stateChanged = () => onChange?.();
  const sourceText = () => fileSource?.text || document.getElementById('hero-single-input-field')?.value || '';
  const sourceSummary = (session = getSession()) => {
    if (fileSource?.filename) return fileSource.filename;
    const text = sourceText().trim().replace(/\s+/g, ' ').slice(0, 240);
    if (text) return text;
    return session?.awaiting?.key === 'target' ? 'Source saved' : '';
  };
  const descriptor = () => fileSource ? {
    normalizationVersion,
    extractionVersion: fileSource.extractionVersion,
    parserVersion: fileSource.parserVersion,
    sourceKind: fileSource.sourceKind,
    provenance: { ...fileSource.provenance },
  } : {
    normalizationVersion,
    extractionVersion: 'browser-paste-v1',
    parserVersion: 'plain-text-v1',
    sourceKind: 'paste',
    provenance: { intake_surface: 'promoted-alpha-file-intake', input_method: 'paste' },
  };
  const sourceReady = (session = getSession()) => {
    if (session?.awaiting?.key === 'target') return true;
    return !fileBusy && Boolean(sourceText().trim()) && sourceFits(sourceText());
  };
  const ready = (session = getSession()) => {
    const target = document.getElementById('hero-cold-guess-field');
    return Boolean((target?.value || '').trim()) && sourceReady(session);
  };
  const setCurrentTrack = (sourceTrack, targetTrack, targetStep) => {
    sourceTrack?.removeAttribute?.('aria-current');
    targetTrack?.removeAttribute?.('aria-current');
    (targetStep ? targetTrack : sourceTrack)?.setAttribute?.('aria-current', 'step');
  };
  const focusCurrent = () => {
    const session = getSession();
    if (step === 'target' || session?.awaiting?.key === 'target') {
      document.getElementById('hero-cold-guess-field')?.focus();
      return;
    }
    const focusTarget = fileSource
      ? document.getElementById('hero-source-file-action')
      : document.getElementById('hero-single-input-field');
    focusTarget?.focus();
  };
  const render = (waitingForTarget = false, busy = false) => {
    const previousStep = step;
    if (waitingForTarget) step = 'target';
    const targetStep = step === 'target';
    const session = getSession();
    const sourceLocked = session?.awaiting?.key === 'target';
    const form = document.getElementById('hero-single-input');
    const sourceStep = document.getElementById('hero-source-step');
    const targetStepEl = document.getElementById('hero-target-step');
    const sourceTrack = document.getElementById('hero-source-track');
    const targetTrack = document.getElementById('hero-target-track');
    const sourceField = document.getElementById('hero-single-input-field');
    const fileInput = document.getElementById('hero-source-file-input');
    const fileValue = document.getElementById('hero-source-file-value');
    const fileAction = document.getElementById('hero-source-file-action');
    const fileRemove = document.getElementById('hero-source-file-remove');
    const sourceNext = document.getElementById('hero-source-next');
    const sourceRevise = document.getElementById('hero-source-revise');
    const summary = document.getElementById('hero-source-summary');
    const targetField = document.getElementById('hero-cold-guess-field');
    const announcement = document.getElementById('hero-step-announcement');
    const hasFile = Boolean(fileSource);
    const unavailable = busy || fileBusy;
    if (form?.dataset) form.dataset.step = step;
    if (sourceStep) sourceStep.hidden = targetStep;
    if (targetStepEl) targetStepEl.hidden = !targetStep;
    setCurrentTrack(sourceTrack, targetTrack, targetStep);
    if (sourceField) {
      sourceField.hidden = hasFile;
      sourceField.disabled = unavailable || sourceLocked;
    }
    if (fileInput) fileInput.disabled = unavailable || sourceLocked;
    if (fileValue) {
      fileValue.hidden = !(fileBusy || hasFile);
      fileValue.textContent = fileBusy ? `Reading ${fileReadName}…` : (fileSource?.filename || '');
    }
    if (fileAction) {
      const actionLabel = hasFile ? `Replace ${fileSource.filename}` : 'Attach source file';
      fileAction.disabled = unavailable || sourceLocked;
      fileAction.setAttribute?.('aria-label', actionLabel);
      fileAction.setAttribute?.('title', actionLabel);
    }
    if (fileRemove) {
      fileRemove.hidden = !hasFile;
      fileRemove.disabled = unavailable || sourceLocked;
      fileRemove.setAttribute?.('aria-label', hasFile ? `Remove ${fileSource.filename}` : 'Remove attached file');
    }
    if (sourceNext) sourceNext.disabled = unavailable || !sourceReady(session);
    if (sourceRevise) sourceRevise.disabled = unavailable || sourceLocked;
    if (summary) summary.textContent = sourceSummary(session);
    if (targetField) targetField.disabled = busy;
    if (announcement && previousStep !== step) announcement.textContent = targetStep ? 'Target' : 'Source';
  };
  const setError = (message) => {
    const error = document.getElementById('hero-source-error');
    if (error) error.textContent = message;
  };
  const showSource = () => {
    if (getSession()?.awaiting?.key === 'target') return false;
    step = 'source';
    render(false, getBusy());
    requestAnimationFrame(() => focusCurrent());
    return true;
  };
  const showTarget = () => {
    if (!sourceReady(getSession())) return false;
    step = 'target';
    render(false, getBusy());
    requestAnimationFrame(() => focusCurrent());
    return true;
  };
  const init = ({ isBusy = () => false, session = () => null } = {}) => {
    getBusy = isBusy;
    getSession = session;
    const field = document.getElementById('hero-single-input-field');
    const guess = document.getElementById('hero-cold-guess-field');
    if (!(field instanceof HTMLTextAreaElement)) return;
    const form = document.getElementById('hero-single-input');
    const fileInput = document.getElementById('hero-source-file-input');
    const onFileAction = () => {
      AudioFX.playFocusTap();
      fileInput?.click();
    };
    const onFileRemove = () => {
      AudioFX.playFocusTap();
      fileSource = null;
      intakeKey = null;
      setError('');
      render(false, getBusy());
      stateChanged();
      requestAnimationFrame(() => field.focus());
    };
    const onSourceInput = () => {
      intakeKey = null;
      setError(field.value && !sourceFits(field.value) ? PASTED_SOURCE_TOO_LARGE : '');
      stateChanged();
    };
    const onFileChange = () => {
      const file = fileInput?.files?.[0];
      if (fileInput) fileInput.value = '';
      if (file) beginFileRead(file);
    };
    document.getElementById('hero-source-file-action')?.addEventListener('click', onFileAction);
    document.getElementById('hero-source-file-remove')?.addEventListener('click', onFileRemove);
    document.getElementById('hero-source-next')?.addEventListener('click', showTarget);
    document.getElementById('hero-source-revise')?.addEventListener('click', showSource);
    field.addEventListener('input', onSourceInput);
    guess?.addEventListener('input', stateChanged);
    fileInput?.addEventListener('change', onFileChange);
    const printable = (event) => !event.metaKey && !event.ctrlKey && !event.altKey && !event.repeat && (event.key.length === 1 || event.key === 'Backspace' || event.key === 'Enter');
    [field, guess].forEach((element) => element?.addEventListener('focus', () => AudioFX.playFocusTap()));
    field.addEventListener('keydown', (event) => {
      if (printable(event)) AudioFX.playKeyClick();
      if ((event.metaKey || event.ctrlKey) && event.key === 'Enter') {
        event.preventDefault();
        showTarget();
      }
    });
    guess?.addEventListener('keydown', (event) => {
      if (printable(event)) AudioFX.playKeyClick();
      if ((event.metaKey || event.ctrlKey) && event.key === 'Enter' && ready(getSession())) {
        event.preventDefault();
        form?.requestSubmit?.();
      }
    });
    render(false, getBusy());
    stateChanged();
  };
  function beginFileRead(file) {
    const generation = ++readGeneration;
    intakeKey = null;
    fileBusy = true;
    fileReadName = file.name;
    setError('');
    render(false, getBusy());
    stateChanged();
    readSourceFile(
      file,
      (text, filename) => completeFileRead(generation, file, text, filename),
      (message) => failFileRead(generation, message),
    );
  }
  function completeFileRead(generation, file, text, filename) {
    if (generation !== readGeneration) return;
    const extracted = String(text || '').trim();
    fileBusy = false;
    fileReadName = '';
    if (!sourceFits(extracted)) {
      setError(FILE_SOURCE_TOO_LARGE);
    } else {
      const sourceKind = file.name.split('.').pop().toLowerCase();
      const pdf = sourceKind === 'pdf';
      fileSource = {
        text: extracted,
        filename: String(filename || file.name),
        sourceKind,
        extractionVersion: pdf ? 'pdfjs-3.11.174' : 'browser-file-reader-v1',
        parserVersion: pdf ? 'pdfjs-3.11.174' : 'plain-text-v1',
        provenance: { intake_surface: 'promoted-alpha-file-intake', input_method: 'file' },
      };
      setError('');
    }
    render(false, getBusy());
    stateChanged();
    if (fileSource?.text === extracted) {
      requestAnimationFrame(() => document.getElementById('hero-source-next')?.focus());
    }
  }
  function failFileRead(generation, message) {
    if (generation !== readGeneration) return;
    fileBusy = false;
    fileReadName = '';
    setError(message || 'This file could not be read. Choose another file.');
    render(false, getBusy());
    stateChanged();
  }
  return {
    init, render, ready, sourceReady, sourceText, sourceSummary, descriptor,
    showSource, showTarget, focusCurrent,
    payload: (idempotencyKey) => ({ idempotencyKey, normalizedText: sourceText(), ...descriptor() }),
    get intakeKey() { return intakeKey; }, set intakeKey(value) { intakeKey = value; },
    get fileSource() { return fileSource; }, get fileBusy() { return fileBusy; },
    get step() { return step; },
    clear() {
      readGeneration += 1;
      fileBusy = false;
      fileReadName = '';
      fileSource = null;
      intakeKey = null;
      step = 'source';
      const input = document.getElementById('hero-source-file-input');
      if (input) input.value = '';
      setError('');
      render(false, false);
      stateChanged();
    },
  };
}
