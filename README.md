# ゑびす

<img src="img/ebisusama.png" width="200">

Trading bot for BitMex.  

The author is not responsible for any damage caused by this software.  

## Features

- Swithable strategy
- Back test
- Connect testnet
- Stub trading

## Implemented strategies

1. Channel Breakout
2. Cross SMA
3. RCI
4. Open Close Cross Strategy
5. Trading View Strategy

## Dependencies

- Python: 3.6.5

## How to install

### 1. Install packages

#### OSX

```bash
$ brew install ta-lib
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
$ python main.py --demo --strategy Doten
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

## How to use TV strategy

[Here](TV.md)

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

## Support

if you support to me, please send BTC to me.

wallet: 1GPjM5AkdBDJnCouQ9AcS4mhUhdysXYCW1
