import os
import tempfile
import unittest
from pathlib import Path

from helpers.galileo_api_helpers import (
    get_galileo_log_stream_id,
    get_galileo_project_id,
)
from setup_env import setup_environment


CANONICAL_ENV_KEYS = {
    "GALILEO_DOMAIN",
    "GALILEO_LOG_STREAM",
    "GALILEO_LOG_STREAM_ID",
    "GALILEO_LOG_STREAM_URL",
    "GALILEO_PROJECT",
    "GALILEO_PROJECT_ID",
    "GALILEO_PROJECT_URL",
}


class CanonicalDeploymentTests(unittest.TestCase):
    def setUp(self):
        self.original_cwd = os.getcwd()
        self.original_env = {key: os.environ.get(key) for key in CANONICAL_ENV_KEYS}

    def tearDown(self):
        os.chdir(self.original_cwd)
        for key, value in self.original_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

    def test_ids_short_circuit_api_discovery(self):
        os.environ.update(
            {
                "GALILEO_PROJECT": "project-name",
                "GALILEO_PROJECT_ID": "project-id",
                "GALILEO_LOG_STREAM": "stream-name",
                "GALILEO_LOG_STREAM_ID": "stream-id",
            }
        )
        self.assertEqual(get_galileo_project_id("project-name"), "project-id")
        self.assertEqual(
            get_galileo_log_stream_id("project-id", "stream-name"),
            "stream-id",
        )

    def test_canonical_metadata_only_overrides_its_target_domain(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / ".streamlit").mkdir()
            (root / ".streamlit" / "secrets.toml").write_text(
                "\n".join(
                    [
                        'galileo_api_key = "test-key"',
                        'galileo_console_url = "https://console.example.test/"',
                        'galileo_domain = "healthcare"',
                        'galileo_project = "canonical-project"',
                        'galileo_project_id = "project-id"',
                        'galileo_project_url = "https://console.example.test/project/project-id"',
                        'galileo_log_stream = "canonical-stream"',
                        'galileo_log_stream_id = "stream-id"',
                        'galileo_log_stream_url = "https://console.example.test/project/project-id/log-streams/stream-id"',
                    ]
                ),
                encoding="utf-8",
            )
            os.chdir(root)

            setup_environment(
                "healthcare",
                {"galileo": {"project": "yaml-project", "log_stream": "yaml-stream"}},
            )
            self.assertEqual(os.environ["GALILEO_PROJECT"], "canonical-project")
            self.assertEqual(os.environ["GALILEO_LOG_STREAM"], "canonical-stream")
            self.assertEqual(os.environ["GALILEO_PROJECT_ID"], "project-id")
            self.assertEqual(os.environ["GALILEO_LOG_STREAM_ID"], "stream-id")

            setup_environment(
                "bank",
                {"galileo": {"project": "bank-project", "log_stream": "bank-stream"}},
            )
            self.assertEqual(os.environ["GALILEO_PROJECT"], "bank-project")
            self.assertEqual(os.environ["GALILEO_LOG_STREAM"], "bank-stream")
            self.assertNotIn("GALILEO_PROJECT_ID", os.environ)
            self.assertNotIn("GALILEO_LOG_STREAM_ID", os.environ)


if __name__ == "__main__":
    unittest.main()
