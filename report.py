# report.py
import warnings
warnings.filterwarnings("ignore", category=UserWarning)
import json
from datetime import datetime
import logging
from decimal import Decimal, getcontext

from run_service import (
    load_local_config,
    get_service_template,
    CHAIN_ID_TO_METADATA,
    OPERATE_HOME
)

from utils import (
    _print_section_header,
    _print_subsection_header,
    _print_status,
    wei_to_eth,
    _warning_message,
    get_chain_name,
    load_operator_address,
    validate_config,
    _get_agent_status,
)

from run_service import fetch_agent_fund_requirement
from wallet_info import save_wallet_info, load_config as load_wallet_config
from staking_report import staking_report

# Set decimal precision
getcontext().prec = 18

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(message)s')

def load_wallet_info():
    save_wallet_info()
    file_path = OPERATE_HOME / "wallets" / "wallet_info.json"
    try:
        with open(file_path, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Error: Wallet info file not found at {file_path}")
        return {}
    except json.JSONDecodeError:
        print("Error: Wallet info file contains invalid JSON.")
        return {}

def get_chain_rpc(optimus_config, chain_name):
    chain_name_to_rpc = {
        'mode': optimus_config.mode_rpc
    }
    return chain_name_to_rpc.get(chain_name.lower())

def generate_report():
    try:
        # First, update the wallet info
        wallet_info = load_wallet_info()
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

        optimus_config = load_local_config()
        # Service Report Header
        print("")
        print("==============")
        print("Olas Modius Service Report")
        print("Generated on: ", datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        print("==============")

        staking_report(config)
        home_chain_id = config.get("home_chain_id")
        service_id = config.get("chain_configs", {}).get(str(home_chain_id), {}).get("chain_data", {}).get("token")
        if not service_id:
            print(f"Error: 'token' not found in chain data for chain ID {home_chain_id}.")
            return

        # Service Section
        _print_section_header("Service")
        _print_status("ID", str(service_id))

        # Agent Section
        agent_status = _get_agent_status()
        _print_subsection_header("Agent")
        _print_status("Status (on this machine)", agent_status)
        _print_status("Address", wallet_info.get('main_wallet_address', 'N/A'))

        for chain_id, chain_config in config.get("chain_configs", {}).items():
            chain_name = get_chain_name(chain_id, CHAIN_ID_TO_METADATA)
            if  optimus_config.allowed_chains and chain_name.lower() not in optimus_config.allowed_chains:
                continue
            balance_info = wallet_info.get('main_wallet_balances', {}).get(chain_name, {})
            balance_formatted = balance_info.get('balance_formatted', 'N/A')
            _print_status(f"{chain_name} Balance", balance_formatted)

            # Low balance check
            agent_threshold_wei = fetch_agent_fund_requirement(chain_id, get_chain_rpc(optimus_config, chain_name))
            if agent_threshold_wei is None:
                agent_threshold_wei = chain_config.get("chain_data", {}).get("user_params", {}).get("fund_requirements", {}).get("agent")
            if agent_threshold_wei:
                agent_threshold_eth = wei_to_eth(agent_threshold_wei)
                current_balance_str = balance_formatted.split()[0]
                try:
                    current_balance = Decimal(current_balance_str)
                    if current_balance < agent_threshold_eth:
                        warning_msg = _warning_message(current_balance, agent_threshold_eth, f"Balance below threshold of {agent_threshold_eth:.5f} ETH")
                        _print_status("Warning", warning_msg)
                except (ValueError, Exception):
                    print(f"Warning: Could not parse balance '{balance_formatted}' for chain '{chain_name}'.")

        # Safe Section
        _print_subsection_header("Safe")
        safe_balances = wallet_info.get('safe_balances', {})
        for chain_id, chain_config in config.get("chain_configs", {}).items():
            chain_name = get_chain_name(chain_id, CHAIN_ID_TO_METADATA)
            if  optimus_config.allowed_chains and chain_name.lower() not in optimus_config.allowed_chains:
                continue
            if optimus_config.target_investment_chains and chain_name.lower() not in optimus_config.target_investment_chains:
                print(f"WARNING: In the current setting, operability is restricted over {chain_name}")

            safe_info = safe_balances.get(chain_name, {})
            _print_status(f"Address ({chain_name})", safe_info.get('address', 'N/A'))
            _print_status(f"{safe_info.get('token', 'ETH')} Balance", safe_info.get('balance_formatted', 'N/A'))

            # Check for USDC balance on Principal Chain
            if chain_name.lower() == optimus_config.principal_chain:
                usdc_balance_formatted = safe_info.get('usdc_balance_formatted', 'N/A')
                _print_status("USDC Balance", usdc_balance_formatted)
            
            # Check for OLAS balance on Staking chain
            if chain_name.lower() == optimus_config.staking_chain:
                olas_balance_formatted = safe_info.get('olas_balance_formatted', 'N/A')
                _print_status("OLAS Balance", olas_balance_formatted)
            
            # Low balance check
            safe_threshold_wei = chain_config.get("chain_data", {}).get("user_params", {}).get("fund_requirements", {}).get("safe")
            if safe_threshold_wei:
                safe_threshold_eth = wei_to_eth(safe_threshold_wei)
                balance_str = safe_info.get('balance_formatted', '0').split()[0]
                try:
                    current_balance = Decimal(balance_str)
                    if current_balance < safe_threshold_eth:
                        warning_msg = _warning_message(current_balance, safe_threshold_eth, f"Balance below threshold of {safe_threshold_eth:.5f} ETH")
                        _print_status("Warning", warning_msg)
                except (ValueError, Exception):
                    print(f"Warning: Could not parse balance '{balance_str}' for chain '{chain_name}'.")
            print()
        # Owner/Operator Section
        _print_subsection_header("Owner/Operator")
        _print_status("Address", operator_address)
        for chain_name, balance_info in wallet_info.get('operator_balances', {}).items():
            _print_status(f"{chain_name} Balance", balance_info.get('balance_formatted', 'N/A'))

    except Exception as e:
        print(f"An unexpected error occurred in generate_report: {e}")

if __name__ == "__main__":
    generate_report()
