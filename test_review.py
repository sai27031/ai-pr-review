import hashlib
import hmac
import unittest
from unittest.mock import Mock
from reviewer import find_comment, review, verified

files = [{"filename": "demo.py", "patch": "@@ -5,2 +5,3 @@\n try:\n-old\n+    run()\n+except:"}]
event = {"repository": {"full_name": "demo/repo"}, "number": 3, "pull_request": {"head": {"sha": "abc"}}}


class ReviewTest(unittest.TestCase):
    def test_inline(self):
        api = Mock(side_effect=[files, event["pull_request"], {}])
        review(event, api)
        method, path = api.call_args.args
        self.assertEqual((method, path), ("POST", "/repos/demo/repo/pulls/3/comments"))
        payload = api.call_args.kwargs["json"]
        self.assertEqual((payload["path"], payload["line"], payload["side"], payload["commit_id"]),
                         ("demo.py", 7, "RIGHT", "abc"))

    def test_stale(self):
        api = Mock(side_effect=[files, {"head": {"sha": "new"}}])
        review(event, api)
        self.assertEqual(api.call_count, 2)

    def test_clean(self):
        self.assertIsNone(find_comment([dict(files[0], patch=files[0]["patch"] + " ValueError:")]))

    def test_signature(self):
        sig = "sha256=" + hmac.new(b"secret", b"body", hashlib.sha256).hexdigest()
        self.assertTrue(verified("secret", b"body", sig))
        self.assertFalse(verified("secret", b"changed", sig))
