# coding: UTF-8

import random

from hyperopt import hp

from src import highest, lowest, sma, crossover, crossunder, last, rci, double_ema, ema, triple_ema, wma, \
    ssma, hull, stdev, vix
from src.bot import Bot


# チャネルブレイクアウト戦略
class Doten(Bot):
    def __init__(self):
        Bot.__init__(self, '2h')

    def options(self):
        return {
            'length': hp.randint('length', 1, 30, 1),
        }

    def strategy(self, open, close, high, low, volume):
        lot = self.exchange.get_lot()
        length = self.input('length', int, 9)
        up = last(highest(high, length))
        dn = last(lowest(low, length))
        self.exchange.plot('up', up, 'b')
        self.exchange.plot('dn', dn, 'r')
        self.exchange.entry("Long", True, round(lot / 2), stop=up)
        self.exchange.entry("Short", False, round(lot / 2), stop=dn)


# SMAクロス戦略
class SMA(Bot):
    def __init__(self):
        Bot.__init__(self, '2h')

    def options(self):
        return {
            'fast_len': hp.quniform('fast_len', 1, 30, 1),
            'slow_len': hp.quniform('slow_len', 1, 30, 1),
        }

    def strategy(self, open, close, high, low, volume):
        lot = self.exchange.get_lot()
        fast_len = self.input('fast_len', int, 9)
        slow_len = self.input('slow_len', int, 16)
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

    def options(self):
        return {
            'rcv_short_len': hp.quniform('rcv_short_len', 1, 10, 1),
            'rcv_medium_len': hp.quniform('rcv_medium_len', 5, 15, 1),
            'rcv_long_len': hp.quniform('rcv_long_len', 10, 20, 1),
        }

    def strategy(self, open, close, high, low, volume):
        lot = self.exchange.get_lot()

        itv_s = self.input('rcv_short_len', int, 5)
        itv_m = self.input('rcv_medium_len', int, 9)
        itv_l = self.input('rcv_long_len', int, 15)

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


# OCC
class OCC(Bot):
    variants = [sma, ema, double_ema, triple_ema, wma, ssma, hull]
    eval_time = None

    def __init__(self):
        Bot.__init__(self, '1m')

    def ohlcv_len(self):
        return 15 * 30

    def options(self):
        return {
            'variant_type': hp.quniform('variant_type', 0, len(self.variants) - 1, 1),
            'basis_len': hp.quniform('basis_len', 1, 30, 1),
            'resolution': hp.quniform('resolution', 1, 15, 1)
        }

    def strategy(self, open, close, high, low, volume):
        lot = self.exchange.get_lot()

        variant_type = self.input(defval=5, title="variant_type", type=int)
        basis_len = self.input(defval=18,  title="basis_len", type=int)
        resolution = self.input(defval=15, title='resolution', type=int)

        source = self.exchange.security(str(resolution) + 'm')

        if self.eval_time is not None and \
                self.eval_time == source.iloc[-1].name:
            return

        series_open = source['open'].values
        series_close = source['close'].values

        variant = self.variants[variant_type]

        val_open = variant(series_open,  basis_len)
        val_close = variant(series_close, basis_len)

        long = crossover(val_close, val_open)
        short = crossunder(val_close, val_open)

        self.exchange.plot('val_open', val_open[-1], 'b')
        self.exchange.plot('val_close', val_close[-1], 'r')
        self.exchange.entry("Long", True,   lot, when=long)
        self.exchange.entry("Short", False, lot, when=short)

        self.eval_time = source.iloc[-1].name


class VixRci(Bot):
    def __init__(self):
        Bot.__init__(self, '5m')

    def options(self):
        return {
            'pd': hp.quniform('pd', 23, 30, 1),
            'bbl': hp.quniform('bbl', 20, 30, 1),
            'mult': hp.uniform('mult', 1, 2.5),
            'lb': hp.quniform('lb', 80, 100, 1),
            'ph': hp.uniform('ph', 0, 1),
            'pl': hp.uniform('pl', 1, 2),
            'rci_limit': hp.quniform('rci_limit', 70, 90, 1),
            'rci_diff': hp.quniform('rci_diff', 10, 40, 1),
            'itvs': hp.quniform('itvs', 1, 30, 1),
            'itvm': hp.quniform('itvm', 20, 50, 1),
            'itvl': hp.quniform('itvl', 40, 70, 1),
        }

    def strategy(self, open, close, high, low, volume):
        lot = self.exchange.get_lot()
        pos = self.exchange.get_position_size()

        pd = self.input('pd', int, 23)
        bbl = self.input('bbl', int, 23)
        mult = self.input('mult', float, 1.6774175598800714)
        lb = self.input('lb', int, 99)
        ph = self.input('ph', float, 0.8637612775288673)
        pl = self.input('pl', float, 1.3352574714599486)

        rci_limit = self.input('rci_limit', float, 88)
        rci_diff = self.input('rci_diff', float, 28)

        itvs = self.input('itvs', int, 18)
        itvm = self.input('itvm', int, 47)
        itvl = self.input('itvl', int, 62)

        green_hist, red_hist = vix(close, low, pd, bbl, mult, lb, ph, pl)

        # VIX Color Change
        up1 = [(not green_hist[-i]) and green_hist[-i - 1] and green_hist[-i - 2]
               and (not green_hist[-i - 3]) and (not green_hist[-i - 4]) for i in range(len(green_hist) - 5)][::-1]
        dn1 = [(not red_hist[-i]) and red_hist[-i - 1] and red_hist[-i - 2]
               and (not red_hist[-i - 3]) and (not red_hist[-i - 4]) for i in range(len(red_hist) - 5)][::-1]

        dvup = red_hist[-1] and red_hist[-2]
        dvdn = green_hist[-1] and green_hist[-2]

        # RCI
        rci_short_arr = rci(close, itvs)
        rci_middle_arr = rci(close, itvm)
        rci_long_arr = rci(close, itvl)

        rci_short = rci_short_arr[-1]
        rci_middle = rci_middle_arr[-1]
        rci_long = rci_long_arr[-1]

        up2 = rci_short < 0
        dn2 = rci_short > 0

        up31 = rci_long < 0 and rci_middle < 0 and crossover(rci_middle_arr, rci_long_arr)
        up32 = rci_long < -1 * rci_limit and rci_middle < -1 * rci_limit
        up33 = rci_long < 0 and 0 > rci_middle > rci_long
        up34 = rci_long < 0 and rci_middle < 0 > rci_middle and rci_long - rci_middle < rci_diff

        up3 = up31 or up32 or up33 or up34

        dn31 = rci_long > 0 and rci_middle > 0 and crossunder(rci_middle_arr, rci_long_arr)
        dn32 = rci_long > rci_limit and rci_middle > rci_limit
        dn33 = rci_long > 0 and 0 < rci_middle < rci_long
        dn34 = rci_long > 0 and rci_middle > 0 < rci_middle and rci_middle - rci_long < rci_diff

        dn3 = dn31 or dn32 or dn33 or dn34

        long1 = (up1[-1] or up1[-2] or up1[-3]) and (up2 or up3)
        long2 = dvup and up2 and up3
        short1 = (dn1[-1] or dn1[-2] or dn1[-3]) and (dn2 or dn3)
        short2 = dvdn and dn2 and dn3

        exit_long = (pos > 0 and (rci_middle > 70 or (short1 or short2)))
        exit_short = (pos < 0 and (rci_middle < -70 or (long1 or long2)))

        long_condition = (long1 or long2) and not exit_long and rci_short < -75 and not (
                close[-1] < close[-2] < close[-3])
        short_condition = (short1 or short2) and not exit_short and rci_short < 75 and not (
                close[-1] > close[-2] > close[-3])
        exit_condition = ((pos > 0) and (exit_long or short_condition) and rci_short > 70 and rci_middle > 60) or \
                         ((pos < 0) and (exit_short or long_condition) and rci_short < -70 and rci_middle < -60)

        if long_condition:
            self.exchange.entry("Long", True, lot)
        elif short_condition:
            self.exchange.entry("Short", False, lot)
        elif exit_condition:
            self.exchange.close_all()


# サンプル戦略
class Sample(Bot):
    def __init__(self):
        # 第一引数: 戦略で使う足幅
        # 1分足で直近10期間の情報を戦略で必要とする場合
        Bot.__init__(self, '1m')

    def options(self):
        return {}

    def strategy(self, open, close, high, low, volume):
        lot = self.exchange.get_lot()
        which = random.randrange(2)
        if which == 0:
            self.exchange.entry("Long", True, lot)
        else:
            self.exchange.entry("Short", False, lot)
