/**
 * Feedback module — handles user feedback submission.
 * Captures cloud feedback and stores it in Supabase via /api/feedback.
 */
export const Feedback = (() => {
  const overlay = document.getElementById('feedback-overlay');
  const form = document.getElementById('feedback-form');
  const textarea = document.getElementById('feedback-message');
  const status = document.getElementById('feedback-status');
  const submitBtn = document.getElementById('feedback-submit');

  function show() {
    if (!overlay) return;
    overlay.hidden = false;
    textarea.value = '';
    status.textContent = '';
    status.className = 'modal-status';
    textarea.focus();
    // Close sidebar if open (mobile)
    if (window.App && typeof App.closeDrawer === 'function') {
      App.closeDrawer();
    }
  }

  function hide() {
    if (!overlay) return;
    overlay.hidden = true;
  }

  async function submit(event) {
    if (event) event.preventDefault();
    const message = textarea.value.trim();
    if (message.length < 10) {
      setStatus('Message must be at least 10 characters.', 'err');
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
        body: JSON.stringify({ message }),
      });

      if (!response.ok) {
        const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
        throw new Error(error.detail || `Server error: ${response.status}`);
      }

      setStatus('Thank you! Feedback captured.', 'ok');
      textarea.value = '';
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

  // Export to global scope for onclick handlers in HTML
  window.Feedback = { show, hide, submit };

  return { show, hide, submit };
})();
