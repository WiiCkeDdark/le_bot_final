from modules.scraping import get_data
from strategy.crossing_ema.strategy import preprocess, strategy, calculate_performance
import pandas as pd
import numpy as np
import datetime
import time
import os
from tqdm import tqdm


async def getting_best_parameters_crossing_ema(pair, interval, when, backtest_time, settings):

    time_needed_for_preprocessing = (int(interval.rstrip('m')) * settings['max_range'])/60/24
    timedelta = backtest_time + int(time_needed_for_preprocessing) + 1

    print(f'Downloading {pair} on {interval}...\n')

    raw_data = get_data(settings['exchange'], 3, pair, interval, timedelta, 1000)

    #Créer une variable until qui est minuit de hier, et since qui est minuit de avant-hier
    until = when
    since = until - datetime.timedelta(days=1) 

    interval_multiplier = int(interval.rstrip('m'))
    since_range = since - datetime.timedelta(minutes=settings['max_range'] * interval_multiplier)

    results = pd.DataFrame(columns=['Open_ma', 'Close_ma', 'Performance', 'Buy_and_hold_performance', 'Superiority', 'Volatility', 'Sharpe_ratio', 'Max_drawdown', 'Sortino_ratio', 'Calmar_ratio', 'Number_of_trades'])

    print(f'Getting best parameters for {pair} on {interval}...\n')

    # Créer une boucle qui va essayer toutes les combinaisons de de ewa avec une range de 1 à 240 data['EMA_open'] = data['Open'].ewm(span=fast_ma, adjust=False).mean() et data['EMA_close'] = data['Close'].ewm(span=slow_ma, adjust=False).mean()
    for open_ma in tqdm(range(settings['min_range'], settings['max_range'] + 1)):
        for close_ma in range(settings['min_range'], settings['max_range'] + 1):

            # Copy the necessary data
            data_ema = raw_data[since_range:until].copy()

            # Preprocess the data
            data_ema = preprocess(data_ema.copy(), open_ma, close_ma)

            # Copy the data for the specified range
            data = data_ema[since:until].copy()

            # Apply the strategy
            data = strategy(data.copy())

            # Calculate the performance
            row = calculate_performance(data, settings, open_ma, close_ma)

            # Append the row to the results with concat
            results = pd.concat([results, pd.DataFrame([row])])
            
    # Enregistrer la meilleure combinaison dans un fichier
    results = results.sort_values(by='Performance', ascending=False)

    best_combination = results.sort_values(by='Performance', ascending=False).iloc[0].to_frame().T

    # Add date to the index of best_combination
    best_combination['Date'] = since
    best_combination.set_index('Date', inplace=True)

    if os.path.exists('strategy/crossing_ema/best_combination.csv'):
        best_combination.to_csv('strategy/crossing_ema/best_combination.csv', mode='a', header=False)
    else:
        best_combination.to_csv('strategy/crossing_ema/best_combination.csv')

    open_ma = best_combination['Open_ma'].values[0]
    close_ma = best_combination['Close_ma'].values[0]

    print(f'Based on yesterday, best parameters for {pair} on {interval} are: Open_ma {open_ma}, Close_ma {close_ma}\n')

    return open_ma, close_ma

if __name__ == '__main__':
    
    symbols = 'BTC/USDT'
    intervals = '15m'
    backtest_time = 1
    when = datetime.datetime.now()

    settings = {
        'exchange': 'binance',
        'max_range': 240,
        'min_range': 1,
        'money': 100,
        'buy_and_hold': 100
    }

    getting_best_parameters_crossing_ema(symbols, intervals, when, backtest_time, settings)