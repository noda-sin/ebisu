# coding: UTF-8

import sys

from src.mex_stub import BitMexStub
from src.mex_test import BitMexTest

from src.mex import BitMex


class Bot:
    def __init__(self, demo=False, test=False, tr='1h', periods=20, params=None):
        if params is None:
            params = {}
        self.params = params

        if demo:
            self.bitmex = BitMexStub(tr=tr, periods=periods)
        elif test:
            self.bitmex = BitMexTest(tr=tr, periods=periods)
        else:
            self.bitmex = BitMex(tr=tr, periods=periods)

    def input(self, title, defval):
        if title in self.params:
            return self.params[title]
        else:
            return defval

    def strategy(self, open, close, high, low):
        pass

    def run(self):
        self.bitmex.on_update(listener=self.strategy)
        self.bitmex.print_result()

    def close(self):
        self.bitmex.close_order()
        self.bitmex.close_position()
        sys.exit()
