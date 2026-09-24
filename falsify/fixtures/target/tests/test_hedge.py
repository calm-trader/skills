import unittest

from ledger.hedge import delta_hedge, hedge_qty


class HedgeTests(unittest.TestCase):
    def test_hedge_qty(self):
        self.assertEqual(hedge_qty(2, 0.5), 1.0)
        self.assertEqual(hedge_qty(-4, 0.25), -1.0)

    def test_delta_hedge_offsets(self):
        for d in (3, -7, 0):
            self.assertEqual(delta_hedge(d) + d, 0)
