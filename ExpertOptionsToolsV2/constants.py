"""
Constants for ExpertOptionsToolsV2
Contains asset IDs and symbols based on server data from 2025-05-05
"""
data_assets = {
    142: 'EURUSD',
    151: 'AUDCAD',
    152: 'AUDJPY',
    153: 'AUDUSD',
    154: 'EURGBP',
    155: 'GBPUSD',
    156: 'NZDUSD',
    157: 'USDCAD',
    158: 'USDCHF',
    159: 'USDJPY',
    160: 'BTCUSD',
    161: 'LTCUSD',
    162: 'ETHUSD',
    163: 'BTCLTC',
    164: 'BTCCNY',
    165: 'BTCINR',
    166: 'BTCTHB',
    167: 'BCHUSD',
    168: 'IOTUSD',
    169: 'DSHUSD',
    170: 'BITGOLDUSD',
    171: 'XMRUSD',
    172: 'ZECUSD',
    173: 'XRPUSD',
    174: 'USDT',
    175: 'ETCUSD',
    176: 'XAUUSD',
    177: 'UKOil',
    178: 'SI',
    179: 'EURUSD_OTC',
    180: 'GBPUSD_OTC',
    181: 'USDJPY_OTC',
    182: 'USDCHF_OTC',
    183: 'EURGBP_OTC',
    184: 'AUDUSD_OTC',
    185: 'USDCAD_OTC',
    186: 'NZDUSD_OTC',
    187: 'EURJPY_OTC',
    188: 'EURCAD_OTC',
    189: 'FB',
    190: 'BABA',
    191: 'GOOG',
    192: 'AAPL',
    193: 'AMZN',
    194: 'MSFT',
    195: 'TSLA',
    196: 'LMT',
    197: 'VRX',
    198: 'AGN',
    199: 'YUM',
    200: 'IBM',
    201: 'AABA',
    202: 'MCD',
    203: 'DIS',
    204: 'F',
    205: 'C',
    206: 'GS',
    207: 'KO',
    208: 'BIDU',
    209: 'NFLX',
    210: 'USDNOK',
    211: 'EURAUD',
    212: 'EURCHF',
    214: 'GBPCAD',
    216: 'GBPCHF',
    217: 'EURJPY',
    218: 'AUDCHF',
    219: 'AUDNZD',
    221: 'XPTUSD',
    224: 'USWALLST30',
    225: 'HONGKONG33',
    227: 'GERMANY30',
    229: 'altcoinindex',
    230: 'topcryptoindex',
    231: 'BTCUSD',
    232: 'BTCUSD',
    233: 'USDX',
    235: 'ADAUSD',
    239: 'USINDEX100',
    240: 'SMRTY',
    245: 'EURUSD',
    247: 'COPPER',
    248: 'USDJPY',
    249: 'USDCHF',
    250: 'GBPUSD',
    251: 'XAUUSD',
    252: 'SPY',
    253: 'VTI',
    254: 'EEM',
    255: 'IWM',
    256: 'GLD',
    257: 'TLT',
    258: 'EFA',
    259: 'EWJ',
    260: 'USO',
    261: 'UNG',
    262: 'XLK',
    263: 'XLF',
    264: 'XLE',
    265: 'XLRE',
    266: 'XLB',
    267: 'UKOil_OTC',
    268: 'SI',
    269: 'INTEL',
    270: 'GOOG',
    271: 'META',
    272: 'INDIAN_INDEX_OTC_R',
    273: 'AUDUSD_OTC',
    274: 'USDCAD_OTC',
    275: 'NZDUSD_OTC',
    276: 'CRICKET_INDEX_OTC_R',
    277: 'CAMEL_RACE_INDEX_OTC_R',
    278: 'FOOTBALL_INDEX_OTC_R',
    279: 'CSCO',
    280: 'NVDA',
    281: 'XOM',
    282: 'PG',
    283: 'GM',
    284: 'NKE',
    285: 'AI_INDEX_OTC_R',
    286: 'LUXURY_INDEX_OTC_R',
    287: 'EURSAR',
    288: 'EURAED',
    289: 'AEDSAR',
    316: 'TRUMPUSD'
}

symbol_to_id = {v: k for k, v in data_assets.items()}

def get_asset_id(symbol: str) -> int:
    """Return asset ID from symbol."""
    return symbol_to_id.get(symbol.upper())

def get_asset_name(asset_id: int) -> str:
    """Return asset symbol from ID."""
    return data_assets.get(asset_id)

async def get_active_asset_id(symbol: str, fetch_assets_func) -> int | None:
    """Return the active asset ID for a given symbol based on server data."""
    try:
        assets = await fetch_assets_func()
        active_assets = [
            asset for asset in assets
            if asset.get('symbol', '').upper() == symbol.upper() and
            asset.get('is_active', 0) == 1 and
            asset.get('profit', 0) > 0
        ]
        if not active_assets:
            return None
        selected_asset = max(active_assets, key=lambda x: x.get('profit', 0))
        return selected_asset.get('id')
    except Exception as e:
        print(f"Error fetching active asset ID for {symbol}: {e}")
        return None

# Servers configuration
SERVERS = {
    "EUROPE": "wss://fr24g1eu.expertoption.com/",
    "INDIA": "wss://fr24g1in.expertoption.com/",
    "HONG_KONG": "wss://fr24g1hk.expertoption.com/",
    "SINGAPORE": "wss://fr24g1sg.expertoption.com/",
    "UNITED_STATES": "wss://fr24g1us.expertoption.com/"
}

DEFAULT_SERVER = SERVERS["EUROPE"]
