import requests
import logging
from datetime import datetime
from web3 import Web3
from eth_account import Account
from eth_account.messages import encode_defunct
import random
import time
from decimal import Decimal
import asyncio

# Set logging configuration
logging.basicConfig(format="%(levelname)s: %(asctime)s: %(message)s", level=logging.INFO, datefmt='%Y-%m-%d %H:%M:%S')


def get_time_left(target_timestamp):
    current_timestamp = int(datetime.now().timestamp())
    return target_timestamp - current_timestamp


def generate_new_eth_address():
    # Generate a new Ethereum account
    account = Account.create()
    # Return the address and private key
    return account.address


# Initialize Web3 with the provided RPC URL
RPC_URL = 'https://rpc-testnet.inichain.com'
web3 = Web3(Web3.HTTPProvider(RPC_URL))

# Check connection
if not web3.is_connected():
    raise ConnectionError("Failed to connect to testnet")


def send_testnet_eth(private_key: str, receiver_address: str, amount_in_ether: float, retries: int = 3):
    """
    Sends testnet ETH with retries, increasing gas price by 10% for each retry if sending fails.

    :param private_key: Sender's private key as a string
    :param receiver_address: Receiver's wallet address as a string
    :param amount_in_ether: Amount to send in Ether
    :param retries: Number of retries (default: 3)
    :return: Transaction hash as a string if successful
    """
    sender_address = web3.eth.account.from_key(private_key).address
    amount_in_wei = web3.to_wei(amount_in_ether, 'ether')

    nonce = web3.eth.get_transaction_count(sender_address, 'pending')
    gas_price = web3.eth.gas_price  # Fetch the current gas price

    for attempt in range(1, retries + 1):
        try:
            # Build the transaction
            transaction = {
                'to': receiver_address,
                'value': amount_in_wei,
                'gas': 100000,
                'gasPrice': int(gas_price * 1.5),
                'nonce': nonce,
                'chainId': web3.eth.chain_id
            }

            # Sign and send the transaction
            signed_tx = web3.eth.account.sign_transaction(transaction, private_key)
            tx_hash = web3.eth.send_raw_transaction(signed_tx.raw_transaction)

            # Wait for transaction receipt
            receipt = web3.eth.wait_for_transaction_receipt(tx_hash, timeout=300)

            if receipt['status'] == 1:
                logging.info(f"Account {short_address(sender_address)}: Transferred {amount_in_ether} INI to {receiver_address} successfully!")
                return tx_hash.hex()  # Return transaction hash if successful
            else:
                raise Exception(f"Account {short_address(sender_address)}: Transaction failed")

        except Exception as e:
            logging.warning(f"Account {short_address(sender_address)}: Transaction failed ({attempt}) with error: {str(e)}")

            if attempt < retries:
                gas_price = int(gas_price * 1.5)  # Increase gas price by 10% for the next attempt
                logging.info(f"Increasing gas price to {gas_price} for retry {attempt + 1}")
            else:
                logging.error("Max retries reached. Transaction failed.")
                raise  # Re-raise the exception if retries are exhausted


class INISwapper:
    def __init__(self, network_url, private_key):
        self.web3 = Web3(Web3.HTTPProvider(network_url))
        self.account = Account.from_key(private_key)
        self.wallet_address = self.account.address

        # Convert addresses to checksum format
        self.router_address = Web3.to_checksum_address("0x4ccB784744969D9B63C15cF07E622DDA65A88Ee7")
        self.token1_address = Web3.to_checksum_address("0xfbecae21c91446f9c7b87e4e5869926998f99ffe")
        self.token2_address = Web3.to_checksum_address("0xcf259bca0315c6d32e877793b6a10e97e7647fde")

        # Known ratio from transaction
        self.ini_to_usdt_ratio = Decimal('5.74')

        # Extended ABI to include USDT->INI swap function
        self.router_abi = [
            {
                "inputs": [
                    {"internalType": "uint256", "name": "amountOutMin", "type": "uint256"},
                    {"internalType": "address[]", "name": "path", "type": "address[]"},
                    {"internalType": "address", "name": "to", "type": "address"},
                    {"internalType": "uint256", "name": "deadline", "type": "uint256"}
                ],
                "name": "swapExactETHForTokensSupportingFeeOnTransferTokens",
                "outputs": [],
                "stateMutability": "payable",
                "type": "function"
            },
            {
                "inputs": [
                    {"internalType": "uint256", "name": "amountIn", "type": "uint256"},
                    {"internalType": "uint256", "name": "amountOutMin", "type": "uint256"},
                    {"internalType": "address[]", "name": "path", "type": "address[]"},
                    {"internalType": "address", "name": "to", "type": "address"},
                    {"internalType": "uint256", "name": "deadline", "type": "uint256"}
                ],
                "name": "swapExactTokensForTokens",
                "outputs": [{"internalType": "uint256[]", "name": "amounts", "type": "uint256[]"}],
                "stateMutability": "nonpayable",
                "type": "function"
            }
        ]

        self.router_contract = self.web3.eth.contract(
            address=self.router_address,
            abi=self.router_abi
        )

        # USDT token contract ABI for approval
        self.token_abi = [
            {
                "inputs": [
                    {"internalType": "address", "name": "spender", "type": "address"},
                    {"internalType": "uint256", "name": "amount", "type": "uint256"}
                ],
                "name": "approve",
                "outputs": [{"internalType": "bool", "name": "", "type": "bool"}],
                "stateMutability": "nonpayable",
                "type": "function"
            }
        ]

        self.usdt_contract = self.web3.eth.contract(
            address=self.token2_address,
            abi=self.token_abi
        )

    def calculate_min_output(self, ini_amount, slippage_percentage=1):
        """
        Calculate minimum USDT output based on INI input
        ini_amount: amount in wei
        slippage_percentage: allowed slippage (default 1%)
        """
        # Convert wei to INI for calculation
        ini_amount_eth = Decimal(str(Web3.from_wei(ini_amount, 'ether')))

        # Calculate expected USDT output
        expected_usdt = ini_amount_eth * self.ini_to_usdt_ratio

        # Apply slippage tolerance
        slippage_multiplier = Decimal(str(100 - slippage_percentage)) / Decimal('100')
        min_output = expected_usdt * slippage_multiplier

        # Convert back to wei
        return Web3.to_wei(float(min_output), 'ether')

    def calculate_min_ini_output(self, usdt_amount, slippage_percentage=1):
        """
        Calculate minimum INI output based on USDT input
        usdt_amount: amount in wei
        slippage_percentage: allowed slippage (default 1%)
        """
        # Convert wei to USDT for calculation
        usdt_amount_eth = Decimal(str(Web3.from_wei(usdt_amount, 'ether')))

        # Calculate expected INI output (inverse of USDT ratio)
        expected_ini = usdt_amount_eth / self.ini_to_usdt_ratio

        # Apply slippage tolerance
        slippage_multiplier = Decimal(str(100 - slippage_percentage)) / Decimal('100')
        min_output = expected_ini * slippage_multiplier

        # Convert back to wei
        return Web3.to_wei(float(min_output), 'ether')

    def get_gas_price_with_premium(self, premium=10):
        """Get current gas price and add 10% premium"""
        premium = (100 + premium) / 100
        base_gas_price = self.web3.eth.gas_price
        return int(base_gas_price * premium)

    def approve_usdt(self, amount):
        """
        Approve USDT spending for router
        """
        nonce = self.web3.eth.get_transaction_count(self.account.address)
        gas_price = self.get_gas_price_with_premium()

        approve_txn = self.usdt_contract.functions.approve(
            self.router_address,
            amount
        ).build_transaction({
            'from': self.account.address,
            'gas': 100000,
            'gasPrice': gas_price,
            'nonce': nonce
        })

        signed_txn = self.web3.eth.account.sign_transaction(approve_txn, self.account.key)
        tx_hash = self.web3.eth.send_raw_transaction(signed_txn.raw_transaction)
        return self.web3.eth.wait_for_transaction_receipt(tx_hash, timeout=300)

    def swap_usdt_to_ini(self, amount_usdt, max_retries=3):
        """
        Swap USDT for INI with retry logic
        amount_usdt: amount in USDT to swap (in wei)
        max_retries: maximum number of retry attempts
        """
        # Calculate minimum INI output with 1% slippage tolerance
        min_ini_out = self.calculate_min_ini_output(amount_usdt)

        logging.info(
            f"Account {short_address(self.wallet_address)}: Swapping {Web3.from_wei(amount_usdt, 'ether')} USDT -> {Web3.from_wei(min_ini_out, 'ether')} INI")

        # First approve USDT spending
        self.approve_usdt(amount_usdt)

        premium = 10
        for attempt in range(max_retries):
            try:
                deadline = self.web3.eth.get_block('latest').timestamp + 600
                nonce = self.web3.eth.get_transaction_count(self.account.address)
                gas_price = self.get_gas_price_with_premium(premium=premium)

                # logging.info(f"Token path: {self.token2_address} -> {self.token1_address}")

                swap_txn = self.router_contract.functions.swapExactTokensForTokens(
                    amount_usdt,
                    min_ini_out,
                    [self.token2_address, self.token1_address],  # Reversed path for USDT->INI
                    self.account.address,
                    deadline
                ).build_transaction({
                    'from': self.account.address,
                    'gas': 300000,
                    'gasPrice': gas_price,
                    'nonce': nonce
                })

                signed_txn = self.web3.eth.account.sign_transaction(swap_txn, self.account.key)
                tx_hash = self.web3.eth.send_raw_transaction(signed_txn.raw_transaction)

                wallet_address = self.account.address
                logging.info(f"Account {short_address(wallet_address)}: Swap Transaction Pending swap_usdt_to_ini...")
                receipt = self.web3.eth.wait_for_transaction_receipt(tx_hash, timeout=300)
                return receipt
            except Exception as e:
                if "replacement transaction underpriced" in str(e):
                    if attempt < max_retries - 1:
                        premium += 50
                        logging.error(
                            f"Transaction underpriced, retrying with higher gas price... (Attempt {attempt + 1}/{max_retries})")
                        time.sleep(2)
                        continue
                logging.error(f"Account {short_address(self.wallet_address)}: Detailed error: {str(e)}")
                raise e

    def swap_ini_to_usdt(self, amount_ini, max_retries=3):
        """
        Swap INI for USDT with retry logic
        amount_ini: amount in INI to swap (in wei)
        max_retries: maximum number of retry attempts
        """
        # Calculate minimum USDT output with 1% slippage tolerance
        min_usdt_out = self.calculate_min_output(amount_ini)

        logging.info(
            f"Account {self.wallet_address}: Swapping {Web3.from_wei(amount_ini, 'ether')} INI -> {Web3.from_wei(min_usdt_out, 'ether')} USDT")

        premium = 50
        for attempt in range(max_retries):
            try:
                deadline = self.web3.eth.get_block('latest').timestamp + 600
                nonce = self.web3.eth.get_transaction_count(self.account.address)
                gas_price = self.get_gas_price_with_premium(premium=premium)

                # logging.info(f"Token path: {self.token1_address} -> {self.token2_address}")

                swap_txn = self.router_contract.functions.swapExactETHForTokensSupportingFeeOnTransferTokens(
                    min_usdt_out,
                    [self.token1_address, self.token2_address],
                    self.account.address,
                    deadline
                ).build_transaction({
                    'from': self.account.address,
                    'gas': 300000,
                    'gasPrice': gas_price,
                    'nonce': nonce,
                    'value': amount_ini
                })

                signed_txn = self.web3.eth.account.sign_transaction(swap_txn, self.account.key)
                tx_hash = self.web3.eth.send_raw_transaction(signed_txn.raw_transaction)

                logging.info(f"Account {short_address(self.wallet_address)}: Transaction Pending `swap_ini_to_usdt`...")
                receipt = self.web3.eth.wait_for_transaction_receipt(tx_hash, timeout=300)
                return receipt
            except Exception as e:
                if "replacement transaction underpriced" in str(e):
                    if attempt < max_retries - 1:
                        premium += 50
                        logging.error(
                            f"Transaction underpriced, retrying with higher gas price... (Attempt {attempt + 1}/{max_retries})")
                        time.sleep(2)
                        continue
                logging.error(f"Detailed error: {str(e)}")
                raise e


def swap_ini(private_key):
    # Your testnet network URL

    # Get sender address from private key
    wallet_address = web3.eth.account.from_key(private_key).address

    # Initialize swapper
    swapper = INISwapper(RPC_URL, private_key)

    # Amount to swap (0.173121 INI)
    amount = random.randint(1, 100)
    amount_ini = Web3.to_wei(Decimal(f'0.0000001{amount}'), 'ether')

    result = swapper.swap_usdt_to_ini(amount_ini)
    if dict(result)['status'] == 1:
        logging.info(
            f"Account {short_address(wallet_address)}: USDT -> INI Swap successful!")
        return
    else:
        logging.error(f"Account {short_address(wallet_address)}: USDT -> INI Swap failed")
        result = swapper.swap_ini_to_usdt(amount_ini)
        if dict(result)['status'] == 1:
            logging.info(
                f"Account {short_address(wallet_address)}: INI -> USDT Swap successful!")
            return
        else:
            logging.error(f"Account {short_address(wallet_address)}: INI -> USDT Swap failed")


def get_task_status(wallet_address):
    url = f'https://candyapi.inichain.com/airdrop/v1/user/UserTaskStatus?address={wallet_address}'
    r = requests.get(url)
    if r.status_code == 200:
        data = r.json()["data"]
        return data


def get_swap_info(wallet_address):
    daily_task_info = get_task_status(wallet_address)['dailyTaskInfo']
    swap_count = daily_task_info[1]['count']
    swap_timestamp = daily_task_info[1]['time']
    return swap_count, swap_timestamp


def get_checkin_info(wallet_address):
    daily_task_info = get_task_status(wallet_address)['dailyTaskInfo']
    days = daily_task_info[0]['days']
    complete_days = daily_task_info[0]['completeDays']
    checkin_count = f"{complete_days}/{days}"
    checkin_timestamp = daily_task_info[0]['time']
    return checkin_count, checkin_timestamp


def short_address(wallet_address):
    address = f"{''.join(wallet_address[:5])}..{''.join(wallet_address[-5:])}"
    return address


def perform_daily_checkin(private_key, max_retries=3):
    """
    Performs INI daily check-in process including transaction and message signing.
    Args:
        web3: Web3 instance connected to INI network
        private_key: Account private key
        max_retries: Maximum retry attempts for failed transactions
    Returns:
        tuple (transaction receipt, signed message)
    """
    account = web3.eth.account.from_key(private_key)
    wallet_address = account.address
    abridged_address = short_address(wallet_address)

    checkin_address = web3.to_checksum_address("0x73439c32e125B28139823fE9C6C079165E94C6D1")

    # Check balance first
    balance = web3.eth.get_balance(account.address)
    logging.info(f"{short_address(account.address)}: Current balance: {web3.from_wei(balance, 'ether')} INI")

    # Check-in contract ABI
    checkin_abi = [{
        "inputs": [],
        "name": "checkIn",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
        "constant": False,
        "payable": False,
        "signature": "0x183ff085"
    }]

    checkin_contract = web3.eth.contract(address=checkin_address, abi=checkin_abi)

    for attempt in range(max_retries):
        try:
            # Use a much lower gas price
            gas_price = int(1e9)  # 1 Gwei
            estimated_gas = web3.eth.estimate_gas({
                'to': checkin_address,
                'from': account.address,
                'data': "0x183ff085"  # checkIn function signature
            })

            total_cost = gas_price * estimated_gas
            if balance < total_cost:
                raise Exception(f"Insufficient balance. Need {web3.from_wei(total_cost, 'ether')} INI for gas")

            # Build check-in transaction
            nonce = web3.eth.get_transaction_count(account.address)
            checkin_txn = checkin_contract.functions.checkIn().build_transaction({
                'from': account.address,
                'gas': estimated_gas,
                'gasPrice': gas_price,
                'nonce': nonce
            })

            # Sign and send transaction
            signed_txn = web3.eth.account.sign_transaction(checkin_txn, private_key)
            tx_hash = web3.eth.send_raw_transaction(signed_txn.raw_transaction)
            logging.info(f"Account {abridged_address}: Check-in transaction pending...")

            # Wait for transaction receipt
            receipt = web3.eth.wait_for_transaction_receipt(tx_hash, timeout=300)

            if dict(receipt)['status'] != 1:
                raise Exception(f"Account {abridged_address}: Check-in transaction failed")

            # Sign required message
            message = "0x77b460b444a342e7ea764336bb7bf5fdb079f85c82ce7d732e03d431b86f08be"
            signed_message = web3.eth.account.sign_message(
                encode_defunct(hexstr=message),
                private_key=private_key
            )

            logging.info(f"Account {abridged_address}: Daily check-in successful!")

            return receipt, signed_message

        except Exception as e:
            if "replacement transaction underpriced" in str(e) and attempt < max_retries - 1:
                logging.error(f"Transaction underpriced, retrying... (Attempt {attempt + 1}/{max_retries})")
                time.sleep(2)
                continue
            logging.error(f"Account {abridged_address}: Check-in failed: {str(e)}")
            raise e


async def swap_tokens(private_key):
    while True:
        try:
            wallet_address = web3.eth.account.from_key(private_key).address
            abridged_address = short_address(wallet_address)

            swap_count, swap_time = get_swap_info(wallet_address)
            time_left = get_time_left(swap_time) + (10 * 60)

            if time_left < 0:
                swap_ini(private_key)
                await asyncio.sleep(30)  # pause for swap to update
                swap_count, swap_time = get_swap_info(wallet_address)
                logging.info(f"Account {abridged_address}: Swap Count {swap_count}")
            else:
                logging.info(f"Account {abridged_address}: Swap wait time: {time_left} seconds ...")
                await asyncio.sleep(time_left)

        except Exception as e:
            logging.error(f'Account {abridged_address}: Swap failed \n{e}')
            await asyncio.sleep(10)


def perform_task(url, address):
    task = url.split('/')[-1]
    data = {'address': address}
    r = requests.post(url, data=data)
    status = r.json()['status']
    message = r.json()['message']
    if status:
        logging.info(f"Account {short_address(address)}: Additional Task {task} - Completed successfully")
    else:
        logging.error(f"Account {short_address(address)}: Additional Tasks - {message}")


async def additional_task(private_key):
    while True:
        try:
            wallet_address = web3.eth.account.from_key(private_key).address
            additional_tasks = get_task_status(wallet_address)["additionalTaskInfo"]
            additional_tasks_urls = ['https://candyapi.inichain.com/airdrop/v1/twitter/like',
                                     'https://candyapi.inichain.com/airdrop/v1/twitter/retweet',
                                     'https://candyapi.inichain.com/airdrop/v1/twitter/quote',
                                     'https://candyapi.inichain.com/airdrop/v1/twitter/reply']
            tasks_and_urls = list(zip(additional_tasks, additional_tasks_urls))
            for task, url in tasks_and_urls:
                if not task:  # If the task is not yet performed
                    perform_task(url, wallet_address)
                else:
                    logging.info(f'Account {short_address(wallet_address)}: Task already completed')
            await asyncio.sleep(60 * 60 * 2)
        except Exception as e:
            wallet_address = web3.eth.account.from_key(private_key).address
            logging.error(f'Account {short_address(wallet_address)}: Daily check-in error {e}')


async def send_tokens(private_key):
    # Initialize Web3 with the provided RPC URL
    wallet_address = web3.eth.account.from_key(private_key).address
    abridged_address = short_address(wallet_address)

    while True:
        new_address = generate_new_eth_address()
        try:
            tx = send_testnet_eth(private_key, new_address, 0.000001)
            logging.info(f"Account {abridged_address}: Send Token Successful!")
            await asyncio.sleep(60 * 2)
        except Exception as e:
            logging.error(f"Account {abridged_address}: Error when sending token \n{e}")


# Function 3: Daily check-in every 24 hours
async def daily_check_in(private_key):
    while True:
        try:
            wallet_address = web3.eth.account.from_key(private_key).address
            abridged_address = short_address(wallet_address)

            checkin_count, checkin_time = get_checkin_info(wallet_address)
            time_left = get_time_left(checkin_time) + (60 * 60 * 24)
            display_time_left = f"{time_left} seconds" if time_left < 3600 else f"{int(time_left/3600)} Hours"

            if time_left < 0:
                logging.info(f"Account {abridged_address}: Performing daily check-in...")
                perform_daily_checkin(private_key)
                await asyncio.sleep(30)  # pause for swap to update
                checkin_count, checkin_time = get_swap_info(wallet_address)
                logging.info(f"Account {abridged_address}: Check-in completed! ({checkin_count})")
            else:
                logging.info(f"Account {abridged_address}: Daily check in already performed ({checkin_count}). Waiting {display_time_left}...")
                await asyncio.sleep(time_left)

        except Exception as e:
            logging.error(f'Account {abridged_address}: Daily Check in failed \n{e}')
            await asyncio.sleep(10)


# Run tasks for all private keys concurrently
async def run_all(private_keys: list):
    tasks = []  # Collect all tasks here
    for private_key in private_keys:
        tasks.append(asyncio.gather(
            daily_check_in(private_key),
            additional_task(private_key),
            swap_tokens(private_key),
            send_tokens(private_key),
        ))

    # Run all tasks concurrently
    await asyncio.gather(*tasks)
