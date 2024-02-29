from scrap import get_data
import pandas as pd
import numpy as np
import datetime
import time
import os

def preprocess(data, open_ma, close_ma):
    data['EMA_open'] = data['Open'].ewm(span=open_ma, adjust=False).mean()
    data['EMA_close'] = data['Close'].ewm(span=close_ma, adjust=False).mean()
    return data

def strategy(data, open_ma, close_ma):
    data['Target'] = np.where(data['EMA_close'] > data['EMA_open'], 1, -1)
    data['Target'] = data['Target'].shift(1)
    data['Trade_on'] = (data['Target'] != np.roll(data['Target'], 1)).astype(int)
    return data

def calculate_performance(data, settings):
    # Drop NA values
    data = data.dropna()

    # Calculate portfolio change
    close_shifted = data['Close'].shift(1)
    data['Port_change'] = np.where(data['Target'] == 1,
                                   (data['Close'] - close_shifted) / close_shifted,
                                   (close_shifted - data['Close']) / close_shifted)
    # Shift 'Target' column
    data['Target'] = data['Target'].shift(1)
    data['Port_change'] = data['Port_change'].fillna(0)

    # Account for trading fee
    data['Port_change'] = np.where(data['Trade_on'] == 1, data['Port_change'] - 0.002, data['Port_change'])
    

    # Calculate number of trades
    #nmb_trades = data['Trade_on'].sum()

    # Calculate portfolio value
    data['Port'] = (1 + data['Port_change']).cumprod() * settings['money']
    return data

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
    
    return data

settings = {
    'exchange': 'binance',
    'max_range': 1,
    'min_range': 1,
    'money': 100,
    'buy_and_hold': 100
}

symbols = ['ETH/USDT']
intervals = ['30m']
backtest_time = 12

time_needed_for_preprocessing = (int(max(intervals, key=lambda x: int(x[:-1])).rstrip('m')) * settings['max_range'])/60/24
timedelta = backtest_time + int(time_needed_for_preprocessing) + 1

genetic = False



for symbol in symbols:
    for interval in intervals:

        # Construit le chemin du fichier
        symbol_name = symbol.replace("/", "")
        file_path = f'C:/Users/antoi/Code/le_bot_clean/data/raw/{symbol_name}_{interval}_{timedelta}.csv'
        
        # Vérifie si le fichier n'existe pas déjà
        if not os.path.exists(file_path):
            print(f'Downloading {symbol} on {interval}...\n')
            raw_data = get_data(settings['exchange'], 3, symbol, interval, timedelta, 1000)
            
            # Enregistre en csv avec le nom du symbol et de l'intervalle
            raw_data.to_csv(file_path)
        

for symbol in symbols:
    for interval in intervals:
        
        print(f'Getting back {symbol} on {interval}...\n')

        symbol_name = symbol.replace("/", "")

        raw_data = pd.read_csv(f'C:/Users/antoi/Code/le_bot_clean/data/raw/{symbol_name}_{interval}_{timedelta}.csv', index_col=0, parse_dates=True)

        print(f'Getting best parameters for {symbol} on {interval}...\n')

        best_parameters_results = pd.DataFrame(columns=['Open_ma', 'Close_ma', 'Performance', 'Buy_and_hold_performance', 'Superiority', 'Volatility', 'Sharpe_ratio', 'Max_drawdown', 'Sortino_ratio', 'Calmar_ratio', 'Number_of_trades'])

        ########################################
        # GETTING BEST PARAMETERS FOR STRATEGY #
        ########################################
        
        for i in range(backtest_time):

            until = datetime.datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) - datetime.timedelta(days=i+1)
            since = until - datetime.timedelta(days=1)

            interval_multiplier = int(interval.rstrip('m'))
            since_range = since - datetime.timedelta(minutes=settings['max_range'] * interval_multiplier)
            

            #print(f"Day {i+1}: Since {since}, Until {until}, Since Range {since_range}")

            results = pd.DataFrame(columns=['Open_ma', 'Close_ma', 'Performance', 'Buy_and_hold_performance', 'Superiority', 'Volatility', 'Sharpe_ratio', 'Max_drawdown', 'Sortino_ratio', 'Calmar_ratio', 'Number_of_trades'])

            if genetic == True:
                print("do")
            else:
                for open_ma in range(settings['min_range'], settings['max_range'] + 1):
                    for close_ma in range(settings['min_range'], settings['max_range'] + 1):

                        # Copy the necessary data
                        data_ema = raw_data[since_range:until].copy()
                        
                        # Preprocess the data
                        data_ema = preprocess(data_ema, open_ma, close_ma)

                        # Copy the data for the specified range
                        data = data_ema[since:until].copy()

                        # Apply the strategy
                        data = strategy(data, open_ma, close_ma)

                        # Calculate the performance
                        row = calculate_performance(data, settings)

                        # Append the row to the results with concat
                        results = pd.concat([results, row])
                        
                # Sort results by performance and get the best combination
                best_combination = results.sort_values(by='Performance', ascending=False).iloc[0].to_frame().T

                # Add date to the index of best_combination
                best_combination['Date'] = since
                best_combination.set_index('Date', inplace=True)

            print(f"{i/backtest_time*100}% done for {symbol} on {interval}")

            # Append the best combination to best_parameters_results and sort by index
            best_parameters_results = pd.concat([best_parameters_results, best_combination]).sort_index()
        
        # Get start and end dates
        start_date, end_date = best_parameters_results.index[0].strftime("%Y-%m-%d"), best_parameters_results.index[-1].strftime("%Y-%m-%d")

        # Save backtest_results to a CSV file
        best_parameters_results.to_csv(f'C:/Users/antoi/Code/le_bot_clean/strategy/crossing_ema/strategy/{symbol_name}_{interval}_{start_date}_{end_date}_best_parameters.csv')
        
        print(f"Saved {symbol} on {interval} from {start_date} to {end_date} to strategy/{symbol}_{interval}_{start_date}_{end_date}_best_parameters.csv\n")

        print(f'Backtesting {symbol} on {interval}...\n')

        backtest_results = pd.DataFrame(columns=['Date', 'Open_ma', 'Close_ma', 'Performance', 'Buy_and_hold_performance', 'Superiority', 'Volatility', 'Sharpe_ratio', 'Max_drawdown', 'Sortino_ratio', 'Calmar_ratio', 'Number_of_trades'])

        ########################################
        # BACKTESTING THE STRATEGY             #
        ########################################

dftest = pd.DataFrame()

for symbol in symbols:
    for interval in intervals:

        for day in best_parameters_results.sort_index().index:
            
            #Récupère close_ma et open_ma de la ligne de backtest_results
            close_ma = best_parameters_results.loc[day, 'Close_ma']
            open_ma = best_parameters_results.loc[day, 'Open_ma']

            #Récupère les données de la journée
            data = raw_data[day + datetime.timedelta(days=1) - datetime.timedelta(minutes=settings['max_range']):day + datetime.timedelta(days=2)].copy()
            
            #Preprocess the data
            data = preprocess(data, open_ma, close_ma)

            #Copy the data for the specified range
            data = data[day + datetime.timedelta(days=1):day + datetime.timedelta(days=2)].copy()
            
            # Apply the strategy
            data = strategy(data, open_ma, close_ma)

            dftest = pd.concat([dftest, data])

            # Calculate the performance
            row = calculate_performance(data, settings)

            row['Date'] = day + datetime.timedelta(days=1)

            # Concat row to backtest_results with  day + datetime.timedelta(days=1) en index
            backtest_results = pd.concat([backtest_results, row])


        # Fait un cumprod de la colonne performance et buy_and_hold_performance
        backtest_results['Performance Cumprod'] = backtest_results['Performance'].cumprod()
        backtest_results['Buy_and_hold_performance Cumprod'] = backtest_results['Buy_and_hold_performance'].cumprod()

        backtest_results['Performance portfolio'] = backtest_results['Performance Cumprod'] * settings['money']
        backtest_results['Performance buy and hold'] = backtest_results['Buy_and_hold_performance Cumprod'] * settings['buy_and_hold']

        dftest = calculate_performance(dftest, settings)

        dftest.to_csv(f"C:/Users/antoi/Code/le_bot_clean/strategy/crossing_ema/backtest_{symbol_name}_{interval}-to-visualise.csv")

        # Save backtest_results to a CSV file
        backtest_results.to_csv(f'C:/Users/antoi/Code/le_bot_clean/strategy/crossing_ema/{symbol_name}_{interval}_{start_date}_{end_date}_backtest_results.csv')

        print(f"Finished {symbol} on {interval}!\n")
