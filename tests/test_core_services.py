import unittest

from services.config_store import normalize_sop_code_display, normalize_sop_code_value
from services.excel_exporter import _parse_hours_to_minutes
from services.file_processor import classify_source_file, is_allowed_file
from services.session_store import build_session_id, is_valid_session_id


class FileIntakeTests(unittest.TestCase):
    def test_public_intake_formats_match_the_application_contract(self) -> None:
        for filename in ("card.pdf", "card.jpg", "card.jpeg", "card.png", "card.heic"):
            with self.subTest(filename=filename):
                self.assertTrue(is_allowed_file(filename))

        for filename in ("card.xlsx", "card.xls", "card.txt", "card.exe"):
            with self.subTest(filename=filename):
                self.assertFalse(is_allowed_file(filename))

    def test_source_classification_is_conservative(self) -> None:
        self.assertEqual(classify_source_file("attendance_table.png"), "multi_worker_attendance_table")
        self.assertEqual(classify_source_file("printed_export.pdf"), "pdf_or_excel_style")
        self.assertEqual(classify_source_file("worker_timecard.jpg"), "physical_time_card")


class NormalizationTests(unittest.TestCase):
    def test_sop_codes_have_stable_comparison_and_display_forms(self) -> None:
        self.assertEqual(normalize_sop_code_value("  Medical   Leave "), "medical leave")
        self.assertEqual(normalize_sop_code_display("  Medical   Leave "), "Medical Leave")

    def test_hours_are_converted_to_minutes(self) -> None:
        self.assertEqual(_parse_hours_to_minutes("8h 30m"), 510)
        self.assertEqual(_parse_hours_to_minutes("45m"), 45)
        self.assertEqual(_parse_hours_to_minutes("invalid"), 0)


class SessionContractTests(unittest.TestCase):
    def test_session_ids_use_a_bounded_year_month_shape(self) -> None:
        self.assertEqual(build_session_id(2026, 7), "2026-07")
        self.assertTrue(is_valid_session_id("2026-07"))
        self.assertFalse(is_valid_session_id("2026-7"))
        self.assertFalse(is_valid_session_id("../../etc"))


if __name__ == "__main__":
    unittest.main()
