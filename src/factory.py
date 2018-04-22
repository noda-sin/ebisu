# coding: UTF-8

from src.strategy import ChannelBreakout

class BotFactory():
    def create(self, name, demo=False, test=False, params={}):
        if name == 'doten':
            return ChannelBreakout(demo=demo, test=test, params=params)

        raise Exception('Not Found Strategy : ' + name)