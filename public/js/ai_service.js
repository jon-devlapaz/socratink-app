// ai_service.js
// Calls the local Python backend for AI extraction.

export async function generateKnowledgeMap(rawText, onProgress) {
  if (onProgress) onProgress('Drafting map...');
  const apiKey = localStorage.getItem('gemini_key') || undefined;
  const response = await fetch('/api/extract', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ text: rawText, api_key: apiKey }),
  });
  if (!response.ok) {
    const err = await response.text().catch(() => '');
    throw new Error(`Server error ${response.status}: ${err}`);
  }
  const data = await response.json();
  return data.knowledge_map;
}
