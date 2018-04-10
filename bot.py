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
DEFAULT_LEVA = 3

OHLC_FILENAME = os.path.join(os.path.dirname(__file__), "ohlc.csv")

def highest(source, period):
    return pd.rolling_max(source, period, 1)

def lowest(source, period):
    return pd.rolling_min(source, period, 1)

def stdev(source, period):
    return pd.rolling_std(source, period, 1)

def sma(source, period):
    return pd.rolling_mean(source, period, 1)

class BitMex:
    listener = None

    def __init__(self, test=True):
        apiKey = os.environ.get('BITMEX_APIKEY') if test else os.environ.get('BITMEX_TEST_APIKEY')
        secret = os.environ.get('BITMEX_SECRET') if test else os.environ.get('BITMEX_TEST_SECRET')
        self.client = bitmex.bitmex(test=test, api_key=apiKey, api_secret=secret)

    def current_position(self):
        return self.client.Position.Position_get(filter=json.dumps({'symbol': 'XBTUSD'})).result()[0][0]['currentQty']

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

    def fetch_ohlc(self, starttime=(datetime.now() + timedelta(days=-30)), endTime=datetime.now()):
        candles = self.client.Trade.Trade_getBucketed(symbol='XBTUSD', binSize='1h',
                                                      startTime=starttime, endTime=endTime).result()[0]
        return candles[:-1]

    def _crawler_run(self):
        dt_prev = datetime.now()
        while True:
            dt_now = datetime.now()
            if dt_now - dt_prev < timedelta(hours=1):
                continue
            try:
                source = self.fetch_ohlc()
                if self.listener is not None:
                    self.listener(source)
            except Exception as e:
                print(e)
                continue
            dt_prev = dt_now

    def on_update(self, listener):
        self.listener = listener
        crawler = threading.Thread(target=self._crawler_run)
        crawler.start()

class BitMexStub(BitMex):
    balance      = DEFAULT_BL
    current_qty  = 0
    entry_price  = 0
    market_price = 0

    now_index    = None
    now_time     = None

    buy_signals  = []
    sell_signals = []
    balance_history = []

    def __init__(self):
        BitMex.__init__(self)
        self.load_ohlc()

    def current_leverage(self):
        return DEFAULT_LEVA

    def current_position(self):
        return self.current_qty

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
            profit = ((self.entry_price - self.market_price) / self.entry_price - self.trade_fee()) * self.current_qty * self.current_leverage()
            self.balance += profit
            print(str(self.now_time) + ' Closed Position @ ' + str(self.balance))

        if next_qty != 0:
            print(str(self.now_time) + ' Create Order: ' + str(next_qty) + ' / ' + str(self.market_price) + ' @ ' + str(self.balance))
            self.current_qty = next_qty
            self.entry_price = self.market_price

    def load_ohlc(self):
        if os.path.exists(OHLC_FILENAME):
            self.ohlc_df = pd.read_csv(OHLC_FILENAME)
            return

        starttime = datetime(year=2017, month=1, day=1, hour=0, minute=0)
        endtime   = datetime(year=2018, month=4, day=1, hour=0, minute=0)

        lefttime  = starttime
        righttime = starttime + 99 * timedelta(hours=1)

        list = []
        while True:
            print('Fetch ohlc ' + str(lefttime) + ' ... ' + str(righttime))
            source = BitMex.fetch_ohlc(self, starttime=lefttime, endTime=righttime)
            list.extend(source)

            lefttime  = lefttime  + 100 * timedelta(hours=1)
            righttime = righttime + 100 * timedelta(hours=1)

            if lefttime < endtime and righttime > endtime:
                righttime = endtime
                continue
            elif lefttime > endtime:
                break
            time.sleep(0.5)

        self.ohlc_df = pd.DataFrame(list)
        self.ohlc_df.to_csv(OHLC_FILENAME)

    def _crawler_run(self):
        source = []
        for index, row in self.ohlc_df.iterrows():
            source.append((row[9], row[7], row[1], row[3], row[6]))
            self.market_price = row[1]
            self.now_index    = index
            self.now_time     = row[9]
            if len(source) > 20:
                self.listener(source)
                source.pop(0)
            self.balance_history.append(self.balance-DEFAULT_BL)

    def on_update(self, listener):
        self.listener = listener
        self._crawler_run()

    def plot_result(self):
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
    def __init__(self, lot=DEFAULT_LOT, test=True):
        self.originallot = lot
        self.is_test = test
        if test:
            self.bitmex = BitMexStub()
        else:
            self.bitmex = BitMex()

    def strategy(self, source):
        open  = np.array([v[Source.Open]  for _, v in enumerate(source)])
        high  = np.array([v[Source.High]  for _, v in enumerate(source)])
        low   = np.array([v[Source.Low]   for _, v in enumerate(source)])
        close = np.array([v[Source.Close] for _, v in enumerate(source)])

        is_up = high[-1] == highest(high, 18)[-1]
        is_dn = low[-1]  == lowest(low, 18)[-1]

        pos = self.bitmex.current_position()
        lot = self.originallot
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
            if self.is_test:
                self.bitmex.plot_result()
            else:
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
