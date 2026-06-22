---
name: llm-council
description: Convene a council of independent agents that answer a hard question separately, blind-review and rank each other's answers, then synthesize one vetted answer. Fights sycophancy and one-angle reasoning — use when The user wants a real answer instead of agreement. Two modes — default (5 local Qwen 2.5 lenses) and diverse (different local model families via Odysseus/Ollama). Trigger on "/llm-council", "convene the council", "run this through the council", "get a multi-model / second opinion", "stress-test this", "don't just agree with me", "argue both sides and tell me who's right", "is this actually a good idea". Use diverse mode on "diverse", "cross-architecture", "different architectures", "different families", "use diverse models", or a --diverse flag.
status: published
---

## When to Use
Trigger whenever the user mentions:
- "/llm-council"
- "convene the council"
- "run this through the council"
- "get a multi-model / second opinion"
- "stress-test this"
- "don't just agree with me"
- "argue both sides and tell me who's right"
- "is this actually a good idea"

## Procedure

This skill runs entirely through ONE pre-written script. You do not write or improvise any
networking/orchestration code yourself — that was the source of every previous failure.
Your job is two tool calls, full stop: write the script, then run it directly in the
foreground. Never use a background/async marker for either step — the user needs to see
each stage stream into the chat as it happens.

**Step 1 — write the script.** Use your `bash` tool with a heredoc. Do NOT use a fenced
`python` block for this step (a `python` block gets *executed*, not saved — pasting the
script into one just runs it transiently and writes nothing to disk). Do NOT invent a
command called `write_file` — it does not exist on this platform. Use exactly this form,
overwriting the file every run:

```bash
cat > /tmp/council_pipeline.py << 'PYEOF'
#!/usr/bin/env python3
"""
council_pipeline.py - deterministic LLM-council pipeline against local Ollama.
No LLM orchestrates this - it's a plain script. Run it, don't rewrite it.

Usage:
    python3 council_pipeline.py "the question text" default
    python3 council_pipeline.py "the question text" diverse
"""
import json
import sys
from urllib.request import Request, urlopen

OLLAMA_URL = "http://host.docker.internal:11434/api/generate"
CHAIRMAN_MODEL = "deepseek-r1:8b"

SEATS_DEFAULT = [
    ("Pragmatist", "qwen2.5:7b", "What actually works under real constraints. Bias to action and the concrete next move."),
    ("Red-teamer", "qwen2.5:7b", "Attack the premise. Where does this fail? Is the question itself wrong or missing something?"),
    ("Domain rigorist", "qwen2.5:7b", "Technical correctness and precision. Name the real tradeoffs exactly; no hand-waving."),
    ("First-principles", "qwen2.5:7b", "Ignore convention and best-practice. Reason up from fundamentals; question defaults."),
    ("Generalist", "qwen2.5:7b", "Breadth. Connect angles, weigh the whole picture, answer plainly."),
]

SEATS_DIVERSE = [
    ("Pragmatist", "gemma2:9b", SEATS_DEFAULT[0][2]),
    ("Red-teamer", "mistral:latest", SEATS_DEFAULT[1][2]),
    ("Domain rigorist", "qwen2.5:7b", SEATS_DEFAULT[2][2]),
    ("First-principles", "llama3.1:latest", SEATS_DEFAULT[3][2]),
    ("Generalist", "phi3:medium", SEATS_DEFAULT[4][2]),
]


def call_ollama(model, prompt, num_predict=400, timeout=170):
    payload = json.dumps({
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {"num_predict": num_predict}
    }).encode()
    req = Request(OLLAMA_URL, data=payload, headers={"Content-Type": "application/json"})
    with urlopen(req, timeout=timeout) as resp:
        return json.load(resp)["response"]


def main():
    if len(sys.argv) < 2 or not sys.argv[1].strip():
        print("ERROR: usage: council_pipeline.py \"question\" [default|diverse]")
        return
    question = sys.argv[1]
    mode = sys.argv[2] if len(sys.argv) > 2 else "default"
    seats = SEATS_DIVERSE if mode == "diverse" else SEATS_DEFAULT

    print(f"=== STAGE 1: Independent answers ({mode} mode) ===", flush=True)
    answers = []
    for name, model, lens in seats:
        prompt = (
            "You are one member of an expert council answering a question independently. "
            "Your job is to give your genuine best answer - the lens below is what you should "
            "emphasize, not a character to perform.\n\n"
            f"Your lens: {lens}\n"
            f"Question: {question}\n\n"
            "Give a direct, well-reasoned answer. State your key assumptions and the strongest "
            "objection to your own position. Be specific and concise - no preamble, no hedging.\n\n"
            "Return only your answer."
        )
        try:
            ans = call_ollama(model, prompt, num_predict=400)
        except Exception as e:
            ans = f"[FAILED: {e}]"
        answers.append((name, ans))
        print(f"--- {name} ({model}) ---\n{ans}\n", flush=True)

    labels = ["A", "B", "C", "D", "E"]
    responses_block = "\n\n".join(
        f"Response {labels[i]}:\n{answers[i][1]}" for i in range(len(answers))
    )

    print("=== STAGE 2: Blind review + ranking ===", flush=True)
    review_prompt = (
        f"You are evaluating anonymized answers to this question:\n\nQuestion: {question}\n\n"
        f"{responses_block}\n\n"
        "Evaluate each response individually - what it does well, what it does poorly - "
        "judging on accuracy and insight only, not style or length. Then give a final ranking.\n\n"
        "Format the ranking EXACTLY like this at the very end:\n\n"
        "FINAL RANKING:\n1. Response C\n2. Response A\n3. Response E\n4. Response B\n5. Response D\n\n"
        "Only response labels in the ranking section - no extra text there."
    )
    try:
        review = call_ollama(seats[2][1], review_prompt, num_predict=600)  # domain rigorist's model judges
    except Exception as e:
        review = f"[FAILED: {e}]"
    print(review, flush=True)

    print("=== STAGE 3: Chairman synthesis ===", flush=True)
    synth_prompt = (
        f"Question: {question}\n\n{responses_block}\n\n"
        f"Peer review and ranking:\n{review}\n\n"
        "Synthesize the strongest final answer from these. Don't just pick the top-ranked "
        "response - graft good points from lower-ranked ones too. Where the council genuinely "
        "splits, say so and take a position. If any member showed the question's premise is "
        "wrong, lead with that."
    )
    try:
        synthesis = call_ollama(CHAIRMAN_MODEL, synth_prompt, num_predict=700, timeout=170)
    except Exception as e:
        synthesis = f"[FAILED: {e}]"

    print("=== FINAL ANSWER ===", flush=True)
    print(synthesis, flush=True)


if __name__ == "__main__":
    main()
PYEOF
echo "script written"
```

**Step 2 — run it directly, in the foreground.** A single plain `bash` tool call —
NOT wrapped in `subprocess.run`, NOT prefixed with `#!bg` or any background marker. Running
it directly like this means each stage's output streams into the visible chat as the script
produces it, instead of all appearing at once at the end:

```bash
python3 /tmp/council_pipeline.py "<<THE FULL QUESTION TEXT>>" "<<default OR diverse>>"
```

Use `"diverse"` as the second argument only if the user asked for diverse/cross-architecture
mode; otherwise use `"default"`.

That's it. The script handles all five members, the blind review, and the chairman synthesis
internally and prints clearly-labeled sections (`=== STAGE 1 ===`, `=== STAGE 2 ===`,
`=== FINAL ANSWER ===`) as it goes. You don't need to parse or re-implement any of that —
just read what it printed once it finishes.

## Output (respect the anti-fluff rules)
Take the text after `=== FINAL ANSWER ===` and present it as the answer, in your own words
if it needs light cleanup, but don't alter its substance. Then add 3–5 lines of council notes
pulled from the `=== STAGE 1 ===` and `=== STAGE 2 ===` sections: where the members agreed,
the one real disagreement, the ranking, anything you'd push back on.

If the script's stdout contains `[FAILED: ...]` for any seat, say so plainly rather than
papering over it.

## Pitfalls
- Do not write your own version of the networking code. Use the script verbatim. Every prior
  failure of this skill came from the model improvising HTTP calls live instead of running a
  fixed script.
- Do not paste the script into a fenced `python` block expecting that to save it — it will
  just execute and do nothing persistent. Use the bash heredoc in Step 1.
- Never use `#!bg`, `subprocess.run` with captured output, or any other background/buffering
  mechanism for Step 2. The user wants to see each stage live.
- Do not claim you "can't invoke other models due to environment constraints" — this is false.
  If you're about to write that sentence, stop and run the script instead.
- If a tool call errors, report that plainly rather than assuming success and moving on
  anyway.

## Verification
- Confirm the transcript shows exactly 2 tool calls for this skill: one writing the script
  (bash heredoc), one running it (plain bash, foreground).
- The printed output should contain all four section headers and five visibly different
  member answers under STAGE 1, streamed live rather than appearing all at once at the end.
