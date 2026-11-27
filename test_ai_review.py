import base64
import json
import unittest
from unittest.mock import Mock, patch

from reviewer import review
from test_review import event

SOURCE = "def average(values):\n    return sum(values) / len(values)\n"
FILES = [{"filename": "demo.py", "patch": "@@ -0,0 +1,2 @@\n+def average(values):\n+    return sum(values) / len(values)"}]
CONTENTS = {"encoding": "base64", "content": base64.b64encode(SOURCE.encode()).decode()}


class AIReviewTest(unittest.TestCase):
    def run_review(self, line, head="abc"):
        response = Mock()
        response.json.return_value = {"message": {"content": json.dumps({"findings": [{
            "path": "demo.py",
            "line": line,
            "trigger": "An empty list",
            "impact": "Raises ZeroDivisionError",
            "fix": "Handle an empty list before dividing",
        }]})}}
        github = Mock(side_effect=[FILES, CONTENTS, {"head": {"sha": head}}, {}])
        with patch("ai_reviewer.post", return_value=response) as ollama:
            review(event, github, model="local-test")
        github.assert_any_call("GET", "/repos/demo/repo/contents/demo.py", params={"ref": "abc"})
        prompt = json.loads(ollama.call_args.kwargs["json"]["messages"][1]["content"])
        self.assertEqual(prompt[0]["added_lines"], [1, 2])
        self.assertIn("1: def average(values):", prompt[0]["source"])
        return github

    def test_ai_comment_is_posted_on_added_line(self):
        github = self.run_review(2)
        self.assertEqual(github.call_args.args, ("POST", "/repos/demo/repo/pulls/3/comments"))
        payload = github.call_args.kwargs["json"]
        self.assertEqual((payload["commit_id"], payload["line"]), ("abc", 2))
        self.assertIn("ZeroDivisionError", payload["body"])

    def test_ai_comment_outside_diff_is_discarded(self):
        github = self.run_review(5)
        self.assertEqual(github.call_count, 2)

    def test_ai_comment_on_stale_commit_is_discarded(self):
        github = self.run_review(2, head="new")
        self.assertEqual(github.call_count, 3)
