---
name: llm-council
description: Convene a council that answers a hard question from five independent lenses, blind-reviews and ranks the answers, then synthesizes one vetted recommendation. One model, five lenses, pure reasoning — no tools, no code, no other models. Trigger on "/llm-council", "convene the council", "run this through the council", "get a multi-angle / second opinion", "stress-test this", "don't just agree with me", "argue both sides and tell me who's right", "is this actually a good idea". Do NOT use this skill if the user specifically asks for real different models, cross-vendor, diverse, or Ollama — use llm-council-diverse for that instead.
status: published
---

## When to Use
Trigger whenever the user mentions:
- "/llm-council"
- "convene the council"
- "run this through the council"
- "get a multi-angle / second opinion"
- "stress-test this"
- "don't just agree with me"
- "argue both sides and tell me who's right"
- "is this actually a good idea"
- Any moment a decision needs real pressure-testing rather than automatic agreement.

If the user's request explicitly says "diverse", "cross-vendor", "different models", "real
models", or "use ollama" — stop, this is the wrong skill. Use `llm-council-diverse` instead.

## Procedure

There is no sub-agent dispatch tool on this platform and no way to spawn a second model
mid-conversation. You are the entire council. Diversity comes from genuinely committing to
five different lenses, not from five different models — this matches how even the original
version of this skill worked by default: same model, five times, different lenses.

Write or run no code for this. The procedure below is the entire skill.

The question is whatever the user passed. If it's vague, ask one clarifying question first —
a sharp question is worth more than five answers to a fuzzy one.

### Stage 1 — Five independent answers
Write a direct, well-reasoned answer from each lens below, one at a time, in this response.
Treat each as a genuinely separate attempt: state that lens's key assumption and its
strongest self-objection. Once a lens's answer is written, do not revise it to match a later
one — real independence means the Red-teamer doesn't get softened just because the Pragmatist
already landed somewhere comfortable.

| Member | Lens (what to prioritize) |
|---|---|
| Pragmatist | What actually works under real constraints. Bias to action and the concrete next move. |
| Red-teamer | Attack the premise. Where does this fail? Is the question itself wrong or missing something? |
| Domain rigorist | Technical correctness and precision. Name the real tradeoffs exactly; no hand-waving. |
| First-principles | Ignore convention and best practice. Reason up from fundamentals; question defaults. |
| Generalist | Breadth. Connect angles, weigh the whole picture, answer plainly. |

For each: be specific and concise, no preamble, no hedging. Return only that lens's answer.

### Stage 2 — Blind review + ranking
Label the five answers `Response A` through `Response E`. Now evaluate them the way a neutral
judge would — not which one you (as author) like best, but which is strongest on accuracy and
insight alone, ignoring style or length. Give brief notes on each, then a final ranking best to
worst. If two or more lenses ended up saying nearly the same thing with no real tension, that's
usually a sign the adversarial lenses (Red-teamer, First-principles) weren't pushed hard enough
— go back and sharpen them before ranking, rather than ranking five answers that don't actually
disagree about anything.

### Stage 3 — Chairman synthesis
Now synthesize. Don't just promote the #1-ranked answer to be the final one, and don't drift
back toward whatever the user's question implied they wanted to hear.
- Build the final answer from the strongest reasoning across all five, grafting good points
  even from lower-ranked answers.
- Where the lenses genuinely split, say so and take a position — don't average the
  disagreement into mush.
- If the Red-teamer (or anyone) showed the question's premise is wrong, that leads. The
  council exists to push back, not rubber-stamp.

## Output (respect the anti-fluff rules)
Lead with the answer. Keep the council note tight.

1. **The answer** — the synthesized recommendation, stated plainly and directly.
2. **Council notes** — 3–5 lines max: where the lenses agreed, the one real disagreement (and
   which side you took, why), the ranking, anything you overrode and why.

Don't dump all five full Stage-1 answers by default. If the user asks to "see each member" or
"show the work," show the per-lens answers and the review then.

## Pitfalls
- Writing or running any code for this skill. There is nothing to execute — the procedure
  above is the entire skill.
- Claiming "five different models" answered. Be honest in the council notes that this is one
  model reasoning from five lenses — that's also how the original skill's default mode worked.
- Letting all five lenses converge to the same answer with no real tension. If that happens,
  it means the adversarial lenses weren't actually committed to — rewrite them, don't just
  rank a homogeneous set.
- Treating a vague question as answerable without checking first. One clarifying question
  beats five confident answers to the wrong question.
- Running this skill when the user actually asked for diverse/cross-vendor/real models. Use
  `llm-council-diverse` for that instead.

## Verification
- The response contains five visibly distinct paragraphs under five different lens labels —
  not one merged answer wearing five headers.
- Stage 2 contains an actual ranking with real differentiation, not uniform praise.
- Stage 3 names a genuine disagreement and takes a side on it, rather than claiming unanimous
  agreement.
