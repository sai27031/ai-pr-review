"""Run a paired review against the local model without GitHub credentials."""
import os

from ai_reviewer import function_context, review_contexts

model = os.environ.get("OLLAMA_MODEL", "qwen2.5-coder:3b")
for name, guard in [("Original", ""), ("Guarded", "    if not values:\n        return None\n")]:
    source = "def average(values):\n" + guard + "    return sum(values) / len(values)\n"
    context = function_context("demo_ai_review.py", source, enumerate(source.splitlines(), 1))
    print(f"{name} ({model})", flush=True)
    comment = review_contexts(model, context)
    if comment:
        print(f"Line {comment['line']}\n{comment['body']}", flush=True)
    else:
        print("No accepted finding", flush=True)
