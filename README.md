
# Crypto Trading Bot README

## Description

This crypto trading bot is designed for automated trading on cryptocurrency exchanges. It's developed in Python, leveraging libraries like ccxt for exchange interactions, pandas and numpy for data manipulation, and asyncio with websockets for real-time operations. The bot utilizes exponential moving averages (EMAs) for trading decisions and includes Telegram integration for trade alerts.

## Features

- Real-time data streaming with WebSocket.
- EMA-based trading strategy. (strategy which works moderately but other more robust strategies are being developed, including one in partnership with a thesis)
- Supports automated trading Futures (Long and Short) on OKX exchange.
- Optimized costs to place most orders as a market maker.
- Telegram notifications for trades and updates.
- Genetic algorithm for trading parameter optimization.
- Historical data scraping for strategy backtesting.
- Automated error handling and reconnection.

## Requirements

- Python 3.11.4
- Libraries: ccxt, pandas, numpy, asyncio, websockets, datetime, pytz, telegram

## Installation

1. Clone or download the repository.
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Set up configuration files for API keys and settings.

## Usage


### Creating a Telegram API

To use Telegram notifications in the bot, you need to create a Telegram Bot and obtain its API token. Here's how to do it:

1. **Start a Chat with BotFather**: Open Telegram and search for 'BotFather'. Start a conversation with this bot, which is Telegram's official bot for creating other bots.
2. **Create a New Bot**: Send the `/newbot` command to BotFather. You'll be prompted to choose a name and a username for your bot.
3. **Get the API Token**: After creating the bot, BotFather will provide you with an API token. This token is a unique identifier and a key to access the Telegram API. Make sure to keep it secure.
4. **Configure the Token in Your Bot**: Integrate this token into your trading bot's configuration, allowing it to send messages via your Telegram bot.

(You can find the actual channel here : https://t.me/+Wb-TlUKPmQw2YjJk)

### Creating an OKX API

To perform trading operations on OKX, you need to create an API key through the OKX platform. Follow these steps:

1. **Log In to Your OKX Account**: Access your account on the OKX website. If you don't have an account, you will need to create one.
2. **Access API Management**: Navigate to the API section in your account settings. This is usually found under the 'Account' or 'Security' settings.
3. **Create a New API Key**: Select the option to create a new API key. You will be asked to set permissions for this key (e.g., read, trade) and possibly link it to an IP address for security.
4. **Note Down the API Details**: Once the API key is created, you will receive an API key, a secret key, and a passphrase. These credentials are used to connect your trading bot to the OKX API.
5. **Implement the API in Your Bot**: Create new file keys.json with template keys.json.example and replace with our personnal keys

1. Configure API keys and settings.
2. Run the script:
   ```bash
   python main.py
   ```
3. Monitor via terminal and Telegram.

## Strategy Overview

The bot uses EMAs to determine buy or sell signals, optimized with a genetic algorithm.
Other strategies are coming.

## Disclaimer

- Use at your own risk; understand the risks involved in cryptocurrency trading.
- This bot is for educational purposes; not responsible for any financial losses.

## Contributions

Contributions and feature requests are welcome. Check the issues page for more details.
Contributors : 
- Jules Mourgues Haroche
- Antoine de Parthenay

## Contact

For queries or assistance, open an issue in the repository.

## Server and Docker Deployment

This trading bot is designed to run on a server environment, utilizing Docker for containerization. This ensures easy deployment and consistent operation across different systems. The Docker setup encapsulates all necessary dependencies, making it straightforward to deploy the bot on any server that supports Docker.
The Docker configuration is maintained in the "Dockerfile".


## Working In Progress 

- We realized a bias in our strategy backtest, which led us to revise our strategies. We are working on a machine learning strategy with XGBoost (Heavily inspired by: "https://www.kaggle.com/code/vbmokin/crypto-btc-advanced-analysis-forecasting") and a daily optimization of the model parameters using a genetic algorithm, allowing us to apply the best model to the following day.
- We chose to trade in minutes, which led us to incur a significant amount of transaction fees, thus impacting performance (optimization during order placement to minimize orders with taker fees).
- Comprehensive reporting of the day, week, month, and year to date.
- Interactivity with the Telegram bot.
