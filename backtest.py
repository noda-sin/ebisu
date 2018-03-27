from datetime import datetime

from exchange import BitMexStub
from strategy import Strategy, Trend

import pandas as pd

lot = 20
starttime = datetime(2018, 1, 1, 0, 0, 0, 000000)
mex = BitMexStub(starttime=starttime, timeframe='1h')

def on_update(time, source):
    strategy = Strategy(source)
    trend    = strategy.momentum()

    if trend == Trend.buy and not mex.current_position()[0] > 0:
        if mex.current_position()[0] < 0:
            mex.create_order('buy',  lot, time=time)
        mex.create_order('buy', lot, time=time)
    elif trend == Trend.sell and not mex.current_position()[0] < 0:
        if mex.current_position()[0] > 0:
            mex.create_order('sell', lot, time=time)
        mex.create_order('sell', lot, time=time)
    elif trend == Trend.close and mex.current_position()[0] == 0:
        mex.close_position()

mex.on_update(on_update)
while mex.is_processing:
    continue

print(mex.wallet_history())

pd.DataFrame(mex.wallet_history()).to_csv('backtest.csv')
