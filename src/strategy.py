# coding: UTF-8

import numpy as np
import time

from src.bot import Bot
from src.util import Side, highest, lowest, ema, stdev, sma, rci, crossover, crossunder


class ChannelBreakout(Bot):

    def __init__(self, demo=False, test=False, params={}):
        Bot.__init__(self, demo=demo, test=test, tr='1h', periods=20, params=params)

    def strategy(self, source):
        high = np.array([v['high'] for _, v in enumerate(source[:-1])])
        low  = np.array([v['low']  for _, v in enumerate(source[:-1])])

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

class BBMacd(Bot):

    def __init__(self, demo=False, test=False, params={}):
        Bot.__init__(self, demo=demo, test=test, tr='5m', periods=50, params=params)

    def strategy(self, source):
        close = np.array([v['close'] for _, v in enumerate(source[:-1])])

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

class VixRCI(Bot):

    def __init__(self, demo=False, test=False, params={}):
        Bot.__init__(self, demo=demo, test=test, tr='5m', periods=115, params=params)

    def strategy(self, source):
        close = np.array([v['close'] for _, v in enumerate(source[:-1])])
        low   = np.array([v['low']   for _, v in enumerate(source[:-1])])
        pos   = self.bitmex.position_qty()
        lot   = self.bitmex.wallet_balance() / 20

        pd   = 24
        bbl  = 20
        mult = 1.9
        lb   = 85
        ph   = 0.85
        pl   = 1.01

        rci_limit = 20
        rci_diff  = 30

        itvs = 9
        itvm = 36
        itvl = 52

        wvf        = ((highest(close, pd) - low) / (highest(close, pd))) * 100
        s_dev      = mult * stdev(wvf, bbl)
        mid_line   = sma(wvf, bbl)
        lower_band = mid_line - s_dev
        upper_band = mid_line + s_dev
        range_high = (highest(wvf, lb)) * ph
        range_low  = (lowest(wvf, lb)) * pl
        green_hist = [wvf[-i] >= upper_band[-i] or wvf[-i] >= range_high[-i] for i in range(8)][::-1]
        red_hist   = [wvf[-i] <= lower_band[-i] or wvf[-i] <= range_low[-i]  for i in range(8)][::-1]

        up1 = [(not green_hist[-i]) and green_hist[-i-1] and green_hist[-i-2]
               and (not green_hist[-i-3]) and (not green_hist[-i-4]) for i in range(len(green_hist)-5)][::-1]
        dn1 = [(not red_hist[-i]) and red_hist[-i-1] and red_hist[-i-2]
               and (not red_hist[-i-3]) and (not red_hist[-i-4])     for i in range(len(red_hist)-5)][::-1]

        dvup = red_hist[-1]   and red_hist[-2]
        dvdn = green_hist[-1] and green_hist[-2]

        rci_short_arr  = rci(close, itvs)
        rci_middle_arr = rci(close, itvm)
        rci_long_arr   = rci(close, itvl)

        rci_short  = rci_short_arr[-1]
        rci_middle = rci_middle_arr[-1]
        rci_long   = rci_long_arr[-1]

        up2 = rci_short < 0
        dn2 = rci_short > 0

        up31 = rci_long < 0 and rci_middle < 0 and crossover(rci_middle_arr, rci_long_arr)
        up32 = rci_long < -100 + rci_limit and rci_middle < -100 + rci_limit
        up33 = rci_long < 0 and rci_middle < 0 and rci_middle > rci_long
        up34 = rci_long < 0 and rci_middle < 0 and rci_long > rci_middle and rci_long - rci_middle < rci_diff

        up3 = up31 or up32 or up33 or up34

        dn31 = rci_long > 0 and rci_middle > 0 and crossunder(rci_middle_arr, rci_long_arr)
        dn32 = rci_long > 100 - rci_limit and rci_middle > 100 - rci_limit
        dn33 = rci_long > 0 and rci_middle > 0 and rci_middle < rci_long
        dn34 = rci_long > 0 and rci_middle > 0 and rci_long < rci_middle and rci_middle - rci_long < rci_diff

        dn3 = dn31 or dn32 or dn33 or dn34

        long1  = (up1[-1] or up1[-2] or up1[-3]) and (up2 or up3)
        long2  = dvup and up2 and up3
        short1 = (dn1[-1] or dn1[-2] or dn1[-3]) and (dn2 or dn3)
        short2 = dvdn and dn2 and dn3

        exitlong  = (pos > 0 and (rci_middle > 70  or (short1 or short2)))
        exitshort = (pos < 0 and (rci_middle < -70 or (long1 or long2)))

        if (long1 or long2) and pos <= 0:
            if pos < 0:
                lot = 2 * lot
            self.bitmex.entry(side=Side.Long, size=lot)

        if (short1 or short2) and pos >= 0:
            if pos > 0:
                lot = 2 * lot
            self.bitmex.entry(side=Side.Short, size=lot)

        if (exitlong or exitshort) and pos != 0:
            self.bitmex.close_position()