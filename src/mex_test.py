# coding: UTF-8

import os
import time
from datetime import timedelta, datetime, timezone

import pandas as pd

from src import change_rate, logger, allowed_range, retry, delta
from src.mex_stub import BitMexStub

OHLC_DIRNAME = os.path.join(os.path.dirname(__file__), "../ohlc/{}")
OHLC_FILENAME = os.path.join(os.path.dirname(__file__), "../ohlc/{}/ohlc_{}.csv")

# バックテスト用クラス
class BitMexTest(BitMexStub):
    # 取引価格
    market_price = 0
    # 時間足データ
    ohlcv_data_frame = None
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
    # 残高履歴
    balance_history = []
    # 残高の開始
    start_balance = 0
    # プロットデータ
    plot_data = {}

    def __init__(self, tr):
        """
        コンストラクタ
        :param tr:
        :param periods:
        """
        BitMexStub.__init__(self, tr, run=False)
        self.__load_ohlcv()
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
        BitMexStub.entry(self, id, long, qty, limit, stop, when)

    def commit(self, id, long, qty, price):
        """
        約定する。
        :param id: 注文番号
        :param long: ロング or ショート
        :param qty: 注文量
        :param price: 価格
        """
        BitMexStub.commit(self, id, long, qty, price)

        if long:
            self.buy_signals.append(self.index)
        else:
            self.sell_signals.append(self.index)

    def __crawler_run(self):
        """
        データを取得して、戦略を実行する。
        """
        length = 90

        start = time.time()

        for i in range(length):
            self.balance_history.append(self.get_balance() - self.start_balance)

        for i in range(len(self.ohlcv_data_frame)-length):
            slice = self.ohlcv_data_frame.iloc[i:i+length,:]
            timestamp = slice['timestamp'].iloc[-1]
            close = slice['close'].values
            open = slice['open'].values
            high = slice['high'].values
            low = slice['low'].values

            self.market_price = close[-1]
            self.time = (timestamp + timedelta(hours=8)).tz_localize('Asia/Tokyo')
            self.index = timestamp
            self.listener(open, close, high, low)
            self.balance_history.append(self.get_balance() - self.start_balance)

        self.close_all()

        logger.info(f"Back test time : {time.time() - start}")

    def on_update(self, listener):
        """
        戦略の関数を登録する。
        :param listener:
        """
        BitMexStub.on_update(self, listener)
        self.__crawler_run()

    def __load_ohlcv_file(self):
        """
        ファイルからデータを読み込む。
        """
        i = 0
        while True:
            filename = OHLC_FILENAME.format(self.tr, i)
            if os.path.exists(filename) and self.ohlcv_data_frame is None:
                self.ohlcv_data_frame = pd.read_csv(filename)
                i += 1
            elif os.path.exists(filename):
                self.ohlcv_data_frame = pd.concat([self.ohlcv_data_frame, pd.read_csv(filename)], ignore_index=True)
                i += 1
            else:
                break

        source = []
        for index, row in self.ohlcv_data_frame.iterrows():
            if len(source) == 0:
                source.append({
                    'timestamp': row['timestamp'],
                    'open': row['open'],
                    'close': row['close'],
                    'high': row['high'],
                    'low': row['low']
                })
                continue

            prev_row = source[-1]

            timestamp = row['timestamp']
            open = prev_row['open'] if change_rate(prev_row['open'], row['open']) > 1.5 else row['open']
            close = prev_row['close'] if change_rate(prev_row['close'], row['close']) > 1.5 else row['close']
            high = prev_row['high'] if change_rate(prev_row['high'], row['high']) > 1.5 else row['high']
            low = row['low']

            source.append({'timestamp': timestamp, 'open': open, 'close': close, 'high': high, 'low': low})

        source = pd.DataFrame(source)
        self.ohlcv_data_frame = pd.DataFrame({
            'timestamp': pd.to_datetime(source['timestamp']),
            'open': source['open'],
            'close': source['close'],
            'high': source['high'],
            'low': source['low']
        })
        self.ohlcv_data_frame.index = self.ohlcv_data_frame['timestamp']

    def __save_ohlcv(self):
        """
        データをサーバーから取得する。
        """
        os.makedirs(OHLC_DIRNAME.format(self.tr), exist_ok=True)

        if self.tr.endswith('d') or self.tr.endswith('h'):
            start_time = datetime(year=2017, month=1, day=1, hour=0, minute=0).astimezone(timezone.utc)
        else:
            start_time = datetime.now(timezone.utc) - timedelta(days=31)

        end_time = datetime.now(timezone.utc)

        data = []
        i = 0
        left_time = None
        right_time = None
        source = None
        is_last_fetch = False
        while True:
            if left_time is None:
                left_time = start_time
                right_time = left_time + delta(allowed_range[self.tr][0]) * 99
            else:
                left_time = source[-1]["timestamp"] + + delta(allowed_range[self.tr][0]) * allowed_range[self.tr][2]
                right_time = left_time + delta(allowed_range[self.tr][0]) * 99

            if right_time > end_time:
                right_time = end_time
                is_last_fetch = True

            source = retry(lambda: self.fetch_ohlcv(start_time=left_time, end_time=right_time))

            data.extend(source)

            if is_last_fetch:
                df = pd.DataFrame(data)
                df.to_csv(OHLC_FILENAME.format(self.tr, i))
                break
            elif len(data) > 65000:
                df = pd.DataFrame(data)
                df.to_csv(OHLC_FILENAME.format(self.tr, i))
                data = []
                i += 1
            time.sleep(2)

    def __load_ohlcv(self):
        """
        データを読み込む。
        :return:
        """
        if os.path.exists(OHLC_FILENAME.format(self.tr, 0)):
            self.__load_ohlcv_file()
        else:
            self.__save_ohlcv()
            self.__load_ohlcv_file()

    def show_result(self):
        """
        取引結果を表示する。
        """
        logger.info(f"============== Result ================")
        logger.info(f"TRADE COUNT   : {self.order_count}")
        logger.info(f"BALANCE       : {self.get_balance()}")
        logger.info(f"WIN RATE      : {0 if self.order_count == 0 else self.win_count/self.order_count*100} %")
        logger.info(f"PROFIT FACTOR : {self.win_profit if self.lose_loss == 0 else self.win_profit/self.lose_loss}")
        logger.info(f"MAX DRAW DOWN : {self.max_draw_down * 100}")
        logger.info(f"======================================")

        import matplotlib.pyplot as plt
        plt.figure()
        plt.subplot(211)
        plt.plot(self.ohlcv_data_frame.index, self.ohlcv_data_frame["high"])
        plt.plot(self.ohlcv_data_frame.index, self.ohlcv_data_frame["low"])
        for k, v in self.plot_data.items():
            plt.plot(self.ohlcv_data_frame.index, self.ohlcv_data_frame[k])
        plt.ylabel("Price(USD)")
        ymin = min(self.ohlcv_data_frame["low"]) - 200
        ymax = max(self.ohlcv_data_frame["high"]) + 200
        plt.vlines(self.buy_signals, ymin, ymax, "blue", linestyles='dashed', linewidth=1)
        plt.vlines(self.sell_signals, ymin, ymax, "red", linestyles='dashed', linewidth=1)
        plt.subplot(212)
        plt.plot(self.ohlcv_data_frame.index, self.balance_history)
        plt.hlines(y=0, xmin=self.ohlcv_data_frame.index[0],
                   xmax=self.ohlcv_data_frame.index[-1], colors='k', linestyles='dashed')
        plt.ylabel("PL(USD)")
        plt.show()

    def plot(self, name, value, color):
        """
        グラフに描画する。
        """
        self.ohlcv_data_frame.at[self.index, name] = value
        if name not in self.plot_data:
            self.plot_data[name] = {'color': color}

