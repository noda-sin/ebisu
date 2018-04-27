# coding: UTF-8

import src.util as util
from src.bot import Bot


class ChannelBreakout(Bot):
    def __init__(self, demo=False, test=False, params=None):
        Bot.__init__(self, '1h', 20, demo=demo, test=test, params=params)

    def strategy(self, open, close, high, low):
        length = self.input('length', 18)
        lot = self.exchange.get_balance() / 20
        up = util.highest(high[:-1], length)[-1]
        dn = util.lowest(low[:-1], length)[-1]
        self.exchange.entry(True, lot, stop=up)
        self.exchange.entry(False, lot, stop=dn)
