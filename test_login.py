import asyncio
import configparser
import os
import re
from ExpertOptionsToolsV2.expertoption import ExpertOptionAsync
from rich import print

def manage_config(config_file='config.txt'):
    """Manage reading and writing configuration data to config.txt."""
    config = configparser.ConfigParser()
    default_settings = {
        'token': 'Your_Token_Here',
        'account_type': 'DEMO'
    }

    # Check if config file exists
    if os.path.exists(config_file):
        config.read(config_file)
        settings = {}
        if 'Settings' in config:
            for key in default_settings:
                settings[key] = config['Settings'].get(key, default_settings[key])
        else:
            settings = default_settings
    else:
        settings = default_settings
        print("Config file not found. Please enter settings:")
        settings['token'] = input("Enter Token: ") or default_settings['token']
        # Validate token format (simple regex for alphanumeric)
        while not re.match(r'^[a-zA-Z0-9]{32}$', settings['token']):
            print("Invalid token format. Must be 32 alphanumeric characters.")
            settings['token'] = input("Enter Token: ") or default_settings['token']
        
        settings['account_type'] = input("Enter Account Type (REAL/DEMO): ") or default_settings['account_type']
        # Validate account type
        while settings['account_type'].upper() not in ['REAL', 'DEMO']:
            print("Invalid account type. Must be REAL or DEMO.")
            settings['account_type'] = input("Enter Account Type (REAL/DEMO): ") or default_settings['account_type']

    # Save settings to config file
    config['Settings'] = {k: str(v) for k, v in settings.items()}
    with open(config_file, 'w', encoding='utf-8') as configfile:
        config.write(configfile)

    return settings

async def test_login():
    """Test login for REAL and DEMO accounts."""
    settings = manage_config()
    token = settings['token']
    account_type = settings['account_type'].upper()

    # Initialize API
    api = ExpertOptionAsync(token=token, demo=(account_type == 'DEMO'))

    try:
        # Connect to ExpertOption
        print("Connecting to ExpertOption...")
        await api.connect()
        print(f"Connected successfully! Token: {token[:8]}...")

        # Set account mode
        if account_type == 'REAL':
            api.demo = False
            await api.set_mode()
            print("Switched to REAL account")
        else:
            api.demo = True
            await api.set_mode()
            print("Switched to DEMO account")

        # Fetch and display balance
        balance = await api.balance()
        print(f"Current Balance: {balance}")

    except Exception as e:
        print(f"Error during login: {e}")

    finally:
        print("Disconnecting...")
        await api.disconnect()

if __name__ == "__main__":
    asyncio.run(test_login())
