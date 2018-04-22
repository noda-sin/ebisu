# coding: UTF-8

from src.bot import Bot
from util import Side, highest, lowest, ema, stdev, sma


class ChannelBreakout(Bot):

    def __init__(self, demo=False, test=False, params={}):
        Bot.__init__(self, demo=demo, test=test, tr='1h', periods=20, params=params)

    def strategy(self, source):
        high = [v['high'] for _, v in enumerate(source[:-1])]
        low  = [v['low'] for _, v in enumerate(source[:-1])]

        length = self.input('length', 18)
        lot = self.bitmex.wallet_balance() / 20

        is_up = (high[-1] == highest(high, length)[-1])
        is_dn = (low[-1] == lowest(low, length)[-1])

        pos = self.bitmex.position_qty()

        # エントリー
        if is_up and pos <= 0:
            if pos < 0:
                lot = 2 * lot
            self.bitmex.entry(side=Side.Long, size=lot)
        elif is_dn and pos >= 0:
            if pos > 0:
                lot = 2 * lot
            self.bitmex.entry(side=Side.Short, size=lot)