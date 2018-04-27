# coding: UTF-8

from src.mex import BitMex
from src.util import lineNotify

class BitMexStub(BitMex):
    balance      = 1000
    leverage     = 2
    current_qty  = 0
    entry_price  = 0

    order_count  = 0

    win_count    = 0
    lose_count   = 0

    win_profit   = 0
    lose_loss    = 0

    max_drowdown = 0

    orders = []

    def __init__(self, tr='1h', periods=30, notify=True):
        BitMex.__init__(self, tr=tr, periods=periods)
        self.notify = notify

    def wallet_balance(self):
        return self.balance

    def current_leverage(self):
        return self.leverage

    def position_qty(self):
        return self.current_qty

    def position_price(self):
        return self.entry_price

    def close_position(self):
        pos = self.current_qty
        if pos > 0:
            self.entry(True, abs(pos))
        elif pos < 0:
            self.entry(False, abs(pos))

    def close_order(self):
        self.orders = []

    def entry(self, long, qty, limit=0, stop=0, when=True):
        if not when:
            return

        self.close_order()
        pos = self.position_qty()

        if long and pos > 0:
            return

        if not long and pos < 0:
            return

        if limit > 0 or stop > 0:
            self.orders.append({"long": long, "qty": qty, "limit": limit, "stop": stop})
        else:
            self.__commit(long, qty, self.market_price())
            return

    def __commit(self, long, qty, price):
        order_qty = qty if long else -qty
        next_qty  = self.current_qty + order_qty

        if (self.current_qty > 0 and order_qty <= 0) or \
                (self.current_qty < 0 and order_qty > 0):

            if self.entry_price > price:
                close_rate = ((self.entry_price - price) / price - self.trade_fee()) * self.current_leverage()
                profit = -1 * self.current_qty * close_rate
            else:
                close_rate = ((price - self.entry_price) / self.entry_price - self.trade_fee()) * self.current_leverage()
                profit = self.current_qty * close_rate

            if profit > 0:
                self.win_profit += profit
                self.win_count  += 1
            else:
                self.lose_loss  += -1 * profit
                self.lose_count += 1
                if close_rate > self.max_drowdown:
                    self.max_drowdown = close_rate

            self.balance += profit

            if self.notify:
                lineNotify('{} # Close Position @ {}'.format(self.now_time(), profit))
                lineNotify('{} # Balance @ {}'.format(self.now_time(), self.balance))
            else:
                print('{} # Close Position @ {}'.format(self.now_time(), profit))
                print('{} # Balance @ {}'.format(self.now_time(), self.balance))

        if next_qty != 0:
            if self.notify:
                lineNotify('{} # Create Order : {} / {} @ {}'.format(self.now_time(), side, size, price))
            else:
                print('{} # Create Order : {} / {} @ {}'.format(self.now_time(), side, size, price))
            self.current_qty = next_qty
            self.entry_price = price
        else:
            self.current_qty = 0
            self.entry_price = 0

        self.order_count+=1

    def on_update(self, listener):
        def __overwride_listener(open, close, high, low):
            new_orders = []

            for _, order in enumerate(self.orders):
                long  = order["long"]
                qty   = order["qty"]
                limit = order["limit"]
                stop  = order["stop"]

                if limit > 0 and stop > 0:
                    if (long and high > stop and close < limit) or (not long and low < stop and close > limit):
                        self.__commit(long, qty, limit)
                        continue
                    elif (long and high > stop) or (not long and low < stop):
                        new_orders.append({"long":long, "qty": qty, "limit": limit, "stop": 0})
                        continue
                elif limit > 0:
                    if (long and low < limit) or (not long and high > limit):
                        self.__commit(long, qty, limit)
                        continue
                elif stop > 0:
                    if (long and high > stop) or (not long and low < stop):
                        self.__commit(long, qty, stop)
                        continue
                new_orders.append(order)
            self.orders = new_orders
            listener(open, close, high, low)

        BitMex.on_update(self, __overwride_listener)