import argparse
import json
import os
import sys
import threading
import time
from datetime import datetime, timedelta
import numpy as np
import pandas as pd
import bitmex

from bitmex_ws import BitMexWs

class Source:
    Open  = 1
    High  = 2
    Low  = 3
    Close = 4

class Side:
    Long  = "long"
    Short = "short"

DEFAULT_BL   = 999999
DEFAULT_LOT  = 100
DEFAULT_LEVA = 1

OHLC_DIRNAME  = os.path.join(os.path.dirname(__file__), "ohlc/{}")
OHLC_FILENAME = os.path.join(os.path.dirname(__file__), "ohlc/{}/ohlc_{}.csv")

def highest(source, period):
    return pd.rolling_max(source, period, 1)

def lowest(source, period):
    return pd.rolling_min(source, period, 1)

def stdev(source, period):
    return pd.rolling_std(source, period, 1)

def sma(source, period):
    return pd.rolling_mean(source, period, 1)

def delta(tr='1h'):
    if tr == '1d':
        return timedelta(days=1)
    elif tr == '5m':
        return timedelta(minutes=5)
    elif tr == '1m':
        return timedelta(minutes=1)
    else:
        return timedelta(hours=1)

def change_rate(a, b):
    if a > b:
        return a/b
    else:
        return b/a

class BitMex:
    listener = None
    source   = []

    def __init__(self, test=False, timerange='1h'):
        apiKey = os.environ.get('BITMEX_TEST_APIKEY') if test else os.environ.get('BITMEX_APIKEY')
        secret = os.environ.get('BITMEX_TEST_SECRET') if test else os.environ.get('BITMEX_SECRET')
        self.client = bitmex.bitmex(test=test, api_key=apiKey, api_secret=secret)
        self.ws     = BitMexWs()
        self.tr     = timerange

    def current_position(self):
        return self.client.Position.Position_get(filter=json.dumps({'symbol': 'XBTUSD'})).result()[0][0]['currentQty']

    def current_entryprice(self):
        return self.client.Position.Position_get(filter=json.dumps({'symbol': 'XBTUSD'})).result()[0][0]['avgEntryPrice']

    def close_position(self, time=datetime.now()):
        self.client.Order.Order_closePosition(symbol='XBTUSD').result()
        print(str(time) + ' Close Position')

    def trade_fee(self):
        return 0.075/100

    def entry(self, side, size):
        order = self.client.Order.Order_new(symbol='XBTUSD', ordType='Market',
                                    side=side.capitalize(), orderQty=size).result()[0]
        print(str(datetime.now()) + ' Create Order: ' + order['ordType'] + ' ' + order['side'] + ': ' +
              str(order['orderQty']) + ' @ ' + str(order['price']) + ' / ' + order['orderID'])

    def cancel_orders(self):
        orders = self.client.Order.Order_cancelAll().result()[0]
        for order in orders:
            print(str(datetime.now()) + ' Cancel Order: ' + order['ordType'] + ' ' + order['side'] + ': ' +
                  str(order['orderQty']) + ' @ ' + str(order['price']))

    def fetch_ohlc(self, starttime=(datetime.now() + timedelta(days=-20)), endtime=datetime.now()):
        candles = self.client.Trade.Trade_getBucketed(symbol='XBTUSD', binSize=self.tr,
                                                      startTime=starttime, endTime=endtime).result()[0]
        return candles

    def __on_update(self, data):
        self.source.append(data)
        self.source.pop(0)
        print(self.source)

    def on_update(self, listener):
        self.listener = listener
        endtime   = datetime.now() - timedelta(hours=9)
        starttime = endtime - 20 * delta(tr=self.tr)
        self.source = self.fetch_ohlc(starttime=starttime, endtime=endtime)
        print(self.source)
        self.ws.on_update(key=self.tr, func=self.__on_update)

    def print_result(self):
        pass

    def __del__(self):
        self.ws.close()

class BitMexStub(BitMex):
    balance      = DEFAULT_BL
    current_qty  = 0
    entry_price  = 0
    market_price = 0

    ohlc_df      = None
    now_index    = None
    now_time     = None
    order_count  = 0

    win_count    = 0
    lose_count   = 0

    win_profit   = 0
    lose_loss    = 0

    max_drowdown = 0

    buy_signals  = []
    sell_signals = []
    balance_history = []

    def __init__(self, timerange='1h'):
        BitMex.__init__(self, timerange=timerange)
        self.load_ohlc()

    def current_leverage(self):
        return DEFAULT_LEVA

    def current_position(self):
        return self.current_qty

    def current_entryprice(self):
        return self.entry_price

    def close_position(self, time=datetime.now()):
        pos = self.current_qty
        if pos > 0:
            self.entry(side=Side.Short, size=pos)
        elif pos < 0:
            self.entry(side=Side.Long, size=-1*pos)

    def entry(self, side, size):
        if side == Side.Long:
            self.buy_signals.append(self.now_index)
            order_qty = size
        else:
            self.sell_signals.append(self.now_index)
            order_qty = -size

        next_qty = self.current_qty + order_qty

        if (self.current_qty > 0 and order_qty <= 0) or \
                (self.current_qty < 0 and order_qty > 0):

            if self.entry_price > self.market_price:
                close_rate = (self.entry_price - self.market_price) / self.market_price - self.trade_fee()
                profit = -1 * self.current_qty * self.current_qty * close_rate
            else:
                close_rate = (self.market_price - self.entry_price) / self.entry_price - self.trade_fee()
                profit = self.current_qty * self.current_qty * close_rate

            if profit > 0:
                self.win_profit += profit
                self.win_count  += 1
            else:
                self.lose_loss  += -1 * profit
                self.lose_count += 1
                if close_rate > self.max_drowdown:
                    self.max_drowdown = close_rate

            self.balance += profit
            print('{} # Close Position @ {} {} {} {}'.format(self.order_count, side, self.now_time, self.market_price, profit))

        if next_qty != 0:
            print('{} # Create Order   @ {} {} {}'.format(self.order_count, side, self.now_time, self.market_price))

            self.current_qty = next_qty
            self.entry_price = self.market_price

        self.order_count+=1

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
                    self.clean_ohlc()
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
            source.append((row['timestamp'], row['open'], row['close'], row['high'], row['low']))
            self.market_price = row['open']
            self.now_time     = row['timestamp'] + timedelta(hours=9)
            self.now_index    = index
            if len(source) > 20:
                self.listener(source)
                source.pop(0)
            self.balance_history.append(self.balance-DEFAULT_BL)

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

class Bot:
    def __init__(self, lot=DEFAULT_LOT, test=True, params={}):
        self.originallot = lot
        self.is_test = test
        self.params  = params
        if test:
            self.bitmex = BitMexStub()
        else:
            self.bitmex = BitMex(timerange='1m')

    def input(self, title, defval):
        if title in self.params:
            return self.params[title]
        else:
            return defval

    def strategy(self, source):
        open  = np.array([v[Source.Open]  for _, v in enumerate(source[:-1])])
        high  = np.array([v[Source.High]  for _, v in enumerate(source[:-1])])
        low   = np.array([v[Source.Low]   for _, v in enumerate(source[:-1])])
        close = np.array([v[Source.Close] for _, v in enumerate(source[:-1])])

        length = self.input('length', 18)

        is_up = high[-1] == highest(high, length)[-1]
        is_dn = low[-1] == lowest(low, length)[-1]

        pos = self.bitmex.current_position()
        lot = self.originallot

        # エントリー
        if is_up and pos <= 0:
            if pos < 0:
                lot = 2 * self.originallot
            self.bitmex.entry(side=Side.Long, size=lot)
        elif is_dn and pos >= 0:
            if pos > 0:
                lot = 2 * self.originallot
            self.bitmex.entry(side=Side.Short, size=lot)

    def run(self):
        try:
            self.bitmex.on_update(listener=self.strategy)
            self.bitmex.print_result()
            if not self.is_test:
                while True: time.sleep(100)
        except (KeyboardInterrupt, SystemExit):
            self.exit()

    def exit(self):
        self.bitmex.cancel_orders()
        self.bitmex.close_position()
        sys.exit()

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='This is trading script on bitmex')
    parser.add_argument('--debug', default=False, action='store_true')
    args = parser.parse_args()

    bot = Bot(test=args.debug)
    bot.run()
