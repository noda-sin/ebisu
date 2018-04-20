# coding: UTF-8

import argparse
import os

from flask import Flask

from src.factory import BotFactory

app = Flask(__name__)

@app.route('/healty', methods=['GET'])
def healty():
    return 'ok'

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='This is trading script on bitmex')
    parser.add_argument('--test',     default=False,   action='store_true')
    parser.add_argument('--demo',     default=False,   action='store_true')
    parser.add_argument('--strategy', default='doten')
    args = parser.parse_args()

    factory = BotFactory()
    bot = factory.create(args.strategy, demo=args.demo, test=args.test)
    bot.run()

    if not args.test:
        try:
            port = int(os.environ.get('PORT')) or 5000
            app.run(host='0.0.0.0', port=port)
        except (KeyboardInterrupt, SystemExit):
            bot.exit()
