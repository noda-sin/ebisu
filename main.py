import argparse
import json
import os
import sys
import threading
import time

import numpy as np
import talib
import ccxt

OPEN  = 1
HIGH  = 2
LOW   = 3
CLOSE = 4

def trend(arr):
    ret = []
    for i in range(len(arr)):
        if arr[i] > 0:
            ret.append(1)
        elif arr[i] < 0:
            ret.append(-1)
        else:
            ret.append(0)
    return np.array(ret)

def bar_trend(close, open):
    ret = []
    for i in range(len(close)):
        if close[i] > open[i]:
            ret.append(1)
        elif close[i] < open[i]:
            ret.append(-1)
        else:
            ret.append(0)
    return np.array(ret)

def body_trend(close, open, length):
    body = np.abs(close - open)
    abody = talib.SMA(body, timeperiod=length) / 3.0
    ret = []
    for i in range(len(body)):
        if body[i] > abody[i]:
            ret.append(1)
        elif body[i] < abody[i]:
            ret.append(-1)
        else:
            ret.append(0)
    return np.array(ret)

def highest(arr, length):
    ret = []
    for i in range(len(arr)):
        slice = arr[i-length:i]
        if len(slice) != length:
            ret.append(np.nan)
        else:
            ret.append(np.max(slice))
    return  np.array(ret)

def lowest(arr, length):
    ret = []
    for i in range(len(arr)):
        slice = arr[i-length:i]
        if len(slice) != length:
            ret.append(np.nan)
        else:
            ret.append(np.min(slice))
    return  np.array(ret)

class Deepmex:
    def __init__(self, debug=True):
        apiKey = os.environ.get('BITMEX_APIKEY')
        secret = os.environ.get('BITMEX_SECRET')

        if debug:
            apiKey = os.environ.get('BITMEX_TEST_APIKEY')
            secret = os.environ.get('BITMEX_TEST_SECRET')

        bitmex = ccxt.bitmex({
            'apiKey': apiKey,
            'secret': secret,
        })
        if debug:
            bitmex.urls['api'] = bitmex.urls['test']
            bitmex.verbose = True

        self.client = bitmex

    def current_leverage(self):
        return self.current_position()['leverage']

    def has_open_orders(self):
        return len(self.fetch_open_orders()) > 0

    def has_position(self):
        return self.current_position()['currentQty'] != 0

    def current_position(self):
        position = self.client.private_get_position('BTC/USD')[0]
        # print('POS: ' + str(self.client.private_get_position('BTC/USD')))
        return position

    def close_position(self):
        print('--- Closed Position ---')
        position = self.current_position()
        position_size = position['currentQty']
        if position_size == 0:
            return
        side = 'buy' if position_size < 0 else 'sell'
        self.market_order(side=side, size=position_size)
        print('-----------------------')

    def market_last_price(self):
        return self.client.fetch_ticker('BTC/USD')['last']

    def create_order(self, type, side, size, price=0):
        order = self.client.create_order('BTC/USD', type=type, side=side, price=price, amount=size)
        print('Create Order: ' + order['info']['ordType'] + ' ' + order['info']['side'] + ': ' +
              str(order['info']['orderQty']) + ' @ ' + str(order['info']['price']) + ' / ' + order['id'])
        return order

    def limit_order(self, side, price, size):
        return self.create_order(type='limit', side=side, price=price, size=size)

    def market_order(self, side, size):
        return self.create_order(type='market', side=side, size=size)

    def fetch_open_orders(self):
        orders = self.client.fetch_open_orders()
        return orders

    def cancel_orders(self):
        orders = self.fetch_open_orders()
        for order in orders:
            cancel = self.client.cancel_order(order['id'])
            print('Cancel Order: ' + order['info']['ordType'] + ' ' + order['info']['side'] + ': ' +
                  str(order['info']['orderQty']) + ' @ ' + str(order['info']['price']) + ' / ' + order['id'])

    def fetch_ohlc(self):
        timest = self.client.fetch_ticker('BTC/USD')['timestamp'] - 50 * 3600000
        candles = self.client.fetch_ohlcv('BTC/USD', timeframe='1h', since=timest)
        return candles[:-1]

    def opener_run(self):
        while True:
            try:
                if self.has_open_orders():
                    time.sleep(10)
                    continue

                ohlc = self.fetch_ohlc()

                timeperiod = 7
                lot = 20

                open  = np.array([v[OPEN]  for _, v in enumerate(ohlc)])
                high  = np.array([v[HIGH]  for _, v in enumerate(ohlc)])
                low   = np.array([v[LOW]   for _, v in enumerate(ohlc)])
                close = np.array([v[CLOSE] for _, v in enumerate(ohlc)])

                ma   = talib.SMA(close, timeperiod=timeperiod)
                hest = highest(high, timeperiod)
                lest = lowest(low, timeperiod)

                avg  = ((hest + lest) / 2.0 + ma) / 2.0
                val  = talib.SMA(talib.LINEARREG(close - avg, timeperiod=timeperiod), timeperiod=timeperiod)

                trend_1 = trend(val)
                trend_2 = bar_trend(close, open)
                trend_3 = body_trend(close, open, timeperiod)

                up = (trend_1[-1] == 1 and trend_2[-1] == -1 and trend_3[-1] == 1)
                dn = (trend_1[-1] == -1 and trend_2[-1] == 1 and trend_3[-1] == 1)

                position = self.current_position()
                position_size = position['currentQty']

                if up and position_size <= 0:
                    self.market_order('buy', lot)
                elif dn and position_size >= 0:
                    self.market_order('sell', lot)
            except Exception as e:
                print(e)
            time.sleep(10)

    def closer_run(self):
        while True:
            try:
                if not self.has_position():
                    time.sleep(10)
                    continue

                ohlc = self.fetch_ohlc()
                close = np.array([v[CLOSE] for _, v in enumerate(ohlc)])

                position = self.current_position()
                position_size = position['currentQty']
                position_avg_price = position['avgEntryPrice']

                if position_size > 0 and close[-1] > position_avg_price + 20:
                    print('LOSS CUT !!')
                    self.close_position()
                elif position_size < 0 and close[-1] < position_avg_price - 20:
                    print('LOSS CUT !!')
                    self.close_position()
            except Exception as e:
                print(e)
            time.sleep(10)

    def run(self):
        try:
            opener = threading.Thread(target=self.opener_run)
            opener.daemon = True
            opener.start()

            closer = threading.Thread(target=self.closer_run)
            closer.daemon = True
            closer.start()
            while True: time.sleep(100)
        except (KeyboardInterrupt, SystemExit):
            self.exit()

    def exit(self):
        self.cancel_orders()
        self.close_position()
        sys.exit()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='This is trading script on bitmex')
    parser.add_argument('--debug', default=False, action='store_true')
    args = parser.parse_args()

    mex = Deepmex(debug=args.debug)
    mex.run()
