# coding: UTF-8

import sys

from mex import BitMex
from mex_stub import BitMexStub
from mex_test import BitMexTest

class Bot:
    def __init__(self, demo=False, test=False, timerange='1h', duration=20, params={}):
        self.params  = params

        if demo:
            self.bitmex = BitMexStub(timerange=timerange, duration=duration)
        elif test:
            self.bitmex = BitMexTest(timerange=timerange, duration=duration)
        else:
            self.bitmex = BitMex(timerange=timerange, duration=duration)

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

    def exit(self):
        self.bitmex.cancel_orders()
        self.bitmex.close_position()
        sys.exit()
