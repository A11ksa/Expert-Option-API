import asyncio
import time
from datetime import datetime, timedelta
from ExpertOptionsToolsV2.expertoption.asyncronous import ExpertOptionAsync
from ExpertOptionsToolsV2.tracing import LogBuilder
from ExpertOptionsToolsV2.constants import get_asset_name
from rich import print

# Configure logger: only file logging
LOG_FILE = f"log-{time.strftime('%d-%m-%Y')}.txt"
logger = LogBuilder().log_file(LOG_FILE, "INFO").build()

async def get_server_time(api):
    try:
        return await api.get_server_time()
    except Exception as e:
        logger.error(f"Failed to get server time: {e}")
        return int(time.time())

async def get_account_context(api: ExpertOptionAsync) -> str:
    try:
        profile = await api.fetch_profile()
        return profile.get("context", "demo")
    except Exception as e:
        logger.error(f"Failed to get account context: {e}")
        return "demo"

async def test_new_functions(api):
    """Test new API functions."""
    # Test fetch_currencies
    print("[cyan]===== Fetching Currencies =====[/cyan]")
    try:
        currencies = await api.fetch_currencies()
        if not currencies:
            print("[yellow]No currencies available.[/yellow]")
            logger.warning("No currencies retrieved")
        else:
            print("[green]Available Currencies:[/green]")
            print("  -----------------------------------")
            for currency in currencies[:5]:  # Show first 5 for brevity
                print(f"  ID: {currency['id']:<4} | Name: {currency['name']:<8} | Sign: {currency['sign']:<3} | Active: {'Yes' if currency['is_active'] else 'No'}")
            if len(currencies) > 5:
                print(f"  ... and {len(currencies) - 5} more currencies")
            print("  -----------------------------------")
            logger.info(f"Currencies: {currencies}")
    except Exception as e:
        print(f"[red]Failed to fetch currencies: {e}[/red]")
        logger.error(f"Failed to fetch currencies: {e}")

    # Test fetch_countries
    print("[cyan]===== Fetching Countries =====[/cyan]")
    try:
        countries = await api.fetch_countries()
        if not countries:
            print("[yellow]No countries available.[/yellow]")
            logger.warning("No countries retrieved")
        else:
            print("[green]Available Countries (First 5):[/green]")
            print("  -----------------------------------")
            for country in countries[:5]:
                print(f"  ID: {country['id']:<4} | Name: {country['name']:<16} | Code: +{country['code']}")
            if len(countries) > 5:
                print(f"  ... and {len(countries) - 5} more countries")
            print("  -----------------------------------")
            logger.info(f"Countries: {countries[:5]}")
    except Exception as e:
        print(f"[red]Failed to fetch countries: {e}[/red]")
        logger.error(f"Failed to fetch countries: {e}")

    # Test fetch_user_deposit_sum
    print("[cyan]===== Fetching User Deposit Sum =====[/cyan]")
    try:
        deposit_sum = await api.fetch_user_deposit_sum()
        deposit_amount = deposit_sum.get("userDepositSum", 0)
        print("[green]Total Deposit Sum:[/green]")
        print("  -----------------------------------")
        print(f"  Amount: ${deposit_amount:.2f}")
        print("  -----------------------------------")
        logger.info(f"Deposit Sum: {deposit_sum}")
    except Exception as e:
        print(f"[red]Failed to fetch deposit sum: {e}[/red]")
        logger.error(f"Failed to fetch deposit sum: {e}")

    # Test fetch_user_achievements
    print("[cyan]===== Fetching User Achievements =====[/cyan]")
    try:
        achievements = await api.fetch_user_achievements()
        if not achievements:
            print("[yellow]No achievements available.[/yellow]")
            logger.warning("No achievements retrieved")
        else:
            print("[green]User Achievements:[/green]")
            print("  -----------------------------------")
            achieved = achievements.get("achieved", [])
            for ach in achieved[:3]:  # Show first 3 for brevity
                level = str(ach.get('level', 'N/A'))  # Convert level to string to avoid NoneType error
                print(f"  Name: {ach['name']:<30} | Level: {level:<4} | Description: {ach['description']}")
            if len(achieved) > 3:
                print(f"  ... and {len(achieved) - 3} more achieved")
            print("  -----------------------------------")
            logger.info(f"Achievements: {achievements}")
    except Exception as e:
        print(f"[red]Failed to fetch achievements: {e}[/red]")
        logger.error(f"Failed to fetch achievements: {e}")

    # Test subscribe_expert_options
    print("[cyan]===== Subscribing to Expert Options =====[/cyan]")
    try:
        subscription = await api.subscribe_expert_options()
        options = subscription.get("options", [])
        if not options:
            print("[yellow]No expert options available.[/yellow]")
            logger.warning("No expert options retrieved")
        else:
            print("[green]Expert Options (First 3):[/green]")
            print("  -----------------------------------")
            for opt in options[:3]:
                print(f"  User: {opt['name']:<16} | Asset ID: {opt['asset_id']:<4} | Amount: ${opt['amount_usd']:.2f} | Type: {'Call' if opt['type'] == 0 else 'Put'}")
            if len(options) > 3:
                print(f"  ... and {len(options) - 3} more options")
            print("  -----------------------------------")
            logger.info(f"Expert Subscription: {subscription}")
    except Exception as e:
        print(f"[red]Failed to subscribe to expert options: {e}[/red]")
        logger.error(f"Failed to subscribe to expert options: {e}")

    # Test open_trades
    print("[cyan]Fetching open trades...[/cyan]")
    try:
        open_trades = await api.open_trades(count=10)
        print(f"[green]Open Trades: {open_trades}[/green]")
        logger.info(f"Open Trades: {open_trades}")
    except Exception as e:
        print(f"[red]Failed to fetch open trades: {e}[/red]")
        logger.error(f"Failed to fetch open trades: {e}")

    # Test trade_history
    print("[cyan]Fetching trade history...[/cyan]")
    try:
        trade_history = await api.trade_history(count=10)
        print(f"[green]Trade History: {trade_history}[/green]")
        logger.info(f"Trade History: {trade_history}")
    except Exception as e:
        print(f"[red]Failed to fetch trade history: {e}[/red]")
        logger.error(f"Failed to fetch trade history: {e}")

async def test_candle_functions(api, asset_id, symbol, timeframe):
    """Test candle-related functions."""
    server_time = await get_server_time(api)

    # Test historySteps
    print(f"[cyan]Fetching historical candles for {symbol} with timeframe {timeframe}s...[/cyan]")
    logger.info(f"Fetching historical candles for Asset ID {asset_id}...")
    try:
        historical_candles = await api.historySteps(
            asset_id=asset_id,
            timeframe=timeframe,
            start_time=server_time - 7200,  # 2 hours ago
            end_time=server_time - 3600     # 1 hour ago
        )
        if not historical_candles:
            print("[yellow]No historical candles retrieved...[/yellow]")
            logger.warning("No historical candles retrieved for Asset ID {asset_id}")
        else:
            print("[green]Historical Candles (First 5):[/green]")
            # Validate candle structure
            for candle in historical_candles[:5]:  # Show first 5 for brevity
                print(f"Time: {candle['time']}, Open: {candle['open']}, High: {candle['high']}, Low: {candle['low']}, Close: {candle['close']}")
            logger.info(f"Historical candles retrieved: {len(historical_candles)} candles for Asset ID {asset_id}")
    except Exception as e:
        print(f"[red]Failed to fetch historical candles: {e}[/red]")
        logger.error(f"Failed to fetch historical candles for Asset ID {asset_id}: {e}")

    # Test expTimes in candle_cache
    print(f"[cyan]Checking expTimes for {symbol}...[/cyan]")
    exp_times = api.candle_cache.get(asset_id, {}).get(timeframe, {}).get("expTimes", [])
    print(f"[green]Expiration Times: {exp_times}[/green]")
    logger.info(f"Expiration Times for Asset ID {asset_id}: {exp_times}")

async def test_subscriptions(api, asset_id, symbol, timeframe):
    """Test subscription to live candles, chunked candles, and timed candles."""
    # Test subscribe_symbol (standard live candles)
    print(f"[cyan]===== Subscribing to Live Candles for {symbol} (Timeframe: {timeframe}s) =====[/cyan]")
    logger.info(f"Subscribing to live candles for Asset ID {asset_id}...")
    try:
        subscription = await api.subscribe_symbol(asset_id, [timeframe])
        async with asyncio.timeout(10):  # Set a 10-second timeout
            async for data in subscription:
                print("[green]Received Live Candle:[/green]")
                print("  -----------------------------------")
                print(f"  Time: {data['time']} | Open: {data['open']:.3f} | High: {data['high']:.3f} | Low: {data['low']:.3f} | Close: {data['close']:.3f}")
                print("  -----------------------------------")
                logger.info(f"Received live candle for Asset ID {asset_id}: {data}")
                break  # Stop after one candle for testing
    except asyncio.TimeoutError:
        print("[yellow]No live candles received within 10 seconds, proceeding...[/yellow]")
        logger.warning("No live candles received within 10 seconds for Asset ID {asset_id}")
    except Exception as e:
        print(f"[red]Subscription error for live candles: {e}[/red]")
        logger.error(f"Subscription error for live candles for Asset ID {asset_id}: {e}")
        raise

    # Test subscribe_symbol_chunked (aggregated candles by chunk size)
    print(f"[cyan]===== Subscribing to Chunked Candles for {symbol} (Chunk Size: 5) =====[/cyan]")
    logger.info(f"Subscribing to chunked candles for Asset ID {asset_id} with chunk size 5...")
    try:
        subscription_chunked = await api.subscribe_symbol_chunked(asset_id, chunk_size=5)
        async with asyncio.timeout(10):  # Set a 10-second timeout
            async for data in subscription_chunked:
                print("[green]Received Chunked Candle:[/green]")
                print("  -----------------------------------")
                print(f"  Time: {data['time']} | Open: {data['open']:.3f} | High: {data['high']:.3f} | Low: {data['low']:.3f} | Close: {data['close']:.3f}")
                print("  -----------------------------------")
                logger.info(f"Received chunked candle for Asset ID {asset_id}: {data}")
                break  # Stop after one aggregated candle
    except asyncio.TimeoutError:
        print("[yellow]No chunked candles received within 10 seconds, proceeding...[/yellow]")
        logger.warning("No chunked candles received within 10 seconds for Asset ID {asset_id}")
    except Exception as e:
        print(f"[red]Subscription error for chunked candles: {e}[/red]")
        logger.error(f"Subscription error for chunked candles for Asset ID {asset_id}: {e}")
        raise

    # Test subscribe_symbol_timed (aggregated candles by time interval)
    print(f"[cyan]===== Subscribing to Timed Candles for {symbol} (30s Interval) =====[/cyan]")
    logger.info(f"Subscribing to timed candles for Asset ID {asset_id} with 30-second interval...")
    try:
        subscription_timed = await api.subscribe_symbol_timed(asset_id, interval=timedelta(seconds=30))
        async with asyncio.timeout(15):  # Set a 15-second timeout
            async for data in subscription_timed:
                print("[green]Received Timed Candle:[/green]")
                print("  -----------------------------------")
                print(f"  Time: {data['time']} | Open: {data['open']:.3f} | High: {data['high']:.3f} | Low: {data['low']:.3f} | Close: {data['close']:.3f}")
                print("  -----------------------------------")
                logger.info(f"Received timed candle for Asset ID {asset_id}: {data}")
                break  # Stop after one aggregated candle
    except asyncio.TimeoutError:
        print("[yellow]No timed candles received within 15 seconds, proceeding...[/yellow]")
        logger.warning("No timed candles received within 15 seconds for Asset ID {asset_id}")
    except Exception as e:
        print(f"[red]Subscription error for timed candles: {e}[/red]")
        logger.error(f"Subscription error for timed candles for Asset ID {asset_id}: {e}")
        raise

async def select_tradable_asset(api: ExpertOptionAsync, preferred_timeframe: int = 5) -> tuple:
    """Select a tradable asset and timeframe."""
    assets = await api.filter_active_assets()
    if not assets:
        logger.error("No active assets available for trading")
        raise ValueError("No active assets available for trading")
    # Preferred assets in order: SMRTY, EURUSD, GBPUSD, USDJPY
    preferred_ids = [240, 142, 155, 159]
    for asset_id in preferred_ids:
        for asset in assets:
            if asset["id"] == asset_id and asset.get("profit", 0) > 0:
                timeframes = await api.fetch_asset_timeframes(asset_id)
                if preferred_timeframe in timeframes:
                    return asset, preferred_timeframe
                else:
                    alternative_timeframes = [60, 300, 900]
                    for tf in alternative_timeframes:
                        if tf in timeframes:
                            logger.info(f"Asset ID {asset_id} does not support timeframe {preferred_timeframe}, using {tf} instead")
                            return asset, tf
    # Fallback to highest payout asset with supported timeframe
    for asset in sorted(assets, key=lambda x: x.get("profit", 0), reverse=True):
        timeframes = await api.fetch_asset_timeframes(asset["id"])
        if preferred_timeframe in timeframes:
            return asset, preferred_timeframe
        for tf in [60, 300, 900]:
            if tf in timeframes:
                logger.info(f"Asset ID {asset['id']} does not support timeframe {preferred_timeframe}, using {tf} instead")
                return asset, tf
    logger.error("No assets support the requested or alternative timeframes")
    raise ValueError("No assets support the requested or alternative timeframes")

def format_trade_result(trade_result: dict, trade_type: str, symbol: str, amount: float) -> str:
    """Format trade result for console display."""
    result = trade_result.get("result", "unknown")
    profit = trade_result.get("profit", 0.0)
    details = trade_result.get("details", {})
    strike_rate = details.get("strike_rate", 0.0)
    exp_rate = details.get("exp_rate", 0.0)
    strike_time = details.get("strike_time", 0)
    exp_time = details.get("exp_time", 0)

    strike_time_str = datetime.utcfromtimestamp(strike_time).strftime("%Y-%m-%d %H:%M:%S") if strike_time else "N/A"
    exp_time_str = datetime.utcfromtimestamp(exp_time).strftime("%Y-%m-%d %H:%M:%S") if exp_time else "N/A"

    result_color = "green" if result == "win" else "red" if result == "loss" else "yellow"
    profit_str = f"[green]+{profit:.2f}[/green]" if profit > 0 else f"[red]{profit:.2f}[/red]"

    summary = (
        f"[bold {result_color}]{trade_type.upper()} TRADE RESULT: {result.upper()}[/bold {result_color}]\n"
        f"[cyan]Asset:[/cyan] {symbol}\n"
        f"[cyan]Amount:[/cyan] {amount:.2f}\n"
        f"[cyan]Profit/Loss:[/cyan] {profit_str}\n"
        f"[cyan]Strike Rate:[/cyan] {strike_rate:.3f}\n"
        f"[cyan]Expiration Rate:[/cyan] {exp_rate:.3f}\n"
        f"[cyan]Strike Time:[/cyan] {strike_time_str}\n"
        f"[cyan]Expiration Time:[/cyan] {exp_time_str}"
    )
    return summary

async def main():
    token = "e7789ca5335af40ac51abc31be796e95"
    api = ExpertOptionAsync(token=token, demo=True)

    total_trades = 0
    wins = 0
    losses = 0
    net_profit = 0.0

    try:
        print("[cyan]Connecting to ExpertOption...[/cyan]")
        logger.info("Connecting to ExpertOption...")
        await api.connect()
        print(f"[green]Connected successfully! Token: {api.token}[/green]")
        logger.info(f"Connected successfully! Token: {api.token}")

        # Account context
        context = await get_account_context(api)
        print(f"[yellow]Account Type: {context.upper()}[/yellow]")
        logger.info(f"Account Type: {context.upper()}")

        # Balance
        balance = await api.balance()
        print(f"[yellow]Current Balance: {balance}[/yellow]")
        logger.info(f"Current Balance: {balance}")

        # Test new functions
        await test_new_functions(api)
        await api.print_available_assets()

        # Select asset and timeframe
        selected_asset, selected_timeframe = await select_tradable_asset(api, preferred_timeframe=5)
        asset_id = selected_asset["id"]
        symbol = selected_asset["symbol"]
        profit = selected_asset.get("profit", 0)
        print(f"[blue]Selected asset: {symbol} (ID: {asset_id}, Profit: {profit}%, Timeframe: {selected_timeframe}s)[/blue]")
        logger.info(f"Selected asset: {symbol} (ID: {asset_id}, Profit: {profit}%, Timeframe: {selected_timeframe}s)")

        # Fetch candles
        print(f"[cyan]Fetching candles for {symbol} with timeframe {selected_timeframe}s...[/cyan]")
        logger.info(f"Fetching candles for Asset ID {asset_id}...")
        try:
            candles = await api.get_candles(
                asset_id=asset_id,
                period=selected_timeframe,
                offset=0,
                duration=1800
            )
            if candles.empty:
                print("[yellow]No candles retrieved, proceeding anyway...[/yellow]")
                logger.warning("No candles retrieved for Asset ID {asset_id}")
            else:
                print("[green]Candles DataFrame:[/green]")
                print(candles.head())
                logger.info(f"Candles retrieved: {len(candles)} rows for Asset ID {asset_id}")
        except Exception as e:
            print(f"[red]Failed to fetch candles: {e}[/red]")
            logger.error(f"Failed to fetch candles for Asset ID {asset_id}: {e}")

        await test_candle_functions(api, asset_id, symbol, selected_timeframe)
        await test_subscriptions(api, asset_id, symbol, selected_timeframe)

        # Check balance for real account
        if context != "demo" and (balance is None or balance < 10):
            print("[red]Cannot place trade: Real account with insufficient balance.[/red]")
            logger.error("Cannot place trade: Real account with insufficient balance.")
            return

        # Trade settings
        amount = max(4.0, selected_asset.get("min_bet", 4.0))  # Ensure amount meets min_bet
        expiration_times = [60, 120, 180]  # Multiple expiration times for flexibility

        # Buy trade
        print(f"[blue]Initiating buy trade for {symbol}...[/blue]")
        logger.info(f"Preparing buy trade for Asset ID {asset_id} ({symbol})...")
        buy_success = False
        for exp_time in expiration_times:
            try:
                await asyncio.sleep(5)  # Ensure server time synchronization
                server_time = await get_server_time(api)
                strike_time = server_time + selected_asset.get("purchase_time", 30)
                print(f"[cyan]Attempting buy with expiration: {exp_time}s...[/cyan]")
                logger.info(f"Trying buy with expiration time: {exp_time}s, strike: {strike_time}")
                buy_id, _ = await api.buy(
                    asset_id=asset_id,
                    amount=amount,
                    expiration_time=exp_time,
                    check_win=False
                )
                print(f"[green]Buy Trade Placed Successfully! ID: {buy_id}[/green]")
                logger.info(f"Trade Placed Successfully! Buy ID: {buy_id}")

                # Wait for result
                trade_result = await api.check_win(buy_id)
                total_trades += 1
                if trade_result.get("result") == "win":
                    wins += 1
                    net_profit += trade_result.get("profit", 0.0)
                else:
                    losses += 1
                    net_profit += trade_result.get("profit", 0.0)
                print(format_trade_result(trade_result, "Buy", symbol, amount))
                logger.info(f"Buy Trade Result for Asset ID {asset_id}: {trade_result}")
                buy_success = True
                break
            except Exception as e:
                print(f"[red]Buy failed with expiration {exp_time}s: {e}[/red]")
                logger.error(f"Buy failed with expiration {exp_time}s for Asset ID {asset_id}: {e}")

        if not buy_success:
            print("[red]All buy attempts failed. Try another asset or check account settings.[/red]")
            logger.error("All buy attempts failed for Asset ID {asset_id}.")
            return

        # Sell trade
        print(f"[blue]Initiating sell trade for {symbol}...[/blue]")
        logger.info(f"Preparing sell trade for Asset ID {asset_id} ({symbol})...")
        sell_success = False
        for exp_time in expiration_times:
            try:
                await asyncio.sleep(5)  # Ensure server time synchronization
                server_time = await get_server_time(api)
                strike_time = server_time + selected_asset.get("purchase_time", 30)
                print(f"[cyan]Attempting sell with expiration: {exp_time}s...[/cyan]")
                logger.info(f"Trying sell with expiration time: {exp_time}s, strike: {strike_time}")
                sell_id, _ = await api.sell(
                    asset_id=asset_id,
                    amount=amount,
                    expiration_time=exp_time,
                    check_win=False
                )
                print(f"[green]Sell Trade Placed Successfully! ID: {sell_id}[/green]")
                logger.info(f"Sell Trade Placed Successfully! Sell ID: {sell_id}")

                # Wait for result
                trade_result = await api.check_win(sell_id)
                total_trades += 1
                if trade_result.get("result") == "win":
                    wins += 1
                    net_profit += trade_result.get("profit", 0.0)
                else:
                    losses += 1
                    net_profit += trade_result.get("profit", 0.0)
                print(format_trade_result(trade_result, "Sell", symbol, amount))
                logger.info(f"Sell Trade Result for Asset ID {asset_id}: {trade_result}")
                sell_success = True
                break
            except Exception as e:
                print(f"[red]Sell failed with expiration {exp_time}s: {e}[/red]")
                logger.error(f"Sell failed with expiration {exp_time}s for Asset ID {asset_id}: {e}")

        if not sell_success:
            print("[red]All sell attempts failed. Try another asset or check account settings.[/red]")
            logger.error("All sell attempts failed for Asset ID {asset_id}.")

        # Print trade summary
        net_profit_str = f"[green]+{net_profit:.2f}[/green]" if net_profit > 0 else f"[red]{net_profit:.2f}[/red]"
        print(
            f"[yellow]Trade Summary:[/yellow]\n"
            f"[cyan]Total Trades:[/cyan] {total_trades}\n"
            f"[cyan]Wins:[/cyan] {wins}\n"
            f"[cyan]Losses:[/cyan] {losses}\n"
            f"[cyan]Net Profit:[/cyan] {net_profit_str}"
        )
        logger.info(f"Trade Summary: Total Trades: {total_trades}, Wins: {wins}, Losses: {losses}, Net Profit: {net_profit:.2f}")

    except Exception as e:
        print(f"[red]Error in test: {e}[/red]")
        logger.error(f"Test error: {e}")

    finally:
        print("[grey]Disconnecting...[/grey]")
        logger.info("Disconnecting...")
        await api.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
