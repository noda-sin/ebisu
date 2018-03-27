import json
import os
import threading
import time
from datetime import datetime as dt, timedelta, datetime
from multiprocessing import Lock

import bitmex
import bitmex_websocket

class BitMex:

    listeners = []

    def __init__(self, debug=True):
        apiKey = os.environ.get('BITMEX_APIKEY')
        secret = os.environ.get('BITMEX_SECRET')
        if debug:
            apiKey = os.environ.get('BITMEX_TEST_APIKEY')
            secret = os.environ.get('BITMEX_TEST_SECRET')

        self.client = bitmex.bitmex(test=debug, api_key=apiKey, api_secret=secret)

    def _convert_datetime(self, dstr):
        return dt.strptime(dstr, '%Y-%m-%dT%H:%M:%S.%fZ').strftime('%m/%d')

    def wallet_history(self):
        history = self.client.User.User_getWalletHistory(currency='XBt').result()[0]
        history.reverse()
        return [{'timestamp': h['timestamp'].strftime('%m/%d'),'walletBalance':h['walletBalance']/100000}
                for h in history if h['transactStatus'] == 'Completed']

    def has_open_orders(self):
        return len(self._fetch_open_orders()) > 0

    def has_position(self):
        return self.current_position()[0] != 0

    def current_position(self):
        p = self.client.Position.Position_get(filter=json.dumps({'symbol': 'XBTUSD'})).result()[0][0]
        return (p['currentQty'], p['avgEntryPrice'], p['unrealisedPnl'])

    def close_position(self, time=datetime.now()):
        current_qty = self.current_position()[0]
        if current_qty != 0:
            self.client.Order.Order_closePosition(symbol='XBTUSD').result()
            print(str(time) + ' Close Position')

    def market_last_price(self):
        return self._fetch_ticker()['lastPrice']

    def create_order(self, side, size, price=0, time=datetime.now()):
        p = price if price > 0 else self.market_last_price()

        while True:
            order = self.client.Order.Order_new(symbol='XBTUSD', ordType='Limit',
                                                side=side.capitalize(), price=p, orderQty=size).result()[0]
            time.sleep(10)

            if self.has_open_orders():
                self.cancel_orders()
                if not self.has_position():
                    continue
            break

        print(str(time) + ' Create Order: ' + order['ordType'] + ' ' + order['side'] + ': ' +
              str(order['orderQty']) + ' @ ' + str(order['price']) + ' / ' + order['orderID'])

    def _fetch_open_orders(self):
        orders = self.client.Order.Order_getOrders(symbol='XBTUSD', filter=json.dumps({'open':True})).result()[0][0]
        return orders

    def _fetch_ticker(self):
        return self.client.Instrument.Instrument_get(symbol='XBTUSD').result()[0][0]

    def cancel_orders(self, time=datetime.now()):
        orders = self.client.Order.Order_cancelAll().result()[0]
        for order in orders:
            print(str(time) + ' Cancel Order: ' + order['ordType'] + ' ' + order['side'] + ': ' +
                  str(order['orderQty']) + ' @ ' + str(order['price']))

    def fetch_ohlc(self, starttime=(datetime.now()+timedelta(days=-30)), endTime=datetime.now()):
        candles = self.client.Trade.Trade_getBucketed(symbol='XBTUSD', binSize='1h',
                                                      startTime=starttime, endTime=endTime).result()[0]
        return candles[:-1]

    def on_update(self, func):
        self.listeners.append(func)

class BitMexStub(BitMex):
    balance   = 100

    history   = []

    current_qty    = 0
    entry_price    = 0
    unrealised_pnl = 0

    lock = Lock()

    def __init__(self, starttime, timeframe='1h'):
        BitMex.__init__(self)

        # バックテストをテストを実行する期間とBINサイズ
        self.is_processing = True
        self.starttime     = starttime
        self.endtime       = datetime.now()
        self.tf            = timeframe

        self._clear_position()

    def _append_hisotry(self, time, source):
        # 履歴に保存する
        h = {
            'timestamp': time.strftime("%Y/%m/%d %H:%M"),
            'open' : source['open'],
            'high' : source['high'],
            'low'  : source['low'],
            'close': source['close'],
            'walletBalance': self.balance
        }
        self.history.append(h)

    def wallet_history(self):
        return self.history

    def has_open_orders(self):
        return False

    def has_position(self):
        return self.current_qty != 0

    def current_position(self):
        return (self.current_qty, self.entry_price, self.unrealised_pnl)

    def close_position(self):
        if self.current_qty != 0:
            price = self.market_last_price()
            self._make_position(-self.current_qty, price)
            self._clear_position()

    def market_last_price(self):
        return self.market_price

    def create_order(self, side, size, price=0, time=datetime.now()):
        type = 'limit' if price > 0 else 'market'
        s = size if side == 'buy' else -size
        p = price if price > 0 else self.market_last_price()
        order = {'ordType': type, 'side': side, 'size': s, 'price': p}
        print(str(time) + ' Create Order: ' + order['ordType'] + ' ' + order['side'] + ': ' +
              str(order['size']) + ' @ ' + str(order['price']))
        self._make_position(s, p, time)

    def cancel_orders(self):
        pass

    def _clear_position(self):
        self.current_qty = 0
        self.entry_price = None
        self.unrealised_pnl = 0

    def _make_position(self, qty, price, time):
        self.lock.acquire()

        current_qty   = self.current_qty
        current_price = 0 if self.entry_price is None else self.entry_price

        next_qty = current_qty + qty

        if (current_qty > 0 and qty <= 0) or \
                (current_qty < 0 and qty > 0):
            profit = (current_price - price) / current_price * current_qty
            self.balance += profit

        if next_qty == 0:
            print(str(time) + ' Closed Position @ ' + str(self.balance))
            self._clear_position()
        else:
            print(str(time) + ' Entry: ' + str(next_qty) + ' / ' + str(price) + ' @ ' + str(self.balance))
            self.current_qty    = next_qty
            self.entry_price    = price
            self.unrealised_pnl = 0

        self.lock.release()

    def _crawler_run(self):
        now = datetime.now()

        if self.tf == '1h':
            delta = timedelta(hours=1)
        elif self.tf == '1m':
            delta = timedelta(minutes=1)
        elif self.tf == '5m':
            delta = timedelta(minutes=5)
        else:
            delta = timedelta(days=1)

        lefttime  = self.starttime - 20 * delta
        righttime = self.starttime

        while righttime <= now:
            try:
                lefttime  += delta
                righttime += delta
                source = BitMex.fetch_ohlc(self, starttime=lefttime, endTime=righttime)
                self.market_price = source[-1]['close']

                for listener in self.listeners:
                    listener(source[-1]['timestamp'], source)

                self._append_hisotry(time, source[-1])

            except Exception as e:
                print(e)
                time.sleep(10)
            time.sleep(0.1)

        self.is_processing = False

    def on_update(self, func):
        self.is_processing = True
        BitMex.on_update(self, func)
        crawler = threading.Thread(target=self._crawler_run)
        crawler.start()

if __name__ == '__main__':
    mex = BitMex(debug=True)

    print(mex.wallet_history())
    print(mex.market_last_price())
    print(mex.current_position().current_qty)

    mex.limit_order('buy', 8000, 10)
    mex.cancel_orders()

    mex.market_order('buy', 10)
    mex.close_position()

    print(mex.fetch_ohlc())