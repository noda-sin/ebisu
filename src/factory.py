# coding: UTF-8

from src.strategy import ChannelBreakout, VixRCI, BBMacd


class BotFactory():
    def create(self, name, demo=False, test=False, params={}):
        if name == 'doten':
            return ChannelBreakout(demo=demo, test=test, params=params)
        if name == 'bbmacd':
            return BBMacd(demo=demo, test=test, params=params)
        if name == 'vix':
            return VixRCI(demo=demo, test=test, params=params)

        raise Exception('Not Found Strategy : ' + name)