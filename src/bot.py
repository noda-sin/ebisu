# coding: UTF-8

import sys

from src import logger
from src.mex import BitMex
from src.mex_stub import BitMexStub
from src.mex_test import BitMexTest


class Bot:
    # パラメータ
    params = {}
    # 取引所
    exchange = None
    # 時間足
    tr = '1h'
    # 足の期間
    periods = 20
    # テストネットを利用するか
    test_net = False
    # バックテストか
    back_test = False
    # スタブ取引か
    stub_test = False

    def __init__(self, tr):
        """
        コンストラクタ。
        :param tr: 時間足
        :param periods: 期間
        """
        self.tr = tr

    def input(self, title, defval):
        """
        パレメータを取得する関数。
        :param title: パレメータ名
        :param defval: デフォルト値
        :return: 値
        """
        p = {} if self.params is None else self.params
        if title in p:
            return p[title]
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

    def run(self):
        """
˜       Botを起動する関数。
        """
        if self.stub_test:
            self.exchange = BitMexStub(self.tr)
        elif self.back_test:
            self.exchange = BitMexTest(self.tr)
        else:
            self.exchange = BitMex(self.tr, demo=self.test_net)

        logger.info(f"Starting Bot")
        logger.info(f"Strategy : {type(self).__name__}")

        self.exchange.on_update(self.strategy)
        self.exchange.show_result()

    def close(self):
        """
˜       Botを停止する関数。Openしている注文は、キャンセルする。
        """
        if self.exchange is None:
            return

        logger.info(f"Stopping Bot")

        self.exchange.stop()
        self.exchange.cancel_all()
        sys.exit()
