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

  const stateChanged = () => onChange?.();
  const sourceText = () => fileSource?.text || document.getElementById('hero-single-input-field')?.value || '';
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
  const render = (waitingForTarget = false, busy = false) => {
    const sourceField = document.getElementById('hero-single-input-field');
    const sourceLabel = document.querySelector('label[for="hero-single-input-field"]');
    const fileState = document.getElementById('hero-source-file-state');
    const fileInput = document.getElementById('hero-source-file-input');
    const fileValue = document.getElementById('hero-source-file-value');
    const fileAction = document.getElementById('hero-source-file-action');
    const fileRemove = document.getElementById('hero-source-file-remove');
    const hasFile = Boolean(fileSource);
    const unavailable = busy || fileBusy;
    if (sourceField) sourceField.hidden = waitingForTarget || hasFile;
    if (sourceLabel) sourceLabel.hidden = waitingForTarget || hasFile;
    if (fileState) fileState.hidden = waitingForTarget;
    if (fileInput) fileInput.disabled = unavailable;
    if (fileValue) fileValue.textContent = fileBusy ? `Reading ${fileReadName}…` : (fileSource?.filename || 'TXT, MD, or PDF · up to 2MB');
    if (fileAction) {
      fileAction.textContent = hasFile ? 'Replace' : 'Attach';
      fileAction.disabled = unavailable;
      fileAction.setAttribute('aria-label', hasFile ? `Replace ${fileSource.filename}` : 'Attach a technical file');
    }
    if (fileRemove) {
      fileRemove.hidden = !hasFile;
      fileRemove.disabled = unavailable;
      fileRemove.setAttribute('aria-label', hasFile ? `Remove ${fileSource.filename}` : 'Remove attached file');
    }
  };
  const setError = (message) => {
    const error = document.getElementById('hero-source-error');
    if (error) error.textContent = message;
  };
  const ready = (session) => {
    const guess = document.getElementById('hero-cold-guess-field');
    if (!guess || !(guess.value || '').trim()) return false;
    if (session?.awaiting?.key === 'target') return true;
    return !fileBusy && Boolean(sourceText().trim()) && sourceFits(sourceText());
  };
  const init = ({ isBusy = () => false, session = () => null } = {}) => {
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
      render(false, isBusy());
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
      if (file) beginFileRead(file, { isBusy, guess });
    };
    document.getElementById('hero-source-file-action')?.addEventListener('click', onFileAction);
    document.getElementById('hero-source-file-remove')?.addEventListener('click', onFileRemove);
    field.addEventListener('input', onSourceInput);
    guess?.addEventListener('input', stateChanged);
    fileInput?.addEventListener('change', onFileChange);
    const printable = (event) => !event.metaKey && !event.ctrlKey && !event.altKey && !event.repeat && (event.key.length === 1 || event.key === 'Backspace' || event.key === 'Enter');
    [field, guess].forEach((element) => {
      element?.addEventListener('focus', () => AudioFX.playFocusTap());
      element?.addEventListener('keydown', (event) => {
        if (printable(event)) AudioFX.playKeyClick();
        if ((event.metaKey || event.ctrlKey) && event.key === 'Enter' && ready(session())) {
          event.preventDefault();
          form?.requestSubmit?.();
        }
      });
    });
    render(false, isBusy()); stateChanged();
  };
  function beginFileRead(file, { isBusy, guess }) {
    const generation = ++readGeneration;
    intakeKey = null;
    fileBusy = true;
    fileReadName = file.name;
    setError('');
    render(false, isBusy());
    stateChanged();
    readSourceFile(file, (text, filename) => completeFileRead(generation, file, text, filename, { isBusy, guess }),
      (message) => failFileRead(generation, message, { isBusy }));
  }
  function completeFileRead(generation, file, text, filename, { isBusy, guess }) {
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
    render(false, isBusy());
    stateChanged();
    if (fileSource?.text === extracted) requestAnimationFrame(() => guess?.focus());
  }
  function failFileRead(generation, message, { isBusy }) {
    if (generation !== readGeneration) return;
    fileBusy = false;
    fileReadName = '';
    setError(message || 'This file could not be read. Choose another file.');
    render(false, isBusy());
    stateChanged();
  }
  return {
    init, render, ready, sourceText, descriptor,
    payload: (idempotencyKey) => ({ idempotencyKey, normalizedText: sourceText(), ...descriptor() }),
    get intakeKey() { return intakeKey; }, set intakeKey(value) { intakeKey = value; },
    get fileSource() { return fileSource; }, get fileBusy() { return fileBusy; },
    clear() {
      readGeneration += 1;
      fileBusy = false;
      fileReadName = '';
      fileSource = null;
      intakeKey = null;
      const input = document.getElementById('hero-source-file-input');
      if (input) input.value = '';
      setError('');
      render(false, false);
      stateChanged();
    },
  };
}
