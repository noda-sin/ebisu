# coding: UTF-8

from src.bot import Bot
from util import Side, highest, lowest, ema, stdev, sma


class Dotenkun(Bot):

    def __init__(self, demo=False, test=False, params={}):
        Bot.__init__(self, demo=demo, test=test, params=params)

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

class BB(Bot):

    def __init__(self, demo=False, test=False, params={}):
        Bot.__init__(self, demo=demo, test=test, params=params)

    def strategy(self, source):
        close = [v['close'] for _, v in enumerate(source[:-1])]

        lot    = self.bitmex.wallet_balance() / 20
        bb_len = self.input('bb_len', 10)
        dev    = self.input('dev', 1)
        depth  = self.input('depth', 16)

        # MACD
        fast_len = self.input('fast_len', 12)
        slow_len = self.input('slow_len', 26)

        fast_ma  = ema(close, fast_len)
        slow_ma  = ema(close, slow_len)
        macd     = fast_ma - slow_ma

        # BollingerBands
        std   = stdev(macd, bb_len)
        upper = (std * dev + (sma(macd, bb_len)))
        lower = ((sma(macd, bb_len)) - (std * dev))

        band = upper - lower

        print(band[-1])

        is_up = lower[-1] < macd[-1] and \
                macd[-1] < upper[-1] and \
                lower[-2] < macd[-2] and \
                macd[-2] < upper[-2] and \
                lower[-3] > macd[-3] and \
                band[-1] > depth

        is_dn = lower[-1] < macd[-1] and \
                macd[-1] < upper[-1] and \
                lower[-2] < macd[-2] and \
                macd[-2] < upper[-2] and \
                upper[-3] < macd[-3] and \
                band[-1] > depth

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