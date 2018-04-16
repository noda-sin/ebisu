# coding: UTF-8

from src.mex import BitMex
from src.util import Side, lineNotify

class BitMexStub(BitMex):
    balance      = 200
    leverage     = 2
    current_qty  = 0
    entry_price  = 0

    order_count  = 0

    win_count    = 0
    lose_count   = 0

    win_profit   = 0
    lose_loss    = 0

    max_drowdown = 0

    def __init__(self, timerange='1h', notify=True):
        BitMex.__init__(self, timerange=timerange)
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
            self.entry(side=Side.Short, size=pos)
        elif pos < 0:
            self.entry(side=Side.Long, size=-1*pos)

    def entry(self, side, size):
        price = self.market_price()

        if side == Side.Long:
            order_qty = size
        else:
            order_qty = -size

        next_qty = self.current_qty + order_qty

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

        self.order_count+=1