import os
import threading
from datetime import datetime as dt

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

        bitmex = ccxt.bitmex({
            'apiKey': apiKey,
            'secret': secret,
        })

        if debug:
            bitmex.urls['api'] = bitmex.urls['test']

        self.client = bitmex

    def _convert_datetime(self, dstr):
        return dt.strptime(dstr, '%Y-%m-%dT%H:%M:%S.%fZ').strftime('%m/%d')

    def wallet_history(self):
        history = self.client.privateGetUserWalletHistory()
        history.reverse()
        return [{'timestamp': self._convert_datetime(h['timestamp']),'walletBalance':h['walletBalance']/100000}
                for h in history if h['transactStatus'] == 'Completed']

    def current_leverage(self):
        return self.current_position().leverage

    def has_open_orders(self):
        return len(self._fetch_open_orders()) > 0

    def has_position(self):
        return self.current_position().current_qty != 0

    def current_position(self):
        p = self.client.private_get_position('BTC/USD')[0]
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
        side = 'buy' if position_size < 0 else 'sell'
        self.market_limit_order(side=side, size=position_size)

    def market_last_price(self):
        return self.client.fetch_ticker('BTC/USD')['last']

    def _create_order(self, type, side, size, price=0):
        order = self.client.create_order('BTC/USD', type=type, side=side, price=price, amount=size)
        print('Create Order: ' + order['info']['ordType'] + ' ' + order['info']['side'] + ': ' +
              str(order['info']['orderQty']) + ' @ ' + str(order['info']['price']) + ' / ' + order['id'])
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
        orders = self.client.fetch_open_orders()
        return orders

    def cancel_orders(self):
        orders = self._fetch_open_orders()
        for order in orders:
            self.client.cancel_order(order['id'])
            print('Cancel Order: ' + order['info']['ordType'] + ' ' + order['info']['side'] + ': ' +
                  str(order['info']['orderQty']) + ' @ ' + str(order['info']['price']) + ' / ' + order['id'])

    def fetch_ohlc(self):
        timest = self.client.fetch_ticker('BTC/USD')['timestamp'] - 50 * 3600000
        candles = self.client.fetch_ohlcv('BTC/USD', timeframe='1h', since=timest)
        return candles[:-1]

class BitMexStub(BitMex):
    balance = 100
    position = Position()
    orders = []

    def __init__(self):
        BitMex.__init__(self, debug=True)
        deamon = threading.Thread(target=self._crawler_run)
        deamon.start()

    def has_open_orders(self):
        return len(self.orders) > 0

    def has_position(self):
        return self.position.current_qty != 0

    def close_position(self):
        position = self.current_position()
        position_size = position.current_qty
        if position_size == 0:
            return
        last_price = self.market_last_price()
        self._make_position(-position_size, last_price)

    def _create_order(self, type, side, size, price=0):
        if side == 'market':
            price = self.market_last_price()
        order = { 'ordType': type, 'side': side, 'size': size, 'price': price }
        print('Create Order: ' + order['ordType'] + ' ' + order['side'] + ': ' +
              str(order['orderQty']) + ' @ ' + str(order['price']))
        self.orders.append(order)
        return order

    def cancel_orders(self):
        for order in self.orders:
            print('Cancel Order: ' + order['ordType'] + ' ' + order['side'] + ': ' +
                  str(order['orderQty']) + ' @ ' + str(order['price']))
        self.orders = []

    def _make_position(self, qty, price):
        old_qty = self.position.current_qty
        old_price = self.position.avg_entry_price

        new_qty = old_qty + qty
        new_price = old_price * old_qty + price * qty

        if (old_qty > 0 and new_qty <= 0) or \
                (old_qty < 0 and new_qty >= 0): # close
            profit = (price - old_price) / old_price * old_qty
            print('Profit: ', profit)
            self.balance += profit

        if new_qty == 0:
            self.position.current_qty = 0
            self.position.avg_entry_price = 0
        else:
            self.position.current_qty = new_qty
            self.position.avg_entry_price = new_price

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
                    elif side == 'sell' and price >= last_price:
                        self._make_position(-size, price)

            except Exception as e:
                print(e)
            time.sleep(1)