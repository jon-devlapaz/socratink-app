import { eventBuilders } from "../event-facts.mjs";

export async function handleInitialReconstruction({ events, prompt, ctx }) {
  if (!ctx.sourceText || !ctx.explanationTarget) {
    throw new Error("reconstruction-context-required");
  }

  const text = await prompt.ask(
    "initial_reconstruction",
    "Explain it from memory: ",
  );
  if (!String(text).trim()) throw new Error("reconstruction-required");

  ctx.initialReconstruction = text;
  const at = ctx.now();
  ctx.initialReconstructionAt = at;
  events.push(eventBuilders.initialReconstructionSubmitted({ text, at }));
  console.log("Explanation saved exactly as submitted.");
  return {};
}
