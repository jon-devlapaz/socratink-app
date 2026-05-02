const KEY = import.meta.env.VITE_GEMINI_API_KEY;
const MODEL = 'gemini-2.5-flash';
const ENDPOINT = `https://generativelanguage.googleapis.com/v1beta/models/${MODEL}:generateContent`;

export const hasGeminiKey = () => !!KEY;

export async function chat({ history, systemInstruction, message }) {
  if (!KEY) throw new Error('VITE_GEMINI_API_KEY not set');

  const contents = [
    ...history.map((m) => ({ role: m.role, parts: [{ text: m.text }] })),
    { role: 'user', parts: [{ text: message }] },
  ];

  const body = {
    contents,
    systemInstruction: { parts: [{ text: systemInstruction }] },
    generationConfig: {
      temperature: 0.6,
      // Disable Gemini 2.5's default thinking — keep chat snappy. Thinking
      // tokens count against output and add latency we don't need for
      // single-turn lookups against a small JSON graph.
      thinkingConfig: { thinkingBudget: 0 },
    },
  };

  const res = await fetch(`${ENDPOINT}?key=${encodeURIComponent(KEY)}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });

  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Gemini ${res.status}: ${text.slice(0, 400)}`);
  }

  const data = await res.json();

  if (data.promptFeedback?.blockReason) {
    throw new Error(`Prompt blocked: ${data.promptFeedback.blockReason}`);
  }

  const cand = data.candidates?.[0];
  if (!cand) throw new Error('Gemini returned no candidates');

  if (cand.finishReason === 'SAFETY') {
    throw new Error('Response blocked by safety filter');
  }

  const text = (cand.content?.parts || [])
    .map((p) => p.text || '')
    .join('')
    .trim();

  if (!text) {
    if (cand.finishReason === 'MAX_TOKENS') {
      throw new Error('Response truncated (MAX_TOKENS)');
    }
    throw new Error(`Empty response (finishReason=${cand.finishReason || 'unknown'})`);
  }

  return text;
}
