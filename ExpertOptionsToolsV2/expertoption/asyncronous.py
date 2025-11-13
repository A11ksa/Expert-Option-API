from ExpertOptionsToolsV2.validator import Validator
from ExpertOptionsToolsV2.tracing import Logger, LogBuilder
from ExpertOptionsToolsV2.constants import get_asset_id, DEFAULT_SERVER
from ExpertOptionsToolsV2.constants import *
from datetime import timedelta, datetime
from typing import Optional
import asyncio
import asyncio.locks
import websockets
import json
import time
import ssl
from collections import defaultdict, deque
from uuid import uuid4
import pandas as pd

class AsyncSubscription:
    def __init__(self, subscription):
        """Asynchronous Iterator over JSON objects"""
        self.subscription = subscription

    def __aiter__(self):
        return self

    async def __anext__(self):
        """Return the next item from the subscription without JSON parsing."""
        return await anext(self.subscription)

class WebSocketClient:
    def __init__(self, token, logger, url):
        self.token = token
        self.logger = logger
        self.url = url
        self.ws = None
        self.connected = False
        self.pending_responses = defaultdict(asyncio.Future)
        self.recv_lock = asyncio.Lock()
        self.receive_task = None
        self.ping_task = None
        self.receive_loop_running = False
        self.profile_data = None
        self.assets_data = None
        self.timeframes_data = None
        self.currencies_data = None
        self.countries_data = None
        self.traders_choice = {}
        self.unhandled_messages = []
        self.candle_queue = deque(maxlen=1000)
        self.history_candle_queue = deque(maxlen=1000)

    async def connect(self):
        """Connect to the WebSocket server."""
        try:
            self.logger.info(f"Connecting to {self.url}...")
            headers = {
                "Origin": "https://app.expertoption.com",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Sec-WebSocket-Extensions": "permessage-deflate; client_max_window_bits"
            }
            ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            self.ws = await websockets.connect(self.url, ssl=ssl_context, extra_headers=headers)
            self.connected = True
            self.logger.info("WebSocket connected successfully")
            self.receive_task = asyncio.create_task(self._receive_loop())
            self.ping_task = asyncio.create_task(self._send_ping())
        except Exception as e:
            self.logger.error(f"WebSocket connection failed: {e}")
            self.connected = False
            raise ConnectionError(f"Connection failed: {e}")

    async def disconnect(self):
        """Disconnect from the WebSocket server."""
        if self.ping_task:
            self.ping_task.cancel()
        if self.receive_task:
            self.receive_task.cancel()
        if self.ws:
            try:
                await self.ws.close()
                self.logger.info("WebSocket connection closed")
            except Exception as e:
                self.logger.error(f"Error closing WebSocket: {e}")
            finally:
                self.connected = False

    async def send(self, message):
        """Send a message to the WebSocket server."""
        if not self.connected:
            self.logger.warning("WebSocket not connected. Reconnecting...")
            await self.connect()
        self.logger.debug(f"Sending message: {message}")
        try:
            await self.ws.send(message)
        except websockets.exceptions.ConnectionClosed as e:
            self.logger.warning(f"Connection closed during send: {e}. Reconnecting...")
            await self.connect()
            await self.ws.send(message)

    async def recv(self, key):
        """Receive a response for the given key."""
        async with self.recv_lock:
            if key not in self.pending_responses or self.pending_responses[key].done():
                self.pending_responses[key] = asyncio.Future()
            self.logger.debug(f"Waiting for response with key: {key}")
            response = await self.pending_responses[key]
            self.logger.debug(f"Raw response for key {key}: {response}")
            if isinstance(response, str):
                try:
                    response = json.loads(response)
                except json.JSONDecodeError as e:
                    self.logger.error(f"Failed to parse JSON: {e}, response: {response}")
                    raise ValueError(f"Invalid JSON response: {response}")
            if not isinstance(response, dict):
                self.logger.error(f"Unexpected response type: {type(response)}")
                raise ValueError(f"Expected dict, got {type(response)}")
            self.logger.debug(f"Received response for key: {key}")
            return response

    async def _send_ping(self):
        """Send periodic ping messages to keep the connection alive."""
        while self.connected:
            await self.send(json.dumps({
                "action": "ping",
                "v": 23,
                "message": {}
            }))
            self.logger.debug("Sent ping")
            await asyncio.sleep(30)

    async def _receive_loop(self):
        """Handle incoming WebSocket messages."""
        try:
            while True:
                # Clean up old futures
                expired_keys = [k for k, fut in self.pending_responses.items() if fut.done()]
                for k in expired_keys:
                    del self.pending_responses[k]
                # Trim unhandled_messages
                if len(self.unhandled_messages) > 2000:
                    self.unhandled_messages = self.unhandled_messages[-1000:]
                    self.logger.info("Cleaned old unhandled messages")
                async for message in self.ws:
                    try:
                        data = json.loads(message)
                        if not isinstance(data, dict):
                            self.logger.error(f"Parsed message is not a dict: {data}")
                            continue
                        action = data.get("action")
                        ns = data.get("ns")
                        key = str(ns) if ns else action

                        # Log trade-related messages for debugging
                        if action in ["openTradeSuccessful", "closeTradeSuccessful", "tradesStatus", "optStatus", "optionFinished", "expertOption", "openTrades", "tradeHistory"]:
                            self.logger.debug(f"Received trade-related message: {data}")

                        # Handle error messages
                        if action == "error":
                            self.logger.error(f"Received error: {data.get('message')}")
                            if ns in self.pending_responses:
                                self.pending_responses[ns].set_exception(ValueError(data.get("message")))
                            continue

                        # Route known actions to futures
                        if action == "buyOption" and ns in self.pending_responses:
                            self.pending_responses[ns].set_result(data)
                            continue
                        if action == "token":
                            new_token = data.get("message", {}).get("token")
                            if new_token and new_token != self.token:
                                self.logger.info(f"Updating token to {new_token}")
                                self.token = new_token
                            continue
                        if action == "multipleAction":
                            for sub in data.get("message", {}).get("actions", []):
                                sub_key = str(sub.get("ns")) if sub.get("ns") else sub.get("action")
                                if sub_key in self.pending_responses and not self.pending_responses[sub_key].done():
                                    self.pending_responses[sub_key].set_result({
                                        "action": sub.get("action"),
                                        "message": sub.get("message", {})
                                    })
                            continue

                        if action == "profile":
                            self.profile_data = data
                            if ns in self.pending_responses and not self.pending_responses[ns].done():
                                self.pending_responses[ns].set_result(data)
                            continue

                        if action == "assets":
                            self.assets_data = data
                            if ns in self.pending_responses and not self.pending_responses[ns].done():
                                self.pending_responses[ns].set_result(data)
                            continue

                        if action == "getCandlesTimeframes":
                            self.timeframes_data = data
                            if ns in self.pending_responses and not self.pending_responses[ns].done():
                                self.pending_responses[ns].set_result(data)
                            continue

                        if action == "getCurrency":
                            self.currencies_data = data
                            if ns in self.pending_responses and not self.pending_responses[ns].done():
                                self.pending_responses[ns].set_result(data)
                            continue

                        if action == "getCountries":
                            self.countries_data = data
                            if ns in self.pending_responses and not self.pending_responses[ns].done():
                                self.pending_responses[ns].set_result(data)
                            continue

                        if action == "candles":
                            self.candle_queue.append(data)
                            if key in self.pending_responses and not self.pending_responses[key].done():
                                self.pending_responses[key].set_result(data)
                            continue

                        if action == "assetHistoryCandles":
                            self.history_candle_queue.append(data)
                            if key in self.pending_responses and not self.pending_responses[key].done():
                                self.pending_responses[key].set_result(data)
                            continue

                        if action == "tradesStatus":
                            self.unhandled_messages.append(data)
                            for trade in data.get("message", {}).get("trades", []):
                                tid = str(trade.get("id"))
                                if tid in self.pending_responses and not self.pending_responses[tid].done():
                                    self.pending_responses[tid].set_result(data)
                            continue

                        if action == "tradersChoice":
                            asset_id = data.get("message", {}).get("assets", [{}])[0].get("asset_id", 0)
                            self.traders_choice[asset_id] = data.get("message", {}).get("assets", [{}])[0]
                            continue

                        if action == "expertOption":
                            self.unhandled_messages.append(data)
                            if ns in self.pending_responses and not self.pending_responses[ns].done():
                                self.pending_responses[ns].set_result(data)
                            continue

                        if action == "userGroup":
                            if ns in self.pending_responses and not self.pending_responses[ns].done():
                                self.pending_responses[ns].set_result(data)
                            continue

                        if action == "openTrades":
                            self.unhandled_messages.append(data)
                            if ns in self.pending_responses and not self.pending_responses[ns].done():
                                self.pending_responses[ns].set_result(data)
                            continue

                        if action == "tradeHistory":
                            self.unhandled_messages.append(data)
                            if ns in self.pending_responses and not self.pending_responses[ns].done():
                                self.pending_responses[ns].set_result(data)
                            continue

                        if action == "userAchievements":
                            if ns in self.pending_responses and not self.pending_responses[ns].done():
                                self.pending_responses[ns].set_result(data)
                            continue

                        if action == "userDepositSum":
                            if ns in self.pending_responses and not self.pending_responses[ns].done():
                                self.pending_responses[ns].set_result(data)
                            continue

                        if action == "expertSubscribe":
                            if ns in self.pending_responses and not self.pending_responses[ns].done():
                                self.pending_responses[ns].set_result(data)
                            continue

                        # Handle optStatus and optionFinished
                        if action in ["optStatus", "optionFinished"]:
                            self.unhandled_messages.append(data)
                            for option in data.get("message", {}).get("options", []):
                                tid = str(option.get("id"))
                                if tid in self.pending_responses and not self.pending_responses[tid].done():
                                    self.pending_responses[tid].set_result(data)
                            continue

                        # Default fallback
                        if key in self.pending_responses and not self.pending_responses[key].done():
                            self.pending_responses[key].set_result(data)
                        else:
                            self.unhandled_messages.append(data)
                    except Exception as e:
                        self.logger.error(f"Error handling message: {e}, raw: {message}")
        except websockets.exceptions.ConnectionClosed as e:
            self.connected = False
        except Exception as e:
            self.connected = False

class ExpertOptionAsync:
    def __init__(self, token: str, demo: bool = True, url: str = DEFAULT_SERVER):
        self.logger = Logger()
        self.client = WebSocketClient(token, self.logger, self.url)
        self.url = url
        self.token = token
        self.demo = demo
        self.uid = uid
        self.profile = None
        self.assets_data = []
        self.active_subscriptions = set()
        self.candle_cache = {}  # Cache for candles: {asset_id: {timeframe: {"candles": [], "expTimes": []}}}

    async def connect(self) -> None:
        """Connect to the ExpertOption API."""
        await self.client.connect()
        self.token = self.client.token
        await self.send_multiple_action()
        await asyncio.sleep(0.5)
        await self.send_ping()
        await self.set_mode()
        await asyncio.sleep(0.5)
        await self.fetch_profile()
        await self.fetch_assets()

    async def disconnect(self) -> None:
        """Disconnect from the ExpertOption API."""
        await self.client.disconnect()

    async def send_ping(self) -> None:
        """Send a ping message."""
        await self.client.send(json.dumps({
            "action": "ping",
            "v": 23,
            "message": {}
        }))

    async def set_mode(self) -> None:
        """Set demo or real mode."""
        mode = 1 if self.demo else 0
        ns = str(uuid4())
        await self.client.send(json.dumps({
            "action": "setContext",
            "message": {"is_demo": mode},
            "ns": ns,
            "token": self.token
        }))

    async def send_multiple_action(self):
        """Send multiple initialization actions."""
        ns = str(uuid4())
        payload = {
            "action": "multipleAction",
            "message": {
                "actions": [
                    {"action": "userGroup",   "ns": str(uuid4()), "token": self.token},
                    {"action": "profile",     "ns": str(uuid4()), "token": self.token},
                    {"action": "assets",      "ns": str(uuid4()), "token": self.token},
                    {"action": "getCurrency", "ns": str(uuid4()), "token": self.token},
                    {"action": "getCountries","ns": str(uuid4()), "token": self.token},
                    {
                        "action": "environment",
                        "message": {
                            "supportedFeatures": [
                                "achievements","trade_result_share","tournaments","referral","twofa",
                                "inventory","deposit_withdrawal_error_handling","report_a_problem_form",
                                "ftt_trade","stocks_trade"
                            ],
                            "supportedAbTests": [
                                "tournament_glow","floating_exp_time","tutorial","tutorial_account_type",
                                "tutorial_account_type_reg","hide_education_section","in_app_update_android_2",
                                "auto_consent_reg","btn_finances_to_register","battles_4th_5th_place_rewards",
                                "show_achievements_bottom_sheet","kyc_webview","promo_story_priority",
                                "force_lang_in_app","one_click_deposit"
                            ],
                            "supportedInventoryItems": [
                                "riskless_deal","profit","eopoints","tournaments_prize_x3","mystery_box",
                                "special_deposit_bonus","cashback_offer"
                            ]
                        },
                        "ns": str(uuid4()), "token": self.token
                    },
                    {"action": "defaultSubscribeCandles", "message": {"timeframes": [0, 5, 60]}, "ns": str(uuid4()), "token": self.token},
                    {"action": "setTimeZone",            "message": {"timeZone":180},       "ns": str(uuid4()), "token": self.token},
                    {"action": "getCandlesTimeframes",   "ns": str(uuid4()), "token": self.token}
                ]
            },
            "token": self.token,
            "ns": ns
        }
        await self.client.send(json.dumps(payload))
        self.logger.info("Sent multipleAction request")
        await asyncio.sleep(0.5)

    async def fetch_profile(self) -> dict:
        """Fetch user profile data."""
        ns = str(uuid4())
        await self.client.send(json.dumps({"action":"profile","ns":ns,"token":self.token}))
        response = await self.client.recv(ns)
        self.profile = response.get("message", {}).get("profile", {})
        self.client.profile_data = response
        return self.profile

    async def fetch_assets(self) -> list[dict]:
        """Fetch list of available assets."""
        if self.client.assets_data and self.assets_data:
            return self.assets_data
        ns = str(uuid4())
        await self.client.send(json.dumps({"action":"assets","ns":ns,"token":self.token}))
        response = await self.client.recv(ns)
        self.assets_data = response.get("message", {}).get("assets", [])
        self.client.assets_data = response
        return self.assets_data

    async def fetch_timeframes(self) -> list[int]:
        """Fetch available candle timeframes."""
        default_timeframes = [5, 60, 300, 900, 1800, 3600, 14400, 86400]
        if self.client.timeframes_data:
            timeframes = self.client.timeframes_data.get("message", {}).get("candlesTimeframes", [])
            if timeframes:
                self.logger.info(f"Fetched timeframes from cache: {timeframes}")
                return timeframes
            self.logger.warning("Cached timeframes empty, fetching from server")
        ns = str(uuid4())
        await self.client.send(json.dumps({"action":"getCandlesTimeframes","ns":ns,"token":self.token}))
        try:
            response = await asyncio.wait_for(self.client.recv(ns), timeout=5.0)
            self.client.timeframes_data = response
            timeframes = response.get("message", {}).get("candlesTimeframes", [])
            if not timeframes:
                self.logger.warning("Server returned empty timeframes, using default timeframes")
                return default_timeframes
            self.logger.info(f"Fetched timeframes: {timeframes}")
            return timeframes
        except asyncio.TimeoutError:
            self.logger.warning("Timeout waiting for getCandlesTimeframes response, using default timeframes")
            return default_timeframes
        except Exception as e:
            self.logger.error(f"Failed to fetch timeframes: {e}, using default timeframes")
            return default_timeframes

    async def fetch_asset_timeframes(self, asset_id: int) -> list[int]:
        """Fetch available timeframes for a specific asset."""
        timeframes = await self.fetch_timeframes()
        if not timeframes:
            self.logger.warning(f"No timeframes available for asset ID {asset_id}, using default timeframes")
            return [5, 60, 300, 900, 1800, 3600, 14400, 86400]
        return timeframes

    async def fetch_user_groups(self) -> list[dict]:
        """Fetch user group data."""
        ns = str(uuid4())
        await self.client.send(json.dumps({"action":"userGroup","ns":ns,"token":self.token}))
        response = await self.client.recv(ns)
        return response.get("message", {}).get("userGroups", [])

    async def fetch_expert_options(self, asset_id: int = None) -> list[dict]:
        """Fetch expert options data for a specific asset or all assets."""
        ns = str(uuid4())
        payload = {"action":"expertOption","ns":ns,"token":self.token}
        if asset_id is not None:
            payload["message"] = {"assetId": asset_id}
        await self.client.send(json.dumps(payload))
        response = await self.client.recv(ns)
        options = response.get("message", {}).get("options", [])
        if asset_id is not None:
            options = [opt for opt in options if opt.get("asset_id") == asset_id]
        return options

    async def fetch_currencies(self) -> list[dict]:
        """Fetch available currencies."""
        if self.client.currencies_data:
            return self.client.currencies_data.get("message", {}).get("currency", [])
        ns = str(uuid4())
        await self.client.send(json.dumps({"action":"getCurrency","ns":ns,"token":self.token}))
        response = await self.client.recv(ns)
        self.client.currencies_data = response
        return response.get("message", {}).get("currency", [])

    async def fetch_countries(self) -> list[dict]:
        """Fetch available countries."""
        if self.client.countries_data:
            return self.client.countries_data.get("message", {}).get("countries", [])
        ns = str(uuid4())
        await self.client.send(json.dumps({"action":"getCountries","ns":ns,"token":self.token}))
        response = await self.client.recv(ns)
        self.client.countries_data = response
        return response.get("message", {}).get("countries", [])

    async def fetch_user_deposit_sum(self) -> dict:
        """Fetch total deposit sum for the user."""
        ns = str(uuid4())
        await self.client.send(json.dumps({"action":"userDepositSum","ns":ns,"token":self.token}))
        response = await self.client.recv(ns)
        return response.get("message", {})

    async def fetch_user_achievements(self) -> list[dict]:
        """Fetch user achievements."""
        ns = str(uuid4())
        await self.client.send(json.dumps({"action":"userAchievements","ns":ns,"token":self.token}))
        response = await self.client.recv(ns)
        return response.get("message", {}).get("achievements", [])

    async def subscribe_expert_options(self) -> dict:
        """Subscribe to expert options signals."""
        ns = str(uuid4())
        await self.client.send(json.dumps({
            "action": "expertSubscribe",
            "message": {"is_demo": 1, "subscription_type": "signals"},
            "ns": ns,
            "token": self.token
        }))
        response = await self.client.recv(ns)
        return response.get("message", {})

    async def unsubscribe(self, asset_id: int) -> bool:
        """Unsubscribe from candles for a specific asset."""
        if asset_id not in self.active_subscriptions:
            self.logger.info(f"No active subscription for asset ID {asset_id}")
            return True

        ns = str(uuid4())
        payload = {
            "action": "unsubscribeCandles",
            "message": {"assets": [{"id": asset_id}]},
            "ns": ns,
            "token": self.token
        }
        try:
            await self.client.send(json.dumps(payload))
            self.logger.info(f"Sent unsubscribe request for asset ID {asset_id}")
            response = await asyncio.wait_for(self.client.recv(ns), timeout=5.0)
            self.active_subscriptions.remove(asset_id)
            self.logger.info(f"Unsubscribed from asset ID {asset_id}: {response}")
            return True
        except asyncio.TimeoutError:
            self.logger.warning(f"Timeout waiting for unsubscribe response for asset ID {asset_id}")
            self.active_subscriptions.remove(asset_id)  # Remove anyway to prevent conflicts
            return False
        except Exception as e:
            self.logger.error(f"Failed to unsubscribe from asset ID {asset_id}: {e}")
            return False

    async def filter_active_assets(self) -> list[dict]:
        """Return only active assets with positive profit."""
        assets = await self.fetch_assets()
        return [a for a in assets if a.get("is_active") == 1 and a.get("profit", 0) > 0]

    async def print_available_assets(self) -> None:
        """Print all available assets with IDs and symbols."""
        assets = await self.fetch_assets()
        print("Available Assets:")
        print("=================")
        for asset in assets:
            print(f"ID: {asset.get('id')}, Symbol: {asset.get('symbol')}, Active: {asset.get('is_active')}, Profit: {asset.get('profit')}%")
        print("=================")

    async def select_highest_payout_asset(self) -> dict | None:
        """Select asset with highest payout."""
        active = await self.filter_active_assets()
        if not active:
            return None
        return max(active, key=lambda x: x.get("profit", 0))

    async def check_asset_availability(self, asset_id: int) -> bool:
        """Verify if an asset is tradable."""
        assets = await self.fetch_assets()
        asset = next((a for a in assets if a['id'] == asset_id), None)
        if not asset:
            self.logger.error(f"Asset ID {asset_id} not found")
            return False
        if not asset.get("is_active"):
            self.logger.warning(f"Asset ID {asset_id} is not active")
            return False
        if asset.get("profit", 0) <= 0:
            self.logger.warning(f"Asset ID {asset_id} has no positive profit")
            return False
        self.logger.info(f"Asset ID {asset_id} is available for trading")
        return True

    async def verify_asset_subscription(self, asset_id: int, timeframe: int) -> bool:
        """Verify if an asset supports the given timeframe and is available for subscription."""
        if not await self.check_asset_availability(asset_id):
            self.logger.error(f"Asset ID {asset_id} is not available for subscription")
            return False
        timeframes = await self.fetch_asset_timeframes(asset_id)
        if timeframe not in timeframes:
            self.logger.warning(f"Timeframe {timeframe} is not supported for asset ID {asset_id}. Available timeframes: {timeframes}")
            return False
        self.logger.info(f"Asset ID {asset_id} supports timeframe {timeframe}")
        return True

    async def buy(self, asset_id: int, amount: float, expiration_time: int, strike_time: int = None, check_win: bool = False) -> tuple[str, dict]:
        """
        Place a CALL trade:
        1. Send buyOption
        2. Await its ACK (empty message)
        3. Wait for buySuccessful → extract deal_id
        4. Optionally wait for tradesStatus if check_win=True
        """
        # Reconnect if not connected
        if not self.client.connected:
            self.logger.warning("WebSocket not connected. Reconnecting...")
            await self.client.connect()

        # Validate asset
        if not await self.check_asset_availability(asset_id):
            self.logger.error(f"Asset ID {asset_id} is not available for trading")
            raise ValueError(f"Asset ID {asset_id} is not available for trading")

        # Validate minimum bet amount
        assets = await self.fetch_assets()
        asset = next((a for a in assets if a['id'] == asset_id), None)
        if not asset:
            self.logger.error(f"Asset ID {asset_id} not found in assets")
            raise ValueError(f"Asset ID {asset_id} not found")

        min_bet = asset.get('min_bet', 4.0)
        if amount < min_bet:
            self.logger.error(f"Amount {amount} is below minimum bet amount {min_bet} for asset ID {asset_id}")
            raise ValueError(f"Amount {amount} is below minimum bet amount {min_bet}")

        # Timing params
        expiration_step = asset.get('expiration_step', 5)
        purchase_time = asset.get('purchase_time', 30)
        server_time = await self.get_server_time()
        strike = strike_time or (server_time + purchase_time)

        # Build payload
        ns = str(uuid4())
        expiration_shift = max(2, (expiration_time + expiration_step - 1) // expiration_step)
        payload = {
            "action": "buyOption",
            "ns": ns,
            "token": self.token,
            "message": {
                "type": "call",
                "amount": float(amount),
                "assetid": asset_id,
                "strike_time": strike,
                "is_demo": 1 if self.demo else 0,
                "expiration_shift": expiration_shift,
                "ratePosition": 0
            }
        }
        await self.client.send(json.dumps(payload))
        self.logger.debug(f"Sent buyOption: {payload}")

        # Wait buyOption response
        try:
            buy_resp = await asyncio.wait_for(self.client.recv(ns), timeout=5.0)
            self.logger.info(f"BuyOption response received: {buy_resp}")
            # Check for error in initial response
            if buy_resp.get("action") == "error":
                error_msg = buy_resp.get("message", "Unknown error")
                self.logger.error(f"Initial buyOption error: {error_msg}")
                if error_msg == "ERROR_EXPECT_REAL_CONTEXT" and self.demo:
                    self.logger.error("Trading requires a real account, but demo mode is active")
                    raise ValueError("Trading requires a real account. Please switch to real mode or use a different asset.")
                raise ValueError(f"Initial buyOption failed: {error_msg}")
        except asyncio.TimeoutError:
            self.logger.error(f"Timeout waiting for buyOption response for asset ID {asset_id}")
            raise TimeoutError("No response received for buyOption")
        except ValueError as e:
            if "ERROR_EXPECT_REAL_CONTEXT" in str(e):
                self.logger.error("Trading requires a real account, but demo mode is active")
                raise ValueError("Trading requires a real account. Please switch to real mode or use a different asset.")
            raise
        except Exception as e:
            self.logger.error(f"Unexpected error in buyOption: {e}, response: {buy_resp if 'buy_resp' in locals() else 'None'}")
            raise ValueError(f"Unexpected error in buyOption: {e}")

        # Extract deal_id from buySuccessful
        deal_id = None
        start = time.time()
        while time.time() - start < 10.0:
            for msg in list(self.client.unhandled_messages):
                if msg.get("action") == "buySuccessful":
                    opt = msg["message"].get("option", {})
                    deal_id = opt.get("id")
                    self.client.unhandled_messages.remove(msg)
                    self.logger.info(f"Extracted deal_id: {deal_id}")
                    break
                elif msg.get("action") == "error":
                    error_msg = msg.get("message", "Unknown error")
                    self.logger.error(f"Error in buyOption confirmation: {error_msg}")
                    if error_msg == "ERROR_EXPECT_REAL_CONTEXT":
                        self.logger.error("Trading requires a real account, but demo mode is active")
                        raise ValueError("Trading requires a real account. Please switch to real mode or use a different asset.")
                    raise ValueError(f"Buy confirmation failed: {error_msg}")
            if deal_id is not None:
                break
            await asyncio.sleep(0.1)

        if deal_id is None:
            self.logger.error(f"No buySuccessful message received for asset ID {asset_id}. Unhandled messages: {self.client.unhandled_messages}")
            raise TimeoutError("No buySuccessful message received with deal_id")

        # Optionally wait for win/loss
        if check_win:
            result = await self.check_win(str(deal_id))
            return str(deal_id), result

        return str(deal_id), {}

    async def sell(self, asset_id: int, amount: float, expiration_time: int, strike_time: int = None, check_win: bool = False) -> tuple[str, dict]:
        """
        Place a PUT trade:
        1. Send buyOption
        2. Await its ACK (empty message)
        3. Wait for buySuccessful → extract deal_id
        4. Optionally wait for tradesStatus if check_win=True
        """
        # Reconnect if not connected
        if not self.client.connected:
            self.logger.warning("WebSocket not connected. Reconnecting...")
            await self.client.connect()

        # Validate asset
        if not await self.check_asset_availability(asset_id):
            self.logger.error(f"Asset ID {asset_id} is not available for trading")
            raise ValueError(f"Asset ID {asset_id} is not available for trading")

        # Validate minimum bet amount
        assets = await self.fetch_assets()
        asset = next((a for a in assets if a['id'] == asset_id), None)
        if not asset:
            self.logger.error(f"Asset ID {asset_id} not found in assets")
            raise ValueError(f"Asset ID {asset_id} not found")

        min_bet = asset.get('min_bet', 4.0)
        if amount < min_bet:
            self.logger.error(f"Amount {amount} is below minimum bet amount {min_bet} for asset ID {asset_id}")
            raise ValueError(f"Amount {amount} is below minimum bet amount {min_bet}")

        # Timing params
        expiration_step = asset.get('expiration_step', 5)
        purchase_time = asset.get('purchase_time', 30)
        server_time = await self.get_server_time()
        strike = strike_time or (server_time + purchase_time)

        # Build payload
        ns = str(uuid4())
        expiration_shift = max(2, (expiration_time + expiration_step - 1) // expiration_step)
        payload = {
            "action": "buyOption",
            "ns": ns,
            "token": self.token,
            "message": {
                "type": "put",
                "amount": float(amount),
                "assetid": asset_id,
                "strike_time": strike,
                "is_demo": 1 if self.demo else 0,
                "expiration_shift": expiration_shift,
                "ratePosition": 0
            }
        }
        await self.client.send(json.dumps(payload))
        self.logger.debug(f"Sent buyOption: {payload}")

        # Wait buyOption response
        try:
            buy_resp = await asyncio.wait_for(self.client.recv(ns), timeout=5.0)
            self.logger.info(f"BuyOption response received: {buy_resp}")
            # Check for error in initial response
            if buy_resp.get("action") == "error":
                error_msg = buy_resp.get("message", "Unknown error")
                self.logger.error(f"Initial buyOption error: {error_msg}")
                if error_msg == "ERROR_EXPECT_REAL_CONTEXT" and self.demo:
                    self.logger.error("Trading requires a real account, but demo mode is active")
                    raise ValueError("Trading requires a real account. Please switch to real mode or use a different asset.")
                raise ValueError(f"Initial buyOption failed: {error_msg}")
        except asyncio.TimeoutError:
            self.logger.error(f"Timeout waiting for buyOption response for asset ID {asset_id}")
            raise TimeoutError("No response received for buyOption")
        except ValueError as e:
            if "ERROR_EXPECT_REAL_CONTEXT" in str(e):
                self.logger.error("Trading requires a real account, but demo mode is active")
                raise ValueError("Trading requires a real account. Please switch to real mode or use a different asset.")
            raise
        except Exception as e:
            self.logger.error(f"Unexpected error in buyOption: {e}, response: {buy_resp if 'buy_resp' in locals() else 'None'}")
            raise ValueError(f"Unexpected error in buyOption: {e}")

        # Extract deal_id from buySuccessful
        deal_id = None
        start = time.time()
        while time.time() - start < 10.0:
            for msg in list(self.client.unhandled_messages):
                if msg.get("action") == "buySuccessful":
                    opt = msg["message"].get("option", {})
                    deal_id = opt.get("id")
                    self.client.unhandled_messages.remove(msg)
                    self.logger.info(f"Extracted deal_id: {deal_id}")
                    break
                elif msg.get("action") == "error":
                    error_msg = msg.get("message", "Unknown error")
                    self.logger.error(f"Error in buyOption confirmation: {error_msg}")
                    if error_msg == "ERROR_EXPECT_REAL_CONTEXT":
                        self.logger.error("Trading requires a real account, but demo mode is active")
                        raise ValueError("Trading requires a real account. Please switch to real mode or use a different asset.")
                    raise ValueError(f"Buy confirmation failed: {error_msg}")
            if deal_id is not None:
                break
            await asyncio.sleep(0.1)

        if deal_id is None:
            self.logger.error(f"No buySuccessful message received for asset ID {asset_id}. Unhandled messages: {self.client.unhandled_messages}")
            raise TimeoutError("No buySuccessful message received with deal_id")

        # Optionally wait for win/loss
        if check_win:
            result = await self.check_win(str(deal_id))
            return str(deal_id), result

        return str(deal_id), {}

    async def check_win(self, deal_id: str, timeout: int = 90) -> dict:
        """
        Track trade status to determine win/loss/draw.
        """
        start = time.time()
        interim_result = None

        while time.time() - start < timeout:
            for msg in list(self.client.unhandled_messages):
                action = msg.get("action")

                if action == "openTradeSuccessful":
                    trade = msg.get("message", {}).get("trade", {})
                    if str(trade.get("id")) == deal_id:
                        self.client.unhandled_messages.remove(msg)
                        self.logger.info(f"Trade {deal_id} opened: {trade}")
                        continue

                if action == "optionFinished":
                    for t in msg.get("message", {}).get("options", []):
                        if str(t.get("id")) == deal_id:
                            profit = t.get("result_amount_cash", t.get("profit", 0))
                            self.client.unhandled_messages.remove(msg)
                            result = {
                                "result": "win" if profit > 0 else
                                          "loss" if profit < 0 else "draw",
                                "profit": profit,
                                "details": t
                            }
                            self.logger.info(f"Trade {deal_id} finished with result: {result}")
                            return result

                if action == "closeTradeSuccessful":
                    for t in msg.get("message", {}).get("trades", []):
                        if str(t.get("id")) == deal_id:
                            profit = t.get("result_amount_cash", t.get("profit", 0))
                            self.client.unhandled_messages.remove(msg)
                            result = {
                                "result": "win" if profit > 0 else
                                          "loss" if profit < 0 else "draw",
                                "profit": profit,
                                "details": t
                            }
                            self.logger.info(f"Trade {deal_id} closed with result: {result}")
                            return result

                if action in ["optStatus", "tradesStatus"]:
                    for t in msg.get("message", {}).get("options" if action == "optStatus" else "trades", []):
                        if str(t.get("id")) == deal_id:
                            profit = t.get("profit", 0)
                            self.client.unhandled_messages.remove(msg)
                            interim_result = {
                                "result": "win" if profit > 0 else
                                          "loss" if profit < 0 else "draw",
                                "profit": profit,
                                "details": t
                            }
                            self.logger.debug(f"Trade {deal_id} interim status via {action}: {interim_result}")
                            continue

            await asyncio.sleep(0.1)

        if interim_result:
            self.logger.warning(f"Trade {deal_id} no final result received; returning interim result: {interim_result}")
            return interim_result

        self.logger.error(f"Timeout waiting for result of deal {deal_id}. Remaining unhandled messages: {len(self.client.unhandled_messages)}")
        for msg in self.client.unhandled_messages:
            self.logger.debug(f"Unhandled message: {msg}")
        raise TimeoutError(f"Timeout waiting for result of deal {deal_id}")

    async def get_candles(self, asset_id: int, period: int, offset: int, duration: int = 1800, count_request: int = 3, start_time: int = None, as_dataframe: bool = True) -> list[dict] | pd.DataFrame:
        """Retrieves historical and live candle data for an asset ID."""
        if not await self.verify_asset_subscription(asset_id, period):
            self.logger.error(f"Cannot fetch candles for asset ID {asset_id} with timeframe {period}")
            raise ValueError(f"Invalid asset ID {asset_id} or timeframe {period}")

        if asset_id not in self.active_subscriptions:
            ns_sub = str(uuid4())
            await self.client.send(json.dumps({
                "action": "subscribeCandles",
                "message": {"assets": [{"id": asset_id, "timeframes": [period]}]},
                "ns": ns_sub,
                "token": self.token
            }))
            self.active_subscriptions.add(asset_id)
            self.logger.info(f"Subscribed to candles for asset ID {asset_id}, timeframe {period}")

        if asset_id not in self.candle_cache:
            self.candle_cache[asset_id] = {}
        if period not in self.candle_cache[asset_id]:
            self.candle_cache[asset_id][period] = {"candles": [], "expTimes": []}

        end_time = start_time or (int(time.time()) - offset)

        for _ in range(count_request):
            ns_hist = str(uuid4())
            await self.client.send(json.dumps({
                "action": "assetHistoryCandles",
                "message": {
                    "assetid": asset_id,
                    "periods": [[end_time - duration, end_time]],
                    "timeframes": [period]
                },
                "ns": ns_hist,
                "token": self.token
            }))

            start = time.time()
            while time.time() - start < 5.0:
                while self.client.candle_queue:
                    msg = self.client.candle_queue.popleft()
                    body = msg.get("message", {})
                    if body.get("assetId") == asset_id:
                        await self.update_candle_cache(msg, asset_id, period)

                while self.client.history_candle_queue:
                    msg = self.client.history_candle_queue.popleft()
                    body = msg.get("message", {})
                    if body.get("assetId") == asset_id:
                        await self.update_candle_cache(msg, asset_id, period)

                await asyncio.sleep(0.05)

            candles = self.candle_cache[asset_id][period]["candles"]
            if candles:
                end_time = min(c["time"].timestamp() for c in candles) - duration

        candles = self.candle_cache[asset_id][period]["candles"]
        if not candles:
            self.logger.warning(f"No candles available for asset ID {asset_id}, timeframe {period}")
            return pd.DataFrame() if as_dataframe else []

        self.logger.info(f"Returning {len(candles)} candles for asset ID {asset_id}, timeframe {period}")

        if as_dataframe:
            df = pd.DataFrame(candles)
            df["time"] = pd.to_datetime(df["time"])
            df = df.sort_values(by="time").drop_duplicates(subset="time", keep="last")
            df = df[["time", "open", "high", "low", "close", "timeframe", "volume"]]
            df.set_index("time", inplace=True)
            df = df.resample(f"{period}s").agg({
                "open": "first",
                "high": "max",
                "low": "min",
                "close": "last",
                "timeframe": "first",
                "volume": "sum"
            }).dropna().reset_index()
            return df

        return candles

    async def update_candle_cache(self, candle_response: dict, asset_id: int, timeframe: int):
        """Update candle cache with new candle data."""
        message = candle_response.get("message", {})
        asset_id = message.get("assetId", asset_id)
        timeframe = message.get("tf", timeframe)
        self.logger.debug(f"Processing candles for asset ID {asset_id}, timeframe: {timeframe}")

        candle_data = []
        # Handle candles and historical candles
        candles = message.get("candles", [])
        if candles and isinstance(candles, list) and isinstance(candles[0], dict) and "periods" in candles[0]:
            # Handle assetHistoryCandles structure
            for period in candles[0].get("periods", []):
                period_start = period[0]
                period_candles = period[1]
                for candle in period_candles:
                    if isinstance(candle, list) and len(candle) >= 4:
                        candle_data.append({
                            "time": period_start,
                            "open": float(candle[0]),
                            "high": float(candle[1]),
                            "low": float(candle[2]),
                            "close": float(candle[3]),
                            "timeframe": timeframe,
                            "volume": 0,
                            "source": "historical"
                        })
                        period_start += timeframe
        else:
            # Handle live candles
            for candle in candles:
                if isinstance(candle, dict) and "t" in candle and "v" in candle and len(candle["v"]) >= 4:
                    candle_data.append({
                        "time": candle["t"],
                        "open": float(candle["v"][0]),
                        "high": float(candle["v"][1]),
                        "low": float(candle["v"][2]),
                        "close": float(candle["v"][3]),
                        "timeframe": timeframe,
                        "volume": 0,
                        "source": "live"
                    })
                elif isinstance(candle, list) and len(candle) >= 2 and len(candle[1]) >= 4:
                    candle_data.append({
                        "time": candle[0],
                        "open": float(candle[1][0]),
                        "high": float(candle[1][1]),
                        "low": float(candle[1][2]),
                        "close": float(candle[1][3]),
                        "timeframe": timeframe,
                        "volume": 0,
                        "source": "historical"
                    })

        exp_times = message.get("expTimes", [])
        if candle_data:
            df = pd.DataFrame(candle_data)
            df["time"] = pd.to_datetime(df["time"], unit="s")
            df = df.sort_values(by="time").drop_duplicates(subset=["time", "source"], keep="last")

            if asset_id not in self.candle_cache:
                self.candle_cache[asset_id] = {}
            if timeframe not in self.candle_cache[asset_id]:
                self.candle_cache[asset_id][timeframe] = {"candles": [], "expTimes": []}

            existing_data = self.candle_cache[asset_id][timeframe]
            existing_candles = pd.DataFrame(existing_data["candles"])
            if not existing_candles.empty:
                df = pd.concat([existing_candles, df]).drop_duplicates(subset=["time", "source"], keep="last").sort_values(by="time")

            existing_exp_times = existing_data["expTimes"]
            updated_exp_times = list(set(existing_exp_times + [exp[0] for exp in exp_times]))

            self.candle_cache[asset_id][timeframe] = {
                "candles": df.to_dict("records"),
                "expTimes": updated_exp_times
            }
            self.logger.info(f"Updated candles for asset ID {asset_id}, timeframe {timeframe}, total: {len(self.candle_cache[asset_id][timeframe]['candles'])}")
            self.logger.debug(f"Updated expTimes for asset ID {asset_id}, total: {len(self.candle_cache[asset_id][timeframe]['expTimes'])}")
        else:
            self.logger.debug(f"No valid candle data received for asset ID {asset_id}")

    async def historySteps(self, asset_id: int, timeframe: int, start_time: int, end_time: int) -> list[dict]:
        """Fetch historical candles for specific time range."""
        if not await self.verify_asset_subscription(asset_id, timeframe):
            self.logger.error(f"Cannot fetch historical candles for asset ID {asset_id} with timeframe {timeframe}")
            raise ValueError(f"Invalid asset ID {asset_id} or timeframe {timeframe}")

        ns = str(uuid4())
        await self.client.send(json.dumps({
            "action": "assetHistoryCandles",
            "message": {
                "assetid": asset_id,
                "periods": [[start_time, end_time]],
                "timeframes": [timeframe]
            },
            "ns": ns,
            "token": self.token
        }))
        response = await self.client.recv(ns)
        await self.update_candle_cache(response, asset_id, timeframe)
        return self.candle_cache.get(asset_id, {}).get(timeframe, {}).get("candles", [])

    async def _subscribe_symbol_inner(self, asset_id: int, timeframes: list[int] = None):
        """Subscribe to candles for an asset with specified timeframes."""
        timeframes = timeframes or [5]
        for timeframe in timeframes:
            if not await self.verify_asset_subscription(asset_id, timeframe):
                self.logger.error(f"Cannot subscribe to asset ID {asset_id} with timeframe {timeframe}")
                raise ValueError(f"Invalid asset ID {asset_id} or timeframe {timeframe}")

        # Ensure subscription is active
        if asset_id not in self.active_subscriptions:
            ns_sub = str(uuid4())
            await self.client.send(json.dumps({
                "action": "subscribeCandles",
                "message": {"assets": [{"id": asset_id, "timeframes": timeframes}]},
                "ns": ns_sub,
                "token": self.token
            }))
            self.active_subscriptions.add(asset_id)
            self.logger.info(f"Subscribed to candles for asset ID {asset_id}, timeframes {timeframes}")

        # Process candle queue directly
        while True:
            while self.client.candle_queue:
                msg = self.client.candle_queue.popleft()
                if msg.get("action") != "candles" or msg.get("message", {}).get("assetId") != asset_id:
                    continue
                for candle in msg.get("message", {}).get("candles", []):
                    if candle.get("tf") in timeframes and len(candle.get("v", [])) >= 4:
                        yield {
                            "asset_id": asset_id,
                            "timeframe": candle["tf"],
                            "time": candle["t"],
                            "open": float(candle["v"][0]),
                            "high": float(candle["v"][1]),
                            "low": float(candle["v"][2]),
                            "close": float(candle["v"][3])
                        }
            await asyncio.sleep(0.05)  # Prevent CPU overload

    async def _subscribe_symbol_chunked_inner(self, asset_id: int, chunk_size: int):
        """Subscribe to chunked candles, aggregating chunk_size candles into one."""
        if not await self.verify_asset_subscription(asset_id, 5):
            self.logger.error(f"Cannot subscribe to asset ID {asset_id} with chunked subscription")
            raise ValueError(f"Invalid asset ID {asset_id}")

        if asset_id not in self.active_subscriptions:
            ns_sub = str(uuid4())
            await self.client.send(json.dumps({
                "action": "subscribeCandles",
                "message": {"assets": [{"id": asset_id, "timeframes": [5]}]},
                "ns": ns_sub,
                "token": self.token
            }))
            self.active_subscriptions.add(asset_id)
            self.logger.info(f"Subscribed to chunked candles for asset ID {asset_id}, chunk_size: {chunk_size}")

        chunk = []
        while True:
            while self.client.candle_queue:
                msg = self.client.candle_queue.popleft()
                if msg.get("action") != "candles" or msg.get("message", {}).get("assetId") != asset_id:
                    continue
                for candle in msg.get("message", {}).get("candles", []):
                    if candle.get("tf") == 5 and len(candle.get("v", [])) >= 4:
                        chunk.append({
                            "time": candle["t"],
                            "open": float(candle["v"][0]),
                            "high": float(candle["v"][1]),
                            "low": float(candle["v"][2]),
                            "close": float(candle["v"][3]),
                            "timeframe": 5,
                            "volume": 0
                        })
                        if len(chunk) >= chunk_size:
                            aggregated_candle = await self.aggregate_candles(chunk, 5 * chunk_size)
                            if aggregated_candle:
                                yield aggregated_candle
                            chunk = []
            await asyncio.sleep(0.05)

    async def _subscribe_symbol_timed_inner(self, asset_id: int, interval: timedelta):
        """Subscribe to timed candles, aggregating candles within a specified interval."""
        if not await self.verify_asset_subscription(asset_id, 5):
            self.logger.error(f"Cannot subscribe to asset ID {asset_id} with timed subscription")
            raise ValueError(f"Invalid asset ID {asset_id}")

        if asset_id not in self.active_subscriptions:
            ns_sub = str(uuid4())
            await self.client.send(json.dumps({
                "action": "subscribeCandles",
                "message": {"assets": [{"id": asset_id, "timeframes": [5]}]},
                "ns": ns_sub,
                "token": self.token
            }))
            self.active_subscriptions.add(asset_id)
            self.logger.info(f"Subscribed to timed candles for asset ID {asset_id}, interval: {interval.total_seconds()}s")

        interval_seconds = interval.total_seconds()
        current_interval_start = None
        interval_candles = []

        while True:
            while self.client.candle_queue:
                msg = self.client.candle_queue.popleft()
                if msg.get("action") != "candles" or msg.get("message", {}).get("assetId") != asset_id:
                    continue
                for candle in msg.get("message", {}).get("candles", []):
                    if candle.get("tf") == 5 and len(candle.get("v", [])) >= 4:
                        candle_time = candle["t"]
                        if current_interval_start is None:
                            current_interval_start = candle_time
                        # Yield aggregated candle if enough candles are collected or interval is exceeded
                        interval_candles.append({
                            "time": candle_time,
                            "open": float(candle["v"][0]),
                            "high": float(candle["v"][1]),
                            "low": float(candle["v"][2]),
                            "close": float(candle["v"][3]),
                            "timeframe": 5,
                            "volume": 0
                        })
                        # Check if we can yield an aggregated candle
                        if len(interval_candles) >= 2 or candle_time >= current_interval_start + interval_seconds:
                            aggregated_candle = await self.aggregate_candles(interval_candles, interval_seconds)
                            if aggregated_candle:
                                yield aggregated_candle
                            current_interval_start = candle_time
                            interval_candles = [interval_candles[-1]] if interval_candles else []
            await asyncio.sleep(0.05)  # Prevent CPU overload

    async def aggregate_candles(self, candles: list[dict], timeframe: int) -> dict:
        """Aggregate a list of candles into a single candle."""
        if not candles:
            return {}
        df = pd.DataFrame(candles)
        if df.empty:
            return {}
        aggregated = {
            "time": df["time"].iloc[0],
            "open": df["open"].iloc[0],
            "high": df["high"].max(),
            "low": df["low"].min(),
            "close": df["close"].iloc[-1],
            "timeframe": timeframe,
            "volume": df["volume"].sum(),
            "source": "aggregated"
        }
        return aggregated

    async def subscribe_symbol(self, asset_id: int, timeframes: list[int] = None) -> AsyncSubscription:
        """Real-time candle subscription for an asset with specified timeframes."""
        return AsyncSubscription(self._subscribe_symbol_inner(asset_id, timeframes))

    async def subscribe_symbol_chunked(self, asset_id: int, chunk_size: int) -> AsyncSubscription:
        """Chunked candle subscription, aggregating chunk_size candles into one."""
        return AsyncSubscription(self._subscribe_symbol_chunked_inner(asset_id, chunk_size))

    async def subscribe_symbol_timed(self, asset_id: int, interval: timedelta) -> AsyncSubscription:
        """Timed candle subscription, aggregating candles within a specified interval."""
        return AsyncSubscription(self._subscribe_symbol_timed_inner(asset_id, interval))

    async def balance(self) -> float:
        """Retrieve current account balance."""
        prof = await self.fetch_profile()
        bal = prof.get("demo_balance" if self.demo else "real_balance", 0.0)
        return bal

    async def payout(self, asset=None) -> dict|list|int:
        """Retrieve payout percentages."""
        assets = await self.fetch_assets()
        payouts = {a["symbol"]: a.get("profit", 0) for a in assets if a.get("is_active")}
        if isinstance(asset, str):
            return payouts.get(asset, 0)
        if isinstance(asset, list):
            return [payouts.get(a, 0) for a in asset]
        return payouts

    async def get_one_time_token(self) -> str:
        """Send getOneTimeToken and update self.token."""
        ns = str(uuid4())
        payload = {
            "action": "getOneTimeToken",
            "ns": ns,
            "token": self.token
        }
        await self.client.send(json.dumps(payload))
        resp = await self.client.recv(ns)
        new_token = resp.get("message", {}).get("token")
        if new_token:
            self.token = new_token
            self.logger.info(f"Updated token: {new_token}")
        return self.token

    async def open_options_stat(self) -> dict:
        """Send openOptionsStat and return stats."""
        ns = str(uuid4())
        payload = {
            "action": "openOptionsStat",
            "ns": ns,
            "token": self.token
        }
        await self.client.send(json.dumps(payload))
        resp = await self.client.recv(ns)
        return resp.get("message", {})

    async def open_trades(self, count: int = 20) -> list[dict]:
        """List all open trades."""
        ns = str(uuid4())
        payload = {
            "action": "openTrades",
            "message": {"count": count, "is_demo": 1 if self.demo else 0},
            "ns": ns,
            "token": self.token
        }
        await self.client.send(json.dumps(payload))
        resp = await self.client.recv(ns)
        return resp.get("message", {}).get("trades", [])

    async def trade_history(self, count: int = 20, cursor: str = None) -> list[dict]:
        """List trade history."""
        ns = str(uuid4())
        payload = {
            "action": "tradeHistory",
            "message": {
                "count": count,
                "cursor": cursor,
                "is_demo": 1 if self.demo else 0
            },
            "ns": ns,
            "token": self.token
        }
        await self.client.send(json.dumps(payload))
        resp = await self.client.recv(ns)
        return resp.get("message", {}).get("trades", [])

    async def opened_deals(self) -> list[dict]:
        """List all open deals."""
        return await self.open_trades()

    async def closed_deals(self) -> list[dict]:
        """List all closed deals."""
        return await self.trade_history()

    async def clear_closed_deals(self) -> None:
        """Clear closed deals from memory."""
        await self.client.send(json.dumps({"action":"clearClosedOptions","ns":str(uuid4())}))

    async def history(self, asset_id: int, period: int) -> list[dict]:
        """Alias for get_candles with dataframe=False."""
        return await self.get_candles(asset_id, period, 0, as_dataframe=False)

    async def get_asset_rates(self, asset_id: int) -> list[dict]:
        """Get rates for a specific asset."""
        assets = await self.fetch_assets()
        ad = next((a for a in assets if a["id"] == asset_id), None)
        if not ad:
            raise ValueError(f"No data for asset {asset_id}")
        return ad.get("rates", [])

    async def get_open_options_stat(self, asset_id: int) -> dict:
        """Get open options statistics for an asset."""
        for msg in list(self.client.unhandled_messages):
            if msg.get("action") == "openOptionsStat":
                opts = msg.get("message", {}).get("openOptions", [])
                for s in opts:
                    if s.get("assetId") == asset_id:
                        self.client.unhandled_messages.remove(msg)
                        return s
        ns = str(uuid4())
        payload = {"action": "openOptionsStat", "message": {"assetId": asset_id}, "ns": ns, "token": self.token}
        await self.client.send(json.dumps(payload))
        resp = await self.client.recv(ns)
        opts = resp.get("message", {}).get("openOptions", [])
        return next((s for s in opts if s.get("assetId") == asset_id), {})

    async def send_raw_message(self, message: str) -> None:
        """Send a raw WebSocket message."""
        await self.client.send(message)

    async def create_raw_order(self, message: str, validator: Validator) -> str:
        """Send raw order and validate response."""
        await self.client.send(message)
        key = json.loads(message).get("ns", json.loads(message).get("action"))
        resp = await self.client.recv(key)
        if validator.check(json.dumps(resp)):
            return json.dumps(resp)
        raise ValueError("Response did not match validator")

    async def create_raw_iterator(self, message: str, validator: Validator):
        """Iterator for validated raw messages."""
        await self.client.send(message)
        key = json.loads(message).get("ns", json.loads(message).get("action"))
        while True:
            async with self.client.recv_lock:
                if key not in self.client.pending_responses or self.client.pending_responses[key].done():
                    self.client.pending_responses[key] = asyncio.Future()
                response = await self.client.pending_responses[key]
                if validator.check(json.dumps(response)):
                    yield response
                else:
                    self.logger.debug(f"Response did not match validator: {response}")

    async def get_server_time(self) -> int:
        """Retrieves the current server time."""
        try:
            if not self.client.connected:
                self.logger.warning("WebSocket not connected. Reconnecting...")
                await self.client.connect()
            await self.send_ping()
            try:
                response = await asyncio.wait_for(self.client.recv("pong"), timeout=5.0)
                ts = response.get("message", {}).get("data", str(int(time.time() * 1000)))[:10]
                return int(ts)
            except asyncio.TimeoutError:
                self.logger.warning("Timeout waiting for pong response, using local time")
                return int(time.time())
        except websockets.exceptions.ConnectionClosed as e:
            self.logger.warning(f"Connection closed during get_server_time: {e}. Reconnecting...")
            await self.client.connect()
            return await self.get_server_time()  # Retry
