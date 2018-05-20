# coding: UTF-8

from daikokuten.strategy import ChannelBreakout


class BotFactory():

    @staticmethod
    def create(name, demo=False, stub=False, test=False, params=None):
        if name == "doten":
            return ChannelBreakout(demo=demo, stub=stub, test=test, params=params)
        raise Exception(f"Not Found Strategy : {name}")
