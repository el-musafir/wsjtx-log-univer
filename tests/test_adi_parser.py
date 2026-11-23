"""Unit tests for the ADIF parser/writer (adi.py) and the unify logic."""

import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from adi import (
    AdifParseError,
    QsoRecord,
    parse_adi_file,
    parse_adi_text,
    render_record,
    write_adi,
)
from unify import unify_records

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SAMPLE_FILE = os.path.join(REPO, "tests", "fixtures", "wsjtx_log.adi")


class ParserFixtureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.records = parse_adi_file(SAMPLE_FILE)

    def test_fixture_has_records(self):
        self.assertGreaterEqual(len(self.records), 20)

    def test_ft8_fields(self):
        rec = self.records[0]
        self.assertEqual(rec.call, "JA7DXX")
        self.assertEqual(rec.mode, "FT8")
        self.assertIsNone(rec.get("submode"))
        self.assertEqual(rec.get("qso_date"), "20250504")
        self.assertEqual(rec.get("time_on"), "194945")
        self.assertEqual(rec.band, "20M")
        self.assertEqual(rec.get("freq"), "14.074849")
        self.assertEqual(rec.get("station_callsign"), "DF3TN")
        self.assertEqual(rec.get("my_gridsquare"), "JN49")
        self.assertEqual(rec.get("time_off"), "194945")

    def test_ft4_mfsk_normalization(self):
        ft4 = [r for r in self.records if r.mode == "FT4"]
        self.assertTrue(ft4)
        rec = ft4[0]
        # Raw WSJT-X representation is kept in the record...
        self.assertEqual(rec.get("mode"), "MFSK")
        self.assertEqual(rec.get("submode"), "FT4")
        # ...and the effective mode is "FT4".
        self.assertEqual(rec.mode, "FT4")

    def test_empty_gridsquare(self):
        self.assertEqual(self.records[0].get("gridsquare"), "")

    def test_gridsquare_present(self):
        self.assertEqual(self.records[1].get("gridsquare"), "OL72")

    def test_compound_callsigns(self):
        calls = {r.call for r in self.records}
        self.assertIn("D95IGN/P", calls)


class ParserEdgeCaseTests(unittest.TestCase):
    def test_header_tags_skipped(self):
        text = ("ADIF Export\n"
                "<adif_ver:5>3.1.1\n"
                "<created_timestamp:15>20250504 194948\n"
                "<eoh>\n"
                "<call:3>ABC <qso_date:8>20250504 <eor>\n")
        records = parse_adi_text(text)
        self.assertEqual([r.call for r in records], ["ABC"])
        self.assertNotIn("adif_ver", records[0])

    def test_eof_terminator(self):
        records = parse_adi_text("<eoh>\n<call:3>XYZ <qso_date:8>20250501 <eof>\n")
        self.assertEqual(records[0].call, "XYZ")

    def test_no_header_at_all(self):
        records = parse_adi_text(
            "<call:2>AB <band:3>20m <eor>\n<call:2>CD <eor>\n")
        self.assertEqual([r.call for r in records], ["AB", "CD"])

    def test_junk_between_tags(self):
        records = parse_adi_text("<eoh><call:2>AB junk<qso_date:8>20250506<eor>")
        self.assertEqual(records[0].call, "AB")
        self.assertEqual(records[0].get("qso_date"), "20250506")

    def test_truncated_file_is_tolerated(self):
        # No <eor> terminator at the end: the record is still returned.
        records = parse_adi_text("<eoh><call:2>AB <band:3>20m")
        self.assertEqual(records[0].call, "AB")
        self.assertEqual(records[0].get("band"), "20m")

    def test_length_overrun_is_tolerated(self):
        # A length that runs past the end of the file is clipped to the
        # available text; parsing still yields the record.
        records = parse_adi_text("<eoh><call:9>AB")
        self.assertEqual(records[0].call, "AB")

    def test_missing_file(self):
        with self.assertRaises(AdifParseError):
            parse_adi_file(os.path.join(REPO, "tests", "fixtures", "nope.adi"))


class WriteTests(unittest.TestCase):
    def test_write_and_reparse_roundtrip(self):
        records = parse_adi_file(SAMPLE_FILE)
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "unified.adi")
            write_adi(path, records)
            again = parse_adi_file(path)
        self.assertEqual(len(records), len(again))
        for rec_a, rec_b in zip(records, again):
            self.assertEqual(rec_a.call, rec_b.call)
            self.assertEqual(rec_a.mode, rec_b.mode)
            self.assertEqual(rec_a.get("qso_date"), rec_b.get("qso_date"))
            self.assertEqual(rec_a.get("time_on"), rec_b.get("time_on"))
            self.assertEqual(rec_a.band, rec_b.band)
            self.assertEqual(rec_a.get("freq"), rec_b.get("freq"))

    def test_output_format(self):
        record = QsoRecord()
        record["call"] = "JA7DXX"
        record["mode"] = "FT8"
        record["qso_date"] = "20250504"
        text = render_record(record)
        self.assertIn("<call:6>JA7DXX", text)
        self.assertIn("<mode:3>FT8", text)
        self.assertTrue(text.endswith("<eor>"))


class UnifyTests(unittest.TestCase):
    @staticmethod
    def rec(call, date, time, band, mode="FT8", grid="", time_off=""):
        r = QsoRecord()
        r["call"] = call
        r["qso_date"] = date
        r["time_on"] = time
        r["band"] = band
        r["mode"] = mode
        if grid:
            r["gridsquare"] = grid
        if time_off:
            r["time_off"] = time_off
        return r

    def test_sorts_by_date_and_time(self):
        records = [
            self.rec("BV1EK", "20250511", "211430", "20M"),
            self.rec("JA7DXX", "20250504", "194945", "20M"),
            self.rec("AA1A", "20250504", "000001", "15M"),
        ]
        unified, removed = unify_records(records, dedupe=False, sort=True)
        self.assertEqual(removed, 0)
        self.assertEqual([r.call for r in unified], ["AA1A", "JA7DXX", "BV1EK"])

    def test_dedupes_exact_duplicates(self):
        records = [
            self.rec("BV1EK", "20250511", "211430", "20M"),
            self.rec("BV1EK", "20250511", "211430", "20M"),
            self.rec("BV1EK", "20250511", "211431", "20M"),  # other time
        ]
        unified, removed = unify_records(records, dedupe=True, sort=False)
        self.assertEqual(removed, 1)
        self.assertEqual(len(unified), 2)

    def test_merges_details_from_duplicates(self):
        base = self.rec("JA7DXX", "20250504", "194945", "20M")
        dupe = self.rec("JA7DXX", "20250504", "194945", "20M",
                        grid="JO60", time_off="194945")
        unified, removed = unify_records([base, dupe], dedupe=True, sort=False)
        self.assertEqual(removed, 1)
        self.assertEqual(len(unified), 1)
        self.assertEqual(unified[0]["gridsquare"], "JO60")
        self.assertEqual(unified[0]["time_off"], "194945")

    def test_no_dedupe_keeps_all(self):
        records = [
            self.rec("BV1EK", "20250511", "211430", "20M"),
            self.rec("BV1EK", "20250511", "211430", "20M"),
        ]
        unified, removed = unify_records(records, dedupe=False, sort=False)
        self.assertEqual(removed, 0)
        self.assertEqual(len(unified), 2)

    def test_fixture_unifies_to_expected_counts(self):
        records = parse_adi_file(SAMPLE_FILE)
        unified, removed = unify_records(records, dedupe=True, sort=True)
        self.assertEqual(len(records), 24)
        self.assertEqual(removed, 1)  # the duplicated ER0ITU
        self.assertEqual(len(unified), 23)
        modes = {r.mode for r in unified}
        self.assertIn("FT8", modes)
        self.assertIn("FT4", modes)


if __name__ == "__main__":
    unittest.main()
