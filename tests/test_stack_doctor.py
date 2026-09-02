import os
import unittest

from plugins.stack_doctor import COMPONENTS, stack_status


class StackDoctorTests(unittest.TestCase):
    def test_status_mentions_every_component(self):
        text = stack_status()
        self.assertIsInstance(text, str)
        for keyword in COMPONENTS:
            self.assertIn(keyword, text)

    def test_offline_degrades_without_raising(self):
        old = {key: os.environ.get(key) for key in ("GBRAIN_URL", "ROUTER_URL")}
        os.environ["GBRAIN_URL"] = "http://9.9.9.9:1/api/health"
        os.environ["ROUTER_URL"] = "http://9.9.9.9:1/api/health"
        try:
            text = stack_status()
        finally:
            for key, value in old.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value
        self.assertIsInstance(text, str)
        self.assertIn("❌", text)

    def test_env_overrides_are_honored(self):
        old = os.environ.get("STACK_REPO")
        os.environ["STACK_REPO"] = "/nonexistent-repo-xyz"
        try:
            text = stack_status()
        finally:
            if old is None:
                os.environ.pop("STACK_REPO", None)
            else:
                os.environ["STACK_REPO"] = old
        self.assertIn("gbrain checkout: unknown", text)


if __name__ == "__main__":
    unittest.main()
