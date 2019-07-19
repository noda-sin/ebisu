# coding: UTF-8

import sys

from hyperopt import fmin, tpe, STATUS_OK, STATUS_FAIL, Trials

from src import logger, notify
from src.bitmex import BitMex
from src.bitmex_stub import BitMexStub
from src.bitmex_backtest import BitMexBackTest


class Bot:
    # Parameters
    params = {}
    # Exchange
    exchange = None
    # Time Frame
    bin_size = '1h'
    # periods
    periods = 20
    # run on test net?
    test_net = False
    # Back test?
    back_test = False
    # Stub Test?
    stub_test = False
    # parameter search?
    hyperopt = False

    def __init__(self, bin_size):
        """
        constructor
        :param bin_size: time_frame
        :param periods: period
        """
        self.bin_size = bin_size

    def options(self):
        """
        Function to obtain value for searching for a parameter.
        """
        pass

    def ohlcv_len(self):
        """
        The length of the OHLC to the strategy
        """
        return 100

    def input(self, title, type, defval):
        """
        function to get param
        :param title: title of the parm
        :param defval: default value
        :return value
        """
        p = {} if self.params is None else self.params
        if title in p:
            return type(p[title])
        else:
            return defval

    def strategy(self, open, close, high, low, volume):
        """
        Strategy function, when creating a bot please inherit this and implement this fn. 
        :param open: open price
        :param close: close price
        :param high: high price
        :param low: low price
        :param volume: volume
        """
        pass

    def params_search(self):
        """
 ˜      function to search params
        """
        def objective(args):
            logger.info(f"Params : {args}")
            try:
                self.params = args
                self.exchange = BitMexBackTest()
                self.exchange.on_update(self.bin_size, self.strategy)
                profit_factor = self.exchange.win_profit/self.exchange.lose_loss
                logger.info(f"Profit Factor : {profit_factor}")
                ret = {
                    'status': STATUS_OK,
                    'loss': 1/profit_factor
                }
            except Exception as e:
                ret = {
                    'status': STATUS_FAIL
                }

            return ret

        trials = Trials()
        best_params = fmin(objective, self.options(), algo=tpe.suggest, trials=trials, max_evals=200)
        logger.info(f"Best params is {best_params}")
        logger.info(f"Best profit factor is {1/trials.best_trial['result']['loss']}")

    def run(self):
        """
˜       Function to run the bot
        """
        if self.hyperopt:
            logger.info(f"Bot Mode : Hyperopt")
            self.params_search()
            return

        elif self.stub_test:
            logger.info(f"Bot Mode : Stub")
            self.exchange = BitMexStub()
        elif self.back_test:
            logger.info(f"Bot Mode : Back test")
            self.exchange = BitMexBackTest()
        else:
            logger.info(f"Bot Mode : Trade")
            self.exchange = BitMex(demo=self.test_net)

        self.exchange.ohlcv_len = self.ohlcv_len()
        self.exchange.on_update(self.bin_size, self.strategy)

        logger.info(f"Starting Bot")
        logger.info(f"Strategy : {type(self).__name__}")
        logger.info(f"Balance : {self.exchange.get_balance()}")

        notify(f"Starting Bot\n"
               f"Strategy : {type(self).__name__}\n"
               f"Balance : {self.exchange.get_balance()/100000000} XBT")

        self.exchange.show_result()

    def stop(self):
        """
˜       Function that stops the bot and cancel all trades.
        """
        if self.exchange is None:
            return

        logger.info(f"Stopping Bot")

        self.exchange.stop()
        self.exchange.cancel_all()
        sys.exit()
