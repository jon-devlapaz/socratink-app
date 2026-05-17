# Test-Driven Learning

> Founder mental model. This is an internal product analogy, not learner-facing
> UI language.

## The Short Version

socratink is test-driven learning.

In test-driven development, the failing test comes before the implementation.
The failure is not embarrassment; it is the signal that tells the engineer what
must be built.

In socratink, the cold attempt comes before the explanation. The imperfect
reconstruction is not a score; it is the signal that tells the system and the
learner what must be repaired.

## The Mapping

| Test-driven development | socratink learning loop |
| --- | --- |
| Write the failing test first. | Make a cold attempt before study appears. |
| Read the failure. | Identify the gap in the learner's reconstruction. |
| Implement the smallest fix. | Show targeted study scoped to that gap. |
| Run the test again. | Reconstruct the mechanism again after spacing. |
| Mark green only when the test passes. | Derive `solidified` only from spaced strong reconstruction. |

The important part is the order. TDD does not begin by writing implementation
and then inventing a test that passes. socratink does not begin by showing an
AI explanation and then asking the learner to recognize it.

The attempt creates the thing to repair.

## Why This Matters

Most education software treats content exposure as the main event. It shows the
learner a summary, quiz, flashcard, or generated lesson, then measures whether
the learner can recognize what was just shown.

socratink reverses that order.

The learner first externalizes their current model. That model may be incomplete,
wrong, vague, or awkwardly phrased. The product should preserve it anyway,
because the learner's own reconstruction is the only honest starting point for
repair.

This protects three product truths:

- **Generation before recognition:** the learner must try before the answer
  appears.
- **Repair before proof:** study can help repair an attempt, but reading is not
  evidence of durable learning.
- **Spacing before solidification:** a later reconstruction is the proof event,
  not a fluent immediate retry.

## What Counts As Green

In TDD, a passing test is specific. It is not a feeling that the implementation
"seems right."

In socratink, `solidified` is also specific. It means socratink has a strong
spaced reconstruction on record. It does not mean the learner has mastered the
concept forever, and it does not mean the learner's mind has been diagnosed.

`solidified` is evidence language, not ability language.

## What This Analogy Forbids

This model is useful because it exposes category mistakes.

- Do not let the learner read the implementation before writing the test.
  In product terms: no explanatory study content before the cold attempt.
- Do not turn the first failure into shame.
  In product terms: no quiz, score, rank, or diagnostic label during cold
  attempt.
- Do not mark the task green because the learner watched the fix.
  In product terms: targeted study does not create mastery or completion.
- Do not treat a same-session echo as durable proof.
  In product terms: immediate repetition is not `solidified` evidence.
- Do not replace the learner's failing test with AI-generated prose.
  In product terms: the Library shows learner reconstruction, not an AI summary.

## Where The Analogy Breaks

The analogy should not become literal UI copy.

Learners should not see a developer metaphor unless the surface is explicitly
for technical users. The product should still sound like a quiet study room:
"What can you reconstruct?", "Compare with notes", "Repair the missing link",
and "Ready to reconstruct again."

The analogy is for product judgment. It helps the founder and agents decide
whether a feature strengthens the learning loop or drifts toward content
theater.

## Product Heuristic

When evaluating a new feature, ask:

> Does this create, repair, or retest learner-generated evidence?

If the answer is no, the feature may still be useful, but it is not part of the
core moat.

The moat is not AI-generated study material. The moat is the disciplined pacing
around:

```
cold attempt -> repair -> spacing -> proof
```

