import asyncio
import time
from datetime import datetime
from ExpertOptionsToolsV2.expertoption import ExpertOptionAsync
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
    # Test fetch_currencies
    print("[cyan]Fetching currencies...[/cyan]")
    currencies = await api.fetch_currencies()
    print(f"[green]Currencies: {currencies}[/green]")
    logger.info(f"Currencies: {currencies}")

    # Test fetch_countries
    print("[cyan]Fetching countries...[/cyan]")
    countries = await api.fetch_countries()
    print(f"[green]Countries: {countries[:5]} (first 5)[/green]")
    logger.info(f"Countries: {countries[:5]}")

    # Test fetch_user_deposit_sum
    print("[cyan]Fetching user deposit sum...[/cyan]")
    deposit_sum = await api.fetch_user_deposit_sum()
    print(f"[green]Deposit Sum: {deposit_sum}[/green]")
    logger.info(f"Deposit Sum: {deposit_sum}")

    # Test fetch_user_achievements
    print("[cyan]Fetching user achievements...[/cyan]")
    achievements = await api.fetch_user_achievements()
    print(f"[green]Achievements: {achievements}[/green]")
    logger.info(f"Achievements: {achievements}")

    # Test subscribe_expert_options
    print("[cyan]Subscribing to expert options...[/cyan]")
    subscription = await api.subscribe_expert_options()
    print(f"[green]Expert Subscription: {subscription}[/green]")
    logger.info(f"Expert Subscription: {subscription}")

    # Test open_trades
    print("[cyan]Fetching open trades...[/cyan]")
    open_trades = await api.open_trades(count=10)
    print(f"[green]Open Trades: {open_trades}[/green]")
    logger.info(f"Open Trades: {open_trades}")

    # Test trade_history
    print("[cyan]Fetching trade history...[/cyan]")
    trade_history = await api.trade_history(count=10)
    print(f"[green]Trade History: {trade_history}[/green]")
    logger.info(f"Trade History: {trade_history}")

async def select_tradable_asset(api: ExpertOptionAsync, preferred_timeframe: int = 5) -> dict:
    assets = await api.filter_active_assets()
    if not assets:
        logger.error("No active assets available for trading")
        raise ValueError("No active assets available for trading")
    # Preferred assets in order: SMRTY, EURUSD, GBPUSD, USDJPY
    preferred_ids = [240, 142, 155, 159]
    for asset_id in preferred_ids:
        for asset in assets:
            if asset["id"] == asset_id and asset.get("profit", 0) > 0:
                # Check if the asset supports the preferred timeframe
                timeframes = await api.fetch_asset_timeframes(asset_id)
                if preferred_timeframe in timeframes:
                    return asset, preferred_timeframe
                else:
                    # Try alternative timeframes
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

    # Convert timestamps to readable format
    strike_time_str = datetime.utcfromtimestamp(strike_time).strftime("%Y-%m-%d %H:%M:%S") if strike_time else "N/A"
    exp_time_str = datetime.utcfromtimestamp(exp_time).strftime("%Y-%m-%d %H:%M:%S") if exp_time else "N/A"

    # Color based on result
    result_color = "green" if result == "win" else "red" if result == "loss" else "yellow"
    profit_str = f"[green]+{profit:.2f}[/green]" if profit > 0 else f"[red]{profit:.2f}[/red]"

    # Summary
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
    # Replace with your valid token
    token = "Add_Your_Token_Here"
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

        # List assets and test new functions
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
        candles = await api.get_candles(
            asset_id=asset_id,
            period=selected_timeframe,
            offset=0,
            duration=1800
        )
        if hasattr(candles, "empty") and candles.empty:
            print("[yellow]No candles retrieved, proceeding anyway...[/yellow]")
            logger.warning("No candles retrieved, proceeding anyway...")
        else:
            print("[green]Candles DataFrame:[/green]")
            print(candles)
            logger.info(f"Candles retrieved: {len(candles)} rows")

        # Check balance for real account
        if context != "demo" and (balance is None or balance < 10):
            print("[red]Cannot place trade: Real account with insufficient balance.[/red]")
            logger.error("Cannot place trade: Real account with insufficient balance.")
            return

        # Trade settings
        amount = 4.0
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
                logger.info(f"Buy Trade Result: {trade_result}")
                buy_success = True
                break
            except Exception as e:
                print(f"[red]Buy failed with expiration {exp_time}s: {e}[/red]")
                logger.error(f"Buy failed with expiration {exp_time}s: {e}")

        if not buy_success:
            print("[red]All buy attempts failed. Try another asset or check account settings.[/red]")
            logger.error("All buy attempts failed.")
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
                logger.info(f"Sell Trade Result: {trade_result}")
                sell_success = True
                break
            except Exception as e:
                print(f"[red]Sell failed with expiration {exp_time}s: {e}[/red]")
                logger.error(f"Sell failed with expiration {exp_time}s: {e}")

        if not sell_success:
            print("[red]All sell attempts failed. Try another asset or check account settings.[/red]")
            logger.error("All sell attempts failed.")

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
