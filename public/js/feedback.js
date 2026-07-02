/**
 * Feedback module — handles user feedback submission.
 * Captures cloud feedback and stores it in Supabase via /api/feedback.
 */
export const Feedback = (() => {
  const overlay = document.getElementById('feedback-overlay');
  const form = document.getElementById('feedback-form');
  const title = document.getElementById('feedback-title');
  const textarea = document.getElementById('feedback-message');
  const ratingInput = document.getElementById('feedback-ux-rating');
  const description = document.getElementById('feedback-desc');
  const status = document.getElementById('feedback-status');
  const submitBtn = document.getElementById('feedback-submit');
  const defaultTitle = title?.textContent || 'Feedback';
  const defaultDescription = description?.textContent || '';
  const defaultSubmitLabel = submitBtn?.textContent || 'Send Feedback';
  let opener = null;
  let currentMoment = '';

  function promptForMoment(moment) {
    if (moment === 'compare notes') return 'How did comparing your answer to the notes feel?';
    if (moment === 'repair checked') return 'How did checking your repair feel?';
    return `How did the ${moment} step feel?`;
  }

  function show(options = {}) {
    if (!overlay) return;
    opener = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    overlay.hidden = false;
    textarea.value = '';
    if (ratingInput) ratingInput.value = '';
    currentMoment = String(options?.moment || '').trim();
    if (title) title.textContent = currentMoment ? 'Rate this moment' : defaultTitle;
    if (description) {
      description.textContent = currentMoment
        ? `${promptForMoment(currentMoment)} A 9 or 10 means the UX feels ready for a new customer.`
        : defaultDescription;
    }
    status.textContent = '';
    status.className = 'modal-status';
    submitBtn.disabled = false;
    submitBtn.textContent = currentMoment ? 'Send Rating' : defaultSubmitLabel;
    const focusTarget = options?.focus === 'rating' && ratingInput ? ratingInput : textarea;
    focusTarget.focus();
  }

  function hide() {
    if (!overlay) return;
    overlay.hidden = true;
    if (opener && document.contains(opener) && typeof opener.focus === 'function') {
      opener.focus({ preventScroll: true });
    }
  }

  async function submit(event) {
    if (event) event.preventDefault();
    const message = textarea.value.trim();
    const rating = ratingInput ? Number.parseInt(ratingInput.value, 10) : NaN;
    if (currentMoment && !ratingInput?.value) {
      setStatus('Please rate this moment 1-10.', 'err');
      ratingInput?.focus();
      return false;
    }
    if (ratingInput?.value && (!Number.isInteger(rating) || rating < 1 || rating > 10)) {
      setStatus('UX feel must be 1-10.', 'err');
      ratingInput.focus();
      return false;
    }
    if (!Number.isInteger(rating) && message.length < 10) {
      setStatus('Message must be at least 10 characters.', 'err');
      return false;
    }
    const payloadMessage = Number.isInteger(rating)
      ? [`UX feel: ${rating}/10`, currentMoment ? `UX moment: ${currentMoment}` : '', message].filter(Boolean).join('\n')
      : message;
    if (payloadMessage.length > 1000) {
      setStatus('Feedback must be 1000 characters or fewer after rating details.', 'err');
      textarea.focus();
      return false;
    }

    submitBtn.disabled = true;
    setStatus('Sending...', '');

    try {
      const response = await fetch('/api/feedback', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ message: payloadMessage }),
      });

      if (!response.ok) {
        const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
        throw new Error(error.detail || `Server error: ${response.status}`);
      }

      setStatus('Thank you! Feedback captured.', 'ok');
      textarea.value = '';
      if (ratingInput) ratingInput.value = '';
      currentMoment = '';
      setTimeout(hide, 2000);
    } catch (err) {
      console.error('Feedback submission failed:', err);
      setStatus(err.message, 'err');
      submitBtn.disabled = false;
    }

    return false;
  }

  function setStatus(text, kind) {
    if (!status) return;
    status.textContent = text;
    status.className = 'modal-status ' + (kind || '');
  }

  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape' && overlay && !overlay.hidden) {
      hide();
    }
  });

  // Export to global scope for onclick handlers in HTML
  window.Feedback = { show, hide, submit };

  return { show, hide, submit };
})();
