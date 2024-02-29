import numpy as np
import pandas as pd

def preprocess(data, open_ma, close_ma):
    data['EMA_open'] = data['Open'].ewm(span=open_ma, adjust=False).mean()
    data['EMA_close'] = data['Close'].ewm(span=close_ma, adjust=False).mean()
    return data

def strategy(data):
    data['Target'] = np.where(data['EMA_close'] > data['EMA_open'], 1, -1)
    # shift the target by one to avoid look-ahead bias
    data['Target'] = data['Target'].shift(1)
    data['Trade_on'] = (data['Target'] != np.roll(data['Target'], 1)).astype(int)
    return data

def calculate_performance(data, settings, open_ma, close_ma):
    # Drop NA values
    data = data.copy().dropna()

    # Calculate portfolio change
    data['Port_change'] = np.where(data['Target'] == 1,
                                   (data['Close'] - data['Open']) / data['Open'],
                                   (data['Open'] - data['Close']) / data['Open'])
    data['Port_change'] = data['Port_change'].fillna(0)

    # Account for trading fee
    data['Port_change'] = np.where(data['Trade_on'] == 1, data['Port_change'] - 0.002, data['Port_change'])

    # Calculate number of trades
    nmb_trades = data['Trade_on'].sum()

    # Calculate portfolio value
    data['Port'] = (1 + data['Port_change']).cumprod() * settings['money']

    # Check for overflow
    if np.any(data['Port'] > np.finfo(np.float64).max):
        print("Overflow occurred")

    # Calculate buy and hold strategy
    buy_and_hold = (1 + (data['Close'].pct_change())).cumprod() * settings['buy_and_hold']
    data['Buy_and_Hold'] = buy_and_hold

    # Calculate performance metrics
    performance = data['Port'].iloc[-1] / settings['money']
    buy_and_hold_performance = data['Buy_and_Hold'].iloc[-1] / settings['buy_and_hold']
    surperiority = performance / buy_and_hold_performance - 1
    portfolio_volatility = data['Port_change'].std() * np.sqrt(252)
    money_end = data['Port'].iloc[-1]
    sharpe_ratio = (money_end - settings['money']) / portfolio_volatility
    data['Drawdown'] = data['Port'] / data['Port'].cummax() - 1
    max_drawdown = data['Drawdown'].min()
    downside = data['Port_change'][data['Port_change'] < 0].std() * np.sqrt(252)
    sortino_ratio = (money_end - settings['money']) / downside
    calmar_ratio = (money_end - settings['money']) / max_drawdown

    row = {'Open_ma': open_ma, 'Close_ma': close_ma, 'Performance': performance, 'Buy_and_hold_performance': buy_and_hold_performance,
                            'Superiority': surperiority, 'Volatility': portfolio_volatility, 'Sharpe_ratio': sharpe_ratio,
                                'Max_drawdown': max_drawdown, 'Sortino_ratio': sortino_ratio, 'Calmar_ratio': calmar_ratio,
                                    'Number_of_trades': nmb_trades}
    
    return row