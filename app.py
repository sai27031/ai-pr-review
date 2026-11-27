import json
import os

from fastapi import FastAPI, HTTPException, Request
from starlette.concurrency import run_in_threadpool

from reviewer import github_review, verified

app = FastAPI()
secret = os.environ["GITHUB_WEBHOOK_SECRET"]
if not secret:
    raise RuntimeError("Set GITHUB_WEBHOOK_SECRET")


@app.post("/webhook")
async def webhook(request: Request):
    raw = await request.body()
    if not verified(secret, raw, request.headers.get("x-hub-signature-256", "")):
        raise HTTPException(401, "Invalid signature")
    if request.headers.get("x-github-event") == "pull_request":
        event = json.loads(raw)
        if event["action"] in {"opened", "reopened", "synchronize"}:
            await run_in_threadpool(github_review, event)
    return {"received": True}
