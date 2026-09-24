import unittest

from ledger import guards, orders


class GuardTests(unittest.TestCase):
    def test_not_released_blocks(self):
        with self.assertRaises(guards.NotReleased):
            guards.check_released(False)

    def test_released_passes(self):
        guards.check_released(True)

    def test_bad_qty_blocks(self):
        for q in (0, -1, 1.5, "2", True):
            with self.assertRaises(guards.BadQuantity):
                guards.check_qty(q)

    def test_submit_sends(self):
        r = orders.submit({"symbol": "NQZ6", "qty": 1, "side": "B"})
        self.assertEqual(r["status"], "sent")
