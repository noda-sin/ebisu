# coding: UTF-8

import sys

from hyperopt import fmin, tpe, STATUS_OK, STATUS_FAIL, Trials

from src import logger
from src.bitmex import BitMex
from src.bitmex_stub import BitMexStub
from src.bitmex_backtest import BitMexBackTest


class Bot:
    # パラメータ
    params = {}
    # 取引所
    exchange = None
    # 時間足
    bin_size = '1h'
    # 足の期間
    periods = 20
    # テストネットを利用するか
    test_net = False
    # バックテストか
    back_test = False
    # スタブ取引か
    stub_test = False
    # パラメータ探索か
    hyperopt = False

    def __init__(self, bin_size):
        """
        コンストラクタ。
        :param bin_size: 時間足
        :param periods: 期間
        """
        self.bin_size = bin_size

    def options(self):
        """
        パレメータ探索用の値を取得する関数。
        """
        pass

    def ohlcv_len(self):
        """
        戦略にわたすOHLCの長さ
        """
        return 100

    def input(self, title, type, defval):
        """
        パレメータを取得する関数。
        :param title: パレメータ名
        :param defval: デフォルト値
        :return: 値
        """
        p = {} if self.params is None else self.params
        if title in p:
            return type(p[title])
        else:
            return defval

    def strategy(self, open, close, high, low):
        """
        戦略関数。Botを作成する際は、この関数を継承して実装してください。
        :param open: 始値
        :param close: 終値
        :param high: 高値
        :param low: 安値
        """
        pass

    def params_search(self):
        """
 ˜      パラメータ検索を行う関数。
        """
        def objective(args):
            logger.info(f"Params : {args}")
            try:
                self.params = args
                self.exchange = BitMexBackTest()
                self.exchange.on_update(self.bin_size, self.strategy)
                profit_factor = self.exchange.win_profit/self.exchange.lose_loss
                logger.info(f"Profit Factor : {profit_factor}")
                ret = {
                    'status': STATUS_OK,
                    'loss': 1/profit_factor
                }
            except Exception as e:
                ret = {
                    'status': STATUS_FAIL
                }

            return ret

        trials = Trials()
        best_params = fmin(objective, self.options(), algo=tpe.suggest, trials=trials, max_evals=200)
        logger.info(f"Best params is {best_params}")
        logger.info(f"Best profit factor is {1/trials.best_trial['result']['loss']}")

    def run(self):
        """
˜       Botを起動する関数。
        """
        logger.info(f"Starting Bot")
        logger.info(f"Strategy : {type(self).__name__}")

        if self.hyperopt:
            logger.info(f"Bot Mode : Hyperopt")
            self.params_search()
            return

        elif self.stub_test:
            logger.info(f"Bot Mode : Stub")
            self.exchange = BitMexStub()
        elif self.back_test:
            logger.info(f"Bot Mode : Back test")
            self.exchange = BitMexBackTest()
        else:
            logger.info(f"Bot Mode : Trade")
            self.exchange = BitMex(demo=self.test_net)

        self.exchange.ohlcv_len = self.ohlcv_len()
        self.exchange.on_update(self.bin_size, self.strategy)
        self.exchange.show_result()

    def stop(self):
        """
˜       Botを停止する関数。Openしている注文は、キャンセルする。
        """
        if self.exchange is None:
            return

        logger.info(f"Stopping Bot")

        self.exchange.stop()
        self.exchange.cancel_all()
        sys.exit()
