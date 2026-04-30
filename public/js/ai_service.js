// ai_service.js
// Calls the local Python backend for AI extraction.

export async function generateKnowledgeMap(rawText, optionsOrProgress) {
  const onProgress = typeof optionsOrProgress === 'function'
    ? optionsOrProgress
    : optionsOrProgress?.onProgress;
  const startingMap = typeof optionsOrProgress === 'object'
    ? optionsOrProgress?.startingMap
    : null;
  if (onProgress) onProgress('Drafting map...');
  const apiKey = localStorage.getItem('gemini_key') || undefined;
  const body = { text: rawText, api_key: apiKey };
  if (startingMap?.global_context) {
    body.starting_map = {
      global_context: startingMap.global_context,
      ...(startingMap.fuzzy_area ? { fuzzy_area: startingMap.fuzzy_area } : {}),
    };
  }
  const response = await fetch('/api/extract', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!response.ok) {
    const err = await response.text().catch(() => '');
    throw new Error(`Server error ${response.status}: ${err}`);
  }
  const data = await response.json();
  return data.knowledge_map;
}
