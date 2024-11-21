# staking_report.py
import warnings
warnings.filterwarnings("ignore", category=UserWarning)
import json
import math
from pathlib import Path
from web3 import Web3, HTTPProvider
from decimal import Decimal, getcontext
import logging

from run_service import (
    get_service_template,
    FALLBACK_STAKING_PARAMS,
    CHAIN_ID_TO_METADATA,
    OPERATE_HOME,
)

from operate.ledger.profiles import STAKING
from operate.types import ChainType

from utils import (
    _print_section_header,
    _print_subsection_header,
    _print_status,
    wei_to_olas,
    wei_to_eth,
    _warning_message,
    StakingState,
    get_chain_name,
    load_operator_safe_balance,
    validate_config,
    _color_bool,
    _color_string,
    ColorCode

)

# Set decimal precision
getcontext().prec = 18

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(message)s')

SCRIPT_PATH = Path(__file__).resolve().parent
STAKING_TOKEN_JSON_PATH = SCRIPT_PATH / "contracts" / "StakingToken.json"
ACTIVITY_CHECKER_JSON_PATH = SCRIPT_PATH / "contracts" / "StakingActivityChecker.json"
SERVICE_REGISTRY_TOKEN_UTILITY_JSON_PATH = SCRIPT_PATH / "contracts" / "ServiceRegistryTokenUtility.json"

def staking_report(config: dict) -> None:
    try:
        _print_section_header("Performance")
        
        operator_address = load_operator_safe_balance(OPERATE_HOME)
        if not operator_address:
            print("Error: Operator address could not be loaded.")
            return

        # Find the chain configuration where use_staking is True
        chain_data = next(
            (
                data for data in config.get("chain_configs", {}).values()
                if data.get("chain_data", {}).get("user_params", {}).get("use_staking")
            ),
            None
        )
        if not chain_data:
            return

        _print_subsection_header("Staking")

        rpc = chain_data.get("ledger_config", {}).get("rpc")
        if not rpc:
            print("Error: RPC endpoint not found in ledger configuration.")
            return

        staking_program_id = chain_data.get("chain_data", {}).get("user_params", {}).get("staking_program_id")
        if not staking_program_id:
            print("Error: 'staking_program_id' not found in user parameters.")
            return

        home_chain_id = config.get("home_chain_id")
        if not home_chain_id:
            print("Error: 'home_chain_id' not found in config.")
            return

        service_id = config.get("chain_configs", {}).get(str(home_chain_id), {}).get("chain_data", {}).get("token")
        if not service_id:
            print(f"Error: 'token' not found in chain data for chain ID {home_chain_id}.")
            return

        multisig_address = config.get("chain_configs", {}).get(str(home_chain_id), {}).get("chain_data", {}).get("multisig")
        if not multisig_address:
            print(f"Error: 'multisig' address not found in chain data for chain ID {home_chain_id}.")
            return

        w3 = Web3(HTTPProvider(rpc))

        home_chain_type = ChainType.from_id(int(home_chain_id))
        staking_token_address = STAKING.get(home_chain_type, {}).get("optimus_alpha")
        if not staking_token_address:
            print("Error: Staking token address not found.")
            return

        # Load ABI files
        with open(STAKING_TOKEN_JSON_PATH, "r", encoding="utf-8") as file:
            staking_token_data = json.load(file)
        staking_token_abi = staking_token_data.get("abi", [])
        staking_token_contract = w3.eth.contract(
            address=staking_token_address, abi=staking_token_abi  # type: ignore
        )

        # Get staking state
        staking_state_value = staking_token_contract.functions.getStakingState(service_id).call()
        staking_state = StakingState(staking_state_value)
        is_staked = staking_state in (StakingState.STAKED, StakingState.EVICTED)
        _print_status("Is service staked?", _color_bool(is_staked, "Yes", "No"))
        if is_staked:
            _print_status("Staking program",("modius_"+ str(staking_program_id) + " " +str(home_chain_type).rsplit('.', maxsplit=1)[-1]))
            _print_status("Staking state", staking_state.name if staking_state == StakingState.STAKED else _color_string(staking_state.name, ColorCode.RED))

            # Activity Checker
            activity_checker_address = staking_token_contract.functions.activityChecker().call()
            with open(ACTIVITY_CHECKER_JSON_PATH, "r", encoding="utf-8") as file:
                activity_checker_data = json.load(file)
            activity_checker_abi = activity_checker_data.get("abi", [])
            activity_checker_contract = w3.eth.contract(
                address=activity_checker_address, abi=activity_checker_abi  # type: ignore
            )

            # Service Registry Token Utility
            with open(SERVICE_REGISTRY_TOKEN_UTILITY_JSON_PATH, "r", encoding="utf-8") as file:
                service_registry_token_utility_data = json.load(file)
            service_registry_token_utility_contract_address = staking_token_contract.functions.serviceRegistryTokenUtility().call()
            service_registry_token_utility_abi = service_registry_token_utility_data.get("abi", [])
            service_registry_token_utility_contract = w3.eth.contract(
                address=service_registry_token_utility_contract_address,
                abi=service_registry_token_utility_abi,
            )

            # Get security deposit
            security_deposit = service_registry_token_utility_contract.functions.getOperatorBalance(
                operator_address, service_id
            ).call()

            # Get agent bond
            agent_ids = FALLBACK_STAKING_PARAMS.get("agent_ids", [])
            if not agent_ids:
                print("Error: 'agent_ids' not found in FALLBACK_STAKING_PARAMS.")
                return
            agent_bond = service_registry_token_utility_contract.functions.getAgentBond(
                service_id, agent_ids[0]
            ).call()

            min_staking_deposit = staking_token_contract.functions.minStakingDeposit().call()
            min_security_deposit = min_staking_deposit

            security_deposit_formatted = wei_to_olas(security_deposit)
            agent_bond_formatted = wei_to_olas(agent_bond)
            min_staking_deposit_formatted = wei_to_olas(min_staking_deposit)

            security_deposit_decimal = Decimal(security_deposit_formatted.split()[0])
            min_security_deposit_decimal = Decimal(min_staking_deposit_formatted.split()[0])

            agent_bond_decimal = Decimal(agent_bond_formatted.split()[0])

            _print_status(
                "Staked (security deposit)",
                security_deposit_formatted,
                _warning_message(security_deposit_decimal, min_security_deposit_decimal)
            )
            _print_status(
                "Staked (agent bond)",
                agent_bond_formatted,
                _warning_message(agent_bond_decimal, min_security_deposit_decimal)
            )

            # Accrued rewards
            service_info = staking_token_contract.functions.mapServiceInfo(service_id).call()
            rewards = service_info[3]
            _print_status("Accrued rewards", wei_to_olas(rewards))

            # Liveness ratio and transactions
            liveness_ratio = activity_checker_contract.functions.livenessRatio().call()
            multisig_nonces_24h_threshold = math.ceil(
                (liveness_ratio * 60 * 60 * 24) / Decimal(1e18)
            )

            multisig_nonces = activity_checker_contract.functions.getMultisigNonces(multisig_address).call()
            multisig_nonces = multisig_nonces[0]
            service_info = staking_token_contract.functions.getServiceInfo(service_id).call()
            multisig_nonces_on_last_checkpoint = service_info[2][0]
            multisig_nonces_since_last_cp = multisig_nonces - multisig_nonces_on_last_checkpoint
            multisig_nonces_current_epoch = multisig_nonces_since_last_cp
            _print_status(
                f"{str(home_chain_type).rsplit('.', maxsplit=1)[-1]} txs in current epoch ",
                str(multisig_nonces_current_epoch),
                _warning_message(
                    Decimal(multisig_nonces_current_epoch),
                    Decimal(multisig_nonces_24h_threshold),
                    f"- Too low. Threshold is {multisig_nonces_24h_threshold}."
                )
            )

    except Exception as e:
        print(f"An unexpected error occurred in staking_report: {e}")

if __name__ == "__main__":
    try:
        # Load configuration
        config = load_config()
        if not config:
            print("Error: Config is empty.")
        else:
            staking_report(config)
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
