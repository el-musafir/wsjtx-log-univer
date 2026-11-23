"""Headless smoke tests for the GUI data logic of LogsApp.

The window itself needs a display; these tests exercise the data logic
(adding logs, toggling selection, reading, saving) with a mocked root.
"""

import os
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import gui
from adi import QsoRecord, parse_adi_file, write_adi

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SAMPLE_FILE = os.path.join(REPO, "tests", "fixtures", "wsjtx_log.adi")
FIXTURES_DIR = os.path.join(REPO, "tests", "fixtures")


@mock.patch.object(gui, "messagebox")
class GuiLogicTests(unittest.TestCase):
    def setUp(self):
        self.root = mock.MagicMock(name="root")
        self.app = gui.LogsApp(self.root)

    def test_add_files_and_read(self, _messagebox):
        self.assertEqual(self.app.add_files([SAMPLE_FILE]), 1)
        self.assertEqual(len(self.app.rows), 1)
        self.app.read_logs()
        self.assertGreater(self.app.rows[0]["count"], 0)
        self.assertIsNone(self.app.rows[0]["error"])

    def test_add_duplicate_file_only_once(self, _messagebox):
        self.app.add_files([SAMPLE_FILE])
        self.assertEqual(self.app.add_files([SAMPLE_FILE]), 0)
        self.assertEqual(len(self.app.rows), 1)

    def test_toggle(self, _messagebox):
        self.app.add_files([SAMPLE_FILE])
        self.assertTrue(self.app.rows[0]["sel"])
        self.assertFalse(self.app.toggle(path=SAMPLE_FILE))
        self.assertFalse(self.app.rows[0]["sel"])
        self.assertTrue(self.app.toggle(path=SAMPLE_FILE))
        self.assertTrue(self.app.rows[0]["sel"])
        self.assertFalse(self.app.toggle(index=0))
        self.assertTrue(self.app.toggle(index=0))
        self.assertIsNone(self.app.toggle(path="no/such/file.adi"))
        self.assertIsNone(self.app.toggle())

    def test_add_directory(self, _messagebox):
        self.assertGreaterEqual(self.app.add_directory(FIXTURES_DIR), 1)

    def test_save_unified(self, _messagebox):
        with tempfile.TemporaryDirectory() as tmp:
            out = os.path.join(tmp, "unified_log.adi")
            self.app.add_files([SAMPLE_FILE])
            path = self.app.save_unified(out)
            self.assertEqual(path, out)
            self.assertTrue(os.path.exists(out))
            records = parse_adi_file(out)
            self.assertGreater(len(records), 0)
            self.assertTrue(all(r.mode for r in records))
            self.assertTrue(any(r.call == "JA7DXX" for r in records))

    def test_save_unified_honors_selector(self, _messagebox):
        other = os.path.join(
            tempfile.mkdtemp(prefix="wsjtx_test_"), "other.adi")
        record = QsoRecord()
        record["call"] = "ZZ9Z"
        record["qso_date"] = "20250501"
        record["time_on"] = "010101"
        record["band"] = "20M"
        record["mode"] = "FT8"
        write_adi(other, [record])
        with tempfile.TemporaryDirectory() as tmp:
            out = os.path.join(tmp, "unified_log.adi")
            self.app.add_files([SAMPLE_FILE, other])
            self.assertEqual(len(self.app.rows), 2)
            self.assertFalse(self.app.toggle(path=other))  # deselect other
            path = self.app.save_unified(out)
            self.assertEqual(path, out)
            records = parse_adi_file(out)
            self.assertTrue(any(r.call == "JA7DXX" for r in records))
            self.assertFalse(any(r.call == "ZZ9Z" for r in records))

    def test_save_unified_without_selection(self, messagebox):
        with tempfile.TemporaryDirectory() as tmp:
            out = os.path.join(tmp, "unified_log.adi")
            self.app.add_files([SAMPLE_FILE])
            self.assertFalse(self.app.toggle(path=SAMPLE_FILE))
            self.assertIsNone(self.app.save_unified(out))
            self.assertFalse(os.path.exists(out))
            messagebox.showwarning.assert_called()

    def test_read_logs_marks_missing_file(self, _messagebox):
        missing = os.path.join(tempfile.mkdtemp(prefix="wsjtx_test_"),
                               "missing.adi")
        self.app.add_files([missing])
        self.app.read_logs()
        self.assertIsNone(self.app.rows[0]["count"])
        self.assertTrue(self.app.rows[0]["error"])


if __name__ == "__main__":
    unittest.main()
