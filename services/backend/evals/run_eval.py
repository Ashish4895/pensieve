#!/usr/bin/env python3
"""Golden-set retrieval eval: scores top-3 chunk hit rate against spaceship_protocol.txt."""
import json
import os
import sys
from pathlib import Path

import django
from dotenv import load_dotenv

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "pensieve.settings")
django.setup()

from chatbot.models import DocumentChunk  # noqa: E402
from chatbot.rag_helper import retrieve_relevant_chunks  # noqa: E402

_repo_env = Path(__file__).resolve().parents[3] / ".env"
if _repo_env.is_file():
    load_dotenv(_repo_env)
else:
    load_dotenv()
GOLDEN_PATH = os.path.join(os.path.dirname(__file__), "golden_qa.json")


def _die(msg: str, steps: list[str]) -> None:
    print(f"Error: {msg}\n")
    for step in steps:
        print(f"  {step}")
    sys.exit(1)


def main() -> None:
    if not os.environ.get("GEMINI_API_KEY"):
        _die(
            "GEMINI_API_KEY not found in environment.",
            [
                "Add GEMINI_API_KEY to .env",
                "./venv/bin/python ingest_docs.py",
                "./venv/bin/python evals/run_eval.py",
            ],
        )

    if not DocumentChunk.objects.exists():
        _die(
            "No document chunks in the database.",
            [
                "./venv/bin/python ingest_docs.py",
                "./venv/bin/python evals/run_eval.py",
            ],
        )

    with open(GOLDEN_PATH, encoding="utf-8") as f:
        cases = json.load(f)

    rows = []
    positive_hits = 0
    positive_total = 0

    for case in cases:
        qid = case["id"]
        question = case["q"]
        try:
            chunks = retrieve_relevant_chunks(question, top_k=3)
        except Exception as exc:
            print(f"Error: retrieval failed for '{qid}': {exc}")
            sys.exit(1)

        if case.get("expect_not_in_docs"):
            # Answer is absent from corpus; low/empty retrieval is acceptable.
            passed = len(chunks) == 0 or not any(
                "birthday" in c["content"].lower() for c in chunks
            )
            note = "no relevant chunks" if len(chunks) == 0 else f"top score {chunks[0]['score']:.2f}"
        else:
            positive_total += 1
            expect = case["expect_substring"]
            passed = any(expect.lower() in c["content"].lower() for c in chunks)
            if passed:
                positive_hits += 1
            note = expect if passed else (
                chunks[0]["content"][:50].replace("\n", " ") + "..." if chunks else "no chunks"
            )

        rows.append((qid, question, "PASS" if passed else "FAIL", note))

    print("| id | question | result | note |")
    print("| --- | --- | --- | --- |")
    for qid, question, result, note in rows:
        q = question.replace("|", "\\|")
        n = str(note).replace("|", "\\|")
        print(f"| {qid} | {q} | {result} | {n} |")

    hit_rate = positive_hits / positive_total if positive_total else 0.0
    print(f"\nPositive retrieval hit rate: {positive_hits}/{positive_total} = {hit_rate:.2f}")

    if hit_rate < 0.8:
        sys.exit(1)


if __name__ == "__main__":
    main()
