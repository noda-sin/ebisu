# coding: UTF-8

import src.util as util
from src.bot import Bot


class ChannelBreakout(Bot):

    def __init__(self, demo=False, test=False, params=None):
        Bot.__init__(self, demo=demo, test=test, tr='1h', periods=20, params=params)

    def strategy(self, open, close, high, low):
        length = self.input('length', 18)
        lot    = self.bitmex.wallet_balance() / 20
        upBound   = util.highest(high[:-1], length)[-1]
        downBound = util.lowest(low[:-1], length)[-1]
        self.bitmex.entry(True,  lot, stop=upBound)
        self.bitmex.entry(False, lot, stop=downBound)

# class BBMacd(Bot):
#
#     def __init__(self, demo=False, test=False, params={}):
#         Bot.__init__(self, demo=demo, test=test, tr='5m', periods=50, params=params)
#
#     def strategy(self, source):
#         close = np.array([v['close'] for _, v in enumerate(source[:-1])])
#         lot   = self.bitmex.wallet_balance() / 20
#
#         # MACD
#         macd, _, _ = util.macd(close, fastperiod=11, slowperiod=27)
#         # BollingerBands
#         upper, _, lower = util.bbands(macd, timeperiod=10)
#
#         is_up = util.crossover(macd, upper)
#         is_dn = util.crossunder(macd, lower)
#
#         pos = self.bitmex.position_qty()
#
#         # エントリー
#         if is_up and pos <= 0:
#             if pos < 0:
#                 lot = 2 * lot
#             self.bitmex.entry(side=Side.Long, size=lot)
#         elif is_dn and pos >= 0:
#             if pos > 0:
#                 lot = 2 * lot
#             self.bitmex.entry(side=Side.Short, size=lot)

# class VixRCI(Bot):
#
#     def __init__(self, demo=False, test=False, params={}):
#         Bot.__init__(self, demo=demo, test=test, tr='2', periods=115, params=params)
#
#     def macd_div(self, close):
#         # MACD
#         macd, _, _ = util.macd(close)
#         is_t = util.is_top(macd)    and util.maybe_top(close)
#         is_b = util.is_bottom(macd) and util.maybe_bottom(close)
#
#         top_macd  = macd[-3]  if is_t else np.nan
#         top_price = close[-3] if is_t else np.nan
#         bot_macd  = macd[-3]  if is_b else np.nan
#         bot_price = close[-3] if is_b else np.nan
#
#         prev_top_macd  = util.valuewhen('top_macd',  is_t, macd[-3])
#         prev_top_price = util.valuewhen('top_price', is_t, close[-3])
#         prev_bot_macd  = util.valuewhen('bot_macd',  is_b, macd[-3])
#         prev_bot_price = util.valuewhen('bot_price', is_b, close[-3])
#
#         pattern_a = is_b and bot_macd > prev_bot_macd and bot_price < prev_bot_price
#         pattern_b = is_b and bot_macd > prev_top_macd and bot_price < prev_top_price
#         pattern_e = is_b and bot_macd < prev_bot_macd and bot_price > prev_bot_price
#         pattern_f = is_b and bot_macd < prev_top_macd and bot_price > prev_top_price
#
#         is_up = (pattern_a or pattern_b or pattern_e or pattern_f)
#
#         pattern_c = is_t and top_macd < prev_top_macd and top_price > prev_top_price
#         pattern_d = is_t and top_macd < prev_bot_macd and top_price > prev_bot_price
#         pattern_g = is_t and top_macd > prev_top_macd and top_price < prev_top_price
#         pattern_h = is_t and top_macd > prev_bot_macd and top_price < prev_bot_price
#
#         is_dn = (pattern_c or pattern_d or pattern_g or pattern_h)
#
#         if is_up:
#             return Side.Long
#         elif is_dn:
#             return Side.Short
#         else:
#             return Side.Unknown
#
#     def adx_di(self, close, high, low):
#         spread  = 20
#         periods = 5
#
#         # ADX DI
#         adx      = util.adx(high, low, close)
#         di_plus  = util.di_plus(high, low, close)
#         di_minus = util.di_plus(high, low, close)
#
#         long1 = util.is_under(adx, 20, periods) and \
#                 di_plus[-periods-1] < di_plus[-1] and \
#                 di_minus[-periods-1] > di_minus[-1]
#         #         abs(di_plus[-1] - di_minus[-1])/abs(di_plus[-periods-1] - di_minus[-periods-1]) > spread
#         #
#         # print(abs(di_plus[-1] - di_minus[-1])/abs(di_plus[-periods-1] - di_minus[-periods-1]))
#
#         print(long1)
#         # long2 = is_over(adx, 20, p)  and spread_narrow(di_minus, di_plus)
#         # is_over(adx, 20, periods)  and crossover(di_plus, di_minus) and
#         #
#         #
#         # // plot(di_plus, color=green)
#         # // plot(di_minus, color=red)
#         # // plot(adx, color=blue)
#         #
#         # // 超高級ADXダイバージェンス
#         # up_div = is_top(di_plus) and di_plus[2] > di_minus[2]
#         # dn_div = is_top(di_minus) and di_minus[2] > di_plus[2]
#         #
#         # up_right_adx = up_div ? adx[1]: 0
#         # up_left_adx = valuewhen(up_div, adx[2], 1)
#         #
#         # dn_right_adx = dn_div ? adx[1]: 0
#         # dn_left_adx = valuewhen(dn_div, adx[2], 1)
#         #
#         # right_di_plus = up_div ? di_plus: 0
#         # left_di_plus = valuewhen(up_div, di_plus[2], 1)
#         #
#         # right_di_minus = dn_div ? di_minus: 0
#         # left_di_minus = valuewhen(dn_div, di_minus[2], 1)
#         #
#         # diff = input(10)
#         # border = input(20)
#         #
#         # will_be_up = up_div and up_left_adx > up_right_adx and abs(
#         #     up_right_adx - up_left_adx) > diff and up_right_adx < border and left_di_plus < right_di_plus
#         # will_be_dn = dn_div and dn_left_adx > dn_right_adx and abs(
#         #     dn_right_adx - dn_left_adx) > diff and dn_right_adx < border and left_di_minus < right_di_minus
#
#     def vix_rci(self, close, low):
#         pd   = 24
#         bbl  = 20
#         mult = 1.9
#         lb   = 85
#         ph   = 0.85
#         pl   = 1.01
#
#         rci_limit = 20
#         rci_diff  = 30
#
#         itvs = 9
#         itvm = 36
#         itvl = 52
#
#         # VIX RCI
#         wvf        = ((util.highest(close, pd) - low) / (util.highest(close, pd))) * 100
#         s_dev      = mult * util.stdev(wvf, bbl)
#         mid_line   = util.sma(wvf, bbl)
#         lower_band = mid_line - s_dev
#         upper_band = mid_line + s_dev
#         range_high = (util.highest(wvf, lb)) * ph
#         range_low  = (util.lowest(wvf, lb)) * pl
#         green_hist = [wvf[-i] >= upper_band[-i] or wvf[-i] >= range_high[-i] for i in range(8)][::-1]
#         red_hist   = [wvf[-i] <= lower_band[-i] or wvf[-i] <= range_low[-i]  for i in range(8)][::-1]
#
#         up1 = [(not green_hist[-i]) and green_hist[-i-1] and green_hist[-i-2]
#                and (not green_hist[-i-3]) and (not green_hist[-i-4]) for i in range(len(green_hist)-5)][::-1]
#         dn1 = [(not red_hist[-i]) and red_hist[-i-1] and red_hist[-i-2]
#                and (not red_hist[-i-3]) and (not red_hist[-i-4])     for i in range(len(red_hist)-5)][::-1]
#
#         dvup = red_hist[-1]   and red_hist[-2]
#         dvdn = green_hist[-1] and green_hist[-2]
#
#         rci_short_arr  = util.rci(close, itvs)
#         rci_middle_arr = util.rci(close, itvm)
#         rci_long_arr   = util.rci(close, itvl)
#
#         rci_short  = rci_short_arr[-1]
#         rci_middle = rci_middle_arr[-1]
#         rci_long   = rci_long_arr[-1]
#
#         up2 = rci_short < 0
#         dn2 = rci_short > 0
#
#         up31 = rci_long < 0 and rci_middle < 0 and util.crossover(rci_middle_arr, rci_long_arr)
#         up32 = rci_long < -100 + rci_limit and rci_middle < -100 + rci_limit
#         up33 = rci_long < 0 and rci_middle < 0 and rci_middle > rci_long
#         up34 = rci_long < 0 and rci_middle < 0 and rci_long > rci_middle and rci_long - rci_middle < rci_diff
#
#         up3 = up31 or up32 or up33 or up34
#
#         dn31 = rci_long > 0 and rci_middle > 0 and util.crossunder(rci_middle_arr, rci_long_arr)
#         dn32 = rci_long > 100 - rci_limit and rci_middle > 100 - rci_limit
#         dn33 = rci_long > 0 and rci_middle > 0 and rci_middle < rci_long
#         dn34 = rci_long > 0 and rci_middle > 0 and rci_long < rci_middle and rci_middle - rci_long < rci_diff
#
#         dn3 = dn31 or dn32 or dn33 or dn34
#
#         long1  = (up1[-1] or up1[-2] or up1[-3]) and (up2 or up3)
#         long2  = dvup and up2 and up3
#         short1 = (dn1[-1] or dn1[-2] or dn1[-3]) and (dn2 or dn3)
#         short2 = dvdn and dn2 and dn3
#         exit   = (rci_middle > 70 or rci_middle < -70)
#
#         if (long1 or long2):
#             return Side.Long
#         elif (short1 or short2):
#             return Side.Short
#         elif exit:
#             return Side.Close
#         else:
#             return Side.Unknown
#
#     def strategy(self, source):
#         close = np.array([v['close'] for _, v in enumerate(source[:-1])])
#         high  = np.array([v['high']  for _, v in enumerate(source[:-1])])
#         low   = np.array([v['low']   for _, v in enumerate(source[:-1])])
#         pos   = self.bitmex.position_qty()
#         lot   = self.bitmex.wallet_balance() / 10
#
#         side1 = self.macd_div(close)
#         self.adx_di(close, high, low)
#         side2 = self.vix_rci(close, low)
#
#         if (side1 == Side.Long) or \
#            (side1 != Side.Short and side2 == Side.Long) and \
#            (pos <= 0): # buy
#             self.bitmex.entry(side=Side.Long, size=lot+abs(pos))
#         elif (side1 == Side.Short) or \
#              (side1 != Side.Long and side2 == Side.Short) and \
#              (pos >= 0): # sell
#             self.bitmex.entry(side=Side.Short, size=lot+abs(pos))
#         elif(side2 == Side.Close) and (pos != 0): # close
#             self.bitmex.close_position()
