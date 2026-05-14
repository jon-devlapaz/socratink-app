export function formatTimerSeconds(timeLeft) {
  const h = Math.floor(timeLeft / 3600).toString().padStart(2, '0');
  const m = Math.floor((timeLeft % 3600) / 60).toString().padStart(2, '0');
  const s = (timeLeft % 60).toString().padStart(2, '0');
  return `${h}:${m}:${s}`;
}

export function createCountdownTimer({
  timerDisplay,
  onComplete,
  initialSeconds = 24 * 60 * 60,
  setIntervalRef = globalThis.setInterval,
  clearIntervalRef = globalThis.clearInterval,
} = {}) {
  let timerInterval = null;
  let timeLeft = initialSeconds;

  function updateDisplay() {
    timerDisplay.textContent = formatTimerSeconds(timeLeft);
  }

  function stop() {
    clearIntervalRef(timerInterval);
    timerInterval = null;
  }

  function start(seconds = timeLeft) {
    timeLeft = Math.max(0, Number(seconds) || 0);
    stop();
    updateDisplay();
    if (timeLeft === 0) {
      if (typeof onComplete === 'function') onComplete();
      return;
    }
    timerInterval = setIntervalRef(() => {
      timeLeft = Math.max(0, timeLeft - 1);
      updateDisplay();
      if (timeLeft === 0) {
        stop();
        if (typeof onComplete === 'function') onComplete();
      }
    }, 1000);
  }

  function fastForward(seconds = 3) {
    timeLeft = seconds;
  }

  function getTimeLeft() {
    return timeLeft;
  }

  return {
    fastForward,
    getTimeLeft,
    start,
    stop,
    updateDisplay,
  };
}
