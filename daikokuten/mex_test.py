# coding: UTF-8

import os
import time
from datetime import timedelta, datetime

import pandas as pd

from daikokuten import change_rate, delta, gen_ohlcv
from daikokuten.mex import BitMex
from daikokuten.mex_stub import BitMexStub

OHLC_DIRNAME = os.path.join(os.path.dirname(__file__), "../ohlc/{}")
OHLC_FILENAME = os.path.join(os.path.dirname(__file__), "../ohlc/{}/ohlc_{}.csv")


class BitMexTest(BitMexStub):
    market_price = 0

    ohlcv_data_frame = None
    index = None
    time = None
    order_count = 0

    buy_signals = []
    sell_signals = []
    balance_history = []

    start_balance = 0

    def __init__(self, tr, periods):
        BitMexStub.__init__(self, tr, periods, run=False)
        self.load_ohlcv()
        self.start_balance = self.get_balance()

    def get_market_price(self):
        return self.market_price

    def now_time(self):
        return self.time

    def entry(self, id, long, qty, limit=0, stop=0, when=True):
        BitMexStub.entry(self, id, long, qty, limit, stop, when)

        if long:
            self.buy_signals.append(self.index)
        else:
            self.sell_signals.append(self.index)

    def __crawler_run(self):
        source = []
        for index, row in self.ohlcv_data_frame.iterrows():
            source.append(row)
            self.market_price = row['open']
            self.time = row['timestamp']
            self.index = index
            if len(source) > self.periods:
                open, close, high, low = gen_ohlcv(source)
                self.listener(open, close, high, low)
                source.pop(0)
            self.balance_history.append(self.get_balance() - self.start_balance)
        self.close_all()

    def on_update(self, listener):
        BitMexStub.on_update(self, listener)
        self.__crawler_run()

    def clean_ohlcv(self):
        source = []
        for index, row in self.ohlcv_data_frame.iterrows():
            if len(source) == 0:
                source.append({
                    'timestamp': row['timestamp'][:-6],
                    'open': row['open'],
                    'close': row['close'],
                    'high': row['high'],
                    'low': row['low']
                })
                continue

            prev_row = source[-1]

            timestamp = row['timestamp'][:-6]
            open = prev_row['open'] if change_rate(prev_row['open'], row['open']) > 1.5 else row['open']
            close = prev_row['close'] if change_rate(prev_row['close'], row['close']) > 1.5 else row['close']
            high = prev_row['high'] if change_rate(prev_row['high'], row['high']) > 1.5 else row['high']
            low = row['low']

            source.append({'timestamp': timestamp, 'open': open, 'close': close, 'high': high, 'low': low})

        source = pd.DataFrame(source)
        self.ohlcv_data_frame = pd.DataFrame({
            'timestamp': pd.to_datetime(source['timestamp']),
            'open': source['open'],
            'close': source['close'],
            'high': source['high'],
            'low': source['low']
        })
        self.ohlcv_data_frame.index = self.ohlcv_data_frame['timestamp']

    def load_ohlcv(self):
        i = 0
        if os.path.exists(OHLC_FILENAME.format(self.tr, i)):
            while True:
                filename = OHLC_FILENAME.format(self.tr, i)
                if os.path.exists(filename) and self.ohlcv_data_frame is None:
                    self.ohlcv_data_frame = pd.read_csv(filename)
                    i += 1
                elif os.path.exists(filename):
                    self.ohlcv_data_frame = pd.concat([self.ohlcv_data_frame, pd.read_csv(filename)], ignore_index=True)
                    i += 1
                else:
                    self.clean_ohlcv()
                    return

        os.makedirs(OHLC_DIRNAME.format(self.tr))

        if self.tr == '1d' or self.tr == '1h' or self.tr == '2h':
            start_time = datetime(year=2017, month=1, day=1, hour=0, minute=0)
        elif self.tr == '5m':
            start_time = datetime.now() - timedelta(days=31)
        else:
            start_time = datetime.now() - timedelta(days=31)

        end_time = datetime.now()

        left_time = start_time
        right_time = start_time + 99 * delta(tr=self.tr)
        if self.tr == '2h':
            right_time = start_time + 99 * delta(tr='1h')

        list = []
        while True:
            try:
                source = BitMex.fetch_ohlcv(self, start_time=left_time, end_time=right_time)
            except Exception as e:
                print(e)
                time.sleep(60)
                continue

            list.extend(source)

            left_time = left_time + 100 * delta(tr=self.tr)
            right_time = right_time + 100 * delta(tr=self.tr)
            if self.tr == '2h':
                left_time = left_time + 100 * delta(tr='1h')
                right_time = right_time + 100 * delta(tr='1h')

            if left_time < end_time < right_time:
                right_time = end_time
            elif left_time > end_time:
                df = pd.DataFrame(list)
                df.to_csv(OHLC_FILENAME.format(self.tr, i))
                break

            time.sleep(2)

            if len(list) > 65000:
                df = pd.DataFrame(list)
                df.to_csv(OHLC_FILENAME.format(self.tr, i))
                list = []
                i += 1

        self.load_ohlcv()

    def show_result(self):
        import matplotlib.pyplot as plt
        plt.figure()
        plt.subplot(211)
        plt.plot(self.ohlcv_data_frame.index, self.ohlcv_data_frame["high"])
        plt.plot(self.ohlcv_data_frame.index, self.ohlcv_data_frame["low"])
        plt.ylabel("Price(USD)")
        ymin = min(self.ohlcv_data_frame["low"]) - 200
        ymax = max(self.ohlcv_data_frame["high"]) + 200
        plt.vlines(self.buy_signals, ymin, ymax, "blue", linestyles='dashed', linewidth=1)
        plt.vlines(self.sell_signals, ymin, ymax, "red", linestyles='dashed', linewidth=1)
        plt.subplot(212)
        plt.plot(self.ohlcv_data_frame.index, self.balance_history)
        plt.hlines(y=0, xmin=self.ohlcv_data_frame.index[0],
                   xmax=self.ohlcv_data_frame.index[-1], colors='k', linestyles='dashed')
        plt.ylabel("PL(USD)")
        plt.show()
