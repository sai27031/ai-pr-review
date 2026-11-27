"""Compare diff-only and function-context inputs using the live review pipeline."""
import argparse
import json
import re
import sys
from collections import Counter
from difflib import unified_diff
from time import monotonic

from requests import RequestException

from ai_reviewer import function_context, review_contexts
from benchmark_fixtures import CASES
from reviewer import added_lines


def inputs(case):
    patch = "".join(unified_diff(
        case.before.splitlines(keepends=True),
        case.after.splitlines(keepends=True),
        fromfile="a/demo.py", tofile="b/demo.py", n=3,
    ))
    additions = list(added_lines(patch))
    expected = [line for line, content in additions if case.target and case.target in content]
    if not additions or len(expected) != bool(case.target):
        raise ValueError(f"Invalid added lines or target for {case.name}")
    return {
        "diff_only": [{"path": "demo.py", "added_lines": [line for line, _ in additions], "source": patch}],
        "function_context": function_context("demo.py", case.after, additions),
    }, expected[0] if expected else None


def score(comment, expected_line, evidence):
    if comment is None:
        return "miss" if expected_line is not None else "clean"
    if (comment["line"] == expected_line
            and re.search(evidence, comment["body"].partition("**Suggested fix:**")[0], re.I)):
        return "hit"
    return "wrong_finding" if expected_line is not None else "false_positive"


def summarize(rows):
    counts = Counter(row["result"] for row in rows)
    hits = counts["hit"]
    findings = hits + counts["wrong_finding"] + counts["false_positive"]
    positives = hits + counts["miss"] + counts["wrong_finding"]
    return {
        "cases": len(rows),
        "correct_findings": hits,
        "missed_bugs": positives - hits,
        "false_positives_on_clean_cases": counts["false_positive"],
        "wrong_findings_on_buggy_cases": counts["wrong_finding"],
        "correctly_silent": counts["clean"],
        "precision": hits / findings if findings else None,
        "recall": hits / positives if positives else None,
        "mean_seconds": round(sum(row["seconds"] for row in rows) / len(rows), 2),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", default="qwen2.5-coder:3b")
    args = parser.parse_args()
    rows = []
    try:
        for case in CASES:
            variants, target_line = inputs(case)
            for mode, contexts in variants.items():
                print(f"Reviewing {case.name} ({mode})", file=sys.stderr, flush=True)
                started = monotonic()
                comment = review_contexts(args.model, contexts)
                rows.append({
                    "case": case.name, "mode": mode, "expected_line": target_line,
                    "result": score(comment, target_line, case.evidence),
                    "seconds": round(monotonic() - started, 3), "comment": comment,
                })
    except RequestException as error:
        print(f"Benchmark stopped because Ollama could not complete a request: {error}", file=sys.stderr)
        return 1

    summary = {
        mode: summarize([row for row in rows if row["mode"] == mode])
        for mode in ("diff_only", "function_context")
    }
    print(json.dumps({"model": args.model, "summary": summary, "cases": rows}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
