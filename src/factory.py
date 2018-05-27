# coding: UTF-8

import src.strategy as strategy


class BotFactory():

    @staticmethod
    def create(name, demo=False, stub=False, test=False, params=None):
        try:
            cls = getattr(strategy, name)
            bot = cls()
            bot.test_net = demo
            bot.back_test = test
            bot.stub_test = stub
            bot.params = params
            return bot
        except Exception as _:
            raise Exception(f"Not Found Strategy : {name}")
