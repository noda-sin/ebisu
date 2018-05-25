# coding: UTF-8

import src.strategy as strategy


class BotFactory():

    @staticmethod
    def create(name, demo=False, stub=False, test=False, params=None):
        try:
            cls = getattr(strategy, name)
            return cls(demo=demo, stub=stub, test=test, params=params)
        except:
            raise Exception(f"Not Found Strategy : {name}")
