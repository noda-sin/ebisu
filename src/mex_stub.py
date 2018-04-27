# coding: UTF-8

from src.mex import BitMex
from src.util import lineNotify


class BitMexStub(BitMex):
    balance = 1000
    leverage = 2
    position_size = 0
    position_avg_price = 0

    order_count = 0

    win_count = 0
    lose_count = 0

    win_profit = 0
    lose_loss = 0

    max_draw_down = 0

    open_orders = []

    def __init__(self, tr, periods, run=True):
        BitMex.__init__(self, tr, periods, run=run)

    def get_balance(self):
        return self.balance

    def get_leverage(self):
        return self.leverage

    def get_position_size(self):
        return self.position_size

    def get_position_avg_price(self):
        return self.position_avg_price

    def close_all(self):
        pos_size = self.position_size
        if pos_size > 0:
            self.entry(True, abs(pos_size))
        elif pos_size < 0:
            self.entry(False, abs(pos_size))

    def cancel_all(self):
        self.open_orders = []

    def entry(self, long, qty, limit=0, stop=0, when=True):
        if not when:
            return

        self.cancel_all()
        pos_size = self.get_position_size()

        if long and pos_size > 0:
            return

        if not long and pos_size < 0:
            return

        if limit > 0 or stop > 0:
            self.open_orders.append({"long": long, "qty": qty, "limit": limit, "stop": stop})
        else:
            self.__commit(long, qty, self.get_market_price())
            return

    def __commit(self, long, qty, price):
        self.order_count += 1

        order_qty = qty if long else -qty
        next_qty = self.position_size + order_qty

        if (self.position_size > 0 >= order_qty) or (self.position_size < 0 < order_qty):
            if self.position_avg_price > price:
                close_rate = ((
                              self.position_avg_price - price) / price - self.get_commission()) * self.get_leverage()
                profit = -1 * self.position_size * close_rate
            else:
                close_rate = ((
                              price - self.position_avg_price) / self.position_avg_price - self.get_commission()) * self.get_leverage()
                profit = self.position_size * close_rate

            if profit > 0:
                self.win_profit += profit
                self.win_count += 1
            else:
                self.lose_loss += -1 * profit
                self.lose_count += 1
                if close_rate > self.max_draw_down:
                    self.max_draw_down = close_rate

            self.balance += profit

        if next_qty != 0:
            self.position_size = next_qty
            self.position_avg_price = price
        else:
            self.position_size = 0
            self.position_avg_price = 0

    def on_update(self, listener):
        def __override_listener(open, close, high, low):
            new_open_orders = []

            for _, order in enumerate(self.open_orders):
                long = order["long"]
                qty = order["qty"]
                limit = order["limit"]
                stop = order["stop"]

                if limit > 0 and stop > 0:
                    if (long and high > stop and close < limit) or (not long and low < stop and close > limit):
                        self.__commit(long, qty, limit)
                        continue
                    elif (long and high > stop) or (not long and low < stop):
                        new_open_orders.append({"long": long, "qty": qty, "limit": limit, "stop": 0})
                        continue
                elif limit > 0:
                    if (long and low < limit) or (not long and high > limit):
                        self.__commit(long, qty, limit)
                        continue
                elif stop > 0:
                    if (long and high > stop) or (not long and low < stop):
                        self.__commit(long, qty, stop)
                        continue

                new_open_orders.append(order)

            self.open_orders = new_open_orders
            listener(open, close, high, low)

        BitMex.on_update(self, __override_listener)
