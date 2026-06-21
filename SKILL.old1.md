---
name: llm-council
description: Convene a council of independent agents that answer a hard question separately, blind-review and rank each other's answers, then synthesize one vetted answer. Fights sycophancy and one-angle reasoning — use when The user wants a real answer instead of agreement. Two modes — default (5 local Qwen 2.5 lenses) and cross-architecture (diverse local families via Odysseus/Ollama, faithful to karpathy/llm-council). Trigger on "/llm-council", "convene the council", "run this through the council", "get a multi-model / second opinion", "stress-test this", "don't just agree with me", "argue both sides and tell me who's right", "is this actually a good idea", or any moment he wants a decision pressure-tested rather than rubber-stamped. Use cross-architecture mode on "cross-architecture", "different architectures", "different families", "use diverse models", "faithful council", or a `--cross-architecture` / `--diverse` flag.
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
**Important platform fact:** Odysseus has no sub-agent dispatch tool. There is no way to "spawn an Agent call on a different model" the way Claude Code can. The only real way to invoke a model other than the one driving this conversation is to use your `python` tool to make a direct HTTP request to the local Ollama API. Every step below that says "call a member" means: issue one `python` tool block that does this.

This only works in Agent mode (Chat mode never executes tool calls at all). Confirm Agent mode is on before running this skill.

The question is whatever the user passed (the `/llm-council` arg, or the thing they asked to run through the council). If it's vague, ask one clarifying question first — a sharp question is worth more than five answers to a fuzzy one.

### Two modes — pick one before Stage 1
- **Default.** All five seats run on `qwen2.5:7b` (already resident as the chat model — no cold-load penalty between seats). Five distinct lenses, one model. Run this one until it's proven reliable.
- **Cross-architecture.** Five different local model families (`gemma2`, `mistral`, `qwen2.5`, `llama3.1`, `phi3`). Catches correlated blind spots a single family shares — but each seat swap is a cold model load on top of generation time, multiplying the risk of any one call running long. Only use this once Default mode is working end to end. Opt-in only — never silently upgrade Default into it.

### Stage 1 — Independent answers (5 members, sequentially)
Issue this as **five separate `python` tool calls, one per seat — never combine seats into a single block.** Each call needs its own execution window; bundling multiple model calls into one script means one slow seat kills all of them together.

```python
import json
from urllib.request import Request, urlopen

payload = json.dumps({
    "model": "qwen2.5:7b",
    "prompt": (
        "You are one member of an expert council answering a question independently. "
        "Your job is to give your genuine best answer — the lens below is what you should "
        "emphasize, not a character to perform.\n\n"
        "Your lens: <LENS TEXT FOR THIS SEAT>\n"
        "Question: <THE QUESTION>\n\n"
        "Give a direct, well-reasoned answer. State your key assumptions and the strongest "
        "objection to your own position. Be specific and concise — no preamble, no hedging.\n\n"
        "Return only your answer."
    ),
    "stream": False,
    "options": {"num_predict": 400}
}).encode()
req = Request("http://host.docker.internal:11434/api/generate", data=payload,
              headers={"Content-Type": "application/json"})
with urlopen(req, timeout=55) as resp:
    result = json.load(resp)
print(result["response"])
```

Swap in the model and lens per seat:

| Member / Lens | Model | Lens (what it's told to prioritize) |
|---|---|---|
| Pragmatist | `qwen2.5:7b` | What actually works under real constraints. Bias to action and the concrete next move. |
| Red-teamer | `qwen2.5:7b` | Attack the premise. Where does this fail? Is the question itself wrong or missing something? |
| Domain rigorist | `qwen2.5:7b` | Technical correctness and precision. Name the real tradeoffs exactly; no hand-waving. |
| First-principles | `qwen2.5:7b` | Ignore convention and best-practice. Reason up from fundamentals; question defaults. |
| Generalist | `qwen2.5:7b` | Breadth. Connect angles, weigh the whole picture, answer plainly. |

`num_predict: 400` caps each answer's length so the call stays well clear of the per-tool timeout. After each call returns, record that seat's printed answer verbatim — these are what Stage 2 needs.

If a call times out or returns an error instead of text, say so plainly in your final output ("the Pragmatist call failed and was excluded") rather than inventing what it would have said.

### Stage 2 — Blind review + ranking (1 combined call)
Don't run five separate reviewers — that's five more cold network round-trips stacked on Stage 1's five, against a 20-step budget per message. Instead, label the five Stage-1 answers `Response A`–`Response E`, strip all lens/model identity, and send all five plus the evaluation instructions to the Domain Rigorist's model in **one** more `python`/Ollama call:

```python
import json
from urllib.request import Request, urlopen

payload = json.dumps({
    "model": "qwen2.5:7b",
    "prompt": (
        "You are evaluating anonymized answers to this question:\n\n"
        "Question: <THE QUESTION>\n\n"
        "Response A:\n<answer>\n\nResponse B:\n<answer>\n\nResponse C:\n<answer>\n\n"
        "Response D:\n<answer>\n\nResponse E:\n<answer>\n\n"
        "Evaluate each response individually — what it does well, what it does poorly — "
        "judging on accuracy and insight only, not style or length. Then give a final ranking.\n\n"
        "Format the ranking EXACTLY like this at the very end:\n\n"
        "FINAL RANKING:\n1. Response C\n2. Response A\n3. Response E\n4. Response B\n5. Response D\n\n"
        "Only response labels in the ranking section — no extra text there."
    ),
    "stream": False,
    "options": {"num_predict": 600}
}).encode()
req = Request("http://host.docker.internal:11434/api/generate", data=payload,
              headers={"Content-Type": "application/json"})
with urlopen(req, timeout=55) as resp:
    result = json.load(resp)
print(result["response"])
```

Parse the `FINAL RANKING:` block from the response.

### Stage 3 — Chairman synthesis (1 call to deepseek-r1:8b)
One more `python`/Ollama call, same pattern, model `"deepseek-r1:8b"`, passing it all five Stage-1 answers, the Stage-2 ranking, and the instructions below. Use its returned text as the basis for your final output — don't just pick the #1-ranked answer, and don't drift back toward whatever the user originally implied.

- Build the final answer from the strongest reasoning across all members, grafting good points even from low-ranked answers.
- Where the council genuinely splits, say so and take a position — don't average the disagreement into mush.
- If the Red-teamer (or anyone) showed the question's premise is wrong, that leads. The council exists to push back, not rubber-stamp.

### Output (respect the anti-fluff rules)
Lead with the answer. Keep the council note tight.

1. **The answer** — the synthesized recommendation, stated plainly and directly.
2. **Council notes** — 3–5 lines max:
   - where they agreed
   - the one real disagreement (and which side you took, why)
   - the aggregate ranking
   - anything you overrode and why
   - any seat that failed/timed out and was excluded

Do not dump the five full answers by default. If the user says "show me each member" / "show the work," print the per-member answers and full review then.

### Cross-architecture mode
Not yet rewritten for direct dispatch — get Default mode working and proven first. Once it is, the same `python`/Ollama call-per-seat pattern applies here too, just swapping in `gemma2:9b`, `mistral:latest`, `qwen2.5:7b`, `llama3.1:latest`, `phi3:medium` per seat instead of `qwen2.5:7b` five times. Expect each seat to take noticeably longer than the Default-mode timings due to cold model loads between families — if a seat times out, that's expected until/unless `num_predict` is tuned down further or the per-tool timeout ceiling is confirmed higher than 55s.

## Pitfalls
- Never combine multiple seats' Ollama calls into a single `python` block — each needs its own timeout window.
- Don't trust your own narration. If you find yourself writing "I will simulate this" or "assuming this would return X," stop — either make the real call or report that you couldn't.
- A `python` tool call with `exit_code=0` and real printed output is the only valid evidence a seat actually answered. A model timing out or erroring is not a reason to invent what it would have said.

## Verification
- Confirm Agent mode (not Chat) is active before running.
- After running, check that the transcript shows 5 distinct `python` tool executions for Stage 1, not one continuous block of generated text with no tool calls in between.
- Confirm the printed answer text differs meaningfully seat-to-seat — if all five "members'" answers in your final summary sound identical, that's a sign no real per-seat calls happened.
