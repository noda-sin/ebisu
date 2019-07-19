# coding: UTF-8

import json
import math
import os
import traceback
from datetime import datetime, timezone
import time

import pandas as pd
from bravado.exception import HTTPNotFound
from pytz import UTC

from src import logger, retry, allowed_range, to_data_frame, \
    resample, delta, FatalError, notify, ord_suffix
from src.bitmex_api import bitmex_api
from src.bitmex_websocket import BitMexWs


# Class for production transaction
from src.orderbook import OrderBook


class BitMex:
    # wallet
    wallet = None
    # 価格
    market_price = 0
    # ポジション
    position = None
    # マージン
    margin = None
    # 利用する時間足
    bin_size = '1h'
    # プライベートAPI用クライアント
    private_client = None
    # パブリックAPI用クライアント
    public_client = None
    # 稼働中
    is_running = True
    # 時間足を取得するクローラ
    crawler = None
    # 戦略を実施するリスナー
    strategy = None
    # ログの出力
    enable_trade_log = True
    # OHLCの長さ
    ohlcv_len = 100
    # OHLCのキャッシュ
    data = None
    # 利確損切戦略
    exit_order = {'profit': 0, 'loss': 0, 'trail_offset': 0}
    # Trailing Stopのためのピン留価格
    trail_price = 0
    # 最後に戦略を実行した時間
    last_action_time = None

    def __init__(self, demo=False, threading=True):
        """
        コンストラクタ
        :param demo:
        :param run:
        """
        self.demo = demo
        self.is_running = threading

    def __init_client(self):
        """
        初期化関数
        """
        if self.private_client is not None and self.public_client is not None:
            return
        api_key = os.environ.get("BITMEX_TEST_APIKEY") if self.demo else os.environ.get("BITMEX_APIKEY")
        api_secret = os.environ.get("BITMEX_TEST_SECRET") if self.demo else os.environ.get("BITMEX_SECRET")
        self.private_client = bitmex_api(test=self.demo, api_key=api_key, api_secret=api_secret)
        self.public_client = bitmex_api(test=self.demo)

    def now_time(self):
        """
        現在の時間
        """
        return datetime.now().astimezone(UTC)

    def get_retain_rate(self):
        """
        証拠金維持率。
        :return:
        """
        return 0.8

    def get_lot(self):
        """
        ロットの計算を行う。
        :return:
        """
        margin = self.get_margin()
        position = self.get_position()
        return math.floor((1 - self.get_retain_rate()) * self.get_market_price()
                          * margin['excessMargin'] / (position['initMarginReq'] * 100000000))

    def get_balance(self):
        """
        残高の取得を行う。
        :return:
        """
        self.__init_client()
        return self.get_margin()["walletBalance"]

    def get_margin(self):
        """
        マージンの取得
        :return:
        """
        self.__init_client()
        if self.margin is not None:
            return self.margin
        else:  # WebSocketで取得できていない場合
            self.margin = retry(lambda: self.private_client
                                .User.User_getMargin(currency="XBt").result())
            return self.margin

    def get_leverage(self):
        """
        レバレッジの取得する。
        :return:
        """
        self.__init_client()
        return self.get_position()["leverage"]

    def get_position(self):
        """
        現在のポジションを取得する。
        :return:
        """
        self.__init_client()
        if self.position is not None:
            return self.position
        else:  # WebSocketで取得できていない場合
            ret = retry(lambda: self.private_client
                                  .Position.Position_get(filter=json.dumps({"symbol": "XBTUSD"})).result())
            if len(ret) > 0:
                self.position = ret[0]
            return self.position

    def get_position_size(self):
        """
        現在のポジションサイズを取得する。
        :return:
        """
        self.__init_client()
        return self.get_position()['currentQty']

    def get_position_avg_price(self):
        """
        現在のポジションの平均価格を取得する。
        :return:
        """
        self.__init_client()
        return self.get_position()['avgEntryPrice']

    def get_market_price(self):
        """
        現在の取引額を取得する。
        :return:
        """
        self.__init_client()
        if self.market_price != 0:
            return self.market_price
        else:  # WebSocketで取得できていない場合
            self.market_price = retry(lambda: self.public_client
                                      .Instrument.Instrument_get(symbol="XBTUSD").result())[0]["lastPrice"]
            return self.market_price

    def get_trail_price(self):
        """
        Trail Priceを取得する。
        :return:
        """
        return self.trail_price

    def set_trail_price(self, value):
        """
        Trail Priceを設定する。
        :return:
        """
        self.trail_price = value

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
        orders = retry(lambda: self.private_client.Order.Order_cancelAll().result())
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
        order = retry(lambda: self.private_client.Order.Order_closePosition(symbol="XBTUSD").result())
        logger.info(f"Close Position : (orderID, orderType, side, orderQty, limit, stop) = "
                    f"({order['orderID']}, {order['ordType']}, {order['side']}, {order['orderQty']}, "
                    f"{order['price']}, {order['stopPx']})")
        logger.info(f"Close All Position")

    def cancel(self, id):
        """
        注文をキャンセルする。
        :param id: 注文番号
        :return 成功したか:
        """
        self.__init_client()
        order = self.get_open_order(id)
        if order is None:
            return False

        try:
            retry(lambda: self.private_client.Order.Order_cancel(orderID=order['orderID']).result())[0]
        except HTTPNotFound:
            return False
        logger.info(f"Cancel Order : (orderID, orderType, side, orderQty, limit, stop) = "
                    f"({order['orderID']}, {order['ordType']}, {order['side']}, {order['orderQty']}, "
                    f"{order['price']}, {order['stopPx']})")
        return True

    def __new_order(self, ord_id, side, ord_qty, limit=0, stop=0, post_only=False):
        """
        注文を作成する
        """
        if limit > 0 and post_only:
            ord_type = "Limit"
            retry(lambda: self.private_client.Order.Order_new(symbol="XBTUSD", ordType=ord_type, clOrdID=ord_id,
                                                              side=side, orderQty=ord_qty, price=limit,
                                                              execInst='ParticipateDoNotInitiate').result())
        elif limit > 0 and stop > 0:
            ord_type = "StopLimit"
            retry(lambda: self.private_client.Order.Order_new(symbol="XBTUSD", ordType=ord_type, clOrdID=ord_id,
                                                              side=side, orderQty=ord_qty, price=limit,
                                                              stopPx=stop).result())
        elif limit > 0:
            ord_type = "Limit"
            retry(lambda: self.private_client.Order.Order_new(symbol="XBTUSD", ordType=ord_type, clOrdID=ord_id,
                                                              side=side, orderQty=ord_qty, price=limit).result())
        elif stop > 0:
            ord_type = "Stop"
            retry(lambda: self.private_client.Order.Order_new(symbol="XBTUSD", ordType=ord_type, clOrdID=ord_id,
                                                              side=side, orderQty=ord_qty, stopPx=stop).result())
        elif post_only: # market order with post only
            ord_type = "Limit"
            i = 0
            while True:
                prices = self.ob.get_prices()
                limit = prices[1] if side == "Buy" else prices[0]
                retry(lambda: self.private_client.Order.Order_new(symbol="XBTUSD", ordType=ord_type, clOrdID=ord_id,
                                                                  side=side, orderQty=ord_qty, price=limit,
                                                                  execInst='ParticipateDoNotInitiate').result())
                time.sleep(1)

                if not self.cancel(ord_id):
                    break
                time.sleep(2)
                i += 1
                if i > 10:
                    notify(f"Order retry count exceed")
                    break
            self.cancel_all()
        else:
            ord_type = "Market"
            retry(lambda: self.private_client.Order.Order_new(symbol="XBTUSD", ordType=ord_type, clOrdID=ord_id,
                                                              side=side, orderQty=ord_qty).result())

        if self.enable_trade_log:
            logger.info(f"========= New Order ==============")
            logger.info(f"ID     : {ord_id}")
            logger.info(f"Type   : {ord_type}")
            logger.info(f"Side   : {side}")
            logger.info(f"Qty    : {ord_qty}")
            logger.info(f"Limit  : {limit}")
            logger.info(f"Stop   : {stop}")
            logger.info(f"======================================")

            notify(f"New Order\nType: {ord_type}\nSide: {side}\nQty: {ord_qty}\nLimit: {limit}\nStop: {stop}")

    def __amend_order(self, ord_id, side, ord_qty, limit=0, stop=0, post_only=False):
        """
        注文を更新する
        """
        if limit > 0 and stop > 0:
            ord_type = "StopLimit"
            retry(lambda: self.private_client.Order.Order_amend(origClOrdID=ord_id,
                                                                orderQty=ord_qty, price=limit, stopPx=stop).result())
        elif limit > 0:
            ord_type = "Limit"
            retry(lambda: self.private_client.Order.Order_amend(origClOrdID=ord_id,
                                                                orderQty=ord_qty, price=limit).result())
        elif stop > 0:
            ord_type = "Stop"
            retry(lambda: self.private_client.Order.Order_amend(origClOrdID=ord_id,
                                                                orderQty=ord_qty, stopPx=stop).result())
        elif post_only: # market order with post only
            ord_type = "Limit"
            prices = self.ob.get_prices()
            limit = prices[1] if side == "Buy" else prices[0]
            retry(lambda: self.private_client.Order.Order_amend(origClOrdID=ord_id,
                                                                orderQty=ord_qty, price=limit).result())
        else:
            ord_type = "Market"
            retry(lambda: self.private_client.Order.Order_amend(origClOrdID=ord_id,
                                                                orderQty=ord_qty).result())

        if self.enable_trade_log:
            logger.info(f"========= Amend Order ==============")
            logger.info(f"ID     : {ord_id}")
            logger.info(f"Type   : {ord_type}")
            logger.info(f"Side   : {side}")
            logger.info(f"Qty    : {ord_qty}")
            logger.info(f"Limit  : {limit}")
            logger.info(f"Stop   : {stop}")
            logger.info(f"======================================")

            notify(f"Amend Order\nType: {ord_type}\nSide: {side}\nQty: {ord_qty}\nLimit: {limit}\nStop: {stop}")

    def entry(self, id, long, qty, limit=0, stop=0, post_only=False, when=True):
        """
        注文をする。pineの関数と同等の機能。
        https://jp.tradingview.com/study-script-reference/#fun_strategy{dot}entry
        :param id: 注文の番号
        :param long: ロング or ショート
        :param qty: 注文量
        :param limit: 指値
        :param stop: ストップ指値
        :param post_only: ポストオンリー
        :param when: 注文するか
        :return:
        """
        self.__init_client()

        if self.get_margin()['excessMargin'] <= 0 or qty <= 0:
            return

        if not when:
            return

        pos_size = self.get_position_size()

        if long and pos_size > 0:
            return

        if not long and pos_size < 0:
            return

        ord_qty = qty + abs(pos_size)

        self.order(id, long, ord_qty, limit, stop, post_only, when)

    def order(self, id, long, qty, limit=0, stop=0, post_only=False, when=True):
        """
        注文をする。pineの関数と同等の機能。
        https://jp.tradingview.com/study-script-reference/#fun_strategy{dot}order
        :param id: 注文の番号
        :param long: ロング or ショート
        :param qty: 注文量
        :param limit: 指値
        :param stop: ストップ指値
        :param post_only: ポストオンリー
        :param when: 注文するか
        :return:
        """
        self.__init_client()

        if self.get_margin()['excessMargin'] <= 0 or qty <= 0:
            return

        if not when:
            return

        side = "Buy" if long else "Sell"
        ord_qty = qty

        order = self.get_open_order(id)
        ord_id = id + ord_suffix() if order is None else order["clOrdID"]

        if order is None:
            self.__new_order(ord_id, side, ord_qty, limit, stop, post_only)
        else:
            self.__amend_order(ord_id, side, ord_qty, limit, stop, post_only)

    def get_open_order(self, id):
        """
        注文を取得する。
        :param id: 注文番号
        :return:
        """
        self.__init_client()
        open_orders = retry(lambda: self.private_client
                            .Order.Order_getOrders(filter=json.dumps({"symbol": "XBTUSD", "open": True}))
                            .result())
        open_orders = [o for o in open_orders if o["clOrdID"].startswith(id)]
        if len(open_orders) > 0:
            return open_orders[0]
        else:
            return None

    def exit(self, profit=0, loss=0, trail_offset=0):
        """
        利確、損切戦略の登録 lossとtrail_offsetが両方設定されたら、trail_offsetが優先される
        :param profit: 利益(ティックで指定する)
        :param loss: 損切(ティックで指定する)
        :param trail_offset: トレーリングストップの価格(ティックで指定)
        """
        self.exit_order = {'profit': profit, 'loss': loss, 'trail_offset': trail_offset}

    def get_exit_order(self):
        """
        利確、損切戦略を取得する
        """
        return self.exit_order

    def eval_exit(self):
        """
        利確、損切戦略の評価
        """
        if self.get_position_size() == 0:
            return

        unrealised_pnl = self.get_position()['unrealisedPnl']

        # trail assetが設定されていたら
        if self.get_exit_order()['trail_offset'] > 0 and self.get_trail_price() > 0:
            if self.get_position_size() > 0 and \
                    self.get_market_price() - self.get_exit_order()['trail_offset'] < self.get_trail_price():
                logger.info(f"Loss cut by trailing stop: {self.get_exit_order()['trail_offset']}")
                self.close_all()
            elif self.get_position_size() < 0 and \
                    self.get_market_price() + self.get_exit_order()['trail_offset'] > self.get_trail_price():
                logger.info(f"Loss cut by trailing stop: {self.get_exit_order()['trail_offset']}")
                self.close_all()

        # lossが設定されていたら
        if unrealised_pnl < 0 and \
                0 < self.get_exit_order()['loss'] < abs(unrealised_pnl / 100000000):
            logger.info(f"Loss cut by stop loss: {self.get_exit_order()['loss']}")
            self.close_all()

        # profitが設定されていたら
        if unrealised_pnl > 0 and \
                0 < self.get_exit_order()['profit'] < abs(unrealised_pnl / 100000000):
            logger.info(f"Take profit by stop profit: {self.get_exit_order()['profit']}")
            self.close_all()

    def fetch_ohlcv(self, bin_size, start_time, end_time):
        """
        足データを取得する
        :param start_time: 開始時間
        :param end_time: 終了時間
        :return:
        """
        self.__init_client()

        fetch_bin_size = allowed_range[bin_size][0]
        left_time = start_time
        right_time = end_time
        data = to_data_frame([])

        while True:
            source = retry(lambda: self.public_client.Trade.Trade_getBucketed(symbol="XBTUSD", binSize=fetch_bin_size,
                                                                              startTime=left_time, endTime=right_time,
                                                                              count=500, partial=False).result())
            if len(source) == 0:
                break

            source = to_data_frame(source)
            data = pd.concat([data, source])

            if right_time > source.iloc[-1].name + delta(fetch_bin_size):
                left_time = source.iloc[-1].name + delta(fetch_bin_size)
                time.sleep(2)
            else:
                break

        return resample(data, bin_size)

    def security(self, bin_size):
        """
        別時間軸データを再計算して、取得する
        """
        return resample(self.data, bin_size)[:-1]

    def __update_ohlcv(self, action, new_data):
        """
        データを取得して、戦略を実行する。
        """

        if self.data is None:
            end_time = datetime.now(timezone.utc)
            start_time = end_time - self.ohlcv_len * delta(self.bin_size)
            d1 = self.fetch_ohlcv(self.bin_size, start_time, end_time)
            if len(d1) > 0:
                d2 = self.fetch_ohlcv(allowed_range[self.bin_size][0],
                                      d1.iloc[-1].name + delta(allowed_range[self.bin_size][0]), end_time)

                self.data = pd.concat([d1, d2])
            else:
                self.data = d1
        else:
            self.data = pd.concat([self.data, new_data])

        # 最後の行は不確定情報のため、排除する
        re_sample_data = resample(self.data, self.bin_size)[:-1]

        if self.data.iloc[-1].name == re_sample_data.iloc[-1].name:
            self.data = re_sample_data.iloc[-1 * self.ohlcv_len:, :]

        if self.last_action_time is not None and \
                self.last_action_time == re_sample_data.iloc[-1].name:
            return

        open = re_sample_data['open'].values
        close = re_sample_data['close'].values
        high = re_sample_data['high'].values
        low = re_sample_data['low'].values
        volume = re_sample_data['volume'].values

        try:
            if self.strategy is not None:
                self.strategy(open, close, high, low, volume)
            self.last_action_time = re_sample_data.iloc[-1].name
        except FatalError as e:
            # 致命的エラー
            logger.error(f"Fatal error. {e}")
            logger.error(traceback.format_exc())

            notify(f"Fatal error occurred. Stopping Bot. {e}")
            notify(traceback.format_exc())
            self.stop()
        except Exception as e:
            logger.error(f"An error occurred. {e}")
            logger.error(traceback.format_exc())

            notify(f"An error occurred. {e}")
            notify(traceback.format_exc())

    def __on_update_instrument(self, action, instrument):
        """
         取引価格を更新する
        """
        if 'lastPrice' in instrument:
            self.market_price = instrument['lastPrice']

            # trail priceの更新
            if self.get_position_size() > 0 and \
                    self.market_price > self.get_trail_price():
                self.set_trail_price(self.market_price)
            if self.get_position_size() < 0 and \
                    self.market_price < self.get_trail_price():
                self.set_trail_price(self.market_price)

    def __on_update_wallet(self, action, wallet):
        """
         walletを更新する
        """
        self.wallet = {**self.wallet, **wallet} if self.wallet is not None else self.wallet

    def __on_update_position(self, action, position):
        """
         ポジションを更新する
        """
        # ポジションサイズの変更がされたか
        is_update_pos_size = self.get_position()['currentQty'] != position['currentQty']

        # ポジションサイズが変更された場合、トレイル開始価格を現在の価格にリセットする
        if is_update_pos_size and position['currentQty'] != 0:
            self.set_trail_price(self.market_price)

        if is_update_pos_size:
            logger.info(f"Updated Position\n"
                        f"Price: {self.get_position()['avgEntryPrice']} => {position['avgEntryPrice']}\n"
                        f"Qty: {self.get_position()['currentQty']} => {position['currentQty']}\n"
                        f"Balance: {self.get_balance()/100000000} XBT")
            notify(f"Updated Position\n"
                   f"Price: {self.get_position()['avgEntryPrice']} => {position['avgEntryPrice']}\n"
                   f"Qty: {self.get_position()['currentQty']} => {position['currentQty']}\n"
                   f"Balance: {self.get_balance()/100000000} XBT")

        self.position = {**self.position, **position} if self.position is not None else self.position

        # 利確損切の評価
        self.eval_exit()

    def __on_update_margin(self, action, margin):
        """
         マージンを更新する
        """
        self.margin = {**self.margin, **margin} if self.margin is not None else self.margin

    def on_update(self, bin_size, strategy):
        """
        戦略の関数を登録する。
        :param strategy:
        """
        self.bin_size = bin_size
        self.strategy = strategy
        if self.is_running:
            self.ws = BitMexWs(test=self.demo)
            self.ws.bind(allowed_range[bin_size][0], self.__update_ohlcv)
            self.ws.bind('instrument', self.__on_update_instrument)
            self.ws.bind('wallet', self.__on_update_wallet)
            self.ws.bind('position', self.__on_update_position)
            self.ws.bind('margin', self.__on_update_margin)
            self.ob = OrderBook(self.ws)

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

    def plot(self, name, value, color, overlay=True):
        """
        グラフに描画する。
        """
        pass
