# Ebisu

<img src="img/ebisusama.png" width="200">

BitMex用トレーディングボットプログラム。

作者は本ソフトウェアによって生じる一切の損害について責任を負いません。

## 特徴

- 戦略切替機能
- バックテスト機能
- テストネット取引機能
- 本番スタブ取引機能

## 実装済の戦略

1. チャネルブレイクアウト戦略
2. SMAのクロス戦略
3. Rci戦略
4. VixRci戦略

## 依存環境

- Python: 3.6.5

## インストール方法

### OSX

```bash
$ brew install talib
$ git clone git@gitlab.com:noda.sin/ebisu.git
$ cd ebisu/
$ python install -r requirements.txt
```

### LINUX

```bash
$ wget http://prdownloads.sourceforge.net/ta-lib/ta-lib-0.4.0-src.tar.gz
$ tar xvzf ta-lib-0.4.0-src.tar.gz
$ cd ta-lib/
$ ./configure --prefix=/usr
$ make
$ sudo make install
$ git clone git@gitlab.com:noda.sin/ebisu.git
$ cd ebisu/
$ python install -r requirements.txt
```

## 実行方法

```bash
$ python main.py -h
usage: main.py [-h] [--test] [--stub] [--demo] --strategy STRATEGY

This is trading script on bitmex

optional arguments:
  -h, --help           show this help message and exit
  --test
  --stub
  --demo
  --strategy STRATEGY
 ```

本番でのトレーディング

```bash
$ vi ~/.bashrc
BITMEX_APIKEY=***********
BITMEX_SECRET=***********
$ python main.py --strategy Doten
```

バックテスト

```bash
$ vi ~/.bashrc
BITMEX_TEST_APIKEY=***********
BITMEX_TEST_SECRET=***********
$ python main.py --test --strategy Doten
```

## 戦略の追加方法

以下のように、`src/strategy.py`に新しいクラスを作成してください。
これは、ランダムにエントリーする実装です。

```python
class Sample(Bot):
    def __init__(self):
        # 第一引数: 戦略で使う足幅
        # 第二引数: 戦略で使うデータ期間
        # 1分足で直近10期間の情報を戦略で必要とする場合
        Bot.__init__(self, '1m', 10)

    def strategy(self, open, close, high, low):
        lot = self.exchange.get_lot()
        which = random.randrange(2)
        if which == 0:
            self.exchange.entry("Long", True, lot)
        else:
            self.exchange.entry("Short", False, lot)
```
