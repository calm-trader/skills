import os
import tempfile
import unittest

from ledger import capture, status


class CaptureTests(unittest.TestCase):
    def test_capture_writes_rows(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "fills.csv")
            n = capture.capture([{"ts": 1, "symbol": "NQZ6", "qty": 1, "side": "B", "price": 1.0}], path=p)
            self.assertEqual(n, 1)
            with open(p) as fh:
                self.assertEqual(len(fh.read().splitlines()), 2)

    def test_select_keeps_cme(self):
        self.assertEqual(capture.select([{"venue": "CME"}, {"venue": "XNAS"}]), [{"venue": "CME"}])

    def test_status_shape(self):
        self.assertIn("capture", status.status())
