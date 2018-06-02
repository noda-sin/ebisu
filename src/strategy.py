# coding: UTF-8
import random

from src import highest, lowest, sma, crossover, crossunder, last
from src.bot import Bot

# チャネルブレイクアウト戦略
class Doten(Bot):
    def __init__(self):
        Bot.__init__(self, '2h', 20)

    def strategy(self, open, close, high, low):
        lot = self.exchange.get_lot()
        length = self.input('length', 9)
        up = last(highest(high, length))
        dn = last(lowest(low, length))
        self.exchange.plot('up', up, 'b')
        self.exchange.plot('dn', dn, 'r')
        self.exchange.entry("Long",  True,  round(lot / 2), stop=up)
        self.exchange.entry("Short", False, round(lot / 2), stop=dn)

# SMAクロス戦略
class SMA(Bot):
    def __init__(self):
        Bot.__init__(self, '2h', 18)

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

# サンプル戦略
class Sample(Bot):
    def __init__(self):
        # 第一引数: 戦略で使う足幅
        # 第二引数: 戦略で使うデータ期間
        # 1分足で直近10期間の情報を戦略で必要とする場合
        Bot.__init__(self, '1m', 10)

    def strategy(self, open, close, high, low):
        lot = self.exchange.get_lot()
        which = random.randrange(2)
        if which == 0:
            self.exchange.entry("Long", True, lot)
        else:
            self.exchange.entry("Short", False, lot)
