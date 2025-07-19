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
- [Setting Context (Demo / Live)](#setting-context-demo--live)  
- [Modules](#modules)  
- [Examples](#examples)  
- [Configuration](#configuration)  
- [Troubleshooting](#troubleshooting)  
- [Contributing](#contributing)  
- [License](#license)  
- [Contact](#contact)  

---

## Overview

ExpertOptionsToolsV2 is a Python library for interacting with the Expert Option trading platform via its WebSocket API. It supports both asynchronous (`asyncio`) and synchronous workflows, offering robust connection management, real-time market data access, trade execution, and comprehensive logging.

---

## Installation

```bash
git clone https://github.com/A11ksa/Expert-Option-API.git
cd Expert-Option-API
python3 -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install .
```

### Requirements

- `websockets>=11.0.3`
- `pandas>=1.5.0`
- `rich>=13.0.0`

### Development Requirements

```bash
pip install pytest pytest-asyncio black isort
```

---

## Quick Start

```python
import asyncio
from ExpertOptionsToolsV2.expertoption.asyncronous import ExpertOptionAsync
from ExpertOptionsToolsV2.constants import DEFAULT_SERVER

async def main():
    token = "YOUR_AUTH_TOKEN"
    client = ExpertOptionAsync(token=token, demo=True, url=DEFAULT_SERVER)
    await client.connect()
    balance = await client.balance()
    print("Balance:", balance)
    await client.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
```

---

## Setting Context (Demo / Live)

Before sending any other messages, set the context to demo or live using the following JSON payload:

```json
{"action":"setContext","message":{"is_demo":1},"token":"d0bf01282227898aa46dc2a0ad62f6b8","ns":1}
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

---

## Modules

- **Async Client** (`expertoption/asyncronous.py`): `ExpertOptionAsync`  
- **Sync Client** (`expertoption/syncronous.py`): `ExpertOption`  
- **Constants & Helpers** (`constants.py`): Asset mappings and utility functions  
- **Validator** (`validator.py`): `Validator` for message format validation  
- **Tracing & Logging** (`tracing.py`): `Logger` and `LogBuilder`  

---

## Examples

### Basic Async Workflow

```python
import asyncio
from ExpertOptionsToolsV2.expertoption.asyncronous import ExpertOptionAsync

async def demo():
    client = ExpertOptionAsync(token="...", demo=True)
    await client.connect()
    print(await client.balance())
    await client.disconnect()

asyncio.run(demo())
```

### Historical Candles DataFrame

```python
df = await client.get_candles(asset_id=142, period=60, offset=0, duration=300)
print(df.head())
```

### Synchronous Trading Script

```python
from ExpertOptionsToolsV2.expertoption.syncronous import ExpertOption

client = ExpertOption(token="YOUR_TOKEN", demo=False)
client.connect()
print("Live balance:", client.balance())
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
        print(f"Executed {sid} -> {result}")

# Use with any asyncio.Queue for signals
```

---

## Configuration

- **Token**: Extract from browser DevTools cookie `auth`.  
- **Demo vs Live**: Pass `demo=True` or `False`.  
- **Server URL**: Override via the `url=` parameter.  

---

## Troubleshooting

- **Invalid token**: Verify the `token` value.  
- **Timeouts**: Adjust `ping_interval` or `timeout`.  
- **Disconnects**: Implement retry logic around `connect()`.

---

## Contributing

Please fork the repository, create a feature branch, follow PEP8, run `black` & `isort`, add tests under `tests/`, and submit a pull request.

---

## License

MIT License. See [LICENSE](LICENSE) for details.

---

## Contact

- **Author**: Ahmed <ar123ksa@gmail.com>  
- **Telegram**: https://t.me/A11ksa
