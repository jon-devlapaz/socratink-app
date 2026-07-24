import { eventBuilders } from "../event-facts.mjs";

function requiredText(value, code) {
  const text = String(value ?? "");
  if (!text.trim()) throw new Error(code);
  return text;
}

export async function handleSourceIntake({ events, prompt, ctx }) {
  if (ctx.sourceText === null) {
    const sourceText = requiredText(
      await prompt.ask("source", "Technical source: "),
      "source-required",
    );
    ctx.sourceText = sourceText;
    events.push(eventBuilders.sourceSubmitted({
      text: sourceText,
      at: ctx.now(),
    }));
  }

  if (ctx.explanationTarget === null) {
    const target = requiredText(
      await prompt.ask("target", "Explanation target: "),
      "target-required",
    );
    ctx.explanationTarget = target;
    events.push(eventBuilders.targetSubmitted({
      text: target,
      at: ctx.now(),
    }));
  }

  return {};
}
