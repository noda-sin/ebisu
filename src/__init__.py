import logging
import os
import time
from datetime import timedelta

import numpy as np
import pandas as pd
import requests
import talib
from bravado.exception import HTTPNotFound, HTTPError

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

allowed_range = {
    "1m": ["1m", "1T", 1,    1],  "3m": ["1m",  "3T",  3,   3],
    "5m": ["5m", "5T", 1,    5], "15m": ["5m", "15T",  3,  15], "30m": ["5m", "30T", 6, 30],
    "1h": ["1h", "1H", 1,   60],  "2h": ["1h",  "2H",  2, 120],
    "3h": ["1h", "3H", 3,  180],  "4h": ["1h",  "4H",  4, 240],
    "6h": ["1h", "6H", 6,  360], "12h": ["1h", "12H", 12, 720],
    "1d": ["1d", "1D", 1, 1440],
    # not support yet '3d', '1w', '2w', '1m'
}

class FatalError(Exception):
    pass

def validate_range(r):
    if r not in allowed_range:
        raise Exception(f"Range: {r} is not suppert")

def retry(func, count=5):
    err = None
    for i in range(count):
        try:
            return func()
        except HTTPError as error:
            status_code = error.status_code
            err = error
            if status_code >= 500 or status_code == 408:
                time.sleep(pow(2, i+1))
                continue
            elif status_code == 400 or status_code == 409:
                raise error
            elif error.status_code == 429:
                time.sleep(10)
            elif 400 <= status_code < 500:
                raise FatalError(error)
    raise err

class Side:
    Long = "Long"
    Short = "Short"
    Close = "Close"
    Unknown = "Unknown"

def first(l=[]):
    return l[0]

def last(l=[]):
    return l[-1]

def gen_ohlcv(src):
    df = pd.DataFrame(src)
    return df['open'].values, df['close'].values, df['high'].values, df['low'].values

def highest(source, period):
    return pd.Series(source).rolling(period).max().values


def lowest(source, period):
    return pd.Series(source).rolling(period).min().values


def stdev(source, period):
    return pd.Series(source).rolling(period).std().values


def sma(source, period):
    return pd.Series(source).rolling(period).mean().values


def ema(source, period):
    return talib.EMA(np.array(source), period)


def bbands(source, timeperiod=5, nbdevup=2, nbdevdn=2, matype=0):
    return talib.BBANDS(source, timeperiod, nbdevup, nbdevdn, matype)


def macd(close, fastperiod=12, slowperiod=26, signalperiod=9):
    return talib.MACD(close, fastperiod, slowperiod, signalperiod)


def adx(high, low, close, period=14):
    return talib.ADX(high, low, close, period)


def di_plus(high, low, close, period=14):
    return talib.PLUS_DI(high, low, close, period)


def di_minus(high, low, close, period=14):
    return talib.MINUS_DI(high, low, close, period)


def rsi(close, period=14):
    return talib.RSI(close, period)

def delta(tr='1h'):
    if tr == '1d':
        return timedelta(days=1)
    elif tr == '5m':
        return timedelta(minutes=5)
    elif tr == '1m':
        return timedelta(minutes=1)
    elif tr == '2h':
        return timedelta(hours=2)
    else:
        return timedelta(hours=1)

def change_rate(a, b):
    if a > b:
        return a / b
    else:
        return b / a


def notify(message, fileName=None):
    logger.info(message)
    url = 'https://notify-api.line.me/api/notify'
    api_key = os.environ.get('LINE_APIKEY')
    if api_key is None or len(api_key) == 0:
        return

    payload = {'message': message}
    headers = {'Authorization': 'Bearer ' + api_key}
    if fileName is None:
        try:
            requests.post(url, data=payload, headers=headers)
        except:
            pass
    else:
        try:
            files = {"imageFile": open(fileName, "rb")}
            requests.post(url, data=payload, headers=headers, files=files)
        except:
            pass


def crossover(a, b):
    return a[-2] < b[-2] and a[-1] > b[-1]


def crossunder(a, b):
    return a[-2] > b[-2] and a[-1] < b[-1]


def ord(seq, sort_seq, idx, itv):
    p = seq[idx]
    for i in range(0, itv):
        if p >= sort_seq[i]:
            return i+1


def d(src, itv):
    sort_src = np.sort(src)[::-1]
    sum = 0.0
    for i in range(0, itv):
        sum += pow((i + 1) - ord(src, sort_src, i, itv), 2)
    return sum


def rci(src, itv):
    reversed_src = src[::-1]
    ret = [(1.0 - 6.0 * d(reversed_src[i:i + itv], itv) / (itv * (itv * itv - 1.0))) * 100.0
           for i in range(2)]
    return ret[::-1]


def is_under(src, value, p):
    for i in range(p, -1, -1):
        if src[-i - 1] > value:
            return False
    return True


def is_over(src, value, p):
    for i in range(p, -1, -1):
        if src[-i - 1] < value:
            return False
    return True


def is_top(src):
    return (src[-5] < src[-3] and src[-4] < src[-3] and src[-3] > src[-2] and src[-3] > src[-1])


def is_bottom(src):
    return (src[-5] > src[-3] and src[-4] > src[-3] and src[-3] < src[-2] and src[-3] < src[-1])


def maybe_top(src):
    return (src[-5] < src[-3] and src[-4] < src[-3]) or (src[-3] > src[-2] and src[-3] > src[-1])


def maybe_bottom(src):
    return (src[-5] > src[-3] and src[-4] > src[-3]) or (src[-3] < src[-2] and src[-3] < src[-1])


valuewhen_data = {}


def valuewhen(label, ok, value):
    global valuewhen_data

    if label in valuewhen_data:
        prev = valuewhen_data[label][-1]
        if ok:
            valuewhen_data[label].append(value)
        return prev
    else:
        if ok:
            valuewhen_data[label] = [value]
        return np.nan
