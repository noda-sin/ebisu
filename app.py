# coding: UTF-8

import argparse

from src.factory import BotFactory

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="This is trading script on bitmex")
    parser.add_argument("--test",     default=False,   action="store_true")
    parser.add_argument("--demo",     default=False,   action="store_true")
    parser.add_argument("--strategy", default="doten")
    args = parser.parse_args()

    bot = BotFactory.create(args.strategy, demo=args.demo, test=args.test)
    bot.run()

    if not args.test:
        try:
            while True:
                pass
        except (KeyboardInterrupt, SystemExit):
            bot.close()
