# coding: UTF-8
from daikokuten import highest, lowest
from daikokuten.bot import Bot


class ChannelBreakout(Bot):
    def __init__(self, demo=False, test=False, params=None):
        Bot.__init__(self, '1h', 20, demo=demo, test=test, params=params)

    def strategy(self, open, close, high, low):
        length = self.input('length', 18)
        lot = self.exchange.get_balance() / 20
        up = highest(high[:-1], length)[-1]
        dn = lowest(low[:-1], length)[-1]
        self.exchange.entry("Long",  True,  lot, stop=up)
        self.exchange.entry("Short", False, lot, stop=dn)
