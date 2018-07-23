# coding: UTF-8

import os
import time
from datetime import timedelta, datetime, timezone

import pandas as pd

from src import logger, allowed_range, retry, delta, load_data, resample
from src.bitmex_stub import BitMexStub

OHLC_DIRNAME = os.path.join(os.path.dirname(__file__), "../ohlc/{}")
OHLC_FILENAME = os.path.join(os.path.dirname(__file__), "../ohlc/{}/data.csv")

class BitMexBackTest(BitMexStub):
    # 取引価格
    market_price = 0
    # 時間足データ
    df_ohlcv = None
    # 現在の時間軸
    index = None
    # 現在の時間
    time = None
    # 注文数
    order_count = 0
    # 買い履歴
    buy_signals = []
    # 売り履歴
    sell_signals = []
    # EXIT履歴
    close_signals = []
    # 残高履歴
    balance_history = []
    # 残高の開始
    start_balance = 0
    # プロットデータ
    plot_data = {}
    # 別の時間軸データ
    resample_data = {}

    def __init__(self):
        """
        コンストラクタ
        :param periods:
        """
        BitMexStub.__init__(self, threading=False)
        self.enable_trade_log = False
        self.start_balance = self.get_balance()

    def get_market_price(self):
        """
        取引価格を取得する。
        :return:
        """
        return self.market_price

    def now_time(self):
        """
        現在の時間。
        :return:
        """
        return self.time

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
        BitMexStub.entry(self, id, long, qty, limit, stop, post_only, when)

    def commit(self, id, long, qty, price, need_commission=True):
        """
        約定する。
        :param id: 注文番号
        :param long: ロング or ショート
        :param qty: 注文量
        :param price: 価格
        :param need_commission: 手数料が発生するか
        """
        BitMexStub.commit(self, id, long, qty, price, need_commission)

        if long:
            self.buy_signals.append(self.index)
        else:
            self.sell_signals.append(self.index)

    def close_all(self):
        """
        すべてのポジションを解消する。
        """
        if self.get_position_size() == 0:
            return 
        BitMexStub.close_all(self)
        self.close_signals.append(self.index)

    def __crawler_run(self):
        """
        データを取得して、戦略を実行する。
        """
        start = time.time()

        for i in range(self.ohlcv_len):
            self.balance_history.append((self.get_balance() - self.start_balance)/100000000*self.get_market_price())

        for i in range(len(self.df_ohlcv) - self.ohlcv_len):
            self.data = self.df_ohlcv.iloc[i:i + self.ohlcv_len, :]
            timestamp = self.data.iloc[-1].name
            close = self.data['close'].values
            open = self.data['open'].values
            high = self.data['high'].values
            low = self.data['low'].values
            volume = self.data['volume'].values

            if self.get_position_size() > 0 and low[-1] > self.get_trail_price():
                self.set_trail_price(low[-1])
            if self.get_position_size() < 0 and high[-1] < self.get_trail_price():
                self.set_trail_price(high[-1])

            self.market_price = close[-1]
            self.time = timestamp.tz_convert('Asia/Tokyo')
            self.index = timestamp
            self.strategy(open, close, high, low, volume)

            self.balance_history.append((self.get_balance() - self.start_balance) / 100000000 * self.get_market_price())
            self.eval_exit()

        self.close_all()
        logger.info(f"Back test time : {time.time() - start}")

    def on_update(self, bin_size, strategy):
        """
        戦略の関数を登録する。
        :param strategy:
        """
        self.__load_ohlcv(bin_size)

        BitMexStub.on_update(self, bin_size, strategy)
        self.__crawler_run()

    def security(self, bin_size):
        """
        別時間軸データを再計算して、取得する
        """
        if bin_size not in self.resample_data:
            self.resample_data[bin_size] = resample(self.df_ohlcv, bin_size)
        return self.resample_data[bin_size][:self.data.iloc[-1].name].iloc[-1 * self.ohlcv_len:, :]

    def download_data(self, file, bin_size, start_time, end_time):
        """
        データをサーバーから取得する。
        """
        if not os.path.exists(os.path.dirname(file)):
            os.makedirs(os.path.dirname(file))

        data = pd.DataFrame()
        left_time = None
        source = None
        is_last_fetch = False

        while True:
            if left_time is None:
                left_time = start_time
                right_time = left_time + delta(allowed_range[bin_size][0]) * 99
            else:
                left_time = source.iloc[-1].name + + delta(allowed_range[bin_size][0]) * allowed_range[bin_size][2]
                right_time = left_time + delta(allowed_range[bin_size][0]) * 99

            if right_time > end_time:
                right_time = end_time
                is_last_fetch = True

            source = self.fetch_ohlcv(bin_size=bin_size, start_time=left_time, end_time=right_time)
            data = pd.concat([data, source])

            if is_last_fetch:
                data.to_csv(file)
                break

            time.sleep(2)

    def __load_ohlcv(self, bin_size):
        """
        データを読み込む。
        :return:
        """
        start_time = datetime.now(timezone.utc) - 1 * timedelta(days=31)
        end_time = datetime.now(timezone.utc)
        file = OHLC_FILENAME.format(bin_size)

        if os.path.exists(file):
            self.df_ohlcv = load_data(file)
        else:
            self.download_data(file, bin_size, start_time, end_time)
            self.df_ohlcv = load_data(file)

    def show_result(self):
        """
        取引結果を表示する。
        """
        logger.info(f"============== Result ================")
        logger.info(f"TRADE COUNT   : {self.order_count}")
        logger.info(f"BALANCE       : {self.get_balance()}")
        logger.info(f"PROFIT RATE   : {self.get_balance()/self.start_balance*100} %")
        logger.info(f"WIN RATE      : {0 if self.order_count == 0 else self.win_count/self.order_count*100} %")
        logger.info(f"PROFIT FACTOR : {self.win_profit if self.lose_loss == 0 else self.win_profit/self.lose_loss}")
        logger.info(f"MAX DRAW DOWN : {self.max_draw_down * 100}")
        logger.info(f"======================================")

        import matplotlib.pyplot as plt

        plt_num = len([k for k, v in self.plot_data.items() if not v['overlay']]) + 2
        i = 1

        plt.figure(figsize=(12,8))

        plt.subplot(plt_num,1,i)
        plt.plot(self.df_ohlcv.index, self.df_ohlcv["high"])
        plt.plot(self.df_ohlcv.index, self.df_ohlcv["low"])
        for k, v in self.plot_data.items():
            if v['overlay']:
                color = v['color']
                plt.plot(self.df_ohlcv.index, self.df_ohlcv[k], color)
        plt.ylabel("Price(USD)")
        ymin = min(self.df_ohlcv["low"]) - 200
        ymax = max(self.df_ohlcv["high"]) + 200
        plt.vlines(self.buy_signals, ymin, ymax, "blue", linestyles='dashed', linewidth=1)
        plt.vlines(self.sell_signals, ymin, ymax, "red", linestyles='dashed', linewidth=1)
        plt.vlines(self.close_signals, ymin, ymax, "green", linestyles='dashed', linewidth=1)

        i = i + 1

        for k, v in self.plot_data.items():
            if not v['overlay']:
                plt.subplot(plt_num,1,i)
                color = v['color']
                plt.plot(self.df_ohlcv.index, self.df_ohlcv[k], color)
                plt.ylabel(f"{k}")
                i = i + 1

        plt.subplot(plt_num,1,i)
        plt.plot(self.df_ohlcv.index, self.balance_history)
        plt.hlines(y=0, xmin=self.df_ohlcv.index[0],
                   xmax=self.df_ohlcv.index[-1], colors='k', linestyles='dashed')
        plt.ylabel("PL(USD)")

        plt.show()

    def plot(self, name, value, color, overlay=True):
        """
        グラフに描画する。
        """
        self.df_ohlcv.at[self.index, name] = value
        if name not in self.plot_data:
            self.plot_data[name] = {'color': color, 'overlay': overlay}

