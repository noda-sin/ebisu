# coding: UTF-8

from src.strategy import Dotenkun, BB

class BotFactory():
    def create(self, name, demo=False, test=False, params={}):
        if name == 'doten':
            return Dotenkun(demo=demo, test=test, params=params)
        if name == 'bb':
            return BB(demo=demo, test=test, params=params)
        raise Exception('Not found strategy about ' + name)