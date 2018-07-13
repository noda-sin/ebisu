# Ebisu

<img src="img/ebisusama.png" width="200">

BitMex用トレーディングボットプログラム。

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
$ git clone git@gitlab.com:noda.sin/ebisu.git
$ cd ebisu/
$ python install -r requirements.txt
```

#### LINUX の場合

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

### 2. 環境変数の設定

以下のように環境変数 `BITMEX_APIKEY`, `BITMEX_SECRET` で BitMex のAPIキーを設定します。

```bash
$ vi ~/.bash_profile
BITMEX_APIKEY=***********
BITMEX_SECRET=***********
```

LINEへの通知がしたい場合は、環境変数 `LINE_APIKEY` に LINE のAPIキーを設定します。

```bash
$ vi ~/.bash_profile
LINE_APIKEY=***********
```

## 実行方法

```bash
$ python main.py --strategy STRATEGY
 ```

`STRATEGY` の箇所を変えることで、利用する戦略を切り替えることができます。

#### 例) チャネルブレイクアウト戦略 を利用する場合

 ```bash
 $ python main --strategy Doten
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