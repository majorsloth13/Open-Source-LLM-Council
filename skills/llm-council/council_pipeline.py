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
