# coding: UTF-8
from src import highest, lowest, sma, crossover, crossunder
from src.bot import Bot

class Doten(Bot):
    def __init__(self, demo=False, stub=False, test=False, params=None):
        Bot.__init__(self, '2h', 15, demo=demo, stub=stub, test=test, params=params)

    def strategy(self, open, close, high, low):
        lot = self.exchange.get_lot()
        length = self.input('length', 9)
        up = highest(high[:-1], length)[-1]
        dn = lowest(low[:-1], length)[-1]
        self.exchange.entry("Long",  True,  round(lot / 2), stop=up)
        self.exchange.entry("Short", False, round(lot / 2), stop=dn)

class Sma(Bot):
    def __init__(self, demo=False, stub=False, test=False, params=None):
        Bot.__init__(self, '2h', 18, demo=demo, stub=stub, test=test, params=params)

    def strategy(self, open, close, high, low):
        lot = self.exchange.get_lot()
        fast_len = self.input('fast_len', 9)
        slow_len = self.input('slow_len', 16)
        fast_sma = sma(close, fast_len)
        slow_sma = sma(close, slow_len)
        golden_cross = crossover(fast_sma, slow_sma)
        dead_cross = crossunder(fast_sma, slow_sma)
        market_price = self.exchange.get_market_price()
        if golden_cross:
            self.exchange.entry("Long", True, lot, limit=market_price)
        if dead_cross:
            self.exchange.entry("Short", False, lot, limit=market_price)