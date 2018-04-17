# coding: UTF-8

import os
from datetime import timedelta

import requests
import pandas as pd

class Side:
    Long  = "long"
    Short = "short"

def highest(source, period):
    return pd.rolling_max(source, period, 1)

def lowest(source, period):
    return pd.rolling_min(source, period, 1)

def stdev(source, period):
    return pd.rolling_std(source, period, 1)

def sma(source, period):
    return pd.rolling_mean(source, period, 1)

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