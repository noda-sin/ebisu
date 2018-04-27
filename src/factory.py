# coding: UTF-8

from src.strategy import ChannelBreakout


class BotFactory():

    @staticmethod
    def create(name, demo=False, test=False, params=None):
        if name == "doten":
            return ChannelBreakout(demo=demo, test=test, params=params)
        raise Exception(f"Not Found Strategy : {name}")
