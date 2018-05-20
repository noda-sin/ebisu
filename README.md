# 大黒天

BitMex用トレーディングボットプログラム。

<img src="img/daikokuten.png" width="200">

## インストール方法

```
$ git clone git@github.com:OopsMouse/daikokuten.git
$ cd daikokuten/
$ python install -r requirements.txt
$ python setup.py install
```

## 実行方法

本番でのトレーディング

```
$ vi ~/.bashrc
BITMEX_APIKEY=***********
BITMEX_SECRET=***********
$ daikokuten --strategy doten
```

テスト環境でのトレーディング

```
$ vi ~/.bashrc
BITMEX_TEST_APIKEY=***********
BITMEX_TEST_SECRET=***********
$ daikokuten --strategy doten --demo
```

バックテスト

```
$ vi ~/.bashrc
BITMEX_APIKEY=***********
BITMEX_SECRET=***********
$ daikokuten --strategy doten --stub
```
