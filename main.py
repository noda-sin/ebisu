import argparse
import json
import os
import sys
import threading
import time

import ccxt
import requests

class Deepmex:
    def __init__(self, size, periods=60*24, debug=True):
        bitmex = ccxt.bitmex({
            'apiKey': os.environ.get('BITMEX_APIKEY'),
            'secret': os.environ.get('BITMEX_SECRET'),
        })
        if debug:
            bitmex.urls['api'] = bitmex.urls['test']
            bitmex.verbose = True

        self.order_size = size
        self.periods = periods
        self.client = bitmex

    def current_leverage(self):
        return self.current_position()['leverage']

    def has_open_orders(self):
        return len(self.fetch_open_orders()) > 0

    def has_position(self):
        return self.current_position()['currentQty'] != 0

    def current_position(self):
        position = self.client.private_get_position()[0]
        return position

    def close_position(self):
        position = self.current_position()
        position_size = position['currentQty']
        if position_size == 0:
            return
        side = 'buy' if position_size < 0 else 'sell'
        self.market_order(side=side, size=position_size)
        print('Closed Position')

    def market_last_price(self):
        return self.client.fetch_ticker('BTC/USD')['last']

    def create_order(self, type, side, size, price=0):
        order = self.client.create_order('BTC/USD', type=type, side=side, price=price, amount=size)
        print('Created Order: ' + order['info']['ordType'] + ' ' + order['info']['side'] + ': ' +
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
        for o in orders:
            cancel = self.client.cancel_order(o['id'])
            print(cancel)
            print(cancel['status'] + ' ' + cancel['id'])

    def fetch_ohlc(self, periods='1h'):
        timest = self.client.fetch_ticker('BTC/USD')['timestamp']
        if periods == '3m':
            timest = timest - 3 * 3 * 60
        elif periods == '1h':
            timest = timest - 3 * 3600000
        else:
            timest = timest - 3 * 3600000 * 24

        candles = self.client.fetch_ohlcv('BTC/USD', timeframe=periods, since=timest)
        for c in candles:
            print(c)

        return candles[0], candles[1]

    def calc_pivot(self):
        curr_ohlc, prev_ohlc = self.fetch_ohlc(periods=self.periods)

        prev_high = prev_ohlc[2]
        prev_low = prev_ohlc[3]
        prev_close = prev_ohlc[4]

        pivot = round((prev_high + prev_low + prev_close) / 3, 1)
        r3 = round(prev_high + 2 * (pivot - prev_low))
        r2 = round(pivot + (prev_high - prev_low))
        r1 = round((2 * pivot) - prev_low)
        s1 = round((2 * pivot) - prev_high)
        s2 = round(pivot - (prev_high - prev_low))
        s3 = round(prev_low - 2 * (prev_high - pivot))

        high = curr_ohlc[2]
        low = curr_ohlc[3]

        r = r1
        s = s1

        if r1 < high:
            r = r2
        if r2 < high:
            r = r3

        if s1 > low:
            s = s2
        if s2 > low:
            s = s3

        return r, pivot, s

    def opener_run(self):
        while True:
            try:
                if self.has_open_orders() or self.has_position():
                    time.sleep(10)
                    continue

                r, p, s = self.calc_pivot()

                self.limit_order(side='sell', price=r, size=self.order_size)
                self.limit_order(side='buy', price=s, size=self.order_size)

                leverage = self.current_leverage()
                prev_range=(r-s)/r*100

                print("Leverage: ", leverage)
                print("Periods: ", self.periods)
                print("R: ", r)
                print("S: ", s)
                print("Prev Range %: ", prev_range)

                self.close_percent = prev_range / 3.0 * leverage
                self.loss_cut_percent = -1 * prev_range / 10.0 * leverage

                print("Close %: ", self.close_percent)
                print("Loss cut %: ", self.loss_cut_percent)

                time.sleep(10)
            except Exception as e:
                print(e)

    def closer_run(self):
        while True:
            try:
                if not self.has_position():
                    time.sleep(10)
                    continue

                if self.has_open_orders():
                    self.cancel_orders()

                position = self.current_position()
                position_size = position['currentQty']
                roe_percent = position['unrealisedRoePcnt']*100
                last_price = self.market_last_price()
                side = 'buy' if position_size < 0 else 'sell'

                print("ROE: ", roe_percent)

                if roe_percent >= self.close_percent:
                    print("Close position")
                    self.limit_order(side=side, price=last_price, size=position_size)
                elif roe_percent <= self.loss_cut_percent:
                    print("Loss cut!!")
                    self.market_order(side=side, size=position_size)

                time.sleep(10)
            except Exception as e:
                print(e)

    def run(self):
        try:
            opener = threading.Thread(target=self.opener_run)
            closer = threading.Thread(target=self.closer_run)
            opener.daemon=True
            closer.daemon=True
            opener.start()
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
    parser.add_argument('size', type=int)
    parser.add_argument('periods', default='1h')
    parser.add_argument('--debug', default=False, action='store_true')
    args = parser.parse_args()

    mex = Deepmex(size=args.size, periods=args.periods, debug=args.debug)
    mex.run()
