import { createLoopServer } from "../lib/loop-server/http-server.mjs";

const loopServer = createLoopServer();

function expectedToken() {
  return (
    (process.env.SOCRATINK_LOOP_API_KEY || "").trim() ||
    (process.env.SESSION_COOKIE_KEY || "").trim()
  );
}

function requestToken(req) {
  const header = req.headers["x-socratink-internal-loop-token"];
  return Array.isArray(header) ? header[0] : header || "";
}

function upstreamPathFromRequest(req) {
  const originalUrl = new URL(req.url || "/", "http://internal");
  const queryPath = originalUrl.searchParams.get("path");
  if (queryPath) return `/${queryPath.replace(/^\/+/, "")}`;
  return originalUrl.pathname.replace(/^\/api\/internal-loop/, "") || "/";
}

export default function handler(req, res) {
  const expected = expectedToken();
  if (!expected || requestToken(req) !== expected) {
    res.statusCode = 401;
    res.setHeader("content-type", "application/json; charset=utf-8");
    res.end(JSON.stringify({ error: "unauthorized" }));
    return;
  }

  const originalUrl = new URL(req.url || "/", "http://internal");
  req.url = `${upstreamPathFromRequest(req)}${originalUrl.search}`;
  loopServer.emit("request", req, res);
}
