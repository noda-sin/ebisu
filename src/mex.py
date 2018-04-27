# coding: UTF-8

import json
import os
import threading
import time
from datetime import datetime

import bitmex

from src import util
from src.mex_ws import BitMexWs
from src.util import delta


class BitMex:
    listener = None

    def __init__(self, test=False, tr='1h', periods=30):
        apiKey = os.environ.get('BITMEX_TEST_APIKEY') if test else os.environ.get('BITMEX_APIKEY')
        secret = os.environ.get('BITMEX_TEST_SECRET') if test else os.environ.get('BITMEX_SECRET')
        self.client   = bitmex.bitmex(test=test, api_key=apiKey, api_secret=secret)
        self.ws       = BitMexWs()
        self.tr       = tr
        self.periods  = periods

    def wallet_balance(self):
        pass

    def now_time(self):
        return datetime.now()

    def position_qty(self):
        return self.client.Position.Position_get(filter=json.dumps({'symbol': 'XBTUSD'})).result()[0][0]['currentQty']

    def position_price(self):
        return self.client.Position.Position_get(filter=json.dumps({'symbol': 'XBTUSD'})).result()[0][0]['avgEntryPrice']

    def market_price(self):
        return self.client.Instrument.Instrument_get(symbol='XBTUSD').result()[0][0]['lastPrice']

    def close_position(self):
        self.client.Order.Order_closePosition(symbol='XBTUSD').result()
        print(str(self.now_time()) + ' Close Position')

    def trade_fee(self):
        return 0.075/100

    def entry(self, long, qty, limit=0, stop=0, when=True):
        if not when:
            return

        self.close_order()
        pos = self.position_qty()

        if long and pos > 0:
            return

        if not long and pos < 0:
            return

        side = 'Long' if long else 'Short'
        qty  = qty + abs(pos)
        if limit > 0 and stop > 0:
            ordType = 'StopLimit'
        elif limit > 0:
            ordType = 'Limit'
        elif stop > 0:
            ordType = 'Stop'
        else:
            ordType = 'Market'

        order = self.client.Order.Order_new(symbol='XBTUSD', ordType=ordType,
                                    side=side, orderQty=qty, price=limit, stopPx=stop).result()[0]
        print(str(self.now_time()) + ' Create Order: ' + order['ordType'] + ' ' + order['side'] + ': ' +
              str(order['orderQty']) + ' @ ' + str(order['price']) + ' / ' + order['orderID'])

    def close_order(self):
        orders = self.client.Order.Order_cancelAll().result()[0]
        for order in orders:
            print(str(self.now_time()) + ' Cancel Order: ' + order['ordType'] + ' ' + order['side'] + ': ' +
                  str(order['orderQty']) + ' @ ' + str(order['price']))

    def fetch_ohlcv(self, starttime, endtime):
        candles = self.client.Trade.Trade_getBucketed(symbol='XBTUSD', binSize=self.tr,
                                                      startTime=starttime, endTime=endtime).result()[0]
        return candles

    def __crawler_run(self):
        dt_prev = datetime.now()
        while True:
            dt_now = datetime.now()
            if dt_now - dt_prev < delta(self.tr):
                continue
            try:
                endtime = datetime.now()
                starttime = endtime - self.periods * delta(tr=self.tr)
                source = self.fetch_ohlcv(starttime=starttime, endtime=endtime)
                if self.listener is not None:
                    open, close, high, low = util.ohlcv(source)
                    self.listener(open, close, high, low)
            except Exception as e:
                print(e)
                time.sleep(2)
                continue
            dt_prev = dt_now

    def on_update(self, listener):
        self.listener = listener
        crawler = threading.Thread(target=self.__crawler_run)
        crawler.start()

    def print_result(self):
        pass

    def __del__(self):
        self.ws.close()
