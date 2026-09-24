import unittest

from ledger import adapter, positions


class PositionTests(unittest.TestCase):
    def test_signed(self):
        self.assertEqual(positions.signed_qty(3, 1), 3)
        self.assertEqual(positions.signed_qty(3, -1), -3)

    def test_adapter_maps_sides(self):
        p = adapter.fill_to_position({"symbol": "NQZ6", "qty": 2, "side": "B"})
        self.assertEqual(p["side"], adapter.SIDE["B"])
