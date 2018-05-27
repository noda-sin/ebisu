# coding: UTF-8

import src.strategy as strategy


class BotFactory():

    @staticmethod
    def create(name, demo=False, stub=False, test=False, params=None):
        """
        Botを作成する関数。名前から該当のBotを src/strategy.py から探す。
        :param name: Bot名
        :param demo: テストネット環境を利用するか
        :param stub: スタブ取引か
        :param test: バックテストか
        :param params: 戦略のパラメータ
        :return: Bot
        """
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
