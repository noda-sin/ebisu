import argparse

from flask import Flask, render_template

from bot import Bot

app = Flask(__name__)
bot = Bot()

@app.route('/')
def index():
    title = "hello"
    return render_template('index.html', title=title)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--debug', default=False, action='store_true')
    args = parser.parse_args()

    try:
        bot.debug = app.debug = args.debug
        bot.run()
        app.run(host='0.0.0.0')
    except (KeyboardInterrupt, SystemExit):
        bot.exit()
