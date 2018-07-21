# ゑびす

<img src="img/ebisusama.png" width="200">

Trading bot for BitMex.  
BitMex用トレーディングボットプログラム。

The author is not responsible for any damage caused by this software.  
作者は本ソフトウェアによって生じる一切の損害について責任を負いません。

## Features

- Swithable strategy
- Back test
- Connect testnet
- Stub trading

## Implemented strategies

1. Channel Breakout
2. Cross SMA
3. RCI

## Dependencies

- Python: 3.6.5

## How to install

### 1. Install packages

#### OSX

```bash
$ brew install talib
$ git clone https://github.com/noda-sin/ebisu.git
$ cd ebisu/
$ pip install -r requirements.txt
```

#### LINUX

```bash
$ wget http://prdownloads.sourceforge.net/ta-lib/ta-lib-0.4.0-src.tar.gz
$ tar xvzf ta-lib-0.4.0-src.tar.gz
$ cd ta-lib/
$ ./configure --prefix=/usr
$ make
$ sudo make install
$ git clone https://github.com/noda-sin/ebisu.git
$ cd ebisu/
$ pip install -r requirements.txt
```

### 2. Setting environment

Set BitMex's API key with the environment variables `BITMEX_APIKEY` and` BITMEX_SECRET` as shown below.

```bash
$ vi ~/.bash_profile
export BITMEX_APIKEY=***********
export BITMEX_SECRET=***********
```

If you want to notify LINE, set LINE's API key to the environment variable `LINE_APIKEY`.

```bash
$ vi ~/.bash_profile
export LINE_APIKEY=***********
```

## How to execute

```bash
$ python main.py --strategy STRATEGY
 ```

By changing the value of `STRATEGY` you can switch strategies to use.

#### 例) Case of using Channel Breakout

 ```bash
 $ python main.py --strategy Doten
 ```

## Mode
### 1. Production Trade Mode

```bash
$ python main.py --strategy Doten
```

### 2. Demo Trade Mode

It is possible to trade with [testnet](https://testnet.bitmex.com/).

```bash
$ python main.py --test --strategy Doten
```

### 3. Back test Mode

```bash
$ python main.py --test --strategy Doten
```

### 4. Hyperopt Mode

```bash
$ python main.py --hyperopt --strategy Doten
```

### 5. Stub trade Mode

```bash
$ python main.py --stub --strategy Doten
```

## How to add strategy

You can add strategy by creating a new class in `src / strategy.py` as follows.
For example, this is a random entry implementation.

```python
class Sample(Bot):
    def __init__(self):
        Bot.__init__(self, '1m', 10)

    def options(self):
        return {}

    def strategy(self, open, close, high, low):
        lot = self.exchange.get_lot()
        which = random.randrange(2)
        if which == 0:
            self.exchange.entry("Long", True, lot)
        else:
            self.exchange.entry("Short", False, lot)
```

If you specify the strategy class name with the `--strategy` argument as shown below, you can run the bot with the added strategy.

```
$ python main.py --strategy Sample
```

------

## 特徴

- 戦略切替機能
- バックテスト機能
- テストネット取引機能
- 本番スタブ取引機能

## 実装済の戦略

1. チャネルブレイクアウト戦略
2. SMAのクロス戦略
3. Rci戦略

## 依存環境

- Python: 3.6.5

## インストール方法

### 1. パッケージのインストール

#### OSX の場合

```bash
$ brew install talib
$ git clone https://github.com/noda-sin/ebisu.git
$ cd ebisu/
$ pip install -r requirements.txt
```

#### LINUX の場合

```bash
$ wget http://prdownloads.sourceforge.net/ta-lib/ta-lib-0.4.0-src.tar.gz
$ tar xvzf ta-lib-0.4.0-src.tar.gz
$ cd ta-lib/
$ ./configure --prefix=/usr
$ make
$ sudo make install
$ git clone https://github.com/noda-sin/ebisu.git
$ cd ebisu/
$ pip install -r requirements.txt
```

### 2. 環境変数の設定

以下のように環境変数 `BITMEX_APIKEY`, `BITMEX_SECRET` で BitMex のAPIキーを設定します。

```bash
$ vi ~/.bash_profile
export BITMEX_APIKEY=***********
export BITMEX_SECRET=***********
```

LINEへの通知がしたい場合は、環境変数 `LINE_APIKEY` に LINE のAPIキーを設定します。

```bash
$ vi ~/.bash_profile
export LINE_APIKEY=***********
```

## 実行方法

```bash
$ python main.py --strategy STRATEGY
 ```

`STRATEGY` の箇所を変えることで、利用する戦略を切り替えることができます。

#### 例) チャネルブレイクアウト戦略 を利用する場合

 ```bash
 $ python main.py --strategy Doten
 ```

## モード
### 1. 本稼働モード

`--strategy` 引数のみを設定することで、本稼働での取引を行えます。

```bash
$ python main.py --strategy Doten
```

### 2. デモモード

`--demo` 引数を追加することで、[testnet](https://testnet.bitmex.com/) での取引を行えます。

```bash
$ python main.py --test --strategy Doten
```

### 3. バックテストモード

`--test` 引数を追加することで、戦略のバックテストを行えます。テスト結果後には、グラフが表示されます。

```bash
$ python main.py --test --strategy Doten
```

### 4. Hyperoptモード

`--hyperopt` 引数を追加することで、Hyperoptを使ったパラメータ最適化を行えます。

```bash
$ python main.py --hyperopt --strategy Doten
```

### 5. スタブモード

`--stub` 引数を追加することで、架空の口座を使ったリアルなテストが行えます。
このモードの動作は、あまりテストしていません。。。

```bash
$ python main.py --stub --strategy Doten
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

    def options(self):
        return {}

    def strategy(self, open, close, high, low):
        lot = self.exchange.get_lot()
        which = random.randrange(2)
        if which == 0:
            self.exchange.entry("Long", True, lot)
        else:
            self.exchange.entry("Short", False, lot)
```

以下のように `--strategy` 引数で戦略クラス名を指定すると、追加した戦略でBotを稼働させることができます。

```
$ python main.py --strategy Sample
```

## 投げ銭

ご支援いただける方は、以下のWalletにBTCを送付ください。

1GPjM5AkdBDJnCouQ9AcS4mhUhdysXYCW1

## その他

質問・バグ報告・機能追加・戦略の実装依頼などは、[issue](https://github.com/noda-sin/ebisu/issues)もしくは、Twitterアカウント[@noda_sin](https://twitter.com/noda_sin)にDMでお問い合わせください。
