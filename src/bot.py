# coding: UTF-8

import sys

from src import logger
from src.mex_stub import BitMexStub
from src.mex_test import BitMexTest
from src.mex import BitMex


class Bot:
    def __init__(self, tr, periods, demo=False, stub=False, test=False, params=None):
        if params is None:
            params = {}
        self.params = params

        if stub:
            self.exchange = BitMexStub(tr, periods)
        elif test:
            self.exchange = BitMexTest(tr, periods)
        else:
            self.exchange = BitMex(tr, periods, demo=demo)

    def input(self, title, defval):
        if title in self.params:
            return self.params[title]
        else:
            return defval

    def strategy(self, open, close, high, low):
        pass

    def run(self):
        logger.info(f"Starting Bot")
        logger.info(f"Strategy : {type(self).__name__}")

        self.exchange.on_update(self.strategy)
        self.exchange.show_result()

    def close(self):
        logger.info(f"Stopping Bot")

        self.exchange.stop()
        self.exchange.cancel_all()
        self.exchange.close_all()
        sys.exit()
