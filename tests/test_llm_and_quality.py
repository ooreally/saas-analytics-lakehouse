from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from creative_analytics_platform.contracts import load_contract
from creative_analytics_platform.llm import MockLLMProvider
from creative_analytics_platform.quality import find_duplicate_keys, split_valid_invalid


class LlmAndQualityTest(unittest.TestCase):
    def test_mock_llm_classifies_performance_issue(self) -> None:
        provider = MockLLMProvider()
        result = provider.classify_and_summarize(
            "Asset generation was slow for large PSD files.",
            {"priority": "high"},
        )
        self.assertEqual(result["topic"], "performance")
        self.assertEqual(result["sentiment"], "negative")
        self.assertEqual(result["severity_hint"], "high")

    def test_contract_validation_splits_valid_and_invalid(self) -> None:
        contract = load_contract(ROOT / "conf" / "schemas" / "app_events.yml")
        valid, invalid = split_valid_invalid(
            contract,
            [
                {
                    "event_id": "E001",
                    "event_ts": "2026-03-01T00:00:00Z",
                    "user_id": "U001",
                    "workspace_id": "W001",
                    "event_name": "signup",
                },
                {
                    "event_id": "E099",
                    "event_ts": "2026-03-01T00:00:00Z",
                    "user_id": "U001",
                    "workspace_id": "W001",
                    "event_name": "download_export",
                },
            ],
        )
        self.assertEqual(len(valid), 1)
        self.assertEqual(len(invalid), 1)
        self.assertIn("invalid_enum:event_name=download_export", invalid[0]["_validation_errors"])

    def test_duplicate_detection(self) -> None:
        duplicates = find_duplicate_keys(
            [{"ticket_id": "T001"}, {"ticket_id": "T001"}, {"ticket_id": "T002"}],
            ["ticket_id"],
        )
        self.assertEqual(duplicates, {("T001",): 2})


if __name__ == "__main__":
    unittest.main()
