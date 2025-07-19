<div align="center">
  <h1>ExpertOptionsToolsV2 – Python Async & Sync WebSocket Client</h1>
  <p>
    <b>⚡ Professional Python client for Expert Option via WebSocket (Async & Sync) ⚡</b><br>
    <img src="https://img.shields.io/pypi/v/ExpertOptionsToolsV2?label=PyPI&logo=python" alt="PyPI Version" />
    <img src="https://img.shields.io/github/license/A11ksa/Expert-Option-API?style=flat-square" alt="License" />
    <img src="https://img.shields.io/badge/asyncio-supported-brightgreen?logo=python" alt="AsyncIO Supported"/>
    <img src="https://img.shields.io/badge/rich-output-blue?logo=python" alt="Rich Output"/>
    <img src="https://img.shields.io/badge/status-stable-success?logo=github" alt="Status"/>
  </p>
</div>

---

## Table of Contents

- [Overview](#overview)  
- [Installation](#installation)  
- [Quick Start](#quick-start)  
- [Modules](#modules)  
  - [Async Client](#async-client)  
  - [Sync Client](#sync-client)  
  - [Constants & Helpers](#constants--helpers)  
  - [Validator](#validator)  
  - [Tracing & Logging](#tracing--logging)  
- [Examples](#examples)  
  - [Basic Async Workflow](#basic-async-workflow)  
  - [Historical Candles DataFrame](#historical-candles-dataframe)  
  - [Synchronous Trading Script](#synchronous-trading-script)  
  - [Custom Signal Bot](#custom-signal-bot)  
- [Configuration](#configuration)  
- [Troubleshooting](#troubleshooting)  
- [Contributing](#contributing)  
- [License](#license)  
- [Contact](#contact)  

---

## 📖 Overview

**ExpertOptionsToolsV2** is a Python library that enables seamless interaction with the Expert Option trading platform via its WebSocket API. It supports both **asynchronous** and **synchronous** workflows, offers robust connection management, and integrates powerful utilities for market data, trade execution, and logging.

---

## 🛠️ Installation

```bash
# Clone and install the library
git clone https://github.com/A11ksa/Expert-Option-API.git
cd Expert-Option-API
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install .
```

**Core dependencies**:
- `websockets>=11.0.3`  
- `pandas>=1.5.0`  
- `rich>=13.0.0`  

**Dev dependencies** (for testing & formatting):
```bash
pip install pytest pytest-asyncio black isort
```

---

## ⚡ Quick Start

### Asynchronous Client
```python
import asyncio
from ExpertOptionsToolsV2.expertoption.asyncronous import ExpertOptionAsync
from ExpertOptionsToolsV2.constants import DEFAULT_SERVER

async def main():
    token = "YOUR_AUTH_TOKEN"  # e.g., from DevTools "auth" cookie
    client = ExpertOptionAsync(token=token, demo=True, url=DEFAULT_SERVER)
    await client.connect()

    balance = await client.balance()
    print("Balance:", balance)

    assets = await client.fetch_assets()
    print("Assets:", len(assets), "symbols available")

    # Place a CALL trade for 60 seconds
    trade_id, result = await client.buy(
        asset_id=142,         # e.g., ID for EURUSD
        amount=5.0,
        expiration_time=60,
        check_win=True
    )
    print("Trade complete:", result)

    await client.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
```

---

## 📦 Modules

### Async Client
- **Location**: `ExpertOptionsToolsV2/expertoption/asyncronous.py`  
- **Class**: `ExpertOptionAsync`  
- **Key methods**:  
  - `connect()` / `disconnect()`  
  - `balance()`, `fetch_assets()`, `get_candles()`  
  - `subscribe_symbol()` for streaming updates  
  - `buy()`, `sell()`, `check_win()`

### Sync Client
- **Location**: `ExpertOptionsToolsV2/expertoption/syncronous.py`  
- **Class**: `ExpertOption`  
- **Usage**: identical methods in a blocking style for easy scripting.

### Constants & Helpers
- **`constants.data_assets`**: dict mapping asset names to IDs and metadata.  
- **`constants.DEFAULT_SERVER`**: default WebSocket URL.  
- **Utility**: `symbol_to_id("EURUSD")` → asset ID.

### Validator
```python
from ExpertOptionsToolsV2.validator import Validator

# Validate incoming message format
validator = Validator(prefix="42["getBalance", suffix=""]")
raw_msg = '42["getBalance", {"balance": 100}]'
if validator.validate(raw_msg):
    print("Valid balance payload")
```

### Tracing & Logging
```python
from ExpertOptionsToolsV2.tracing import LogBuilder

logger = (
    LogBuilder()
    .log_file("logs/trades.log", level="INFO")
    .terminal(level="DEBUG")
    .build()
)
logger.info("Client connected!")
```

---

## 🧑‍💻 Examples

### Basic Async Workflow
```python
import asyncio
from ExpertOptionsToolsV2.expertoption.asyncronous import ExpertOptionAsync

async def demo():
    client = ExpertOptionAsync(token="...", demo=True)
    await client.connect()
    print(await client.balance())
    print(await client.fetch_assets())
    candles = await client.get_candles(asset_id=142, period=60, offset=0, duration=300)
    print("Last 5 candles:", candles.tail())
    await client.disconnect()

asyncio.run(demo())
```

### Historical Candles DataFrame
```python
df = await client.get_candles(asset_id=142, period=60, offset=0, duration=3600)
# DataFrame with columns: time, open, high, low, close, volume
print(df.describe())
```

### Synchronous Trading Script
```python
from ExpertOptionsToolsV2.expertoption.syncronous import ExpertOption

client = ExpertOption(token="YOUR_TOKEN", demo=False)
client.connect()
bal = client.balance()
print("Live balance:", bal)
order_id, res = client.buy(asset_id=145, amount=2.5, expiration_time=120)
print("Order result:", res)
client.disconnect()
```

### Custom Signal Bot
```python
import asyncio
from ExpertOptionsToolsV2.expertoption.asyncronous import ExpertOptionAsync

async def signal_bot(signal_queue):
    client = ExpertOptionAsync(token="...", demo=True)
    await client.connect()
    while True:
        signal = await signal_queue.get()
        sid, result = await client.buy(
            asset_id=signal.asset_id,
            amount=signal.amount,
            expiration_time=signal.duration,
            check_win=True
        )
        print(f"Executed {sid} → {result}")
    # (Cleanup omitted)

# Usage with any asyncio queue of signals
```

---

## ⚙️ Configuration

- **Token**: retrieve from browser cookie `"auth"`.  
- **Demo vs Live**: `demo=True/False` flag.  
- **Server URL**: override via `url=` parameter.  

---

## 🛠️ Troubleshooting

- **Invalid auth**: ensure `token` matches your real session cookie.  
- **Timeouts**: increase `ping_interval` or `timeout` when creating client.  
- **Unexpected disconnects**: catch exceptions, implement retry loops:
  ```python
  for _ in range(5):
      try:
          await client.connect()
          break
      except Exception as e:
          await asyncio.sleep(2)
  ```

---

## 🤝 Contributing

1. Fork the repo  
2. Create branch `feature/...`  
3. Follow PEP8, format with `black` & `isort`  
4. Add tests under `tests/`  
5. Open a Pull Request

---

## 📄 License

MIT License. See [LICENSE](LICENSE) for details.

---

## 📬 Contact

- **Author:** Ahmed Althuwaini (ar123ksa@gmail.com)  
- **Telegram:** [@A11ksa](https://t.me/A11ksa)  

---

*Crafted for precision, clarity, and professional-grade examples.*  
