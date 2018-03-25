import argparse
import sys

from flask import Flask, render_template

from exchange import *

class Bot:
    debug = True

    def market_last_price(self):
        return self.bitmex.market_last_price()

    def current_position(self):
        return self.bitmex.current_position()

    def wallet_history(self):
        return self.bitmex.wallet_history()

    def opener_run(self):
        while True:
            try:
                pass
                # time.sleep(5)
                # self.bitmex.market_limit_order('buy', 20)
                # time.sleep(5)
                # self.bitmex.close_position()

                # if self.bitmex.has_open_orders():
                #     time.sleep(10)
                #     continue
                #
                # lot = 20
                # source = self.bitmex.fetch_ohlc()
                # strategy = Strategy(source)
                #
                # position = self.bitmex.current_position()
                # position_size = position.current_qty
                #
                # trend = strategy.momentum()
                #
                # if up and position_size <= 0:
                #     if self.has_position():
                #         self.bitmex.market_limit_order('buy', lot)
                #     self.bitmex.market_limit_order('buy', lot)
                # elif dn and position_size >= 0:
                #     if self.has_position():
                #         self.bitmex.market_limit_order('sell', lot)
                #     self.bitmex.market_limit_order('sell', lot)
            except Exception as e:
                print(e)
            time.sleep(10)

    def closer_run(self):
        pass
        # while True:
        #     try:
        #         if not self.has_position():
        #             time.sleep(10)
        #             continue
        #
        #         ohlc = self.fetch_ohlc()
        #         close = np.array([v[CLOSE] for _, v in enumerate(ohlc)])
        #
        #         position = self.current_position()
        #         position_size = position['currentQty']
        #         position_avg_price = position['avgEntryPrice']
        #
        #         if position_size > 0 and close[-1] > position_avg_price + 20:
        #             print('LOSS CUT !!')
        #             self.close_position()
        #         elif position_size < 0 and close[-1] < position_avg_price - 20:
        #             print('LOSS CUT !!')
        #             self.close_position()
        #     except Exception as e:
        #         print(e)
        #     time.sleep(10)

    def run(self):
        self.bitmex = BitMex(debug=self.debug)

        opener = threading.Thread(target=self.opener_run)
        opener.daemon = True
        opener.start()

        closer = threading.Thread(target=self.closer_run)
        closer.daemon = True
        closer.start()

    def exit(self):
        self.bitmex.cancel_orders()
        self.bitmex.close_position()
        sys.exit()