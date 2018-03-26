import json
import os
import threading
from datetime import datetime as dt, timedelta
from multiprocessing import Lock

import bitmex
import ccxt
import time

class Position:
    leverage        = 1
    current_qty     = 0
    avg_entry_price = None
    unrealised_pnl  = 0

class BitMex:
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

    def current_leverage(self):
        return self.current_position().leverage

    def has_open_orders(self):
        return len(self._fetch_open_orders()) > 0

    def has_position(self):
        return self.current_position().current_qty != 0

    def current_position(self):
        p = self.client.Position.Position_get(filter=json.dumps({'symbol': 'XBTUSD'})).result()[0][0]
        position = Position()
        position.leverage = p['leverage']
        position.current_qty = p['currentQty']
        position.avg_entry_price = p['avgEntryPrice']
        position.unrealised_pnl = p['unrealisedPnl']

        print('------------ POS ------------')
        print('Leverage:      ' + str(position.leverage))
        print('Current Qty:   ' + str(position.current_qty))
        print('AvgEntryPrice: ' + str(position.avg_entry_price))
        print('UnrealisedPnl: ' + str(position.unrealised_pnl))
        print('-----------------------------')

        return position

    def close_position(self):
        position = self.current_position()
        position_size = position.current_qty
        if position_size == 0:
            return
        self.client.Order.Order_closePosition(symbol='XBTUSD').result()

    def market_last_price(self):
        return self._fetch_ticker()['lastPrice']

    def _create_order(self, type, side, size, price=0):
        if type == 'limit':
            order = self.client.Order.Order_new(symbol='XBTUSD', ordType=type.capitalize(),
                                                      side=side.capitalize(), price=price, orderQty=size).result()[0]
        else:
            order = self.client.Order.Order_new(symbol='XBTUSD', ordType=type.capitalize(),
                                                side=side.capitalize(), orderQty=size).result()[0]
        print('Create Order: ' + order['ordType'] + ' ' + order['side'] + ': ' +
              str(order['orderQty']) + ' @ ' + str(order['price']) + ' / ' + order['orderID'])
        return order

    def limit_order(self, side, price, size):
        return self._create_order(type='limit', side=side, price=price, size=size)

    def market_limit_order(self, side, size):
        while True:
            last_price = self.market_last_price()
            self.limit_order(side=side, price=last_price, size=size)
            time.sleep(10)
            if self.has_open_orders():
                self.cancel_orders()
                if not self.has_position():
                    continue
                else:
                    break
            else:
                break

    def market_order(self, side, size):
        return self._create_order(type='market', side=side, size=size)

    def _fetch_open_orders(self):
        orders = self.client.Order.Order_getOrders(symbol='XBTUSD', filter=json.dumps({'open':True})).result()[0][0]
        return orders

    def _fetch_ticker(self):
        return self.client.Instrument.Instrument_get(symbol='XBTUSD').result()[0][0]

    def cancel_orders(self):
        orders = self.client.Order.Order_cancelAll().result()[0]
        for order in orders:
            print('Cancel Order: ' + order['ordType'] + ' ' + order['side'] + ': ' +
                  str(order['orderQty']) + ' @ ' + str(order['price']))

    def fetch_ohlc(self):
        endTime = self._fetch_ticker()['timestamp']
        startTime = endTime + timedelta(days=-30)
        candles = self.client.Trade.Trade_getBucketed(symbol='XBTUSD', binSize='1h',
                                                      startTime=startTime, endTime=endTime).result()[0]
        return candles[:-1]

class BitMexStub(BitMex):
    balance  = 100
    position = Position()
    orders   = []
    history  = []
    lock = Lock()

    def __init__(self):
        BitMex.__init__(self, debug=True)
        deamon = threading.Thread(target=self._crawler_run)
        deamon.start()
        self._append_hisotry()

    def _current_time(self):
        return dt.now().strftime("%m/%d %H:%M")

    def _append_hisotry(self):
        h = {'timestamp':self._current_time(),'walletBalance':self.balance}
        self.history.append(h)

    def wallet_history(self):
        return self.history

    def has_open_orders(self):
        return len(self.orders) > 0

    def has_position(self):
        return self.position.current_qty != 0

    def _print_position(self):
        position = self.current_position()
        print('------------ POS ------------')
        print('Leverage:      ' + str(position.leverage))
        print('Current Qty:   ' + str(position.current_qty))
        print('AvgEntryPrice: ' + str(position.avg_entry_price))
        print('UnrealisedPnl: ' + str(position.unrealised_pnl))
        print('-----------------------------')

    def current_position(self):
        return self.position

    def close_position(self):
        position = self.current_position()
        position_size = position.current_qty
        if position_size == 0:
            return
        last_price = self.market_last_price()

        self._make_position(-position_size, last_price)
        print('Closed position')
        self._print_position()

    def _create_order(self, type, side, size, price=0):
        if side == 'market':
            price = self.market_last_price()
        order = { 'ordType': type, 'side': side, 'size': size, 'price': price }
        print('Create Order: ' + order['ordType'] + ' ' + order['side'] + ': ' +
              str(order['size']) + ' @ ' + str(order['price'] + ' / ' + order['orderID']))
        self.lock.acquire()
        self.orders.append(order)
        self.lock.release()
        return order

    def limit_order(self, side, price, size):
        return self._create_order(type='limit', side=side, price=price, size=size)

    def market_limit_order(self, side, size):
        while True:
            last_price = self.market_last_price()
            self.limit_order(side=side, price=last_price, size=size)
            time.sleep(10)
            if self.has_open_orders():
                self.cancel_orders()
                if not self.has_position():
                    continue
                else:
                    break
            else:
                break

    def market_order(self, side, size):
        return self._create_order(type='market', side=side, size=size)

    def cancel_orders(self):
        for order in self.orders:
            print('Cancel Order: ' + order['ordType'] + ' ' + order['side'] + ': ' +
                  str(order['size']) + ' @ ' + str(order['price']))
        self.lock.acquire()
        self.orders = []
        self.lock.release()

    def _make_position(self, qty, price):
        self.lock.acquire()

        old_qty = self.position.current_qty
        old_price = 0 if self.position.avg_entry_price is None else self.position.avg_entry_price

        new_qty = old_qty + qty

        if (old_qty > 0 and new_qty <= 0) or \
                (old_qty < 0 and new_qty >= 0): # close
            profit = (price - old_price) / old_price * old_qty
            print('Profit: ', profit)
            self.balance += profit
            print('Balance: ', self.balance)
            self._append_hisotry()

        if new_qty == 0:
            self.position.current_qty = 0
            self.position.avg_entry_price = None
            self.position.unrealised_pnl = 0
        else:
            new_price = (old_price * old_qty + price * qty) / (old_qty + qty)
            self.position.current_qty = new_qty
            self.position.avg_entry_price = new_price
            self.position.unrealised_pnl = 0

        self.lock.release()
        self._print_position()

    def _crawler_run(self):
        while True:
            try:
                last_price = self.market_last_price()
                for _, order in enumerate(self.orders):
                    side = order['side']
                    size = order['size']
                    price = order['price']

                    if side == 'buy' and price <= last_price:
                        self._make_position(size, price)
                        self.orders.remove(order)
                        break
                    elif side == 'sell' and price >= last_price:
                        self._make_position(-size, price)
                        self.orders.remove(order)
                        break

                if self.position.current_qty != 0:
                    entry_price = self.position.avg_entry_price
                    profit = (last_price - entry_price) / entry_price * self.position.current_qty
                    self.position.unrealised_pnl = profit
                    self._print_position()

            except Exception as e:
                print(e)
            time.sleep(4)

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