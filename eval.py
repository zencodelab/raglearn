"""
GovShield RAG Evaluation Script

Measures RAG pipeline quality using LLM-as-judge on three metrics:

  Faithfulness     — every claim in the answer is supported by the retrieved
                     context chunks (hallucination detection)
  Answer Relevance — the answer actually addresses the question
  Context Recall   — the retrieved chunks contain the information needed to
                     answer the question

How the scoring works:
  The same local Ollama LLM that runs synthesis is used as the judge. For each
  metric it is given a focused prompt and asked to return a single float 0.0–1.0.
  This is the standard LLM-as-evaluator pattern used in production RAG systems.

For RBAC refusal cases (expected_grounded=False), faithfulness and context recall
are skipped — the important check is whether the pipeline correctly refused to
answer rather than hallucinating.

Usage:
    python eval.py                            # run all tests (L2 clearance default)
    python eval.py --clearance L1             # override clearance for all tests
    python eval.py --output my_results.json   # save to a specific file
    python eval.py --quiet                    # suppress per-test detail, show table only
"""

import argparse
import json
import os
import sys
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime

from llama_index.llms.ollama import Ollama

from retrieval_app import LLM_MODEL, get_query_engine

OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
NOT_GROUNDED_MARKER = "cannot find the answer"


# ── Test cases ────────────────────────────────────────────────────────────────

@dataclass
class EvalCase:
    question: str
    clearance: str          # clearance level the query runs under
    expected_grounded: bool # True → expects a real answer; False → expects refusal
    description: str        # what aspect this test is checking


TEST_CASES: list[EvalCase] = [
    EvalCase(
        question="What is the VPN policy for remote access?",
        clearance="L1",
        expected_grounded=True,
        description="L1 user — IT policy question (should exist in L1 docs)",
    ),
    EvalCase(
        question="What are the office working hours?",
        clearance="Public",
        expected_grounded=True,
        description="Public user — basic office question (should exist in Public/L1 docs)",
    ),
    EvalCase(
        question="How do I reset my password?",
        clearance="L1",
        expected_grounded=True,
        description="L1 user — IT support FAQ (should exist in L1 docs)",
    ),
    EvalCase(
        question="What temperature must the server room maintain?",
        clearance="L2",
        expected_grounded=True,
        description="L2 user — security protocol question (should exist in L2 docs)",
    ),
    EvalCase(
        question="What temperature must the server room maintain?",
        clearance="L1",
        expected_grounded=False,
        description="RBAC test — L1 user asking L2 content (should be refused)",
    ),
    EvalCase(
        question="Who won the FIFA World Cup in 2022?",
        clearance="L2",
        expected_grounded=False,
        description="Hallucination guard — out-of-scope query (should be refused)",
    ),
]


# ── Result dataclass ──────────────────────────────────────────────────────────

@dataclass
class EvalResult:
    question: str
    clearance: str
    description: str
    answer: str
    sources: list[dict]
    faithfulness: float | None    # None when refusal was expected and correct
    answer_relevance: float | None
    context_recall: float | None
    grounded: bool                # did the pipeline actually answer (vs. refuse)?
    expected_grounded: bool
    grounding_correct: bool       # grounded == expected_grounded
    latency_s: float


# ── LLM judge prompts ─────────────────────────────────────────────────────────

_FAITHFULNESS = """\
Given the retrieved context and the answer below, rate whether every factual \
claim in the answer is directly supported by the context (not by external knowledge).

Context:
{context}

Answer: {answer}

Score 0.0–1.0:
  1.0 = every claim explicitly supported by the context
  0.5 = some claims supported, some unclear or missing from context
  0.0 = answer contains claims not in the context, or is fabricated

Reply with ONLY a single decimal number, nothing else."""

_RELEVANCE = """\
Given the question and answer below, rate how well the answer addresses the question.

Question: {question}

Answer: {answer}

Score 0.0–1.0:
  1.0 = answer directly and completely addresses the question
  0.5 = answer is related but incomplete or partially off-topic
  0.0 = answer does not address the question at all

Reply with ONLY a single decimal number, nothing else."""

_CONTEXT_RECALL = """\
Given the question and the retrieved context chunks below, rate whether the \
context contains sufficient information to answer the question.

Question: {question}

Retrieved Context:
{context}

Score 0.0–1.0:
  1.0 = context contains all the information needed to answer
  0.5 = context contains partial information
  0.0 = context does not contain relevant information

Reply with ONLY a single decimal number, nothing else."""


# ── Helpers ───────────────────────────────────────────────────────────────────

def _judge_score(llm: Ollama, prompt: str) -> float:
    """Ask the LLM judge to return a 0.0–1.0 score; clamp and default on failure."""
    try:
        raw = llm.complete(prompt).text.strip()
        score = float(raw.split()[0].rstrip(".,"))
        return max(0.0, min(1.0, score))
    except Exception:
        return 0.0


def _format_context(source_nodes) -> str:
    parts = []
    for i, node in enumerate(source_nodes, 1):
        file_name = node.node.metadata.get("file_name", "unknown")
        snippet = node.node.get_content().strip().replace("\n", " ")
        parts.append(f"[{i}] ({file_name}): {snippet}")
    return "\n".join(parts)


def _is_grounded(answer: str) -> bool:
    return NOT_GROUNDED_MARKER not in answer.lower()


# ── Core evaluation loop ──────────────────────────────────────────────────────

def evaluate(
    cases: list[EvalCase],
    clearance_override: str | None,
    verbose: bool,
) -> list[EvalResult]:
    judge_llm = Ollama(model=LLM_MODEL, base_url=OLLAMA_BASE_URL, request_timeout=120.0)
    results: list[EvalResult] = []

    for i, case in enumerate(cases, 1):
        clearance = clearance_override or case.clearance
        if verbose:
            print(f"\n[{i}/{len(cases)}] {case.description}")
            print(f"  Q: {case.question}  |  clearance={clearance}")

        engine = get_query_engine(user_clearance=clearance)

        t0 = time.perf_counter()
        response = engine.query(case.question)
        latency = round(time.perf_counter() - t0, 2)

        answer = response.response.strip()
        grounded = _is_grounded(answer)
        context_str = _format_context(response.source_nodes)

        sources = [
            {
                "file": n.node.metadata.get("file_name", "unknown"),
                "score": round(n.score, 4),
                "snippet": n.node.get_content().strip()[:120],
            }
            for n in response.source_nodes
        ]

        # Score metrics — skip faithfulness + context recall on correct refusals
        if grounded:
            faithfulness = _judge_score(
                judge_llm,
                _FAITHFULNESS.format(context=context_str, answer=answer),
            )
            answer_relevance = _judge_score(
                judge_llm,
                _RELEVANCE.format(question=case.question, answer=answer),
            )
            context_recall = _judge_score(
                judge_llm,
                _CONTEXT_RECALL.format(question=case.question, context=context_str),
            )
        else:
            # Pipeline refused — only check answer_relevance (was refusal appropriate?)
            faithfulness = None
            context_recall = None
            answer_relevance = _judge_score(
                judge_llm,
                _RELEVANCE.format(question=case.question, answer=answer),
            )

        grounding_correct = grounded == case.expected_grounded

        result = EvalResult(
            question=case.question,
            clearance=clearance,
            description=case.description,
            answer=answer,
            sources=sources,
            faithfulness=faithfulness,
            answer_relevance=answer_relevance,
            context_recall=context_recall,
            grounded=grounded,
            expected_grounded=case.expected_grounded,
            grounding_correct=grounding_correct,
            latency_s=latency,
        )
        results.append(result)

        if verbose:
            f_str = f"{faithfulness:.2f}" if faithfulness is not None else " N/A"
            r_str = f"{answer_relevance:.2f}" if answer_relevance is not None else " N/A"
            c_str = f"{context_recall:.2f}" if context_recall is not None else " N/A"
            gc = "PASS" if grounding_correct else "FAIL"
            print(f"  → faithfulness={f_str}  relevance={r_str}  recall={c_str}  grounding={gc}  ({latency}s)")

    return results


# ── Reporting ─────────────────────────────────────────────────────────────────

def _avg(values: list[float | None]) -> float | None:
    clean = [v for v in values if v is not None]
    return round(sum(clean) / len(clean), 3) if clean else None


def print_report(results: list[EvalResult]) -> None:
    col = 52
    print("\n" + "=" * 80)
    print("  GovShield RAG Evaluation Report")
    print("=" * 80)
    header = f"{'#':<3} {'Description':<{col}} {'Faith':>6} {'Relev':>6} {'Recall':>6} {'Ground':>7}"
    print(header)
    print("-" * 80)

    for i, r in enumerate(results, 1):
        f = f"{r.faithfulness:.2f}" if r.faithfulness is not None else "  N/A"
        rv = f"{r.answer_relevance:.2f}" if r.answer_relevance is not None else "  N/A"
        rc = f"{r.context_recall:.2f}" if r.context_recall is not None else "  N/A"
        gc = "PASS" if r.grounding_correct else "FAIL"
        desc = r.description[:col]
        print(f"{i:<3} {desc:<{col}} {f:>6} {rv:>6} {rc:>6} {gc:>7}")

    print("-" * 80)
    avg_f = _avg([r.faithfulness for r in results])
    avg_rv = _avg([r.answer_relevance for r in results])
    avg_rc = _avg([r.context_recall for r in results])
    gc_pct = round(sum(r.grounding_correct for r in results) / len(results) * 100)

    af = f"{avg_f:.3f}" if avg_f is not None else "  N/A"
    arv = f"{avg_rv:.3f}" if avg_rv is not None else "  N/A"
    arc = f"{avg_rc:.3f}" if avg_rc is not None else "  N/A"
    print(f"{'AVG':<3} {'(answered cases only)':<{col}} {af:>6} {arv:>6} {arc:>6} {gc_pct:>6}%")
    print("=" * 80)


def save_json(results: list[EvalResult], path: str) -> None:
    payload = {
        "run_at": datetime.utcnow().isoformat() + "Z",
        "model": LLM_MODEL,
        "summary": {
            "faithfulness_avg": _avg([r.faithfulness for r in results]),
            "answer_relevance_avg": _avg([r.answer_relevance for r in results]),
            "context_recall_avg": _avg([r.context_recall for r in results]),
            "grounding_accuracy_pct": round(
                sum(r.grounding_correct for r in results) / len(results) * 100
            ),
            "total_cases": len(results),
        },
        "results": [asdict(r) for r in results],
    }
    with open(path, "w") as f:
        json.dump(payload, f, indent=2)
    print(f"\nResults saved → {path}")


# ── Entry point ───────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate the GovShield RAG pipeline")
    parser.add_argument(
        "--clearance",
        choices=["Public", "L1", "L2"],
        default=None,
        help="Override clearance level for all test cases (default: use per-case clearance)",
    )
    parser.add_argument(
        "--output",
        default="eval_results.json",
        help="Path to write JSON results (default: eval_results.json)",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress per-test progress; show summary table only",
    )
    args = parser.parse_args()

    print(f"GovShield RAG Eval — model={LLM_MODEL} | cases={len(TEST_CASES)}")
    print("Ensure Ollama is running and documents have been ingested before running.\n")

    results = evaluate(
        cases=TEST_CASES,
        clearance_override=args.clearance,
        verbose=not args.quiet,
    )

    print_report(results)
    save_json(results, args.output)


if __name__ == "__main__":
    main()
