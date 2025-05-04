from .asyncronous import ExpertOptionAsync
from ExpertOptionsToolsV2.validator import Validator
from ExpertOptionsToolsV2.constants import DEFAULT_SERVER
from datetime import timedelta
import asyncio
import json

class SyncSubscription:
    def __init__(self, subscription):
        self.subscription = subscription
        
    def __iter__(self):
        return self
        
    def __next__(self):
        return json.loads(next(self.subscription))        

class ExpertOption:
    def __init__(self, token: str, demo: bool = True, url: str = DEFAULT_SERVER):
        """
        Initialize synchronous ExpertOption client.

        Args:
            token (str): Authentication token.
            demo (bool): True for demo account, False for real account.
            url (str): WebSocket server URL.
        """
        self.loop = asyncio.new_event_loop()
        self._client = ExpertOptionAsync(token, demo, url)
    
    def __del__(self):
        self.loop.close()

    def buy(self, asset: str, amount: float, time: int, check_win: bool = False) -> tuple[str, dict]:
        """
        Places a buy (call) order for the specified asset.
        """
        return self.loop.run_until_complete(self._client.buy(asset, amount, time, check_win))

    def sell(self, asset: str, amount: float, time: int, check_win: bool = False) -> tuple[str, dict]:
        """
        Places a sell (put) order for the specified asset.
        """
        return self.loop.run_until_complete(self._client.sell(asset, amount, time, check_win))

    def check_win(self, id: str) -> dict:
        """
        Checks the result of a specific trade.
        """
        return self.loop.run_until_complete(self._client.check_win(id))

    def get_candles(self, asset: str, period: int, offset: int) -> list[dict]:
        """
        Retrieves historical candle data for an asset.
        """
        return self.loop.run_until_complete(self._client.get_candles(asset, period, offset))

    def balance(self) -> float:
        """
        Retrieves current account balance.
        """
        return self.loop.run_until_complete(self._client.balance())

    def opened_deals(self) -> list[dict]:
        """
        Returns a list of all open deals.
        """
        return self.loop.run_until_complete(self._client.opened_deals())

    def closed_deals(self) -> list[dict]:
        """
        Returns a list of all closed deals.
        """
        return self.loop.run_until_complete(self._client.closed_deals())

    def clear_closed_deals(self) -> None:
        """
        Removes all closed deals from memory.
        """
        self.loop.run_until_complete(self._client.clear_closed_deals())

    def payout(self, asset: None | str | list[str] = None) -> dict | list[int] | int:
        """
        Retrieves current payout percentages for assets.
        """
        return self.loop.run_until_complete(self._client.payout(asset))

    def history(self, asset: str, period: int) -> list[dict]:
        """
        Returns historical data for the specified asset.
        """
        return self.loop.run_until_complete(self._client.history(asset, period))

    def subscribe_symbol(self, asset: str) -> SyncSubscription:
        """
        Creates a real-time data subscription for an asset.
        """
        return SyncSubscription(self.loop.run_until_complete(self._client._subscribe_symbol_inner(asset)))

    def subscribe_symbol_chunked(self, asset: str, chunk_size: int) -> SyncSubscription:
        """
        Creates a chunked real-time data subscription for an asset.
        """
        return SyncSubscription(self.loop.run_until_complete(self._client._subscribe_symbol_chunked_inner(asset, chunk_size)))

    def subscribe_symbol_timed(self, asset: str, time: timedelta) -> SyncSubscription:
        """
        Creates a timed real-time data subscription for an asset.
        """
        return SyncSubscription(self.loop.run_until_complete(self._client._subscribe_symbol_timed_inner(asset, time)))

    def send_raw_message(self, message: str) -> None:
        """
        Sends a raw WebSocket message without waiting for a response.
        """
        self.loop.run_until_complete(self._client.send_raw_message(message))

    def create_raw_order(self, message: str, validator: Validator) -> str:
        """
        Sends a raw WebSocket message and waits for a validated response.
        """
        return self.loop.run_until_complete(self._client.create_raw_order(message, validator))

    def create_raw_iterator(self, message: str, validator: Validator) -> SyncSubscription:
        """
        Creates a synchronous iterator that yields validated WebSocket messages.
        """
        return SyncSubscription(self.loop.run_until_complete(self._client.create_raw_iterator(message, validator)))

    def get_server_time(self) -> int:
        """
        Retrieves the current server time as a UNIX timestamp.
        """
        return self.loop.run_until_complete(self._client.get_server_time())
