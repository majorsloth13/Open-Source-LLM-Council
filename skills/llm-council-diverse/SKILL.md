---
name: llm-council-diverse
description: Convene a council using real, different local Ollama model families (gemma2, mistral, qwen2.5, llama3.1, phi3) that each answer independently, get blind-reviewed, and get synthesized into one recommendation. Runs a pre-installed script — does not write or improvise any code. Trigger on "/llm-council-diverse", "cross-vendor", "diverse council", "different models", "real models", "use ollama for the council", or a --diverse / --cross-vendor flag. Do NOT use this skill for a plain "/llm-council" or general second-opinion request with no mention of real/different models — use llm-council for that instead.
status: published
---

## When to Use
Trigger whenever the user mentions:
- "/llm-council-diverse"
- "cross-vendor"
- "diverse council" / "diverse mode"
- "different models" / "real models"
- "use ollama" for the council
- a `--diverse` or `--cross-vendor` flag

If the user just wants a quick multi-angle gut-check with no mention of real/different
models — stop, this is the wrong skill. Use `llm-council` instead.

## Procedure

A pre-installed script at `/tmp/council_pipeline.py` does all the work — it is NOT something
you write or retype as part of this skill. Every previous version of this mode failed because
the model tried to retype ~100 lines of Python live, badly, every single run. That step does
not happen here. If the file is missing, you say so and stop; you do not recreate it.

The question is whatever the user passed. If it's vague, ask one clarifying question first.

Run this directly, in the foreground — one plain `bash` tool call, nothing wrapped around it,
no `#!bg` or other background marker, so each stage streams into the chat as it happens:

```bash
python3 /tmp/council_pipeline.py "<<THE FULL QUESTION TEXT>>" diverse
```

If that errors with something like `can't open file '/tmp/council_pipeline.py'`, the script
isn't installed. Say so plainly and tell the user it needs to be (re)installed — do not
attempt to write the file yourself.

The script prints `=== STAGE 1 ===` (five real per-model answers), `=== STAGE 2 ===` (a real
blind ranking from one of the models), `=== STAGE 3 ===` (a real chairman synthesis from
`deepseek-r1:8b`), then `=== FINAL ANSWER ===`. Read all of it once it finishes.

## Output (respect the anti-fluff rules)
Lead with the text after `=== FINAL ANSWER ===`, presented as the answer — light cleanup of
phrasing is fine, don't alter its substance. Then 3–5 lines of council notes pulled from the
`=== STAGE 1 ===` and `=== STAGE 2 ===` sections: where the models agreed, the one real
disagreement, the ranking, anything you'd push back on. Name the real models in the notes
(e.g. `gemma2:9b > llama3.1:latest > ...`) — that's correct here, unlike in the default skill.

If the script's output contains `[FAILED: ...]` for any seat, say so plainly rather than
papering over it.

Don't dump all five full per-seat answers by default — only if the user asks to "see each
member" or "show the work."

## Pitfalls
- Writing or retyping any part of `council_pipeline.py` yourself. Check it exists by trying
  to run it; if it's missing, report that and stop.
- Using `subprocess.run` with captured output, or `#!bg` / any background marker. The user
  needs to see each stage stream live, not get a single dump at the end (or nothing at all).
- Trusting your own narration over real output. If you're about to write "I will simulate
  this" or similar, stop — that means something is wrong; report it instead of inventing a
  result.
- Treating a vague question as answerable without checking first.

## Verification
- The transcript shows exactly one `bash` tool call for this skill — running the script
  directly. No file-write step, no wrapped subprocess call.
- The output contains all four section headers, and the five Stage-1 answers visibly differ
  from each other in both content and the model name shown next to each.
