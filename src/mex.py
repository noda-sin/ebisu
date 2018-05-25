# coding: UTF-8

import json
import os
import threading
import time

from bravado.exception import HTTPNotFound
from pytz import timezone
from datetime import datetime

import bitmex

from src import logger, delta, gen_ohlcv
from src.mex_ws import BitMexWs


class BitMex:
    listener = None

    def __init__(self, tr, periods, demo=False, run=True):
        apiKey = os.environ.get("BITMEX_TEST_APIKEY") if demo else os.environ.get("BITMEX_APIKEY")
        secret = os.environ.get("BITMEX_TEST_SECRET") if demo else os.environ.get("BITMEX_SECRET")
        self.client = bitmex.bitmex(test=demo, api_key=apiKey, api_secret=secret)
        self.ws = BitMexWs()
        self.tr = tr
        self.periods = periods
        self.run = run

    def get_lot(self):
        return self.get_balance() * self.get_leverage()

    def get_balance(self):
        return self.client.User.User_getWallet(currency="XBt").result()[0]["amount"]

    def get_leverage(self):
        return self.client.Position.Position_get(filter=json.dumps({"symbol": "XBTUSD"})).result()[0][0]["leverage"]

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
        orders = self.client.Order.Order_cancelAll().result()[0]
        for order in orders:
            logger.info(f"Cancel Order : (orderID, orderType, side, orderQty, limit, stop) = "
                        f"({order['orderID']}, {order['ordType']}, {order['side']}, {order['orderQty']}, "
                        f"{order['price']}, {order['stopPx']})")

    def close_all(self):
        order = self.client.Order.Order_closePosition(symbol="XBTUSD").result()[0]
        logger.info(f"Close Position : (orderID, orderType, side, orderQty, limit, stop) = "
                    f"({order['orderID']}, {order['ordType']}, {order['side']}, {order['orderQty']}, "
                    f"{order['price']}, {order['stopPx']})")

    def entry(self, id, long, qty, limit=0, stop=0, when=True):
        if not when:
            return

        pos_size = self.get_position_size()

        if long and pos_size > 0:
            return

        if not long and pos_size < 0:
            return

        self.cancel(long)
        side = "Buy" if long else "Sell"
        ord_qty = qty + abs(pos_size)

        if limit > 0 and stop > 0:
            ord_type = "StopLimit"
            self.client.Order.Order_new(symbol="XBTUSD", ordType=ord_type,
                                        side=side, orderQty=ord_qty, price=limit, stopPx=stop).result()
        elif limit > 0:
            ord_type = "Limit"
            self.client.Order.Order_new(symbol="XBTUSD", ordType=ord_type,
                                        side=side, orderQty=ord_qty, price=limit).result()
        elif stop > 0:
            ord_type = "Stop"
            self.client.Order.Order_new(symbol="XBTUSD", ordType=ord_type,
                                        side=side, orderQty=ord_qty, stopPx=stop).result()
        else:
            ord_type = "Market"
            self.client.Order.Order_new(symbol="XBTUSD", ordType=ord_type,
                                        side=side, orderQty=ord_qty).result()

        logger.info(f"========= Create Order ==============")
        logger.info(f"ID     : {id}")
        logger.info(f"Type   : {ord_type}")
        logger.info(f"Side   : {side}")
        logger.info(f"Qty    : {ord_qty}")
        logger.info(f"Price  : {limit} %")
        logger.info(f"StopPx : {stop}")
        logger.info(f"======================================")

    def cancel(self, long):
        side = "Buy" if long else "Sell"
        orders = [order for order in
                  self.client.Order.Order_getOrders(filter=json.dumps({"symbol": "XBTUSD", "open": True})).result()[0]
                  if order["side"] == side]
        if len(orders) == 0:
            return

        for order in orders:
            try:
                self.client.Order.Order_cancel(orderID=order['orderID']).result()[0][0]
            except HTTPNotFound:
                return
            logger.info(f"Cancel Order : (orderID, orderType, side, orderQty, limit, stop) = "
                        f"({order['orderID']}, {order['ordType']}, {order['side']}, {order['orderQty']}, "
                        f"{order['price']}, {order['stopPx']})")

    def get_order_size(self):
        return len(self.client.Order.Order_getOrders(filter=json.dumps({"symbol": "XBTUSD", "open": True})).result()[0])

    def fetch_ohlcv(self, start_time, end_time):
        timeframe = self.tr
        if self.tr == '2h':
            timeframe = '1h'
        ohlc = self.client.Trade.Trade_getBucketed(symbol="XBTUSD", binSize=timeframe,
                                                   startTime=start_time, endTime=end_time).result()[0]
        if self.tr != '2h':
            return ohlc

        ohlc_2h = []
        past = []
        for src in ohlc:
            time = src['timestamp']
            if time.hour % 2 == 0 and len(past) != 0:
                open = past[0]['open']
                close = past[-1]['close']
                high = past[0]['high']
                low = past[0]['low']
                for p in past:
                    if high < p['high']:
                        high = p['high']
                    if low > p['low']:
                        low = p['low']
                ohlc_2h.append({'timestamp': past[0]['timestamp'], 'open': open, 'close': close, 'high': high, 'low': low})
                past = []
            else:
                past.append(src)
        return ohlc_2h

    def __crawler_run(self):
        dt_prev = None
        while True:
            dt_now = datetime.now()
            if dt_prev is not None and dt_now - dt_prev < delta(self.tr):
                time.sleep(10)
                continue
            try:
                end_time = datetime.now(timezone('UTC'))
                start_time = end_time - self.periods * delta(tr=self.tr)
                source = self.fetch_ohlcv(start_time=start_time, end_time=end_time)
                if self.listener is not None:
                    open, close, high, low = gen_ohlcv(source)
                    self.listener(open, close, high, low)
            except Exception as e:
                print(e)
                time.sleep(2)
                continue
            dt_prev = dt_now

    def on_update(self, listener):
        self.listener = listener
        if self.run:
            self.crawler = threading.Thread(target=self.__crawler_run)
            self.crawler.start()

    def show_result(self):
        pass

    def __del__(self):
        self.ws.close()
