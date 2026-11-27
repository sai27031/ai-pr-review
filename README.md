# AI Code Review Bot for GitHub Pull Requests

Milestone 1 connects a signed pull request webhook to an inline comment. The initial reviewer checks added Python lines for a bare except clause. It posts at most one finding per delivery. The LLM reviewer is planned for milestone 2.

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

This prototype processes events synchronously. Large reviews may exceed webhook time limits, and redeliveries can duplicate a comment. Queuing and deduplication belong to the reliability milestone. The initial rule uses text matching and can flag matching text in multiline strings.
