# coding: UTF-8

import os
from datetime import timedelta, datetime
import time
import pandas as pd
from mex_stub import BitMexStub

from mex import BitMex
from util import Side, change_rate, delta

OHLC_DIRNAME  = os.path.join(os.path.dirname(__file__), "ohlc/{}")
OHLC_FILENAME = os.path.join(os.path.dirname(__file__), "ohlc/{}/ohlc_{}.csv")

class BitMexTest(BitMexStub):
    periods      = 20

    price        = 0

    ohlc_df      = None
    index        = None
    time         = None
    order_count  = 0

    buy_signals  = []
    sell_signals = []
    balance_history = []

    start_balance = 0

    def __init__(self, timerange='1h', periods=20):
        BitMexStub.__init__(self, timerange=timerange, notify=False)
        self.load_ohlc()
        self.start_balance = self.wallet_balance()
        self.periods = periods

    def market_price(self):
        return self.price

    def now_time(self):
        return self.time

    def entry(self, side, size):
        BitMexStub.entry(self, side, size)

        if side == Side.Long:
            self.buy_signals.append(self.index)
        else:
            self.sell_signals.append(self.index)

    def clean_ohlc(self):
        source = []
        for index, row in self.ohlc_df.iterrows():
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
            open      = prev_row['open'] if change_rate(prev_row['open'], row['open']) > 1.5 else row['open']
            close     = prev_row['close'] if change_rate(prev_row['close'], row['close']) > 1.5 else row['close']
            high      = prev_row['high'] if change_rate(prev_row['high'], row['high']) > 1.5 else row['high']
            low       = row['low']

            source.append({'timestamp': timestamp, 'open': open, 'close': close, 'high': high, 'low': low})

        source = pd.DataFrame(source)
        self.ohlc_df = pd.DataFrame({
            'timestamp': pd.to_datetime(source['timestamp']),
            'open':  source['open'],
            'close': source['close'],
            'high':  source['high'],
            'low':   source['low']
        })
        self.ohlc_df.index = self.ohlc_df['timestamp']

    def load_ohlc(self):
        i = 0
        if os.path.exists(OHLC_FILENAME.format(self.tr, i)):
            while True:
                filename = OHLC_FILENAME.format(self.tr, i)
                if os.path.exists(filename) and self.ohlc_df is None:
                    self.ohlc_df = pd.read_csv(filename)
                    i += 1
                elif os.path.exists(filename):
                    self.ohlc_df = pd.concat([self.ohlc_df, pd.read_csv(filename)], ignore_index=True)
                    i += 1
                else:
                    # self.clean_ohlc()
                    return

        os.makedirs(OHLC_DIRNAME.format(self.tr))

        starttime = datetime(year=2017, month=1, day=1, hour=0, minute=0)
        endtime   = datetime(year=2018, month=4, day=1, hour=0, minute=0)

        lefttime  = starttime
        righttime = starttime + 99 * delta(tr=self.tr)

        list = []
        while True:
            try:
                source = BitMex.fetch_ohlc(self, starttime=lefttime, endtime=righttime)
            except Exception as e:
                print(e)
                time.sleep(60)
                continue

            list.extend(source)

            lefttime  = lefttime  + 100 * delta(tr=self.tr)
            righttime = righttime + 100 * delta(tr=self.tr)

            if lefttime < endtime and righttime > endtime:
                righttime = endtime
            elif lefttime > endtime:
                df = pd.DataFrame(list)
                df.to_csv(OHLC_FILENAME.format(self.tr, i))
                break

            time.sleep(2)

            if len(list) > 65000:
                df = pd.DataFrame(list)
                df.to_csv(OHLC_FILENAME.format(self.tr, i))
                list = []
                i += 1

        self.load_ohlc()

    def __crawler_run(self):
        source = []
        for index, row in self.ohlc_df.iterrows():
            source.append(row)
            self.price        = row['open']
            self.time         = row['timestamp']
            self.index        = index
            if len(source) > self.periods:
                self.listener(source)
                source.pop(0)
            self.balance_history.append(self.balance-self.start_balance)

    def on_update(self, listener):
        self.listener = listener
        self.__crawler_run()

    def print_result(self):
        print('#--------------------------------------------------------')
        print('# トレード回数 : {}'.format(self.order_count))
        print('# 勝率 : {} %'.format((self.win_count)/(self.win_count+self.lose_count)*100))
        print('# プロフィッットファクター : {}'.format((self.win_profit)/(self.lose_loss)))
        print('# 最大ドローダウン : {}'.format((self.max_drowdown) * 100))
        print('#--------------------------------------------------------')

        import matplotlib.pyplot as plt
        plt.figure()
        plt.subplot(211)
        plt.plot(self.ohlc_df.index, self.ohlc_df["high"])
        plt.plot(self.ohlc_df.index, self.ohlc_df["low"])
        plt.ylabel("Price(USD)")
        ymin = min(self.ohlc_df["low"]) - 200
        ymax = max(self.ohlc_df["high"]) + 200
        plt.vlines(self.buy_signals,  ymin, ymax, "blue", linestyles='dashed', linewidth=1)
        plt.vlines(self.sell_signals, ymin, ymax, "red",  linestyles='dashed', linewidth=1)
        plt.subplot(212)
        plt.plot(self.ohlc_df.index, self.balance_history)
        plt.hlines(y=0, xmin=self.ohlc_df.index[0], xmax=self.ohlc_df.index[-1], colors='k', linestyles='dashed')
        plt.ylabel("PL(USD)")
        plt.show()

