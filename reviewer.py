import hashlib
import hmac
import logging
import os
import re
import time
from pathlib import Path


def verified(secret, raw, signature):
    expected = "sha256=" + hmac.new(secret.encode(), raw, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)


def added_lines(patch):
    line = None
    for row in patch.splitlines():
        header = re.match(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,\d+)? @@", row)
        if header:
            line = int(header[1])
        elif line is not None and row.startswith(("+", " ")):
            if row.startswith("+"):
                yield line, row[1:]
            line += 1


def find_comment(files):
    for item in files:
        path = item["filename"]
        if not path.endswith(".py"):
            continue
        for line, content in added_lines(item.get("patch", "")):
            if re.fullmatch(r"\s*except\s*:\s*(?:#.*)?", content):
                return dict(path=path, line=line, side="RIGHT",
                            body="A bare except also catches KeyboardInterrupt and SystemExit. Which exception do you expect here? Catching that type lets the process stop normally.")


def review(event, request, model=None):
    pr = event["pull_request"]
    repository = event["repository"]["full_name"]
    endpoint = f'/repos/{repository}/pulls/{event["number"]}'
    head = pr["head"]["sha"]
    candidates = []
    for page in range(1, 31):
        files = request("GET", f"{endpoint}/files?per_page=100&page={page}")
        comment = find_comment(files)
        if comment:
            break
        if model and len(candidates) < 5:
            for item in files:
                path = item["filename"]
                if not path.endswith(".py") or not item.get("patch"):
                    continue
                additions = list(added_lines(item["patch"]))
                if additions:
                    candidates.append((path, additions))
                if len(candidates) == 5:
                    break
        if len(files) < 100:
            break

    if not comment and candidates:
        from ai_reviewer import review_with_ollama

        comment = review_with_ollama(model, head, repository, candidates, request)
    if comment and request("GET", endpoint)["head"]["sha"] == head:
        request("POST", endpoint + "/comments", json=dict(commit_id=head, **comment))


def github_review(event):
    import jwt
    import requests

    now = int(time.time())
    key = Path(os.environ["GITHUB_PRIVATE_KEY_PATH"]).read_bytes()
    token = jwt.encode(dict(iat=now-60, exp=now+540, iss=os.environ["GITHUB_APP_ID"]), key, algorithm="RS256")
    with requests.Session() as session:
        def request(method, path, **kwargs):
            response = session.request(method, "https://api.github.com" + path, timeout=10, **kwargs)
            response.raise_for_status()
            return response.json()

        session.headers["Authorization"] = "Bearer " + token
        installation = int(event["installation"]["id"])
        access = request("POST", f"/app/installations/{installation}/access_tokens")
        session.headers["Authorization"] = "Bearer " + access["token"]
        review(event, request, model=os.environ.get("OLLAMA_MODEL"))



def background_review(event):
    try:
        github_review(event)
    except Exception:
        logging.getLogger(__name__).exception("Pull request review failed")
