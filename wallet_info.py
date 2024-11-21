# wallet_info.py
import json
from pathlib import Path
from web3 import Web3
from web3.middleware import geth_poa_middleware
from decimal import Decimal, getcontext
import logging

from run_service import (
    load_local_config,
    get_service_template,
    CHAIN_ID_TO_METADATA,
    USDC_ADDRESS,
    OPERATE_HOME
)

from utils import (
    get_chain_name,
    load_operator_address,
    validate_config,
    wei_to_unit,
    wei_to_eth,
    ColorCode,
)

# Set decimal precision
getcontext().prec = 18

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(message)s')

USDC_ABI = [{
    "constant": True,
    "inputs": [{"name": "_owner", "type": "address"}],
    "name": "balanceOf",
    "outputs": [{"name": "balance", "type": "uint256"}],
    "type": "function"
}]

def load_config():
    try:
        optimus_config = load_local_config()
        service_template = get_service_template(optimus_config)
        service_hash = service_template.get("hash")
        if not service_hash:
            print("Error: Service hash not found in service template.")
            return {}
        config_path = OPERATE_HOME / f"services/{service_hash}/config.json"
        try:
            with open(config_path, "r") as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"Error: Config file not found at {config_path}")
            return {}
        except json.JSONDecodeError:
            print("Error: Config file contains invalid JSON.")
            return {}
    except Exception as e:
        print(f"An error occurred while loading the config: {e}")
        return {}

def get_balance(web3, address):
    try:
        balance = web3.eth.get_balance(address)
        return Decimal(Web3.from_wei(balance, 'ether'))
    except Exception as e:
        print(f"Error getting balance for address {address}: {e}")
        return Decimal(0)

def get_usdc_balance(web3, address, chain_name):
    try:
        usdc_contract = web3.eth.contract(address=USDC_ADDRESS, abi=USDC_ABI)
        balance = usdc_contract.functions.balanceOf(address).call()
        return Decimal(balance) / Decimal(1e6)  # USDC has 6 decimal places
    except Exception as e:
        print(f"Error getting USDC balance for address {address}: {e}")
        return Decimal(0)

class DecimalEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, Decimal):
            return float(o)
        return super(DecimalEncoder, self).default(o)

def save_wallet_info():
    config = load_config()
    optimus_config = load_local_config()
    if not config:
        print("Error: Configuration could not be loaded.")
        return

    main_wallet_address = config.get('keys', [{}])[0].get('address')
    operator_wallet_address = load_operator_address(OPERATE_HOME)
    if not main_wallet_address:
        print("Error: Main wallet address not found in configuration.")
        return

    main_balances = {}
    safe_balances = {}
    operator_balances = {}

    for chain_id, chain_config in config.get('chain_configs', {}).items():
        chain_name = get_chain_name(chain_id, CHAIN_ID_TO_METADATA)
        if optimus_config.allowed_chains and chain_name.lower() not in optimus_config.allowed_chains:
            continue

        rpc_url = chain_config.get('ledger_config', {}).get('rpc')
        if not rpc_url:
            print(f"Error: RPC URL not found for chain ID {chain_id}.")
            continue

        try:
            web3 = Web3(Web3.HTTPProvider(rpc_url))
            if chain_id != "1":  # Ethereum Mainnet
                web3.middleware_onion.inject(geth_poa_middleware, layer=0)

            # Get main wallet balance
            main_balance = get_balance(web3, main_wallet_address)
            operator_balance = get_balance(web3, operator_wallet_address)
            main_balances[chain_name] = {
                "token": "ETH",
                "balance": main_balance,
                "balance_formatted": f"{main_balance:.6f} ETH"
            }
            operator_balances[chain_name] = {
                "token": "ETH",
                "balance": operator_balance,
                "balance_formatted": f"{operator_balance:.6f} ETH"
            } 

            # Get Safe balance
            safe_address = chain_config.get('chain_data', {}).get('multisig')
            if not safe_address:
                print(f"Error: Safe address not found for chain ID {chain_id}.")
                continue

            safe_balance = get_balance(web3, safe_address)
            safe_balances[chain_name] = {
                "address": safe_address,
                "token": "ETH",
                "balance": safe_balance,
                "balance_formatted": f"{safe_balance:.6f} ETH"
            }

            # Get USDC balance for Principal Chain
            if chain_name.lower() == optimus_config.principal_chain:
                usdc_balance = get_usdc_balance(web3, safe_address, chain_name.lower())
                safe_balances[chain_name]["usdc_balance"] = usdc_balance
                safe_balances[chain_name]["usdc_balance_formatted"] = f"{usdc_balance:.2f} USDC"

        except Exception as e:
            print(f"An error occurred while processing chain ID {chain_id}: {e}")
            continue

    wallet_info = {
        "main_wallet_address": main_wallet_address,
        "main_wallet_balances": main_balances,
        "operator_wallet_address": operator_wallet_address,
        "safe_addresses": {
            chain_id: chain_config.get('chain_data', {}).get('multisig', 'N/A')
            for chain_id, chain_config in config.get('chain_configs', {}).items()
        },
        "safe_balances": safe_balances,
        "operator_balances": operator_balances,
        "chain_configs": {
            chain_id: {
                "rpc": chain_config.get('ledger_config', {}).get('rpc'),
                "multisig": chain_config.get('chain_data', {}).get('multisig'),
                "token": chain_config.get('chain_data', {}).get('token'),
                "fund_requirements": chain_config.get('chain_data', {}).get('user_params', {}).get('fund_requirements')
            }
            for chain_id, chain_config in config.get('chain_configs', {}).items()
        }
    }

    file_path = OPERATE_HOME / "wallets" / "wallet_info.json"
    try:
        with open(file_path, "w") as f:
            json.dump(wallet_info, f, indent=2, cls=DecimalEncoder)
        print(f"Wallet info saved to {file_path}")
    except Exception as e:
        print(f"Error saving wallet info to {file_path}: {e}")

if __name__ == "__main__":
    try:
        save_wallet_info()
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
