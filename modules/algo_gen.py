import pandas as pd
from tqdm import tqdm
import random
from datetime import datetime, timedelta
from strategy.crossing_ema.strategy import preprocess, strategy, calculate_performance
from modules.scraping import scrape_candles_to_csv
from modules.scraping import get_data

def optimized_test_strategies(data, fast_ma, slow_ma, money, money_buy_hold):

    settings = {
        'money': money,
        'buy_and_hold': money_buy_hold
    }

    data = preprocess(data.copy(), fast_ma, slow_ma)

    data = strategy(data.copy())
 
    row = calculate_performance(data.copy(), settings, fast_ma, slow_ma)

    df = pd.DataFrame([row], columns=['Open_ma', 'Close_ma', 'Performance', 'Buy_and_hold_performance', 'Superiority', 'Volatility', 'Sharpe_ratio', 'Max_drawdown', 'Sortino_ratio', 'Calmar_ratio', 'Number_of_trades'])

    return df['Performance'].values[0]
    
def generate_initial_population(pop_size, param_range):
    return [(
        random.randint(*param_range),      # fast_ma
        random.randint(*param_range),      # slow_ma
    ) for _ in range(pop_size)]

def calculate_fitness(individual, data, money, money_buy_hold):
    fast_ma, slow_ma = individual
    fitness_scores= optimized_test_strategies(data, fast_ma, slow_ma, money, money_buy_hold)
    return fitness_scores

def select_parents(population, fitness_scores):
    # Higher fitness -> Higher chance of being selected
    parents = random.choices(population, weights=fitness_scores, k=2)
    return parents

def crossover(parent1, parent2):
    # Make sure the crossover handles all three parameters
    child1 = (parent1[0], parent2[1])
    child2 = (parent2[0], parent1[1])
    return [child1, child2]

def mutate(individual, param_range, mutation_rate=0.4):
    # Mutation should consider all three parameters
    if random.random() < mutation_rate:
        individual = list(individual)
        individual[random.randint(0, 1)] = random.randint(*param_range)
        individual = tuple(individual)
    return individual

async def genetic_algorithm(pop_size, param_range, max_generations, mutation_rate, money, money_buy_hold, interval, settings, backtest_time, when, symbols):
    time_needed_for_preprocessing = (int(interval.rstrip('m')) * settings['max_range'])/60/24
    timedelta_var = backtest_time + int(time_needed_for_preprocessing) + 1

    raw_data = get_data(settings['exchange'], 3, symbols, interval, timedelta_var, 1000)

    #Créer une variable until qui est minuit de hier, et since qui est minuit de avant-hier
    until = when
    since = until - timedelta(days=1) 

    interval_multiplier = int(interval.rstrip('m'))
    since_range = since - timedelta(minutes=settings['max_range'] * interval_multiplier)

    data = raw_data[since_range:until].copy()

    population = generate_initial_population(pop_size, param_range)
    
    for _ in tqdm(range(max_generations)):
        fitness_scores = [calculate_fitness(ind, data.copy(), money, money_buy_hold) for ind in population]
        
        new_population = []
        while len(new_population) < pop_size:
            parent1, parent2 = tournament_selection(population, fitness_scores)
            for child in crossover(parent1, parent2):
                # Corrected mutate function call with all required arguments
                new_population.append(mutate(child, param_range, mutation_rate))
        
        population = new_population

    # Find the best individual
    best_fitness = max(fitness_scores)
    best_individual = population[fitness_scores.index(best_fitness)]
    return best_individual, best_fitness

def tournament_selection(population, fitness_scores, tournament_size=3):
    selected_parents = []
    for _ in range(2):  # Selecting two parents
        tournament = random.sample(list(zip(population, fitness_scores)), tournament_size)
        tournament.sort(key=lambda x: x[1], reverse=True)  # Sort by fitness score
        selected_parents.append(tournament[0][0])  # Select the best in the tournament
    return selected_parents[0], selected_parents[1]

if __name__ == "__main__":

    symbols = 'BTC/USDT'
    intervals = '15m'
    
    # download the data in scraping.py
    # Read the data 
    try : 
        data_raw = pd.read_csv(f'data/Binance/{symbols}_{intervals}.csv', header=None)
    except : 
        # download the data in scraping.py
        scrape_candles_to_csv(f'data/Binance/{symbols}_{intervals}.csv', 'binance', 3, symbols, intervals, '2024-02-0100:00:00Z', 1000)
        data_raw = pd.read_csv(f'data/Binance/{symbols}_{intervals}.csv', header=None)
    # Rename columns
    data_raw.columns = ['Timestamp', 'Open', 'High', 'Low', 'Close', 'Volume']
    # Convert timestamp to datetime
    data_raw = data_raw.set_index(pd.to_datetime(data_raw['Timestamp'], unit='ms'))

    # select previous day
    previous_day = datetime.now() - pd.Timedelta(days=1)
    data = data_raw.loc[data_raw.index.date == previous_day.date()].copy()
    data.drop(['Timestamp'], axis=1, inplace=True)

    # Genetic Algorithm Parameters
    POPULATION_SIZE = 50
    PARAM_RANGE = (1, 800)  # Intervalle des paramètres pour les moyennes mobiles
    MAX_GENERATIONS = 50  # Nombre maximum de générations
    mutation_rate = 0.4  # Taux de mutation
    money = 100  # Capital initial
    money_buy_hold = 100  # Capital pour la stratégie buy and hold

    # Run the optimizationie
    best_params, best_fitness = genetic_algorithm(data, POPULATION_SIZE, PARAM_RANGE, MAX_GENERATIONS, mutation_rate, money, money_buy_hold)