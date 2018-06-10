# coding: UTF-8

import src.strategy as strategy


class BotFactory():

    @staticmethod
    def create(args):
        """
        Botを作成する関数。名前から該当のBotを src/strategy.py から探す。
        :param args: 変数
        :return: Bot
        """
        try:
            cls = getattr(strategy, args.strategy)
            bot = cls()
            bot.test_net  = args.demo
            bot.back_test = args.test
            bot.stub_test = args.stub
            bot.hyperopt  = args.hyperopt
            return bot
        except Exception as _:
            raise Exception(f"Not Found Strategy : {args.strategy}")
