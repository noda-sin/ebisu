# coding: UTF-8

import os
from datetime import timedelta

import requests
import pandas as pd
import talib
import numpy as np

class Side:
    Long  = "long"
    Short = "short"

def highest(source, period):
    return pd.Series(source).rolling(period).max().as_matrix()

def lowest(source, period):
    return pd.Series(source).rolling(period).min().as_matrix()

def stdev(source, period):
    return pd.Series(source).rolling(period).std().as_matrix()

def sma(source, period):
    return pd.Series(source).rolling(period).mean().as_matrix()

def ema(source, period):
    return talib.EMA(np.array(source), period)

def delta(tr='1h'):
    if tr == '1d':
        return timedelta(days=1)
    elif tr == '5m':
        return timedelta(minutes=5)
    elif tr == '1m':
        return timedelta(minutes=1)
    else:
        return timedelta(hours=1)

def change_rate(a, b):
    if a > b:
        return a/b
    else:
        return b/a

def lineNotify(message, fileName=None):
    print(message)
    url     = 'https://notify-api.line.me/api/notify'
    apikey  = os.environ.get('LINE_APIKEY')
    payload = {'message': message}
    headers = {'Authorization': 'Bearer ' + apikey}
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

def ord(seq, idx, itv):
    p = seq[idx]
    o = 1
    for i in range(0, itv):
        if p < seq[i]:
            o = o + 1
    return o

def d(src, itv):
    sum = 0.0
    for i in range(0, itv):
        sum = sum + pow((i + 1) - ord(src, i, itv),2)
    return sum

def rci(src, itv):
    reversed_src = src[::-1]
    ret = [(1.0 - 6.0 * d(reversed_src[i:i+itv], itv) / (itv * (itv * itv - 1.0))) * 100.0
            for i in range(len(reversed_src) - itv)]
    return ret[::-1]