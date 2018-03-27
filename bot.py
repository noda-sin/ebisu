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
            pass

    def closer_run(self):
        while True:
            pass

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