# coding: UTF-8

import argparse
import sys
import time
import os

import numpy as np
from flask import Flask

from mex_stub import BitMexStub
from mex_test import BitMexTest

from mex import BitMex
from util import highest, lowest, Side

app = Flask(__name__)

@app.route('/healty', methods=['GET'])
def healty():
    return 'ok'

class Bot:
    def __init__(self, demo=False, test=False, params={}):
        self.is_test = test
        self.params  = params

        if demo:
            self.bitmex = BitMexStub()
        elif test:
            self.bitmex = BitMexTest()
        else:
            self.bitmex = BitMex()

    def input(self, title, defval):
        if title in self.params:
            return self.params[title]
        else:
            return defval

    def strategy(self, source):
        open  = [v['open']  for _, v in enumerate(source[:-1])]
        high  = [v['high']  for _, v in enumerate(source[:-1])]
        low   = [v['low']   for _, v in enumerate(source[:-1])]
        close = [v['close'] for _, v in enumerate(source[:-1])]

        length = self.input('length', 18)
        lot = self.bitmex.wallet_balance() / 20

        is_up = (high[-1] == highest(high, length).iloc[-1])
        is_dn = (low[-1]  == lowest(low, length).iloc[-1])

        pos = self.bitmex.position_qty()

        # エントリー
        if is_up and pos <= 0:
            if pos < 0:
                lot = 2 * lot
            self.bitmex.entry(side=Side.Long, size=lot)
        elif is_dn and pos >= 0:
            if pos > 0:
                lot = 2 * lot
            self.bitmex.entry(side=Side.Short, size=lot)

    def run(self):
        try:
            self.bitmex.on_update(listener=self.strategy)
            self.bitmex.print_result()
            if not self.is_test:
                port = int(os.environ.get('PORT')) or 5000
                app.run(host='0.0.0.0', port=port)
        except (KeyboardInterrupt, SystemExit):
            self.exit()

    def exit(self):
        self.bitmex.cancel_orders()
        self.bitmex.close_position()
        sys.exit()

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='This is trading script on bitmex')
    parser.add_argument('--test', default=False, action='store_true')
    parser.add_argument('--demo', default=False, action='store_true')
    args = parser.parse_args()

    bot = Bot(demo=args.demo, test=args.test)
    bot.run()
