import unittest
from datetime import datetime, timezone, timedelta

from src.bitmex import BitMex


class TestBitMex(unittest.TestCase):

    def test_fetch_ohlcv_5m(self):
        bitmex = BitMex(threading=False)
        end_time = datetime.now(timezone.utc)
        start_time = end_time - 5 * timedelta(minutes=5)
        source = bitmex.fetch_ohlcv('5m', start_time, end_time)
        assert len(source) > 1

    def test_fetch_ohlc_2h(self):
        bitmex = BitMex(threading=False)
        end_time = datetime.now(timezone.utc)
        start_time = end_time - 5 * timedelta(hours=2)
        source = bitmex.fetch_ohlcv('2h', start_time, end_time)
        assert len(source) > 1
