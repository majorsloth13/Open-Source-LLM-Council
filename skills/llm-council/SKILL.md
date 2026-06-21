---
name: llm-council
description: Convene a council of independent agents that answer a hard question separately, blind-review and rank each other's answers, then synthesize one vetted answer. Fights sycophancy and one-angle reasoning — use when The user wants a real answer instead of agreement. Two modes — default (5 local Qwen 2.5 sub-agents) and cross-architecture (diverse local families via Odysseus/Ollama, faithful to karpathy/llm-council). Trigger on "/llm-council", "convene the council", "run this through the council", "get a multi-model / second opinion", "stress-test this", "don't just agree with me", "argue both sides and tell me who's right", "is this actually a good idea", or any moment he wants a decision pressure-tested rather than rubber-stamped. Use cross-architecture mode on "cross-architecture", "different architectures", "different families", "use diverse models", "faithful council", or a `--cross-architecture` / `--diverse` flag.
status: published
---

## When to Use
Trigger this multi-agent logic loop whenever the user explicitly inputs commands or mentions:
- "/llm-council"
- "convene the council"
- "run this through the council"
- "get a multi-model / second opinion"
- "stress-test this"
- "don't just agree with me"
- "argue both sides and tell me who's right"
- "is this actually a good idea"
- Any structural moment a decision needs aggressive pressure-testing rather than automatic agreement.

## Procedure
A 3-stage pipeline adapted for local hardware that produces a vetted answer instead of a sycophantic one. Independent agents answer blind, then blind-review and rank each other's work, then the main loop (using `deepseek-r1:8b` as Chairman) synthesizes the final context.

The question is whatever The user passed (the `/llm-council` arg, or the thing he asked to run through the council). If it's vague, ask one clarifying question first — a sharp question is worth more than five answers to a fuzzy one.

### Two modes — pick one before Stage 1
- **Default (Single-Family council).** Five unique perspective lenses run through a single highly-capable, objective base model architecture (`qwen2.5:7b`). Fast, highly analytical, and holds a strict operational baseline. Follow Stages 1–3 below.
- **Cross-architecture (faithful council).** Five completely different local model families (`gemma2`, `mistral`, `qwen2.5`, `llama3.1`, `phi3`) mixed via Ollama, exactly as karpathy/llm-council intended. Use it when The user says "cross-architecture", "different architectures", "different families", "use diverse models", "faithful council", or passes `--cross-architecture` / `--diverse`. This spins up different local model binaries sequentially and costs more compute/time, so it's opt-in only — never silently upgrade the default into it. Jump to Cross-architecture mode near the bottom, then come back for Stage 3.

The real win of cross-architecture is catching correlated blind spots — things every model of a single family gets wrong the same way. The default catches weak reasoning and one-angle answers but shares a family's blind spots; the faithful council doesn't.

### Stage 1 — Independent answers (5 members, sequentially)
Spawn all five Agent calls sequentially (one at a time) to remain safe within the laptop's 16GB VRAM pool. Every seat gets a top-performing model. Give each the same question plus its lens. Members never see each other.

| Member / Lens | Default Model | Cross-Architecture Model | Lens (what it's told to prioritize) |
|---|---|---|---|
| Pragmatist | `qwen2.5:7b` | `gemma2:9b` | What actually works under real constraints. Bias to action and the concrete next move. |
| Red-teamer | `qwen2.5:7b` | `mistral:latest` | Attack the premise. Where does this fail? Is the question itself wrong or missing something? |
| Domain rigorist | `qwen2.5:7b` | `qwen2.5:7b` | Technical correctness and precision. Name the real tradeoffs exactly; no hand-waving. |
| First-principles | `qwen2.5:7b` | `llama3.1:latest` | Ignore convention and best-practice. Reason up from fundamentals; question defaults. |
| Generalist | `qwen2.5:7b` | `phi3:medium` | Breadth. Connect angles, weigh the whole picture, answer plainly. |

Diversity comes from the lenses or the diverse architectures, not from weaker models — a dumber model is noise, not a fresh perspective. Member count and lenses are easy to tune later.

Prompt template for each member:
> You are one member of an expert council answering a question independently. Your job is to give your genuine best answer — the lens below is what you should emphasize, not a character to perform.
>
> **Your lens:** {lens}
> **Question:** {question}
>
> Give a direct, well-reasoned answer. State your key assumptions and the strongest objection to your own position. Be specific and concise — no preamble, no hedging. You may use read-only tools if you genuinely need a fact to answer well, but lead with reasoning.
>
> Return only your answer.

Collect the five answers verbatim.

### Stage 2 — Blind peer review + ranking (5 reviewers, sequentially)
Label the five Stage-1 answers `Response A`, `Response B`, … `Response E` and strip all identity (no lens names, no model names). Keep your own private map of label → member for the notes later.

Spawn five reviewer Agent calls sequentially, using the corresponding models from Stage 1 (judging answer quality is harder than producing it — never cheap out on the judges). Each reviewer sees all five anonymized answers. (Reviewers are fresh stateless spawns — none can recognize "its own" answer, so there's no self-preference bias.)

Reviewer prompt template:
> You are evaluating anonymized answers to this question:
>
> **Question:** {question}
>
> {Response A … Response E, each as "Response X:\n{answer}"}
>
> Your task:
> 1. Evaluate each response individually — what it does well, what it does poorly — judging on accuracy and insight only, not style or length.
> 2. Then give a final ranking, best to worst.
>
> Format the ranking EXACTLY like this at the very end:
>
> ```
> FINAL RANKING:
> 1. Response C
> 2. Response A
> 3. Response E
> 4. Response B
> 5. Response D
> ```
>
> Only response labels in the ranking section — no extra text there.

Parse each `FINAL RANKING:` block. Aggregate by average position (lower = better) to get the council's overall order.

### Stage 3 — Chairman synthesis (DeepSeek-R1 8B, the main loop)
You now hold all five answers and all five reviews. Route them directly to `deepseek-r1:8b` to act as the Chairman. Do not just pick the #1 answer, and do not drift back toward whatever The user originally implied — synthesize on merit and consensus leveraging the model's native thinking/reasoning tokens.

- Build the final answer from the strongest reasoning across all members, grafting good points even from low-ranked answers.
- Where the council genuinely splits, say so and take a position — don't average the disagreement into mush.
- If the Red-teamer (or anyone) showed the question's premise is wrong, that leads. The council exists to push back, not rubber-stamp.

### Output (respect the anti-fluff rules)
Lead with the answer. Keep the council note tight.

1. **The answer** — the synthesized recommendation, stated plainly and directly.
2. **Council notes** — 3–5 lines max:
   - where they agreed
   - the one real disagreement (and which side you took, why)
   - the aggregate ranking (e.g. `Pragmatist > Rigorist > First-principles > Generalist > Red-teamer`)
   - anything you overrode and why

Do not dump the five full answers by default. If The user says "show me each member" / "show the work," print the per-member answers and full reviews then.

### Cross-architecture mode (Faithful Council via Local Ollama Backend)
Only when The user opted in (see "Two modes"). This replaces Stages 1–2 with a diverse multi-model local queue cycle; Stage 3 is unchanged — DeepSeek-R1 still synthesizes as Chairman.

The internal Odysseus workspace configuration handles the work: it passes the question to each local model family in sequence for its independent answer (Stage 1), then sends each model all the anonymized answers to extract its `FINAL RANKING` (Stage 2), then processes the aggregate array mapping models back to their respective seats.

Your local cross-vendor alignment lineup:

| Seat | Local Model Architecture |
|---|---|
| Pragmatist | `gemma2:9b` |
| Red-teamer | `mistral:latest` |
| Domain Rigorist | `qwen2.5:7b` |
| First-principles | `llama3.1:latest` |
| Generalist | `phi3:medium` |

Then:
1. **Map the responses.** Ensure Odysseus traces each lens output back to its assigned architecture. `aggregate_ranking[]` ranks best-first based on average peer rank.
2. **Be Chairman (Stage 3, same rules as above).** Synthesize on merit and consensus across architectures via `deepseek-r1:8b` — graft strong points even from low-ranked seats; where families genuinely split, say so and take a side; if any model showed the premise is wrong, that leads.
3. **Output (same format as default mode),** but in the council note name the architectures (`Gemma2 > Llama3.1 > Qwen2.5 > Mistral > Phi3`), and call out anything where the foundational models diverged — that divergence is the whole point of local architectural diversity.

Handling workspace environment adjustments:
- If a model request fails, ensure your Ollama background app is fully running in the Windows system tray. Check that the port maps directly to `http://localhost:11434`.
- If your system experiences high memory overhead, confirm that `OLLAMA_NUM_PARALLEL` remains at its default value of `1` in the system variables to prevent simultaneous VRAM allocation crashes.

## Pitfalls
- Setting `OLLAMA_NUM_PARALLEL` higher than 1 will attempt to concurrent-load binaries, crashing the laptop's 16GB VRAM boundaries and forcing sluggish system RAM offloading.

## Verification
- Evaluate the incoming prompt query for explicit trigger phrases inside the text stream before executing the multi-agent task thread.
- Type `/llm-council --diverse` inside the primary Chat workspace view and monitor the console logs to confirm that Ollama performs clean sequential swaps.
- Inspect the final output interface file to confirm that the text block starts immediately with a direct recommendation, hiding the raw scratchpad answers by default.
- Confirm that the final structural breakdown notes contain exactly 3 to 5 lines of context tracking total consensus and directional overrides.

### Body Extra
- **UI/UX Vision Integration Loop:** If a frontend layout snapshot or application UI screenshot file asset is dropped into the active chat channel, the workspace must instantly halt the text-only loop and pass the raw image straight to `qwen3-vl:8b` first. Instruct the multi-modal agent to perform an optical layout assessment focusing on component margins, overlapping elements, padding alignment bugs, and OCR text boundaries. Output this visual critique as an organized markdown data report, and pipe that resulting text report directly as the core entry question for Stage 1 of the council pipeline.
- **Post-Council Code Racing Layout:** Once the Chairman (`deepseek-r1:8b`) delivers the clean system architecture blueprint, the user can pivot straight to the Odysseus Compare Mode tool page. Map your specialized developer engines—`qwen2.5-coder:7b` and `deepseek-coder:6.7b`—side-by-side inside the interface boxes. Submit the council's finalized blueprint requirements to both, forcing them to race concurrently to generate the ultimate, low-latency execution script code blocks.
- **Default Baseline Tuning:** Default mode shares Qwen's blind spots. Every member is a different lens of Qwen 2.5, so it catches weak reasoning, bad assumptions, and one-angle answers — but not blind spots all Qwen models share. Reach for cross-architecture mode when the stakes justify the computational time and you specifically want a completely non-Qwen check on the premise.
