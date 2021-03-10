import backtrader as bt
from datetime import datetime

# Reyner Teo 88% win ratio strategy 
# ticker is above 200 day moving average 
# rsi (period=10) for ticker is below 30
# entry next day open 
# exit when rsi closes above 40 or after 10 days (exit next day open)
class ReynerTeoStrategy(bt.Strategy):
    params = dict(
        sma_period=200,
        rsi_period=10,
        max_hold_period=10,
        rsi_buy_threshold=30,
        rsi_sell_threshold=45
    )

    def __init__(self):
        self.rsi = bt.indicators.RSI_SMA(self.data.close, period=self.p.rsi_period)
        self.sma = bt.indicators.SimpleMovingAverage(self.data.close, period=self.p.sma_period)
        # self.buyList = []
        # self.closeList = []
        self.bar_executed = 0

    def log(self, txt, dt=None):
        dt = dt or self.datas[0].datetime.date(0)
        print('%s %s' % (dt.isoformat(), txt))

    def notify_trade(self, trade):
        # print(trade)
        if trade.isclosed:
            self.log('Operation Profit, Gross: %.2f, Net: %.2f, barlen: %d' % 
                 (trade.pnl, trade.pnlcomm, trade.barlen))

    def notify_order(self, order):
        if order.status in [order.Submitted, order.Accepted]:
            return 
        
        if order.status in [order.Completed]:
            if order.isbuy():
                self.log('Buy executed, price: %.2f, cost: %.2f, comm: %.2f' % (
                    order.executed.price,
                    order.executed.value,
                    order.executed.comm,
                ))

                self.buyprice = order.executed.price
                self.buycomm = order.executed.comm
            else : # sell 
                self.log('SELL EXECUTED, Price: %.2f, Cost: %.2f, Comm %.2f' %
                                (order.executed.price,
                                order.executed.value,
                                order.executed.comm))
                
                # self.bar_executed = len(self)
        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log('Order Canceled/Margin/Rejected')
            # Write down: no pending order
            self.order = None

    def next(self):
        if not self.position:
            if self.data.close > self.sma and self.rsi < self.p.rsi_buy_threshold:
                self.buy(size=100)
        else:
            if self.data.close < self.sma or self.rsi > self.p.rsi_sell_threshold:
                self.close()
                self.bar_executed = 0
                # self.sell(size=100)
        
            # rebalance - close all trades open for more than x bars 
            elif self.bar_executed >= self.p.max_hold_period:
                self.close()
                self.bar_executed = 0

            else :
                self.bar_executed = self.bar_executed + 1 


if __name__ == '__main__':
    startcash = 100000
    cerebro = bt.Cerebro()
    cerebro.broker.setcash(startcash)
    cerebro.addstrategy(ReynerTeoStrategy)
    cerebro.broker.setcommission(commission=0.0015)
    
    tickers = ['infy.ns.csv']
    for ticker in tickers :
        data = bt.feeds.YahooFinanceCSVData(
            dataname=f"data/{ticker}", 
            name=ticker.replace('.NS.csv', '').lower(), 
            plot=False
            # fromdate = datetime(2016,1,1),
            # todate = datetime(2017,1,1),
        )

        #Add the data to Cerebro
        cerebro.adddata(data)
    

    cerebro.run()

    #Get final portfolio Value
    portvalue = cerebro.broker.getvalue()
    pnl = portvalue - startcash

    #Print out the final result
    print('Final Portfolio Value: ${}'.format(portvalue))
    print('P/L: ${}'.format(pnl))

    #Finally plot the end results
    # cerebro.plot(style='line')