# utils.py
import json
from pathlib import Path
from datetime import datetime
from decimal import Decimal, getcontext
import logging
import docker
from web3 import Web3
from web3.middleware import geth_poa_middleware
from enum import Enum
from operate.cli import OperateApp
import yaml
# Set decimal precision
getcontext().prec = 18

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(message)s')

# Terminal color codes
class ColorCode:
    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    RESET = "\033[0m"

class StakingState(Enum):
    """Staking state enumeration for the staking."""
    UNSTAKED = 0
    STAKED = 1
    EVICTED = 2

from run_service import (
    load_local_config,
    get_service_template,
    get_service,
    OPERATE_HOME
)

def _color_string(text: str, color_code: str) -> str:
    return f"{color_code}{text}{ColorCode.RESET}"

def _color_bool(is_true: bool, true_string: str = "True", false_string: str = "False") -> str:
    if is_true:
        return _color_string(true_string, ColorCode.GREEN)
    return _color_string(false_string, ColorCode.RED)

def _warning_message(current_value: Decimal, threshold: Decimal, message: str = "") -> str:
    default_message = _color_string(
        f"- Value too low. Threshold is {threshold:.2f}.",
        ColorCode.YELLOW,
    )
    if current_value < threshold:
        return _color_string(message or default_message, ColorCode.YELLOW)
    return ""

def _print_section_header(header: str, output_width: int = 80) -> None:
    print("\n\n" + header)
    print("=" * output_width)

def _print_subsection_header(header: str, output_width: int = 80) -> None:
    print("\n" + header)
    print("-" * output_width)

def _print_status(key: str, value: str, message: str = "") -> None:
    line = f"{key:<30}{value:<20}"
    if message:
        line += f"{message}"
    print(line)

def wei_to_unit(wei: int) -> Decimal:
    """Convert Wei to unit."""
    return Decimal(wei) / Decimal(1e18)

def wei_to_token(wei: int, token: str = "xDAI") -> str:
    """Convert Wei to token."""
    return f"{wei_to_unit(wei):.2f} {token}"

def wei_to_olas(wei: int) -> str:
    """Converts and formats wei to OLAS."""
    return "{:.2f} OLAS".format(wei_to_unit(wei))

def wei_to_eth(wei_value):
    return Decimal(wei_value) / Decimal(1e18)

def get_chain_name(chain_id, chain_id_to_metadata):
    return chain_id_to_metadata.get(int(chain_id), {}).get("name", f"Chain {chain_id}")

def load_operator_address(operate_home):
    ethereum_json_path = operate_home / "wallets" / "ethereum.json"
    try:
        with open(ethereum_json_path, "r") as f:
            ethereum_data = json.load(f)
        operator_address = ethereum_data.get("address", None)
        if not operator_address:
            print("Error: Operator address not found in the wallet file.")
            return None
        return operator_address
    except FileNotFoundError:
        print(f"Error: Ethereum wallet file not found at {ethereum_json_path}")
        return None
    except json.JSONDecodeError:
        print("Error: Ethereum wallet file contains invalid JSON.")
        return None

def load_operator_safe_balance(operate_home):
    ethereum_json_path = operate_home / "wallets" / "ethereum.json"
    try:
        with open(ethereum_json_path, "r") as f:
            ethereum_data = json.load(f)

        safe_chains = ethereum_data.get("safe_chains", [])
        if not safe_chains:
            print("Error: Safe chains array is empty.")
            return None

        chain_id = safe_chains[0]

        safes = ethereum_data.get("safes", {})
        safe_address = safes.get(str(chain_id))
        if not safe_address:
            print(f"Error: Safe address for chain ID {chain_id} not found in the wallet file.")
            return None

        # Here, you should insert your logic to fetch the safe balance from the blockchain
        # For illustrative purposes, we'll just return the safe address
        return safe_address

    except FileNotFoundError:
        print(f"Error: Ethereum wallet file not found at {ethereum_json_path}")
        return None
    except json.JSONDecodeError:
        print("Error: Ethereum wallet file contains invalid JSON.")
        return None
    
def validate_config(config):
    required_keys = ['home_chain_id', 'chain_configs']
    for key in required_keys:
        if key not in config:
            print(f"Error: '{key}' is missing in the configuration.")
            return False
    return True

def _get_agent_status() -> str:
    operate = OperateApp(
        home=OPERATE_HOME,
    )
    operate.setup()

    optimus_config = load_local_config()
    template = get_service_template(optimus_config)
    manager = operate.service_manager()
    service = get_service(manager, template)
    docker_compose_path = service.path / "deployment" / "docker-compose.yaml"
    try:
        with open(docker_compose_path, "r") as f:
            docker_compose = yaml.safe_load(f)

        abci_service_name = None
        for service_name in docker_compose["services"]:
            if "abci" in service_name:
                abci_service_name = service_name
                break

        client = docker.from_env()
        container = client.containers.get(abci_service_name)
        is_running = container.status == "running"
        return _color_bool(is_running, "Running", "Stopped")
    except FileNotFoundError:
        return _color_string("Stopped", ColorCode.RED)
    except docker.errors.NotFound:
        return _color_string("Not Found", ColorCode.RED)
    except docker.errors.DockerException as e:
        print(f"Error: Docker exception occurred - {str(e)}")
        return _color_string("Error", ColorCode.RED)
