import os
import unittest
from datetime import datetime, timezone, timedelta

import pandas as pd

from src import load_data, resample
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

    def test_combine_data(self):
        file = os.path.join(os.path.dirname(__file__), "ohlc/2h_ohlcv.csv")
        data = load_data(file)

        file = os.path.join(os.path.dirname(__file__), "ohlc/1h_ohlcv.csv")
        new_data = load_data(file)

        print(data)
        print(new_data)
        combine_data = pd.concat([data, new_data])
        print(combine_data)

        print(resample(combine_data, '2h') == data)

        print(combine_data.last)