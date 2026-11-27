# AI Code Review Bot for GitHub Pull Requests

Milestone 1 connects a signed pull request webhook to an inline comment. The initial reviewer checks added Python lines for a bare except clause. It posts at most one finding per delivery. The optional AI reviewer runs through Ollama on your Mac.

## Run the offline tests

Use Python 3.10 or newer. Inside this directory run `python3 -m unittest -v`. The tests use a simulated GitHub API.

## Connect a demo repository

1. Create a GitHub App. Under repository permissions grant Pull requests read and write. Subscribe to Pull request events. Set a long random webhook secret and install the app on a demo repository.
2. Generate the app private key and keep it outside the project directory. In your terminal set GITHUB_APP_ID, GITHUB_PRIVATE_KEY_PATH and GITHUB_WEBHOOK_SECRET as environment variables.
3. Start the server with the commands below. Configure the app webhook URL to point to an HTTPS deployment or tunnel forwarding to port 8000, with path /webhook and content type application/json.

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m uvicorn app:app --port 8000
```

4. Open a PR that adds the following valid Python to a .py file. Expect a comment on the except line. A separate PR using except ValueError: should receive no comment.

```python
def parse_count(value):
    try:
        return int(value)
    except:
        return 0
```

Rule-only reviews run synchronously. Large reviews may exceed webhook time limits. Redeliveries can duplicate a comment. Queuing and deduplication belong to the reliability milestone. The initial rule uses text matching and can flag matching text in multiline strings.

## Enable the local AI reviewer

The bot checks for a bare except clause first. With `OLLAMA_MODEL` set, a pull request that passes the initial rule can also get an AI review. The bot retrieves Python source at the PR's head commit, extracts whole functions using Python's AST, and asks Ollama for one correctness finding with a trigger, impact, and fix. It validates the path and line before posting. The AI pass inspects up to five Python files and sends at most three functions to the local model. It skips functions longer than the context limit.

1. In the GitHub App settings, open **Permissions & events**, set **Repository permissions → Contents** to **Read-only**, and save. Approve the updated permission for your installation if GitHub asks.
2. Start Ollama on this Mac. In a spare terminal run `ollama pull qwen2.5-coder:3b`. If the CLI cannot connect, open the Ollama app or run `ollama serve` in its own terminal first.
3. In the original bot terminal, stop Uvicorn with Control+C. Keep the GitHub App variables and webhook secret already set in that shell. Then run:

```sh
export OLLAMA_MODEL=qwen2.5-coder:3b
python -m uvicorn app:app --port 8000
```

4. Keep the existing tunnel running. Create a new test PR with the following function and check for a comment that explains what happens when the input is empty.

```python
def mean(values):
    return sum(values) / len(values)
```

When AI review is enabled, the webhook acknowledges the event before the review finishes. Watch the Uvicorn terminal for background errors and allow time for the model to load. The AI comments are best-effort. The background tasks are held in memory. Run the full test suite with `python -m unittest -v` from the virtual environment. The tests simulate model responses.
