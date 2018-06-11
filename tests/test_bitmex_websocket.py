# coding: UTF-8

import unittest

from src.bitmex_websocket import BitMexWs


class TestBitMexWs(unittest.TestCase):

    wait = False

    def setUp(self):
        self.wait = True

    def complete(self):
        self.wait = False

    def wait_complete(self):
        while self.wait:
            pass

    def set_guard(self, guard):
        self.guard = guard

    def test_setup(self):
        ws = BitMexWs()
        ws.close()

    def test_subscribe_1m(self):
        ws = BitMexWs()

        def subscribe(x):
            print(x)
            self.complete()

        ws.on_update('1m', subscribe)

        self.wait_complete()
        ws.close()

    def test_subscribe_5m(self):
        ws = BitMexWs()

        def subscribe(x):
            print(x)
            self.complete()

        ws.on_update('5m', subscribe)

        self.wait_complete()
        ws.close()

    def test_subscribe_1h(self):
        ws = BitMexWs()

        def subscribe(x):
            print(x)
            self.complete()

        ws.on_update('1h', subscribe)

        self.wait_complete()
        ws.close()

    def test_subscribe_1d(self):
        ws = BitMexWs()

        def subscribe(x):
            print(x)
            self.complete()

        ws.on_update('1d', subscribe)

        self.wait_complete()
        ws.close()
