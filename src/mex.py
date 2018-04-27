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

    def __init__(self, tr, periods, test=False, run=True):
        apiKey = os.environ.get("BITMEX_TEST_APIKEY") if test else os.environ.get("BITMEX_APIKEY")
        secret = os.environ.get("BITMEX_TEST_SECRET") if test else os.environ.get("BITMEX_SECRET")
        self.client = bitmex.bitmex(test=test, api_key=apiKey, api_secret=secret)
        self.ws = BitMexWs()
        self.tr = tr
        self.periods = periods
        self.run = run

    def get_balance(self):
        pass

    def get_leverage(self):
        pass

    def now_time(self):
        return datetime.now()

    def get_position_size(self):
        return self.client.Position.Position_get(filter=json.dumps({"symbol": "XBTUSD"})).result()[0][0]["currentQty"]

    def get_position_avg_price(self):
        return self.client.Position.Position_get(filter=json.dumps({"symbol": "XBTUSD"})).result()[0][0][
            "avgEntryPrice"]

    def get_market_price(self):
        return self.client.Instrument.Instrument_get(symbol="XBTUSD").result()[0][0]["lastPrice"]

    def get_commission(self):
        return 0.075 / 100

    def cancel_all(self):
        self.client.Order.Order_cancelAll().result()

    def close_all(self):
        self.client.Order.Order_closePosition(symbol="XBTUSD").result()

    def entry(self, long, qty, limit=0, stop=0, when=True):
        if not when:
            return

        self.close_all()
        pos_size = self.get_position_size()

        if long and pos_size > 0:
            return

        if not long and pos_size < 0:
            return

        side = "Long" if long else "Short"
        ord_qty = qty + abs(pos_size)

        if limit > 0 and stop > 0:
            ord_type = "StopLimit"
        elif limit > 0:
            ord_type = "Limit"
        elif stop > 0:
            ord_type = "Stop"
        else:
            ord_type = "Market"

        self.client.Order.Order_new(symbol="XBTUSD", ordType=ord_type,
                                    side=side, orderQty=ord_qty, price=limit, stopPx=stop).result()

    def fetch_ohlcv(self, start_time, end_time):
        return self.client.Trade.Trade_getBucketed(symbol="XBTUSD", binSize=self.tr,
                                                   startTime=start_time, endTime=end_time).result()[0]

    def __crawler_run(self):
        dt_prev = datetime.now()
        while True:
            dt_now = datetime.now()
            if dt_now - dt_prev < delta(self.tr):
                continue
            try:
                end_time = datetime.now()
                start_time = end_time - self.periods * delta(tr=self.tr)
                source = self.fetch_ohlcv(start_time=start_time, end_time=end_time)
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
        if self.run:
            crawler = threading.Thread(target=self.__crawler_run)
            crawler.start()

    def show_result(self):
        pass

    def __del__(self):
        self.ws.close()
