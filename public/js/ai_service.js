// ai_service.js
// Calls the local Python backend for AI extraction.

export async function generateKnowledgeMap(rawText, onProgress) {
  if (onProgress) onProgress("Drafting map...");
  const apiKey = localStorage.getItem("gemini_key") || undefined;
  const response = await fetch("/api/extract", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text: rawText, api_key: apiKey }),
  });
  if (!response.ok) {
    const err = await response.text().catch(() => "");
    throw new Error(`Server error ${response.status}: ${err}`);
  }
  const data = await response.json();
  return data.knowledge_map;
}

/**
 * Conversational concept-create submit. Posts the spec §5.3 payload shape
 * and returns the parsed `provisional_map` (no source) or `knowledge_map`
 * (source attached). On 422, throws an Error with `.status` and `.body`
 * (the parsed `{error, message}` payload) so the caller can render the
 * message inline.
 *
 * @param {{ name: string, startingSketch: string,
 *           source: null | { type: 'text'|'url'|'file', text?: string, url?: string, filename?: string },
 *           apiKey?: string }} args
 * @returns {Promise<{ provisional_map?: object, knowledge_map?: object }>}
 */
export async function submitConceptCreate({ name, startingSketch, source, apiKey }) {
  const body = {
    name,
    starting_sketch: startingSketch,
    source,
    api_key: apiKey,
  };
  const response = await fetch("/api/extract", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (response.status === 422) {
    const payload = await response.json().catch(() => ({}));
    const detail = payload.detail || payload || {};
    const err = new Error(detail.message || "Submission rejected.");
    err.status = 422;
    err.body = detail;
    throw err;
  }
  if (!response.ok) {
    const txt = await response.text().catch(() => "");
    const err = new Error(`Server error ${response.status}: ${txt}`);
    err.status = response.status;
    throw err;
  }
  return response.json();
}
