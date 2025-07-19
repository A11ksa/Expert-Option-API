[![PyPI](https://img.shields.io/pypi/v/ExpertOptionsToolsV2?label=PyPI&logo=python)](https://pypi.org/project/ExpertOptionsToolsV2)
[![License](https://img.shields.io/github/license/A11ksa/Expert-Option-API)](https://github.com/A11ksa/Expert-Option-API/blob/main/LICENSE)
[![Python Versions](https://img.shields.io/pypi/pyversions/ExpertOptionsToolsV2)](https://pypi.org/project/ExpertOptionsToolsV2)
[![Build Status](https://img.shields.io/github/actions/workflow/status/A11ksa/Expert-Option-API/ci.yml?branch=main)](https://github.com/A11ksa/Expert-Option-API/actions)
[![Documentation](https://img.shields.io/badge/docs-wiki-blue?logo=github)](https://github.com/A11ksa/Expert-Option-API/wiki)
[![Coverage](https://img.shields.io/codecov/c/github/A11ksa/Expert-Option-API)](https://codecov.io/gh/A11ksa/Expert-Option-API)
[![Telegram](https://img.shields.io/badge/Telegram-@A11ksa-0088cc?logo=telegram)](https://t.me/A11ksa)

# ExpertOptionsToolsV2  
_A professional, full-featured Python client for Expert Option via WebSocket (Async & Sync)_

---

## 📖 Table of Contents

1. [🚀 Overview](#overview)  
2. [💾 Installation](#installation)  
3. [⚡ Quick Start](#quick-start)  
4. [🔧 Configuration](#configuration)  
5. [📦 Modules & Structure](#modules--structure)  
6. [📝 Examples](#examples)  
7. [🐞 Troubleshooting](#troubleshooting)  
8. [🤝 Contributing](#contributing)  
9. [📝 License](#license)  
10. [📬 Contact](#contact)  

---

## 🚀 Overview

ExpertOptionsToolsV2 is a robust Python library for interacting with the Expert Option trading platform over WebSocket.  
It supports both **asynchronous** (`asyncio`) and **synchronous** workflows, offering:

- **Connection management** with auto-retry & ping  
- **Real‑time market data** subscriptions & historical candles  
- **Trade execution** (buy/sell) with optional win/loss reporting  
- **Comprehensive logging** & trace support  
- **Validator utilities** for message‐format enforcement  

---

## 💾 Installation

### From PyPI

```bash
pip install ExpertOptionsToolsV2
```

### From Source

```bash
git clone https://github.com/A11ksa/Expert-Option-API.git
cd Expert-Option-API
python3 -m venv venv
source venv/bin/activate      # Windows: venv\Scriptsctivate
pip install .
```

#### Development Dependencies

```bash
pip install pytest pytest-asyncio black isort
```

---

## ⚡ Quick Start

## Setting Context (Demo / Live)

Before sending any other messages, set the context to demo or live using the following JSON payload:

```json
{"action":"setContext","message":{"is_demo":1},"token":"d0db01083337898cc46dc2a0af28f888","ns":1}
```

Example implementation in `connect()`:

```python
import json
from websockets import connect

class ExpertOptionAsync:
    async def connect(self):
        self.ws = await connect(self.url)
        await self.ws.send(json.dumps({
            "action": "setContext",
            "message": {"is_demo": 1 if self.demo else 0},
            "token": self.token,
            "ns": 1
        }))
        # Now you can send other requests, e.g.:
        await self.ws.send(json.dumps(["getBalance"]))
```

### Asynchronous Client

```python
import asyncio
from ExpertOptionsToolsV2.expertoption.asyncronous import ExpertOptionAsync
from ExpertOptionsToolsV2.constants import DEFAULT_SERVER

async def main():
    token  = "YOUR_AUTH_TOKEN"               # from browser cookie `auth`
    client = ExpertOptionAsync(token, demo=True, url=DEFAULT_SERVER)
    await client.connect()
    balance = await client.balance()
    print("Balance:", balance)
    # Place a CALL trade on EURUSD (ID 142) for $1 expiring in 60s:
    deal_id, result = await client.buy(asset_id=142, amount=1.0, expiration_time=60, check_win=True)
    print(f"Deal {deal_id} →", result)
    await client.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
```

### Synchronous Client

```python
from ExpertOptionsToolsV2.expertoption.syncronous import ExpertOption

client = ExpertOption(token="YOUR_TOKEN", demo=False)
client.connect()
print("Live balance:", client.balance())
# Place a PUT trade
deal_id, result = client.sell(asset="EURUSD", amount=2.0, time=120, check_win=True)
print(f"Deal {deal_id} →", result)
client.disconnect()
```

---

## 🔧 Configuration

- **Token**: extract from browser DevTools cookie named `auth`.  
- **Demo vs Live**: `demo=True` (demo) or `False` (real account).  
- **Server URL**: override default via `url=` parameter.  
- **Log levels**: configure via `tracing.LogBuilder().terminal("DEBUG")` or file handlers.

---

## 📦 Modules & Structure

```text
ExpertOptionsToolsV2/
├── constants.py         # Asset ID⇄symbol maps & helper functions
├── validator.py         # RawValidator & high‑level Validator wrappers
├── tracing.py           # Logger & LogBuilder for flexible logging
├── expertoption/
│   ├── asyncronous.py   # ExpertOptionAsync & WebSocketClient
│   └── syncronous.py    # ExpertOption (sync wrapper)
└── setup.py             # Package metadata & dependencies
```

- 🗺️ **constants.py**  
  - `data_assets`, `symbol_to_id`  
  - `get_asset_id()`, `get_asset_name()`, `get_active_asset_id()`  
- 🔍 **validator.py**  
  - `Validator.regex()` / `.starts_with()` / `.contains()` / `.any()` / `.all()`  
  - Enforce message formats before processing  
- 🛠️ **tracing.py**  
  - `Logger` (info/debug/error/warning)  
  - `LogBuilder` (file & terminal handlers)  
- 🚀 **expertoption/asyncronous.py**  
  - `ExpertOptionAsync`: connect, fetch_profile/assets/timeframes, buy/sell, get_candles, check_win, etc.  
- 🔄 **expertoption/syncronous.py**  
  - `ExpertOption`: synchronous wrapper around `ExpertOptionAsync`  

---

## 📝 Examples

- **Historical Candles DataFrame**

  ```python
  df = await client.get_candles(asset_id=142, period=60, offset=0, duration=300)
  print(df.head())
  ```

- **Real‑time Candle Subscription**

  ```python
  async for msg in await client.subscribe_symbol(asset_id=142, timeframes=[5]):
      print(msg)
  ```

- **Custom Signal Bot**

  ```python
  import asyncio
  from ExpertOptionsToolsV2.expertoption.asyncronous import ExpertOptionAsync

  async def signal_bot(queue):
      client = ExpertOptionAsync("...", demo=True)
      await client.connect()
      while True:
          sig = await queue.get()
          deal, res = await client.buy(sig.asset_id, sig.amount, sig.duration, check_win=True)
          print(f"Executed {deal} →", res)

  # use asyncio.Queue for your signals
  ```

---

## 🐞 Troubleshooting

- **Invalid token**: check that `auth` cookie is valid & unexpired.  
- **WebSocket timeouts**: adjust `ping` frequency or wrap `connect()` in retry logic.  
- **Empty candle data**: verify `asset_id` & `period` support with `filter_active_assets()`.  
- **Logging not appearing**: initialize `LogBuilder().terminal("INFO").build()` before usage.

---

## 🤝 Contributing

1. Fork the repo & create a feature branch  
2. Follow PEP8 & run `black` + `isort`  
3. Write tests under `tests/`  
4. Submit a pull request, reference relevant issue  

---

## 📝 License

This project is licensed under the **MIT License**. See [LICENSE](LICENSE) for details.

---

## 📬 Contact

- **Author**: Ahmed (`ar123ksa@gmail.com`)  
- **Telegram**: [@A11ksa](https://t.me/A11ksa)  
- **GitHub**: [A11ksa/Expert-Option-API](https://github.com/A11ksa/Expert-Option-API)
