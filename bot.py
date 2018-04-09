import argparse
import json
import os
import sys
import threading
import time
from datetime import datetime, timedelta
import bitmex

class BitMex:
    def __init__(self, test=True):
        apiKey = os.environ.get('BITMEX_APIKEY') if test else os.environ.get('BITMEX_TEST_APIKEY')
        secret = os.environ.get('BITMEX_SECRET') if test else os.environ.get('BITMEX_TEST_SECRET')
        self.client = bitmex.bitmex(test=test, api_key=apiKey, api_secret=secret)

    def has_open_orders(self):
        orders = self.client.Order.Order_getOrders(symbol='XBTUSD', filter=json.dumps({'open': True})).result()[0][0]
        return len(orders) > 0

    def current_position(self):
        return self.client.Position.Position_get(filter=json.dumps({'symbol': 'XBTUSD'})).result()[0][0]['currentQty']

    def close_position(self, time=datetime.now()):
        self.client.Order.Order_closePosition(symbol='XBTUSD').result()
        print(str(time) + ' Close Position')

    def entry(self, side, size):
        order = self.client.Order.Order_new(symbol='XBTUSD', ordType='Market',
                                    side=side.capitalize(), orderQty=size).result()[0]
        print(str(time) + ' Create Order: ' + order['ordType'] + ' ' + order['side'] + ': ' +
              str(order['orderQty']) + ' @ ' + str(order['price']) + ' / ' + order['orderID'])

    def cancel_orders(self):
        orders = self.client.Order.Order_cancelAll().result()[0]
        for order in orders:
            print(str(time) + ' Cancel Order: ' + order['ordType'] + ' ' + order['side'] + ': ' +
                  str(order['orderQty']) + ' @ ' + str(order['price']))

    def fetch_ohlc(self, starttime=(datetime.now() + timedelta(days=-30)), endTime=datetime.now()):
        candles = self.client.Trade.Trade_getBucketed(symbol='XBTUSD', binSize='1h',
                                                      startTime=starttime, endTime=endTime).result()[0]
        return candles[:-1]

class Bot:
    def __init__(self, lot=100, test=True):
        self.originallot = lot
        self.bitmex = BitMex(test=test)

    def _run(self):
        dt_prev = datetime.now()
        while True:
            dt_now = datetime.now()
            if dt_now - dt_prev < timedelta(hours=1):
                continue
            try:
                source = self.bitmex.fetch_ohlc()
                open  = [v[1] for _, v in enumerate(source)]
                high  = [v[2] for _, v in enumerate(source)]
                low   = [v[3] for _, v in enumerate(source)]
                close = [v[4] for _, v in enumerate(source)]
                up_bound = max(high)
                dn_bound = min(low)

                pos = self.bitmex.current_position()
                lot = self.originallot
                if high[-1] == up_bound and pos <= 0:
                    if pos < 0:
                        lot = 2 * self.originallot
                    self.bitmex.entry(side='long', size=lot)
                elif low[-1] == dn_bound and pos >= 0:
                    if pos > 0:
                        lot = 2 * self.originallot
                    self.bitmex.entry(side='short', size=lot)
            except Exception as e:
                print(e)
            dt_prev = dt_now

    def run(self):
        try:
            runner = threading.Thread(target=self._run)
            runner.daemon = True
            runner.start()
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
