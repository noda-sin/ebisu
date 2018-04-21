# coding: UTF-8

import sys

from mex import BitMex
from mex_stub import BitMexStub
from mex_test import BitMexTest

class Bot:
    def __init__(self, demo=False, test=False, tr='1h', periods=20, params={}):
        self.params  = params

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

    def strategy(self, source):
        pass

    def run(self):
        self.bitmex.on_update(listener=self.strategy)
        self.bitmex.print_result()

    def close(self):
        self.bitmex.cancel_orders()
        self.bitmex.close_position()
        sys.exit()
