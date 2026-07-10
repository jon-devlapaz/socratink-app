import { AsyncLocalStorage } from "node:async_hooks";

// eslint-disable-next-line no-control-regex -- strip terminal color codes
const ANSI_RE = /\x1b\[[0-9;]*m/g;
const captureContext = new AsyncLocalStorage();
const originals = {
  log: console.log.bind(console),
  info: console.info.bind(console),
  warn: console.warn.bind(console),
  error: console.error.bind(console),
};
let installed = false;

export function stripAnsi(text) {
  return String(text).replace(ANSI_RE, "");
}

export function withConsoleCapture(sink, operation) {
  installConsoleCapture();
  return captureContext.run(sink, operation);
}

function installConsoleCapture() {
  if (installed) return;
  installed = true;
  for (const level of Object.keys(originals)) {
    console[level] = (...args) => {
      const sink = captureContext.getStore();
      if (sink) sink.push({ level, text: formatLine(args) });
      originals[level](...args);
    };
  }
}

function formatLine(args) {
  return stripAnsi(
    args
      .map((arg) => (typeof arg === "string" ? arg : JSON.stringify(arg)))
      .join(" "),
  );
}
