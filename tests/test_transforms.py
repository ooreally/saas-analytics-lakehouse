from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from creative_analytics_platform.transforms import dedupe_records, mask_email, normalize_plan_tier, sanitize_user_record


class TransformHelpersTest(unittest.TestCase):
    def test_dedupe_keeps_latest_loaded_record(self) -> None:
        records = [
            {"event_id": "E024", "_loaded_at": "2026-03-05T09:55:00+00:00", "event_value": "2"},
            {"event_id": "E024", "_loaded_at": "2026-03-05T10:05:00+00:00", "event_value": "3"},
        ]
        deduped = dedupe_records(records, ["event_id"], "_loaded_at")
        self.assertEqual(len(deduped), 1)
        self.assertEqual(deduped[0]["event_value"], "3")

    def test_user_sanitization_masks_email_and_name(self) -> None:
        record = {
            "user_id": "U001",
            "email": "alice@example.com",
            "full_name": "Alice Rao",
            "acquisition_channel": " Paid Search ",
        }
        cleaned = sanitize_user_record(record)
        self.assertEqual(cleaned["email"], "a***@example.com")
        self.assertEqual(cleaned["full_name"], "user_u001")
        self.assertEqual(cleaned["acquisition_channel"], "paid search")

    def test_plan_tier_normalization(self) -> None:
        self.assertEqual(normalize_plan_tier("pro"), "professional")
        self.assertEqual(normalize_plan_tier("starter"), "starter")
        self.assertEqual(mask_email(""), "")


if __name__ == "__main__":
    unittest.main()
