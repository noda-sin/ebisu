import logging
import os
import time
from datetime import timedelta

import numpy as np
import pandas as pd
import requests
import talib
from bravado.exception import HTTPError

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

allowed_range = {
    "1m": ["1m", "1T", 1, 1], "3m":  ["1m", "3T", 3, 3],
    "5m": ["5m", "5T", 1, 5], "15m": ["5m", "15T", 3, 15], "30m": ["5m", "30T", 6, 30],
    "1h": ["1h", "1H", 1, 1], "2h":  ["1h", "2H", 2, 2],
    "3h": ["1h", "3H", 3, 3], "4h":  ["1h", "4H", 4, 4],
    "6h": ["1h", "6H", 6, 6], "12h": ["1h", "12H", 12, 12],
    "1d": ["1d", "1D", 1, 1],
    # not support yet '3d', '1w', '2w', '1m'
}


class FatalError(Exception):
    pass


def load_data(file):
    """
    ファイルからデータを読み込む。
    """
    source = pd.read_csv(file)
    data_frame = pd.DataFrame({
        'timestamp': pd.to_datetime(source['timestamp']),
        'open': source['open'],
        'close': source['close'],
        'high': source['high'],
        'low': source['low'],
        'volume': source['volume']
    })
    data_frame = data_frame.set_index('timestamp')
    return data_frame.tz_localize(None).tz_localize('UTC', level=0)


def validate_continuous(data, bin_size):
    last_date = None
    for i in range(len(data)):
        index = data.iloc[-1 * (i + 1)].name
        if last_date is None:
            last_date = index
            continue
        if last_date - index != delta(bin_size):
            return False, index
        last_date = index
    return True, None


def to_data_frame(data):
    data_frame = pd.DataFrame(data, columns=["timestamp", "high", "low", "open", "close", "volume"])
    data_frame = data_frame.set_index("timestamp")
    data_frame = data_frame.tz_localize(None).tz_localize('UTC', level=0)
    return data_frame


def resample(data_frame, bin_size):
    resample_time = allowed_range[bin_size][1]
    return data_frame.resample(resample_time).agg({
        "open": "first",
        "high": "max",
        "low": "min",
        "close": "last",
        "volume": "sum",
    })


def retry(func, count=5):
    err = None
    for i in range(count):
        try:
            return func()
        except HTTPError as error:
            status_code = error.status_code
            err = error
            if status_code >= 500 or status_code == 408:
                time.sleep(pow(2, i + 1))
                continue
            elif status_code == 400 or \
                    status_code == 401 or \
                    status_code == 402 or \
                    status_code == 403 or \
                    status_code == 404 or \
                    status_code == 429:
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

def sar(high, low, acceleration=0, maximum=0):
    return talib.SAR(high, low, acceleration, maximum)

def delta(bin_size='1h'):
    if bin_size.endswith('d'):
        return timedelta(days=allowed_range[bin_size][3])
    elif bin_size.endswith('h'):
        return timedelta(hours=allowed_range[bin_size][3])
    elif bin_size.endswith('m'):
        return timedelta(minutes=allowed_range[bin_size][3])

def notify(message: object, fileName: object = None) -> object:
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
            return i + 1


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
