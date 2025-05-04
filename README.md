ExpertOptionsToolsV2
ExpertOptionsToolsV2 is a Python library designed to interact with the Expert Option trading platform via its WebSocket API. It provides both asynchronous (ExpertOptionAsync) and synchronous (ExpertOption) clients to perform trading operations, fetch market data, and manage account activities. The library supports demo and real accounts, asset selection, trade placement (call/put), and real-time candle subscriptions.
Developed by Ahmed (Telegram: @A11ksa).
Features

Asynchronous and Synchronous Clients: Use ExpertOptionAsync for async operations or ExpertOption for synchronous operations.
Trading Operations: Place call (buy) and put (sell) trades with customizable expiration times.
Market Data: Fetch historical candles, real-time candle subscriptions, and asset payout percentages.
Account Management: Retrieve account balance, open/closed deals, and user profile data.
Logging: Built-in logging to file and terminal for debugging and monitoring.
Validation: Flexible message validation for WebSocket responses.
Asset Support: Extensive list of assets (e.g., EURUSD, BTCUSD, AAPL) with IDs and symbols.

Installation
Prerequisites

Python 3.8 or higher
A valid Expert Option API token (obtain from the Expert Option platform)

Install via pip

Clone the repository or download the project files:
git clone https://github.com/A11ksa/Expert-Option-API.git
cd Expert-Option-API


Create and activate a virtual environment (recommended):
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows


Install the library and its dependencies:
pip install .



Dependencies

websockets>=11.0.3
pandas>=1.5.0
rich>=13.0.0 (for colored console output in examples)

Usage
Example: Placing a Trade
The following example demonstrates how to connect to the Expert Option API, fetch available assets, and place a buy (call) trade using the asynchronous client.
import asyncio
from ExpertOptionsToolsV2.expertoption import ExpertOptionAsync
from ExpertOptionsToolsV2.tracing import LogBuilder

# Configure logging
logger = LogBuilder().log_file("trade.log", "INFO").build()

async def main():
    # Initialize the API client (replace with your token)
    token = "Your_ExpertOption_Token"
    api = ExpertOptionAsync(token=token, demo=True)

    try:
        # Connect to the API
        await api.connect()
        print("Connected successfully!")

        # Fetch and print available assets
        await api.print_available_assets()

        # Select an asset with the highest payout
        asset = await api.select_highest_payout_asset()
        if not asset:
            print("No tradable assets available.")
            return

        asset_id = asset["id"]
        symbol = asset["symbol"]
        print(f"Selected asset: {symbol} (ID: {asset_id})")

        # Place a buy trade
        amount = 4.0
        expiration_time = 60  # 60 seconds
        deal_id, result = await api.buy(
            asset_id=asset_id,
            amount=amount,
            expiration_time=expiration_time,
            check_win=True
        )
        print(f"Trade ID: {deal_id}, Result: {result}")

    except Exception as e:
        logger.error(f"Error: {e}")
        print(f"Error: {e}")
    finally:
        await api.disconnect()

if __name__ == "__main__":
    asyncio.run(main())

Example: Fetching Candles
Retrieve historical candle data for an asset and display it as a pandas DataFrame.
import asyncio
from ExpertOptionsToolsV2.expertoption import ExpertOptionAsync

async def main():
    token = "Your_ExpertOption_Token"
    api = ExpertOptionAsync(token=token, demo=True)

    try:
        await api.connect()
        candles = await api.get_candles(
            asset_id=142,  # EURUSD
            period=5,      # 5-second timeframe
            offset=0,      # Recent data
            duration=1800  # 30 minutes of data
        )
        print("Candles DataFrame:")
        print(candles)
    finally:
        await api.disconnect()

if __name__ == "__main__":
    asyncio.run(main())

Key Classes and Modules

ExpertOptionAsync: Asynchronous client for interacting with the Expert Option API.
Methods: buy, sell, get_candles, fetch_profile, subscribe_symbol, etc.


ExpertOption: Synchronous wrapper around ExpertOptionAsync for simpler usage.
constants.py: Contains asset IDs, symbols, and server configurations.
tracing.py: Provides logging utilities (Logger, LogBuilder).
validator.py: Offers tools for validating WebSocket messages.

Configuration

API Token: Obtain from the Expert Option platform and pass to the client constructor.
Demo Mode: Set demo=True for demo accounts or demo=False for real accounts.
Server URL: Defaults to wss://fr24g1eu.expertoption.com/ (Europe). Other regions available in constants.py.

Contributing
Contributions are welcome! Please follow these steps:

Fork the repository.
Create a new branch (git checkout -b feature/your-feature).
Commit your changes (git commit -m "Add your feature").
Push to the branch (git push origin feature/your-feature).
Open a Pull Request.

Report issues or suggest features on the GitHub Issues page.
Contact
For support or inquiries, reach out to the developer:

Telegram: @A11ksa
Email: ar123ksa@gmail.com
GitHub: A11ksa

License
This project is licensed under the MIT License. See the LICENSE file for details.
