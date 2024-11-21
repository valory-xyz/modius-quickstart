import warnings
warnings.filterwarnings("ignore", category=UserWarning)

import json
from datetime import datetime
import logging
from decimal import Decimal, getcontext, ROUND_UP
from pathlib import Path
from typing import Any, Tuple, Dict
from web3 import Web3

from run_service import (
    load_local_config,
    CHAIN_ID_TO_METADATA,
    OPERATE_HOME
)

from utils import (
    _print_subsection_header,
    _print_status,
    get_chain_name,
    load_operator_address,
    validate_config,
)

from wallet_info import save_wallet_info, load_config as load_wallet_config

# Set decimal precision
getcontext().prec = 18
GAS_COSTS_JSON_PATH = OPERATE_HOME / "gas_costs.json"
FUNDING_MULTIPLIER = Decimal(10)
ROUNDING_PRECISION = Decimal('0.0001')
MIN_TRANSACTIONS_SUPPORTED = 5
# Configure logging
logging.basicConfig(level=logging.INFO, format='%(message)s')

class ColorCode:
    """Color code"""
    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    RESET = "\033[0m"

def load_wallet_info() -> dict:
    """Load wallet info from file."""
    save_wallet_info()
    file_path = OPERATE_HOME / "wallets" / "wallet_info.json"
    return _load_json_file(file_path, "Wallet info")

def load_gas_costs(file_path: Path) -> dict:
    """Load gas costs details from file."""
    try: 
        return _load_json_file(file_path, "Gas costs")
    except Exception as e:
        print("No transactions have been recorded until now")
        return {}

def generate_gas_cost_report():
    """Generate and print the gas cost report."""
    try:
        gas_costs = load_gas_costs(GAS_COSTS_JSON_PATH)
        wallet_info = load_wallet_info()
        optimus_config = load_local_config()
        if not wallet_info:
            print("Error: Wallet info is empty.")
            return

        operator_address = load_operator_address(OPERATE_HOME)
        if not operator_address:
            print("Error: Operator address could not be loaded.")
            return

        config = load_wallet_config()
        if not config:
            print("Error: Config is empty.")
            return

        if not validate_config(config):
            return

        _print_report_header()

        for chain_id, _ in config.get("chain_configs", {}).items():
            chain_name = get_chain_name(chain_id, CHAIN_ID_TO_METADATA)
            if optimus_config.allowed_chains and chain_name.lower() not in optimus_config.allowed_chains:
                continue
            if optimus_config.target_investment_chains and chain_name.lower() not in optimus_config.target_investment_chains:
                print(f"WARNING: In the current setting, operability is restricted over {chain_name}")
                continue

            balance_info = wallet_info.get('main_wallet_balances', {}).get(chain_name, {})
            agent_address = wallet_info.get('main_wallet_address', 'N/A')
            chain_rpc = wallet_info.get("chain_configs").get(str(chain_id)).get('rpc')
            analyze_and_report_gas_costs(gas_costs, balance_info, chain_id, chain_name, agent_address, chain_rpc)

    except Exception as e:
        print(f"An unexpected error occurred in generate_gas_cost_report: {e}")

def _load_json_file(file_path: Path, description: str) -> dict:
    """Helper function to load JSON data from a file."""
    try:
        with open(file_path, "r", encoding="utf-8") as file:
            return json.load(file)
    except json.JSONDecodeError:
        print(f"Error: {description} file contains invalid JSON.")
        return {}
    
    return {}

def analyze_and_report_gas_costs(gas_costs: dict, balance_info: Any, chain_id: int, chain_name: str, agent_address: str, chain_rpc: str) -> None:
    """Analyze gas costs and suggest funding amount."""
    _print_subsection_header(f"Funding Recommendation for {chain_name}")

    transactions = gas_costs.get(chain_id, [])
    average_gas_price = _calculate_average_gas_price(chain_rpc)
    if average_gas_price is None:
        print(f"Unable to calculate gas fees for chain_name {chain_name}")
        return 
    if not transactions:
        average_gas_used = 3_00_000
    else:
        total_gas_used = sum(Decimal(tx["gas_used"]) for tx in transactions)
        average_gas_used = total_gas_used / Decimal(len(transactions))

    average_gas_cost = average_gas_used * average_gas_price
    funding_needed, funding_suggestion = _calculate_funding_needed(average_gas_cost, balance_info)
    _report_funding_status(chain_name, balance_info, average_gas_cost, average_gas_price, funding_suggestion, funding_needed, agent_address)

def _calculate_average_gas_price(rpc, fee_history_blocks = 500000, fee_history_percentile = 50) -> Decimal:
    web3 = Web3(Web3.HTTPProvider(rpc))
    block_number = web3.eth.block_number
    fee_history = web3.eth.fee_history(
        fee_history_blocks, block_number, [fee_history_percentile]
    )
    base_fees = fee_history.get('baseFeePerGas')
    if base_fees is None:
        base_fees = [20000000000] #fallback base fee
    
    priority_fees = [reward[0] for reward in fee_history.get('reward',[]) if reward]
    if not priority_fees:
        priority_fees = [2000000000] #fallback priority fee
    
    # Calculate average fees
    average_base_fee = sum(base_fees) / len(base_fees)
    average_priority_fee = sum(priority_fees) / len(priority_fees)

    average_gas_price = average_base_fee + average_priority_fee
    adjusted_gas_price = average_gas_price * 1.5
    return Decimal(adjusted_gas_price)

def _calculate_funding_needed(average_gas_cost: Decimal, balance_info: Any) -> Tuple[Decimal,Decimal]:
    """Calculate the funding needed based on average gas cost and current balance."""
    funding_suggestion = Decimal(average_gas_cost) * FUNDING_MULTIPLIER / Decimal(1e18)
    return max(funding_suggestion - Decimal(balance_info.get('balance', 0)), Decimal(0)), funding_suggestion

def _report_funding_status(chain_name: str, balance_info: Any, average_gas_cost: Decimal, average_gas_price: Decimal, funding_suggestion: Decimal, funding_needed: Decimal, agent_address: str):
    """Report the funding status and suggestions."""
    _print_status(f"[{chain_name}] Current Balance ", balance_info.get('balance_formatted', 'N/A'))
    _print_status(f"[{chain_name}] Average Gas Cost (WEI) ", average_gas_cost)
    _print_status(f"[{chain_name}] Average Gas Price (WEI) ", average_gas_price)
    _print_status(f"[{chain_name}] Amount of ETH to cover for estimated gas cost of the next {FUNDING_MULTIPLIER} Transactions: ", f"{funding_suggestion} ETH")

    average_gas_cost_eth = average_gas_cost / Decimal(1e18)
    current_balance = Decimal(balance_info.get('balance', 0))
    transactions_supported = current_balance / average_gas_cost_eth

    if funding_needed <= 0:
        funding_message = f"[{chain_name}] Current balance can cover for the gas cost of up to {int(transactions_supported)} transactions"
        print(_color_string(funding_message, ColorCode.GREEN))
    elif transactions_supported < MIN_TRANSACTIONS_SUPPORTED:
        funding_needed_rounded = _round_up(funding_needed, ROUNDING_PRECISION)
        funding_message = f"[{chain_name}] BALANCE TOO LOW! Please urgently fund your agent {agent_address} with at least {funding_needed_rounded} ETH to ensure smooth operation"
        print(_color_string(funding_message, ColorCode.RED))
    else:
        funding_needed_rounded = _round_up(funding_needed, ROUNDING_PRECISION)
        funding_message = f"[{chain_name}] Please fund your agent {agent_address} with at least {funding_needed_rounded} ETH to cover future transaction costs"
        print(_color_string(funding_message, ColorCode.YELLOW))

def _round_up(value: Decimal, precision: Decimal) -> Decimal:
    """Round up a Decimal value to a specified precision."""
    return value.quantize(precision, rounding=ROUND_UP)

def _color_string(text: str, color_code: str) -> str:
    return f"{color_code}{text}{ColorCode.RESET}"

def _print_report_header():
    """Print the header for the gas cost report."""
    print("\n==============")
    print("Suggested Funding Report")
    print("Generated on: ", datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    print("==============")

if __name__ == "__main__":
    generate_gas_cost_report()