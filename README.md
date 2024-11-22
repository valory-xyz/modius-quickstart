<h1 align="center">
<b>Olas Modius Quickstart</b>
</h1>



## Olas Modius Agent: Functionality Overview

Olas Modius is an autonomous trader that operates in the crypto echosystem on users' behalf. It requires minimum intervention by you as an end user--it is enough that you fund the agent with initial investment assets and let it run. Modius will intelligentely invest crypto assets in DEXs on your behalf and grow your portfolio.

Modius trades on Balancer over the Mode chain. If you choose to run your Modius agent with staking, in addition to trading profits Modius will also accrue rewards in Olas.


**Operational Process:**
Similar to its human user counterpart, Modius' time is divided in *epoch* days-periods of 24 hours. Throughout one epoch the agent:

1. **Identifies trading opportunities** in investment pools advertised through campaigns on the Merkl platform across the supported DEXs.
2. **Grabs the most interesting one and invests in it:** Starts off by picking the most convenient investment pool amongst the ones with Annual Percentage Yield (APY) higher than 5%. Switches from one investment pool to another when the corresponding APY exceeds that of the previous investment.    
3. **Tracks transactions on the staking chain to accrue Olas staking rewards:** Transactions on Mode serve as key performance indicators (KPIs) for Olas Staking Rewards; in order to collect the corresponding rewards within each epoch, Modius needs to perform a well defined (as per the staking contract) number of them.


#### Notes:

- Staking is currently in a testing phase, so the number of trader agents that can be staked is limited.
- Within each staking period (24hrs) staking happens after the agent has reached its staking contract's KPIs. In the current agent's version, this takes approxiamtely 45 minutes of activity.
- In case a service becomes inactive and remains so for more than 2 staking periods (approx. 48 hours), it faces temporary eviction from the staking program and ceases to accrue additional rewards.
  

## Minimal Funding Requirements

For the initial setup you will need to provide your agent with assets for gas (to cover the costs of the transactions over the operating chain) and for investment funds.

- The initial gas funds amount suggested for Mode is 0.00516 ETH--based on the gas prices observed between Sept 2024 and Nov 2024 included, and may need to be revised.
- The investment fund suggested is of 20 USD (about 20 USDC at the time of the writing).

Additionally, if you choose to run your agent with staking, you will need a total of 40 Olas bridged to Mode.


## Compatible Systems

- Windows 10/11: WSL2
- Mac ARM / Intel
- Linux
- Raspberry Pi 4

## System Requirements

Ensure your machine satisfies the requirements:

- Python `==3.10`
- [Poetry](https://python-poetry.org/docs/) `>=1.4.0`
- [Docker Engine](https://docs.docker.com/engine/install/)
- [Docker Compose](https://docs.docker.com/compose/install/)




## Running the Service: Initial setup

Clone this repository locally and execute:
```bash
chmod +x run_service.sh
./run_service.sh
```

**Tenderly and Price Data Source**

As part of its trading strategies, the agent uses Tenderly to simulate routes for bridges/swaps and pick the best available route at the moment of investment.

- You will need your Tenderly API Key, account slug, and project slug. (Get your own at https://dashboard.tenderly.co/ under settings.)
```bash
Please enter your Tenderly API Key:
Please enter your Tenderly Account Slug:
Please enter your Tenderly Project Slug: 
  ```
Refer to the Tenderly Documentation for more info https://docs.tenderly.co/account/projects.

CoinGecko is used as a price source to compute the initial investment assets you will need to provide the agent with. You will be asked for your CoinGecko API Key. You can get your own at https://www.coingecko.com/. 
Note that, you can also press enter to skip this step. In that case, the agent will fallback to pre-computed values as per the prices observed in Nov 2024.
```bash
Please enter your CoinGecko API Key. Get one at https://www.coingecko.com/:
  ```


**Minimum investment amount**

Successively you will be asked to make a decision on your traded assets limit parameter--the minimum amount to be invested in trades. A pre-computed minimum amount is pompted to you and you can opt to increase it to a value of your choice. Note that this parameter will determine the initial funds requested in a further step by the agent. 

```bash
The minimum investment amount is 15 USD on both USDC and ETH Tokens
Do you want to increase the minimum investment amount? (y/n):
```

**Staking**

The agent will need your answer on staking. If you plan to run it as a non staking agent, please answer _n_ to the question below. Otherwise, please answer _y_ and, consequently when prompted, fund your agent with the required number of bridged Olas in the target staking chain.

```bash
Do you want to stake your service? (y/n):
```

**Investment Activity Chain RPC**

You will be asked for the corresponding RPC for your agent instance. Enter your Mode RPC of preference when you are be prompted with the following request: 

```bash
Please enter a Mode RPC URL:
  ```


## Creating a local user account

When run for the first time, the agent will setup for you a password protected local account. You will be asked to enter and confirm a password as below. 
Please be mindful of storing it in a secure space, for future use. **Hint:** If you do not want to use a password just press Enter when asked to enter and confirm your password.

```bash
Creating a new local user account...
Please enter a password: 
Please confirm your password: 
Creating the main wallet...
```


Finally, when prompted, send the corresponding funds for gas and investment to the corresponding address and you're good to go!



### Service is Running

Once the ./run_service.sh has completed, i.e. the service is running, you can check out the live logs of your Modius agent with:

```bash
docker logs optimus_abci_0 --follow
```

To inspect the tree state transition of the current run of your agent run:

```bash
poetry run autonomy analyse logs --from-dir .olas-modius/services/[service-hash]/deployment/persistent_data/logs/
  --agent aea_0 --fsm --reset-db
```
where `[service-hash]` is the onchain representation of the agent code that you're running. You can get such hash through the following `ls` command:

```bash
ls .olas-modius/services
```



**Service Report**
Additionally, you can execute the service report command to view a summary of the service status, balances, and anything in relation to Olas Staking and accrual of rewards:

```bash
poetry run python report.py
```

**Funding Report**
Finally, you can execute the funding report command to check out balances for each of the chains your service is deployed onto. 

```bash
poetry run suggest_funding_report.py
```
The report will also give you insights on the latest observed gas prices per chain and, if necessary, suggest gas funding values to keep your agent active.  


**Stoppping your agent**
To stop your agent, use:

```bash
./stop_service.sh
```



## Update between versions

Simply pull the latest script:

```bash
git pull origin
```

Then run again your service with:

```bash
./run_service.sh
```



## Terms and Conditions Disclaimer

> :warning: **Warning** <br />
> The code within this repository is provided without any warranties. It leverages third party APIs and it is important to note that the code has not been audited for potential security vulnerabilities.
> Using this code could potentially lead to loss of funds, compromised data, or asset risk.
> Exercise caution and use this code at your own risk. Please refer to the [LICENSE](./LICENSE) file for details about the terms and conditions.



## What's New --- [This is to be reviewed after we have a release v.]

### Release v0.2.9???
Introduces Olas Modius
- Added Mode as default chain for staking and as primary chain for investment funds
- Removed Eth Mainnet from the pool of selectable chains due to gas costs
- Added bridging to support Mode
- Added investment strategy targeting Balancer investment pools on Mode


### Release v0.2.8
New report script added `suggest_funding_report.py`.
For every chain it reports to the user
- Balance in ETH
- the gas cost, gas price per transaction (avg over last 10 transactions)
- Forecast of gas consumption cost for next 10 transactions in ETH
- Potentially a call to action to fund the agent

### Release v0.2.7

Introduces a minimum swap amount threshold (traded assets limit) configurable via script. It dynamically adjusts the initial ETH and USDC funding requirements based on this limit.

### Release v0.2.6
Token swap and bridging process is improved so that if an issue arises, the agent automatically switches to an alternative route without re-starting the bridging process. It ensures costs, such as gas fees, remain within set limits.

### Release v0.2.5
Optimus agent only proceeds with a bridge or swap transaction when both the relayer fee and gas costs are kept within reasonable limits, helping to control transaction costs.


## Advice for Windows users on installing Windows Subsystem for Linux version 2 (WSL2)

1. Open a **Command Prompt** terminal as an Administrator.

2. Run the following commands:

    ```bash
    dism.exe /online /enable-feature /featurename:Microsoft-Windows-Subsystem-Linux /all /norestart
    ```

    ```bash
    dism.exe /online /enable-feature /featurename:VirtualMachinePlatform /all /norestart
    ```

3. Then restart the computer.

4. Open a **Command Prompt** terminal.

5. Make WSL2 the default version by running:

    ```bash
    wsl --set-default-version 2
    ```

6. Install Ubuntu 22.04 by running:

    ```bash
    wsl --install -d Ubuntu-22.04
    ```

7. Follow the on-screen instructions and set a username and password for your Ubuntu installation.

8. Install Docker Desktop and enable the WSL 2 backend by following the instructions from Docker [here](https://docs.docker.com/desktop/wsl/).
