# coding: UTF-8

import json
import os
import threading
import time
from datetime import datetime
import pandas as pd

import bitmex
from bravado.exception import HTTPNotFound
from pytz import UTC

from src import logger, delta, gen_ohlcv, retry, notify, allowed_range, validate_range
from src.mex_ws import BitMexWs

# 本番取引用クラス
class BitMex:
    # 稼働中
    is_running = True
    # 時間足を取得するクローラ
    crawler = None
    # 戦略を実施するリスナー
    listener = None
    # ログの出力
    enable_trade_log = True

    def __init__(self, tr, demo=False, run=True):
        """
        コンストラクタ
        :param tr:
        :param demo:
        :param run:
        """
        validate_range(tr)

        self.demo = demo
        self.tr = tr
        self.run = run

    def __init_client(self):
        """
        初期化関数
        """
        if self.p_client is not None and self.client is not None:
            return
        api_key = os.environ.get("BITMEX_TEST_APIKEY") if self.demo else os.environ.get("BITMEX_APIKEY")
        api_secret = os.environ.get("BITMEX_TEST_SECRET") if self.demo else os.environ.get("BITMEX_SECRET")
        self.p_client = bitmex.bitmex(test=self.demo, api_key=api_key, api_secret=api_secret)
        self.client = bitmex.bitmex(test=self.demo)

    def now_time(self):
        return datetime.now().astimezone(UTC)

    def get_retain_rate(self):
        """
        証拠金維持率。
        :return:
        """
        return 0.2

    def get_lot(self):
        """
        ロットの計算を行う。
        :return:
        """
        return int((1 - self.get_retain_rate()) * self.get_balance() / 100000000 * self.get_leverage() * self.get_market_price())

    def get_balance(self):
        """
        残高の取得を行う。
        :return:
        """
        self.__init_client()
        return retry(lambda: self.p_client.User.User_getWallet(currency="XBt").result()[0]["amount"])

    def get_leverage(self):
        """
        レバレッジの取得する。
        :return:
        """
        self.__init_client()
        return retry(lambda: self.p_client.Position.Position_get(filter=json.dumps({"symbol": "XBTUSD"})).result()[0][0]["leverage"])

    def get_position_size(self):
        """
        現在のポジションサイズを取得する。
        :return:
        """
        self.__init_client()
        return retry(lambda: self.p_client.Position.Position_get(filter=json.dumps({"symbol": "XBTUSD"})).result()[0][0]["currentQty"])

    def get_position_avg_price(self):
        """
        現在のポジションの平均価格を取得する。
        :return:
        """
        self.__init_client()
        return retry(lambda: self.p_client.Position.Position_get(filter=json.dumps({"symbol": "XBTUSD"})).result()[0][0][
            "avgEntryPrice"])

    def get_market_price(self):
        """
        現在の取引額を取得する。
        :return:
        """
        self.__init_client()
        return retry(lambda: self.client.Instrument.Instrument_get(symbol="XBTUSD").result()[0][0]["lastPrice"])

    def get_commission(self):
        """
        手数料を取得する。
        :return:
        """
        return 0.075 / 100

    def cancel_all(self):
        """
        すべての注文をキャンセルする。
        """
        self.__init_client()
        orders = retry(lambda: self.p_client.Order.Order_cancelAll().result()[0])
        for order in orders:
            logger.info(f"Cancel Order : (orderID, orderType, side, orderQty, limit, stop) = "
                        f"({order['orderID']}, {order['ordType']}, {order['side']}, {order['orderQty']}, "
                        f"{order['price']}, {order['stopPx']})")
        logger.info(f"Cancel All Order")

    def close_all(self):
        """
        すべてのポジションを解消する。
        """
        self.__init_client()
        order = retry(lambda: self.p_client.Order.Order_closePosition(symbol="XBTUSD").result()[0])
        logger.info(f"Close Position : (orderID, orderType, side, orderQty, limit, stop) = "
                    f"({order['orderID']}, {order['ordType']}, {order['side']}, {order['orderQty']}, "
                    f"{order['price']}, {order['stopPx']})")
        logger.info(f"Close All Position")

    def entry(self, id, long, qty, limit=0, stop=0, when=True):
        """
        注文をする。pineの関数と同等の機能。
        https://jp.tradingview.com/study-script-reference/#fun_strategy{dot}entry
        :param id: 注文の番号
        :param long: ロング or ショート
        :param qty: 注文量
        :param limit: 指値
        :param stop: ストップ指値
        :param when: 注文するか
        :return:
        """
        self.__init_client()

        if not when:
            return

        pos_size = self.get_position_size()

        if long and pos_size > 0:
            return

        if not long and pos_size < 0:
            return

        side = "Buy" if long else "Sell"
        ord_qty = qty + abs(pos_size)

        if self.exist_open_order(long, ord_qty, limit, stop):
            return

        self.cancel(long)

        if limit > 0 and stop > 0:
            ord_type = "StopLimit"
            retry(lambda: self.p_client.Order.Order_new(symbol="XBTUSD", ordType=ord_type,
                                        side=side, orderQty=ord_qty, price=limit, stopPx=stop).result())
        elif limit > 0:
            ord_type = "Limit"
            retry(lambda: self.p_client.Order.Order_new(symbol="XBTUSD", ordType=ord_type,
                                        side=side, orderQty=ord_qty, price=limit).result())
        elif stop > 0:
            ord_type = "Stop"
            retry(lambda: self.p_client.Order.Order_new(symbol="XBTUSD", ordType=ord_type,
                                        side=side, orderQty=ord_qty, stopPx=stop).result())
        else:
            ord_type = "Market"
            retry(lambda: self.p_client.Order.Order_new(symbol="XBTUSD", ordType=ord_type,
                                        side=side, orderQty=ord_qty).result())

        if self.enable_trade_log:
            logger.info(f"========= Create Order ==============")
            logger.info(f"ID     : {id}")
            logger.info(f"Type   : {ord_type}")
            logger.info(f"Side   : {side}")
            logger.info(f"Qty    : {ord_qty}")
            logger.info(f"Limit  : {limit}")
            logger.info(f"Stop   : {stop}")
            logger.info(f"======================================")

    def get_open_orders(self, long):
        """
        注文を取得する。
        :param long: ロング or ショート
        :return:
        """
        self.__init_client()
        side = "Buy" if long else "Sell"
        return retry(lambda: self.p_client
                     .Order.Order_getOrders(filter=json.dumps({"symbol": "XBTUSD", "open": True, "side": side}))
                     .result()[0])

    def exist_open_order(self, long, qty, limit=0, stop=0):
        """
        同じ注文が存在するか確認する。
        :param long:  ロング or ショート
        :param qty: 注文量
        :param limit: 指値
        :param stop: ストップ指値
        :return:
        """
        orders = self.get_open_orders(long)
        if limit > 0 and stop > 0:
            return len([order for order in orders
                        if order['orderQty'] == qty and order['price'] == limit and order['stopPx'] == stop]) > 0
        elif limit > 0:
            return len([order for order in orders
                        if order['orderQty'] == qty and order['price'] == limit and order['stopPx'] is None]) > 0
        elif stop > 0:
            return len([order for order in orders
                        if order['orderQty'] == qty and order['price'] is None and order['stopPx'] == stop]) > 0
        return False

    def cancel(self, long):
        """
        注文をキャンセルする。
        :param long: ロング or ショート
        :return:
        """
        self.__init_client()
        orders = self.get_open_orders(long)
        if len(orders) == 0:
            return

        for order in orders:
            try:
                retry(lambda: self.p_client.Order.Order_cancel(orderID=order['orderID']).result()[0][0])
            except HTTPNotFound:
                return
            logger.info(f"Cancel Order : (orderID, orderType, side, orderQty, limit, stop) = "
                        f"({order['orderID']}, {order['ordType']}, {order['side']}, {order['orderQty']}, "
                        f"{order['price']}, {order['stopPx']})")

    def get_order_size(self):
        """
        注文の数を取得する。
        :return:
        """
        self.__init_client()
        return len(retry(lambda: self.p_client
                         .Order.Order_getOrders(filter=json.dumps({"symbol": "XBTUSD", "open": True})).result()[0]))

    def fetch_ohlcv(self, start_time, end_time):
        """
        足データを取得する
        :param start_time: 開始時間
        :param end_time: 終了時間
        :return:
        """
        self.__init_client()
        bin_size = allowed_range[self.tr][0]
        resample = allowed_range[self.tr][1]

        data = retry(lambda: self.client.Trade.Trade_getBucketed(symbol="XBTUSD", binSize=bin_size,
                                                   startTime=start_time, endTime=end_time).result()[0])
        data_frame = pd.DataFrame(data[:-1], columns=["timestamp", "high", "low", "open", "close", "volume"])
        data_frame["datetime"] = pd.to_datetime(data_frame["timestamp"], unit="s")
        data_frame = data_frame.set_index("datetime")
        pd.to_datetime(data_frame.index, utc=True)
        data_frame = data_frame.resample(resample).agg({
            "timestamp": "last",
            "open": "first",
            "high": "max",
            "low": "min",
            "close": "last",
            "volume": "sum",
        })
        data_frame.reset_index()
        return data_frame.to_dict("records")

    def __crawler_run(self):
        """
        データを取得して、戦略を実行する。
        """
        if self.is_running: # WebSocketの接続
            self.ws = BitMexWs()
        while self.is_running:
            try:
                end_time = datetime.now()
                start_time = end_time - 90 * delta(allowed_range[self.tr][0]) * allowed_range[self.tr][2]
                source = self.fetch_ohlcv(start_time=start_time, end_time=end_time)
                if self.listener is not None:
                    open, close, high, low = gen_ohlcv(source)
                    self.listener(open, close, high, low)
            except Exception as e:
                logger.error(e)
                time.sleep(2)
                notify(f"An error occurred. {e}")
                continue
            time.sleep(60)

    def on_update(self, listener):
        """
        戦略の関数を登録する。
        :param listener:
        """
        self.listener = listener
        if self.run:
            self.crawler = threading.Thread(target=self.__crawler_run)
            self.crawler.start()

    def stop(self):
        """
        クローラーを止める。
        """
        self.is_running = False
        self.ws.close()

    def show_result(self):
        """
        取引結果を表示する。
        """
        pass

    def plot(self, name, value, color):
        """
        グラフに描画する。
        """
        pass
