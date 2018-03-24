import numpy as np
import talib

OPEN = 1
HIGH = 2
LOW = 3
CLOSE = 4

def sma(source, period):
    return talib.SMA(source, timeperiod=period)

def linereg(source, period):
    return talib.LINEARREG(source, timeperiod=period)

def highest(source, period):
    ret = []
    for i in range(len(source)):
        slice = source[i-period:i]
        if len(slice) != period:
            ret.append(np.nan)
        else:
            ret.append(np.max(slice))
    return  np.array(ret)

def lowest(source, period):
    ret = []
    for i in range(len(source)):
        slice = source[i-period:i]
        if len(slice) != period:
            ret.append(np.nan)
        else:
            ret.append(np.min(slice))
    return  np.array(ret)

def valuewhen(condition, source, when):
    if len(condition) != len(source):
        return np.nan

    n = len(source)
    count = 0
    for i in range(n):
        if condition[n-i-1] > 0 and count == when:
            return source[n-i-1]
        count+=1
    return np.nan

class Trend:
    buy, sell, close, none = range(4)

class Strategy:

    _is_up     = []
    _is_down   = []
    _direction = []
    _zigzag    = []

    def __init__(self, source):
        self.src   = source
        self.src_len = len(source)
        self.open  = np.array([v[OPEN]  for _, v in enumerate(source)])
        self.high  = np.array([v[HIGH]  for _, v in enumerate(source)])
        self.low   = np.array([v[LOW]   for _, v in enumerate(source)])
        self.close = np.array([v[CLOSE] for _, v in enumerate(source)])

    def is_up(self):
        if len(self._is_up) > 0:
            return self._is_up

        ret = []
        for i in range(self.src_len):
            c = self.close[i]
            o = self.open[i]
            ret.append(c >= o)

        self._is_up = ret

        return ret

    def is_down(self):
        if len(self._is_down) > 0:
            return self._is_down

        ret = []
        for i in range(self.src_len):
            c = self.close[i]
            o = self.open[i]
            ret.append(c <= o)

        self._is_down = ret

        return ret

    def direction(self):
        if len(self._direction) > 0:
            return self._direction

        ret = []
        for i in range(self.src_len):
            if i == 0:
                ret.append(0)
                continue

            if self.is_up()[i - 1] and self.is_down()[i]:
                ret.append(-1)
            elif self.is_down()[i - 1] and self.is_up()[i]:
                ret.append(1)
            else:
                ret.append(ret[i - 1])

        self._direction = np.array(ret)
        return self._direction

    def zigzag(self):
        if len(self._zigzag) > 0:
            return self._zigzag

        ret = []
        for i in range(self.src_len):
            if self.is_up()[i - 1] and self.is_down()[i] and self.direction()[i-1] != -1:
                ret.append(highest(self.high, 2)[-1])
            elif self.is_down()[i - 1] and self.is_up()[i] and self.direction()[i-1] != 1:
                ret.append(lowest(self.low, 2)[-1])
            else:
                ret.append(np.nan)

        self._zigzag = np.array(ret)
        return self._zigzag

    def momentum(self):
        period = 7

        ma = sma(self.close, period)
        hest = highest(self.high, period)
        lest = lowest(self.low, period)

        avg = ((hest + lest) / 2.0 + ma) / 2.0
        val = linereg(self.close - avg, period)

        def trend1():
            if val[-1] > 0:
                return 1
            elif val[-1] < 0:
                return -1
            else:
                return 0

        def trend2():
            if self.close[-1] > self.open[-1]:
                return 1
            elif self.close[-1] < self.open[-1]:
                return -1
            else:
                return 0

        def trend3():
            a = np.abs(self.close - self.open)
            b = sma(a, 7) / 3.0
            if a[-1] > b[-1]:
                return 1
            elif a[-1] < b[-1]:
                return -1
            else:
                return 0

        if trend1() > 0 and trend2() < 0 and trend3() > 0:
            return Trend.buy
        elif trend1() < 0 and trend2() > 0 and trend3() > 0:
            return Trend.sell
        else:
            return Trend.none

    def elliott(self):
        sz = self.zigzag()

        close = self.close[-1]
        high = self.high[-1]
        low = self.low[-1]

        x = valuewhen(sz, sz, 4)
        a = valuewhen(sz, sz, 3)
        b = valuewhen(sz, sz, 2)
        c = valuewhen(sz, sz, 1)
        d = valuewhen(sz, sz, 0)

        xab = (abs(b-a)/abs(x-a))
        xad = (abs(a-d)/abs(x-a))
        abc = (abs(b-c)/abs(a-b))
        bcd = (abs(c-d)/abs(b-c))

        fib_range = abs(d-c)

        def is_bat(mode):
            _xab = xab >= 0.382 and xab <= 0.5
            _abc = abc >= 0.382 and abc <= 0.886
            _bcd = bcd >= 1.618 and bcd <= 2.618
            _xad = xad <= 0.618 and xad <= 1.000
            _dc  = (d < c) if mode else (b > c)
            return _xab and _abc and _bcd and _xad and _dc

        def is_anti_bat(mode):
            _xab = xab >= 0.500 and xab <= 0.886
            _abc = abc >= 1.000 and abc <= 2.618
            _bcd = bcd >= 1.618 and bcd <= 2.618
            _xad = xad >= 0.886 and xad <= 1.000
            _dc  = (d < c) if mode else (b > c)
            return _xab and _abc and _bcd and _xad and _dc

        def is_alt_bat(mode):
            _xab = xab <= 0.382
            _abc = abc >= 0.382 and abc <= 0.886
            _bcd = bcd >= 2.0 and bcd <= 3.618
            _xad = xad <= 1.13
            _dc = (d < c) if mode else (b > c)
            return _xab and _abc and _bcd and _xad and _dc

        def is_butterfly(mode):
            _xab = xab <= 0.786
            _abc = abc >= 0.382 and abc <= 0.886
            _bcd = bcd >= 1.618 and bcd <= 2.618
            _xad = xad >= 1.27 and xad <= 1.618
            _dc = (d < c) if mode else (b > c)
            return _xab and _abc and _bcd and _xad and _dc

        def is_anti_butterfly(mode):
            _xab = xab >= 0.236 and xab <= 0.886    # 0.382 - 0.618
            _abc = abc >= 1.130 and abc <= 2.618    # 1.130 - 2.618
            _bcd = bcd >= 1.000 and bcd <= 1.382    # 1.27
            _xad = xad >= 0.500 and xad <= 0.886    # 0.618 - 0.786
            _dc = (d < c) if mode else (b > c)
            return _xab and _abc and _bcd and _xad and _dc

        def is_abcd(mode):
            _abc = abc >= 0.382 and abc <= 0.886
            _bcd = bcd >= 1.13 and bcd <= 2.618
            _dc = (d < c) if mode else (b > c)
            return _abc and _bcd and _dc

        def is_gartley(mode):
            _xab = xab >= 0.5 and xab <= 0.618 # 0.618
            _abc = abc >= 0.382 and abc <= 0.886
            _bcd = bcd >= 1.13 and bcd <= 2.618
            _xad = xad >= 0.75 and xad <= 0.875 # 0.786
            _dc = (d < c) if mode else (b > c)
            return _xab and _abc and _bcd and _xad and _dc

        def is_anti_gartley(mode):
            _xab = xab >= 0.500 and xab <= 0.886    # 0.618 -> 0.786
            _abc = abc >= 1.000 and abc <= 2.618    # 1.130 -> 2.618
            _bcd = bcd >= 1.500 and bcd <= 5.000    # 1.618
            _xad = xad >= 1.000 and xad <= 5.000    # 1.272
            _dc = (d < c) if mode else (b > c)
            return _xab and _abc and _bcd and _xad and _dc

        def is_crab(mode):
            _xab = xab >= 0.500 and xab <= 0.875    # 0.886
            _abc = abc >= 0.382 and abc <= 0.886
            _bcd = bcd >= 2.000 and bcd <= 5.000    # 3.618
            _xad = xad >= 1.382 and xad <= 5.000    # 1.618
            _dc = (d < c) if mode else (b > c)
            return _xab and _abc and _bcd and _xad and _dc

        def is_anti_crab(mode):
            _xab = xab >= 0.250 and xab <= 0.500    # 0.276 -> 0.446
            _abc = abc >= 1.130 and abc <= 2.618    # 1.130 -> 2.618
            _bcd = bcd >= 1.618 and bcd <= 2.618    # 1.618 -> 2.618
            _xad = xad >= 0.500 and xad <= 0.750    # 0.618
            _dc = (d < c) if mode else (b > c)
            return _xab and _abc and _bcd and _xad and _dc

        def is_shark(mode):
            _xab = xab >= 0.500 and xab <= 0.875    # 0.5 --> 0.886
            _abc = abc >= 1.130 and abc <= 1.618    #
            _bcd = bcd >= 1.270 and bcd <= 2.240    #
            _xad = xad >= 0.886 and xad <= 1.130    # 0.886 --> 1.13
            _dc = (d < c) if mode else (b > c)
            return _xab and _abc and _bcd and _xad and _dc

        def is_anti_shark(mode):
            _xab = xab >= 0.382 and xab <= 0.875    # 0.446 --> 0.618
            _abc = abc >= 0.500 and abc <= 1.000    # 0.618 --> 0.886
            _bcd = bcd >= 1.250 and bcd <= 2.618    # 1.618 --> 2.618
            _xad = xad >= 0.500 and xad <= 1.250    # 1.130 --> 1.130
            _dc = (d < c) if mode else (b > c)
            return _xab and _abc and _bcd and _xad and _dc

        def is_5o(mode):
            _xab = xab >= 1.13 and xab <= 1.618
            _abc = abc >= 1.618 and abc <= 2.24
            _bcd = bcd >= 0.5 and bcd <= 0.625 # 0.5
            _xad = xad >= 0.0 and xad <= 0.236 # negative?
            _dc = (d < c) if mode else (b > c)
            return _xab and _abc and _bcd and _xad and _dc

        def is_wolf(mode):
            _xab = xab >= 1.27 and xab <= 1.618
            _abc = abc >= 0 and abc <= 5
            _bcd = bcd >= 1.27 and bcd <= 1.618
            _xad = xad >= 0.0 and xad <= 5
            _dc = (d < c) if mode else (b > c)
            return _xab and _abc and _bcd and _xad and _dc

        def is_hns(mode):
            _xab = xab >= 2.0 and xab <= 10
            _abc = abc >= 0.90 and abc <= 1.1
            _bcd = bcd >= 0.236 and bcd <= 0.88
            _xad = xad >= 0.90 and xad <= 1.1
            _dc = (d < c) if mode else (b > c)
            return _xab and _abc and _bcd and _xad and _dc

        def is_contria(mode):
            _xab = xab >= 0.382 and xab <= 0.618
            _abc = abc >= 0.382 and abc <= 0.618
            _bcd = bcd >= 0.382 and bcd <= 0.618
            _xad = xad >= 0.236 and xad <= 0.764
            _dc = (d < c) if mode else (b > c)
            return _xab and _abc and _bcd and _xad and _dc

        def is_extria(mode):
            _xab = xab >= 1.236 and xab <= 1.618
            _abc = abc >= 1.000 and abc <= 1.618
            _bcd = bcd >= 1.236 and bcd <= 2.000
            _xad = xad >= 2.000 and xad <= 2.236
            _dc = (d < c) if mode else (b > c)
            return _xab and _abc and _bcd and _xad and _dc

        def f_last_fib(rate):
            return d - (fib_range * rate) if d > c else d + fib_range * rate

        ew_rate = 0.236
        tp_rate = 0.618
        sl_rate = -0.236

        buy_patterns_00 = is_abcd(True) or \
                          is_bat(True) or \
                          is_anti_bat(True) or \
                          is_butterfly(True) or \
                          is_gartley(True) or \
                          is_crab(True) or \
                          is_shark(True) or \
                          is_5o(True) or \
                          is_wolf(True) or \
                          is_hns(True) or \
                          is_contria(True) or \
                          is_extria(True)

        buy_patterns_01 = is_anti_bat(True) or \
                          is_anti_butterfly(True) or \
                          is_anti_gartley(True) or \
                          is_anti_crab(True) or \
                          is_anti_shark(True)

        sel_patterns_00 = is_abcd(False) or \
                          is_bat(False) or \
                          is_anti_bat(False) or \
                          is_butterfly(False) or \
                          is_gartley(False) or \
                          is_crab(False) or \
                          is_shark(False) or \
                          is_5o(False) or \
                          is_wolf(False) or \
                          is_hns(False) or \
                          is_contria(False) or \
                          is_extria(False)

        sel_patterns_01 = is_anti_bat(False) or \
                          is_anti_butterfly(False) or \
                          is_anti_gartley(False) or \
                          is_anti_crab(False) or \
                          is_anti_shark(False)

        target01_buy_entry = (buy_patterns_00 or buy_patterns_01) and self.close[-1] <= f_last_fib(ew_rate)
        target01_buy_close = high >= f_last_fib(tp_rate) or low <= f_last_fib(sl_rate)
        target01_sel_entry = (sel_patterns_00 or sel_patterns_01) and close >= f_last_fib(ew_rate)
        target01_sel_close = low <= f_last_fib(tp_rate) or high >= f_last_fib(sl_rate)

        if target01_buy_entry:
            return Trend.buy
        elif target01_sel_entry:
            return Trend.sell
        elif target01_buy_close or target01_sel_close:
            return Trend.close
        else:
            return Trend.none