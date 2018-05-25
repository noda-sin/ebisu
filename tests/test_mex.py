import unittest

from src.mex import BitMex


class TestMex(unittest.TestCase):

    def setUp(self):
        self.mex = BitMex('1h', 20, demo=True, run=False)

    def test_get_balance(self):
        balance = self.mex.get_balance()
        self.assertGreater(balance, 0)

    def test_get_leverage(self):
        leverage = self.mex.get_leverage()
        self.assertGreater(leverage, 0)

    def test_get_commission(self):
        commission = self.mex.get_commission()
        self.assertGreater(commission, 0)

    def test_get_position_size(self):
        pos_size = self.mex.get_position_size()
        self.assertIsNotNone(pos_size)

    def test_get_position_avg_price(self):
        avg_price = self.mex.get_position_avg_price()
        self.assertIsNotNone(avg_price)

    def test_get_market_price(self):
        marekt_price = self.mex.get_market_price()
        self.assertGreater(marekt_price, 0)

    def test_close_all(self):
        self.mex.close_all()

    def test_cancel_all(self):
        self.mex.cancel_all()

    def test_entry_limit_order(self):
        market_price = self.mex.get_market_price()
        self.mex.entry("L", True, 100, limit=market_price-100)
        ord_size = self.mex.get_order_size()
        self.assertGreater(ord_size, 0)
        self.mex.cancel_all()
        ord_size = self.mex.get_order_size()
        self.assertEqual(ord_size, 0)

    def test_entry_stop_limit_order(self):
        market_price = self.mex.get_market_price()
        self.mex.entry("L", True, 100, limit=market_price-100, stop=market_price-100)
        ord_size = self.mex.get_order_size()
        self.assertGreater(ord_size, 0)
        self.mex.cancel_all()
        ord_size = self.mex.get_order_size()
        self.assertEqual(ord_size, 0)

    def test_entry_stop_order(self):
        market_price = self.mex.get_market_price()
        self.mex.entry("L", True, 100, stop=market_price-100)
        ord_size = self.mex.get_order_size()
        self.assertGreater(ord_size, 0)
        self.mex.cancel_all()
        ord_size = self.mex.get_order_size()
        self.assertEqual(ord_size, 0)

    def test_entry_market_order(self):
        self.mex.entry("L", True, 100)
        ord_size = self.mex.get_order_size()
        self.assertEqual(ord_size, 0)
        pos_size = self.mex.get_position_size()
        self.assertGreater(pos_size, 0)
        self.mex.close_all()
        pos_size = self.mex.get_position_size()
        self.assertEqual(pos_size, 0)