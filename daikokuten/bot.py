# coding: UTF-8

import sys

from daikokuten.mex_stub import BitMexStub
from daikokuten.mex_test import BitMexTest
from daikokuten.mex import BitMex


class Bot:
    def __init__(self, tr, periods, demo=False, test=False, params=None):
        if params is None:
            params = {}
        self.params = params

        if demo:
            self.exchange = BitMexStub(tr, periods)
        elif test:
            self.exchange = BitMexTest(tr, periods)
        else:
            self.exchange = BitMex(tr, periods)

    def input(self, title, defval):
        if title in self.params:
            return self.params[title]
        else:
            return defval

    def strategy(self, open, close, high, low):
        pass

    def run(self):
        self.exchange.on_update(self.strategy)
        self.exchange.show_result()

    def close(self):
        self.exchange.cancel_all()
        self.exchange.close_all()
        sys.exit()
