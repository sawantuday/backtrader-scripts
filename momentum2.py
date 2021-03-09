import backtrader as bt
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from scipy.stats import linregress
from datetime import datetime

# TODO:
# update momentum indicator to implement my logic 
# Remove all other indicators to create baseline 
# add nifty 200 sma to decide trade or no trade 
# use sectoral limits - max sector trades 
# use sectoral trades to decide trades 
# use sma, atr and other indicators to decide trades 
# use volume data to decide trades 

class Momentum(bt.Indicator):
    lines = ('trend',)
    params = (('period', 90),)
    
    def __init__(self):
        self.addminperiod(self.params.period)
    
    def next(self):
        returns = np.log(self.data.get(size=self.p.period))
        x = np.arange(len(returns))
        slope, _, rvalue, _, _ = linregress(x, returns)
        annualized = (1 + slope) ** 252
        self.lines.trend[0] = annualized * (rvalue ** 2)
        

class Strategy(bt.Strategy):
    def __init__(self):
        self.i = 0
        self.inds = {}
        self.spy = self.datas[0]
        self.stocks = self.datas[1:]
        
        # use this as nifty 200 sma to decide weather to take long trades or not 
        self.spy_sma200 = bt.indicators.SimpleMovingAverage(self.spy.close,
                                                            period=200)
        for d in self.stocks:
            self.inds[d] = {}
            self.inds[d]["momentum"] = Momentum(d.close, period=90)
            self.inds[d]["sma100"] = bt.indicators.SimpleMovingAverage(d.close, period=100)
            self.inds[d]["atr20"] = bt.indicators.ATR(d, period=20)

    def prenext(self):
        # call next() even when data is not available for all tickers
        self.next()
    
    def next(self):
        if self.i % 5 == 0:
            self.rebalance_portfolio()
        if self.i % 10 == 0:
            self.rebalance_positions()
        self.i += 1
    
    def rebalance_portfolio(self):
        # only look at data that we can have indicators for 
        self.rankings = list(filter(lambda d: len(d) > 100, self.stocks))
        self.rankings.sort(key=lambda d: self.inds[d]["momentum"][0])
        num_stocks = len(self.rankings)
        
        # sell stocks based on criteria
        for i, d in enumerate(self.rankings):
            if self.getposition(self.data).size:
                if i > num_stocks * 0.2 or d < self.inds[d]["sma100"]:
                    self.close(d)
        
        if self.spy < self.spy_sma200:
            return
        
        # buy stocks with remaining cash
        for i, d in enumerate(self.rankings[:int(num_stocks * 0.2)]):
            cash = self.broker.get_cash()
            value = self.broker.get_value()
            if cash <= 0:
                break
            if not self.getposition(self.data).size:
                size = value * 0.001 / self.inds[d]["atr20"]
                self.buy(d, size=size)
                
        
    def rebalance_positions(self):
        num_stocks = len(self.rankings)
        
        if self.spy < self.spy_sma200:
            return

        # rebalance all stocks
        for i, d in enumerate(self.rankings[:int(num_stocks * 0.2)]):
            cash = self.broker.get_cash()
            value = self.broker.get_value()
            if cash <= 0:
                break
            size = value * 0.001 / self.inds[d]["atr20"]
            self.order_target_size(d, size)

startcash = 100000
cerebro = bt.Cerebro(stdstats=False)
cerebro.broker.set_coc(True)
cerebro.broker.setcash(startcash)

# spy = bt.feeds.YahooFinanceData(dataname='SPY',
#                                  fromdate=datetime(2012,2,28),
#                                  todate=datetime(2018,2,28),
#                                  plot=False)
# cerebro.adddata(spy)  # add S&P 500 Index


import os 

for ticker in os.listdir('data'):
    data = bt.feeds.YahooFinanceCSVData(
        dataname=f"data/{ticker}", 
        name=ticker.replace('.NS.csv', '').lower(), 
        plot=True
    )
    cerebro.adddata(data)

    # df = pd.read_csv(f"data/{ticker}", parse_dates=True, index_col=0)
    # if len(df) > 100: # data must be long enough to compute 100 day SMA
    #     data = bt.feeds.PandasData(
    #         dataname=df, plot=True, name=ticker.replace('.NS.csv', '').lower()
    #     )
    #     cerebro.adddata(data)

cerebro.addobserver(bt.observers.Value)
cerebro.addanalyzer(bt.analyzers.SharpeRatio, riskfreerate=0.0)
cerebro.addanalyzer(bt.analyzers.Returns)
cerebro.addanalyzer(bt.analyzers.DrawDown)
cerebro.addstrategy(Strategy)
results = cerebro.run(maxcpus=None) # maxcpus=None means use all available CPUs

#Get final portfolio Value
portvalue = cerebro.broker.getvalue()
pnl = portvalue - startcash

#Print out the final result
print('Final Portfolio Value: ${}'.format(portvalue))
print('P/L: ${}'.format(pnl))

cerebro.plot(iplot=False, volume=False, grid=False)[0][0]

print(results)

# print(f"Sharpe: {results[0].analyzers.sharperatio.get_analysis()['sharperatio']:.3f}")
# print(f"Norm. Annual Return: {results[0].analyzers.returns.get_analysis()['rnorm100']:.2f}%")
# print(f"Max Drawdown: {results[0].analyzers.drawdown.get_analysis()['max']['drawdown']:.2f}%")