# Importation des bibliothèques nécessaires
import ccxt
import ccxt.async_support as ccxt_async
import websockets  # For WebSocket in an async manner
import asyncio
import json
import datetime
import pandas as pd
import numpy as np
import time
from modules.scraping import scrape_ohlcv
from modules.algo_gen import genetic_algorithm
import pytz
import os
from telegram import Bot
from telegram.ext import Updater
import math
from modules.best_parameters_crossing_ema import getting_best_parameters_crossing_ema

# Définition du fuseau horaire global en UTC
pytz.utc

class strategy:
    def __init__(self, data, telegram_bot):
        self.data = data  # Données historiques pour la stratégie
        self.exchange_actions = exchanges_action()
        self.telegram_bot = telegram_bot

    async def telegram_message(self, message):
        chat_id = '-4198741506'  # Replace with your chat ID
        # await self.telegram_bot.send_message(chat_id=chat_id, text=message)

    async def define_ma(self, genetic_algorithm_use=False):

        when = datetime.datetime.now()

        settings = {
            'exchange': 'binance',
            'max_range': 30,
            'min_range': 1,
            'money': 100,
            'buy_and_hold': 100
        }

        symbols = 'ETH/USDT'
        interval = '1m'
        backtest_time = 1

        if genetic_algorithm_use:
            # Paramètres pour l'algorithme génétique
            POPULATION_SIZE = 50
            PARAM_RANGE = (1, 10)  # Intervalle des paramètres pour les moyennes mobiles
            MAX_GENERATIONS = 5  # Nombre maximum de générations
            mutation_rate = 0.4  # Taux de mutation
            money = 100  # Capital initial
            money_buy_hold = 100  # Capital pour la stratégie buy and hold

            # Utilisation de l'algorithme génétique pour trouver les meilleures périodes des moyennes mobiles (plus rapide)
            best_params, best_fitness = await genetic_algorithm(POPULATION_SIZE, PARAM_RANGE, MAX_GENERATIONS, mutation_rate, money, money_buy_hold, interval, settings, backtest_time, when, symbols)
            print(f"Best Parameters: {best_params}, Best Fitness: {best_fitness}")
            open_ma = best_params[0]  # Période pour la moyenne mobile d'ouverture
            close_ma = best_params[1]  # Période pour la moyenne mobile de fermeture
            self.open_ma = open_ma
            self.close_ma = close_ma
        else: 
            # Utilisation de la méthode de recherche des meilleurs paramètres pour les moyennes mobiles (plus longue)
            self.open_ma, self.close_ma = await getting_best_parameters_crossing_ema(symbols, interval, when, backtest_time, settings)
    
    async def signal(self, df_all):

        self.df_all = df_all
        self.df_all['EMA_open'] = self.df_all['Open'].ewm(span=self.open_ma, adjust=False).mean()
        self.df_all['EMA_close'] = self.df_all['Close'].ewm(span=self.close_ma, adjust=False).mean()

        self.df_all['EMA_open'].iat[-1] = np.nan
        self.df_all['EMA_close'].iat[-1] = np.nan

        direction = np.where(self.df_all['EMA_close'] > self.df_all['EMA_open'], 1, -1)

        self.df_all['Target'] = np.where(direction != np.roll(direction, 1), direction, direction)
        self.df_all['Trade_on'] = np.where(direction != np.roll(direction, 1), 1, 0)

        self.df_all['Target'].iat[-1] = np.nan
        self.df_all['Trade_on'].iat[-1] = np.nan

        last_minute = self.df_all.iloc[-2]
        
        await self.determine_action(last_minute)

        return self.df_all
    
    async def determine_action(self, last_minute):
        
        if await self.exchange_actions.retrieve_position() == []:
            if last_minute['Target'] == 1 :
                await self.exchange_actions.order('buy', 'limit')
                await self.telegram_message(f'Order placed: buy at {last_minute["Close"]} ETH/USDT:USDT')
            else: 
                await self.exchange_actionse.order('sell', 'limit')
                await self.telegram_message(f'Order placed: sell at {last_minute["Close"]} ETH/USDT:USDT')
        elif last_minute['Trade_on'] == 1:
            if last_minute['Target'] == 1 :
                await self.exchange_actions.order('buy', 'limit')
                await self.telegram_message(f'Order placed: buy at {last_minute["Close"]} ETH/USDT:USDT')
            else: 
                await self.exchange_actions.order('sell', 'limit')
                await self.telegram_message(f'Order placed: sell at {last_minute["Close"]} ETH/USDT:USDT')
        else:
            return 0

    async def retrieve_data_last_day(self):
        # Récupération des données du dernier jour via ccxt depuis Binance
        symbol = 'ETH/USDT'
        timeframe = '1m'  # Intervalle d'une minute
        exchange = getattr(ccxt, "binance")({
            'enableRateLimit': True,
        })
        yesterday = datetime.datetime.now() - datetime.timedelta(1)
        yesterday_str = yesterday.strftime('%Y-%m-%dT00:00:00Z')

        # Scraping des données OHLCV
        df_daily = pd.DataFrame(scrape_ohlcv(exchange, 3, symbol, timeframe, exchange.parse8601(yesterday_str), 100), 
                                columns=['Timestamp', 'Open', 'High', 'Low', 'Close', 'Volume'])
        df_daily['Timestamp'] = pd.to_datetime(df_daily['Timestamp'], unit='ms')

        # Filtre pour garder uniquement les données du dernier jour complet
        start_of_yesterday = datetime.datetime.now() - datetime.timedelta(days=1)
        start_of_yesterday = start_of_yesterday.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_yesterday = datetime.datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        df_daily = df_daily[(df_daily['Timestamp'] >= start_of_yesterday) & (df_daily['Timestamp'] < end_of_yesterday)]

        await exchange.close()
        return df_daily

class bot:
    def __init__(self, genetic_algorithm_use=False):
        # Initialisation du bot et récupération des données historiques pour le jour courant
        now = datetime.datetime.now()
        exchange = ccxt.binance()
        symbol = 'ETH/USDT'
        timeframe = '1m'  # Intervalle d'une minute
        limit = 1000
        start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
        data = scrape_ohlcv(exchange, 3, symbol, timeframe, exchange.parse8601(start_of_day.strftime('%Y-%m-%dT%H:%M:%SZ')), limit)
        data = pd.DataFrame(data, columns=['Timestamp', 'Open', 'High', 'Low', 'Close', 'Volume'])
        data['Timestamp'] = pd.to_datetime(data['Timestamp'], unit='ms')
        data.set_index('Timestamp', inplace=True)
        self.df_all = data  # DataFrame contenant toutes les données collectées
        self.length = len(data)  # Longueur initiale du DataFrame
        # telegram bot
        telegram_bot = Bot(token='7006816428:AAEoxEDduiYvhJCCsbrm1otv-IghzjanZjE')  # Replace with your bot token
        self.strategy = strategy(data, telegram_bot)  # Initialisation de la stratégie
        self.genetic_algorithm_use = genetic_algorithm_use  # Utilisation de l'algorithme génétique pour trouver les meilleures périodes des moyennes mobiles
        
        # Paramètres pour la reconnexion automatique en cas de déconnexion
        self.retry_count = 0
        self.max_retries = 5
        self.retry_delay = 10  # Délai entre les tentatives de reconnexion en secondes
       
    async def on_message(self, ws, message):
        # Traitement des messages reçus via WebSocket
        data = json.loads(message)
        if 'k' not in data:
            return
        kline = data['k']
        timestamp = datetime.datetime.utcfromtimestamp(kline['t']/1000)
        k_open = kline['o']
        k_close = kline['c']
        k_high = kline['h']
        k_low = kline['l']
        k_volume = kline['v']

        # Ajout des nouvelles données au DataFrame
        row_to_add = {'Open': float(k_open), 'Close': float(k_close), 'High': float(k_high), 'Low': float(k_low), 'Volume': float(k_volume)}
        df = pd.DataFrame([row_to_add], index=[timestamp])

        if not df.empty:
            self.df_all = pd.concat([self.df_all, df])
            self.df_all = self.df_all[~self.df_all.index.duplicated(keep='last')]
        
        # Si la longueur du DataFrame est supérieure à la variable self.length
        if len(self.df_all) != self.length:

            # if midnight 
            if self.df_all.index[-1].hour == 0 and self.df_all.index[-1].minute == 0:
                self.strategy.define_ma(genetic_algorithm_use=True)
                self.strategy.telegram_message(f"New day, new parameters: Open MA: {self.strategy.open_ma}, Close MA: {self.strategy.close_ma}")
                if len(self.df_all) > 3000:
                    self.df_all = self.df_all.iloc[-3000:]
            
            self.df_all = await self.strategy.signal(self.df_all)
                
            self.length = len(self.df_all)  
            
        print(self.df_all.tail(3))

    def on_error(self, ws, error):
        print(error)

    def on_close(self, ws, e, z):
        print("### closed ###")
        # save the data to a file
        self.df_all.to_csv('ethusdt.csv')
        # close all possitions
        self.strategy.exchanges_action_antoine.close_positions()
        self.strategy.exchanges_action_jules.close_positions()
        self.retry_connection()

    def on_open(self, ws):
        print("WS opened")
        
        # Abonnement aux mises à jour de la paire ETH/USDT sur Binance via WebSocket
        params = {
            "method": "SUBSCRIBE",
            "params": ["ethusdt@kline_1m"],
            "id": 1
        }
        ws.send(json.dumps(params))
        
    def retry_connection(self):
        # Tentative de reconnexion en cas de déconnexion
        if self.retry_count < self.max_retries:
            time.sleep(self.retry_delay)
            self.retry_count += 1
            print(f"Attempting to reconnect... Attempt {self.retry_count}")
            self.connect()
        else:
            print("Reached maximum retry attempts. Not retrying anymore.")

    async def connect(self):
        uri = "wss://stream.binance.com:9443/ws/ethusdt@kline_1m"
        await self.strategy.define_ma(self.genetic_algorithm_use)
        async with websockets.connect(uri) as websocket:
            await self.strategy.telegram_message(f"Bot started at {datetime.datetime.now()}\n with Open MA : {self.strategy.open_ma} and Close MA : {self.strategy.close_ma}")
            await self.handle_websocket(websocket)

    async def handle_websocket(self, websocket):
        # Subscribe or listen to the WebSocket stream
        await websocket.send(json.dumps({"method": "SUBSCRIBE", "params": ["ethusdt@kline_1m"], "id": 1}))
        async for message in websocket:
            # Process message
            await self.on_message(websocket, message)

    async def close_connection(self, websocket):
        # Fermeture de la connexion WebSocket
        await self.strategy.telegram_message("Bot stopped")
        await websocket.close()

class exchanges_action: 
    def __init__(self):
        # read credentials from key file
        key_file = 'keys.json'
        keys = {}
        if os.path.exists(key_file):
            with open(key_file) as f:
                keys = json.load(f)
        self.exchange = ccxt_async.okx({
            'apiKey': keys.get('OKX_api', {}).get('api_key', ''),
            'secret': keys.get('OKX_api', {}).get('api_secret', ''),
            'password': keys.get('OKX_api', {}).get('api_password', ''),
            'options': {
                'defaultType': 'futures'
            }
        })
        self.exchange.set_sandbox_mode(True) # Enable sandbox/demo mode
        self.symbol = 'ETH/USDT:USDT'

    def load_markets(self):
        markets = self.exchange.load_markets()
        with open('markets.json', 'w') as f:
            json.dump(markets, f, indent=4)
    
    async def order(self, side, type):
        try :
            open_orders = await self.exchange.fetch_open_orders(symbol=self.symbol)
            if open_orders != []:
                for order in open_orders:
                    await self.exchange.cancel_order(order['id'], self.symbol)
                    print(f"Order cancelled: {order['id']}")
            position = await self.exchange.fetch_position(symbol=self.symbol)
            print(position)
            if position is not None:
                while int(position['info']['pos']) != 0:
                    side = 'sell' if float(position['info']['pos']) > 0 else 'buy'
                    order = await self.exchange.create_order(self.symbol, 'market', side, abs(float(position['info']['pos'])), {'reduceOnly': True})
                    time.sleep(2)
                    position = await self.exchange.fetch_position(symbol=self.symbol)
                    if int(position['info']['pos']) == 0:
                        print(f"Position closed: {side} {abs(float(position['info']['pos']))} contracts")

            btc_price = await self.exchange.fetch_ticker(self.symbol)
            btc_ask = btc_price['ask']
            btc_bid = btc_price['bid']
            btc_price = (btc_ask + btc_bid) / 2
            # calculate the amount of contracts to buy
            balance = await self.exchange.fetch_balance()
            quantity = int(round(round((math.floor((balance['USDT']['free'] / btc_price)* 10000))/ 10000, 5) / 0.01,0) * 0.95)# Nombre de contrats disponibles

            price_multiplier = 0.9999999 if side == 'buy' else 1.0000001
            price = float(btc_bid if side == 'buy' else btc_ask) * price_multiplier

            print(quantity)
            print(price)
        
            type = type # or 'market'
            side = side  # or 'sell
            
            order = await self.exchange.create_order(self.symbol, type, side, quantity, price)
            print(order)
            print(f"Order placed: {side} {quantity} contracts at {price} {self.symbol}")

        except Exception as e:
            print(f"Error placing order: {e}")

    def retrieve_position(self):
        open_pos = self.exchange.fetch_positions()
        return open_pos
    
    def close_positions(self):
        positions = self.retrieve_position()
        for pos in positions:
            if pos['symbol'] == self.symbol:
                size = abs(float(pos['info']['pos']))  # Get the size of the position
                side = 'sell' if float(pos['info']['pos']) > 0 else 'buy'  # Determine the side to close the position
                try:
                    # Place a market order to close the position
                    # close_order = self.exchange.create_order(self.symbol, 'market', side, size)
                    # print(f"Position closed: {close_order}")
                    print(f"Position closed: {side} {size} contracts")
                except Exception as e:
                    print(f"Error closing position: {e}")

class reporting:
    def __init__(self):
        pass

async def main(genetic_algorithm_use=False):
    running_bot = bot(genetic_algorithm_use)
    await running_bot.connect()

if __name__ == "__main__":
    asyncio.run(main(genetic_algorithm_use=True))
