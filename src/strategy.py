# coding: UTF-8
import random

from hyperopt import hp
from src import highest, lowest, sma, crossover, crossunder, last, stdev, rci
from src.bot import Bot

# チャネルブレイクアウト戦略
class Doten(Bot):
    def __init__(self):
        Bot.__init__(self, '2h')

    def options(self):
        return {
            'length': hp.quniform('length', 1, 30, 1),
        }

    def strategy(self, open, close, high, low):
        lot = self.exchange.get_lot()
        length = self.input('length', int, 9)
        up = last(highest(high, length))
        dn = last(lowest(low, length))
        self.exchange.plot('up', up, 'b')
        self.exchange.plot('dn', dn, 'r')
        self.exchange.entry("Long",  True,  round(lot / 2), stop=up)
        self.exchange.entry("Short", False, round(lot / 2), stop=dn)

# SMAクロス戦略
class SMA(Bot):
    def __init__(self):
        Bot.__init__(self, '2h')

    def strategy(self, open, close, high, low):
        lot = self.exchange.get_lot()
        fast_len = self.input('fast_len', 9)
        slow_len = self.input('slow_len', 16)
        fast_sma = sma(close, fast_len)
        slow_sma = sma(close, slow_len)
        golden_cross = crossover(fast_sma, slow_sma)
        dead_cross = crossunder(fast_sma, slow_sma)
        if golden_cross:
            self.exchange.entry("Long", True, lot)
        if dead_cross:
            self.exchange.entry("Short", False, lot)

# Rci戦略
class Rci(Bot):
    def __init__(self):
        Bot.__init__(self, '5m')

    def strategy(self, open, close, high, low):
        lot = self.exchange.get_lot()

        itv_s = self.input('rcv_short_len', 9, )
        itv_m = self.input('rcv_short_len', 13)
        itv_l = self.input('rcv_short_len', 15)

        rci_s = rci(close, itv_s)
        rci_m = rci(close, itv_m)
        rci_l = rci(close, itv_l)

        long = ((-80 > rci_s[-1] > rci_s[-2]) or (-82 > rci_m[-1] > rci_m[-2])) \
                  and (rci_l[-1] < -10 and rci_l[-2] > rci_l[-2])
        short = ((80 < rci_s[-1] < rci_s[-2]) or (rci_m[-1] < -82 and rci_m[-1] < rci_m[-2])) \
                   and (10 < rci_l[-1] < rci_l[-2])
        close_all = 80 < rci_m[-1] < rci_m[-2] or -80 > rci_m[-1] > rci_m[-2]

        if long:
            self.exchange.entry("Long", True, lot)
        elif short:
            self.exchange.entry("Short", False, lot)
        elif close_all:
            self.exchange.close_all()

# VixRci戦略
class VixRci(Bot):
    def __init__(self):
        Bot.__init__(self, '5m')

    def options(self):
        return {
            'pd'       : hp.quniform('pd', 1, 30, 1),
            'bbl'      : hp.quniform('bbl', 1, 30, 1),
            'mult'     : hp.quniform('mult', 1, 30, 1),
            'lb'       : hp.quniform('lb', 1, 30, 1),
            'ph'       : hp.quniform('ph', 1, 30, 1),
            'pl'       : hp.quniform('pl', 1, 30, 1),
            'rci_limit': hp.quniform('rci_limit', 1, 30, 1),
            'rci_diff' : hp.quniform('rci_diff', 1, 30, 1),
            'itvs'     : hp.quniform('itvs', 1, 30, 1),
            'itvm'     : hp.quniform('itvm', 1, 30, 1),
            'itvl'     : hp.quniform('itvl', 1, 30, 1),
        }

    def strategy(self, open, close, high, low):
        lot = self.exchange.get_lot()
        pos = self.exchange.get_position_size()

        pd   = self.input('pd',     int,   24)
        bbl  = self.input('bbl',    int,   20)
        mult = self.input('mult', float,  1.9)
        lb   = self.input('lb',     int,   88)
        ph   = self.input('ph',   float, 0.85)
        pl   = self.input('pl',   float, 1.01)

        rci_limit = self.input('rci_limit', int, 20)
        rci_diff  = self.input('rci_diff',  int, 30)

        itvs = self.input('itvs', int,  9)
        itvm = self.input('itvs', int, 36)
        itvl = self.input('itvs', int, 55)

        wvf        = ((highest(close, pd) - low) / (highest(close, pd))) * 100
        s_dev      = mult * stdev(wvf, bbl)
        mid_line   = sma(wvf, bbl)
        lower_band = mid_line - s_dev
        upper_band = mid_line + s_dev

        range_high = (highest(wvf, lb)) * ph
        range_low  = (lowest(wvf, lb)) * pl

        green_hist = [wvf[-i] >= upper_band[-i] or wvf[-i] >= range_high[-i] for i in range(8)][::-1]
        red_hist   = [wvf[-i] <= lower_band[-i] or wvf[-i] <= range_low[-i]  for i in range(8)][::-1]

        # VIX Color Change
        up1 = [(not green_hist[-i]) and green_hist[-i-1] and green_hist[-i-2]
               and (not green_hist[-i-3]) and (not green_hist[-i-4]) for i in range(len(green_hist)-5)][::-1]
        dn1 = [(not red_hist[-i]) and red_hist[-i-1] and red_hist[-i-2]
               and (not red_hist[-i-3]) and (not red_hist[-i-4])     for i in range(len(red_hist)-5)][::-1]

        dvup = red_hist[-1]   and red_hist[-2]
        dvdn = green_hist[-1] and green_hist[-2]

        # RCI
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

        if (long1 or long2) and not (short1 or short2 or exitlong):
            self.exchange.entry("Long", True, lot)
        elif (short1 or short2) and not (long1 or long2 or exitshort):
            self.exchange.entry("Short", False, lot)
        elif (exitlong or exitshort):
            self.exchange.close_all()

# サンプル戦略
class Sample(Bot):
    def __init__(self):
        # 第一引数: 戦略で使う足幅
        # 1分足で直近10期間の情報を戦略で必要とする場合
        Bot.__init__(self, '1m')

    def strategy(self, open, close, high, low):
        lot = self.exchange.get_lot()
        which = random.randrange(2)
        if which == 0:
            self.exchange.entry("Long", True, lot)
        else:
            self.exchange.entry("Short", False, lot)
