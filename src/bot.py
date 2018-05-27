# coding: UTF-8

import sys

from src import logger, notify
from src.mex_stub import BitMexStub
from src.mex_test import BitMexTest
from src.mex import BitMex


class Bot:
    params = {}
    exchange = None
    tr = '1h'
    periods = 20
    test_net = False
    back_test = False
    stub_test = False

    def __init__(self, tr, periods):
        self.tr = tr
        self.periods = periods

    def input(self, title, defval):
        p = {} if self.params is None else self.params
        if title in p:
            return p[title]
        else:
            return defval

    def strategy(self, open, close, high, low):
        pass

    def run(self):
        if self.stub_test:
            self.exchange = BitMexStub(self.tr, self.periods)
        elif self.back_test:
            self.exchange = BitMexTest(self.tr, self.periods)
        else:
            self.exchange = BitMex(self.tr, self.periods, demo=self.test_net)

        logger.info(f"Starting Bot")
        logger.info(f"Strategy : {type(self).__name__}")

        self.exchange.on_update(self.strategy)
        self.exchange.show_result()

    def close(self):
        if self.exchange is None:
            return

        logger.info(f"Stopping Bot")

        self.exchange.stop()
        self.exchange.cancel_all()
        sys.exit()
