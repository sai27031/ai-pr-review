import hashlib
import hmac
import json
import os
import re
import time
from pathlib import Path


def verified(secret, raw, signature):
    expected = "sha256=" + hmac.new(secret.encode(), raw, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)


def find_comment(files):
    for item in files:
        path = item["filename"]
        if not path.endswith(".py"):
            continue
        line = None
        for row in item.get("patch", "").splitlines():
            header = re.match(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,\d+)? @@", row)
            if header:
                line = int(header[1])
            elif line is not None and row.startswith(("+", " ")):
                if row.startswith("+") and re.fullmatch(r"\s*except\s*:\s*(?:#.*)?", row[1:]):
                    return dict(path=path, line=line, side="RIGHT",
                                body="A bare except also catches KeyboardInterrupt and SystemExit. Which exception do you expect here? Catching that type lets the process stop normally.")
                line += 1


def review(event, request):
    pr = event["pull_request"]
    endpoint = f'/repos/{event["repository"]["full_name"]}/pulls/{event["number"]}'
    head = pr["head"]["sha"]
    for page in range(1, 31):
        files = request("GET", f"{endpoint}/files?per_page=100&page={page}")
        comment = find_comment(files)
        if comment:
            if request("GET", endpoint)["head"]["sha"] == head:
                request("POST", endpoint + "/comments", json=dict(commit_id=head, **comment))
            return
        if len(files) < 100:
            return


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
        review(event, request)
