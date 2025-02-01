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
import colorlog

formatter = colorlog.ColoredFormatter(
    '%(log_color)s%(levelname)s: %(asctime)s: %(message)s',
    log_colors={
        'DEBUG': 'green',
        'INFO': 'cyan',
        'WARNING': 'yellow',
        'ERROR': 'red',
        'CRITICAL': 'red,bg_white'
    },
    datefmt='%Y-%m-%d %H:%M:%S'
)

handler = colorlog.StreamHandler()
handler.setFormatter(formatter)

logger = colorlog.getLogger()
logger.addHandler(handler)
logger.setLevel(colorlog.INFO)


def get_random_user_agent():
    base_user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/{webkit_version} (KHTML, like Gecko) Chrome/{chrome_version} Safari/{webkit_version}",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/{webkit_version} (KHTML, like Gecko) Chrome/{chrome_version} Safari/{webkit_version}",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/{webkit_version} (KHTML, like Gecko) Chrome/{chrome_version} Safari/{webkit_version}",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/{webkit_version} (KHTML, like Gecko) Firefox/{firefox_version}",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:{firefox_version}) Gecko/20100101 Firefox/{firefox_version}",
    ]

    webkit_version = f"{random.randint(500, 600)}.{random.randint(0, 50)}"
    chrome_version = f"{random.randint(80, 100)}.0.{random.randint(4000, 5000)}.{random.randint(100, 150)}"
    firefox_version = f"{random.randint(80, 100)}.0"

    user_agent = random.choice(base_user_agents).format(
        webkit_version=webkit_version,
        chrome_version=chrome_version,
        firefox_version=firefox_version
    )

    return user_agent


headers = {
    "accept": "application/json, text/plain, */*",
    "accept-language": "en-US,en;q=0.9",
    "content-type": "application/json",
    "priority": "u=1, i",
    "sec-ch-ua": "\"Microsoft Edge\";v=\"129\", \"Not=A?Brand\";v=\"8\", \"Chromium\";v=\"129\"",
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": "\"Windows\"",
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "same-origin",
    "user-agent": get_random_user_agent()
}


def short_address(wallet_address):
    address = f"{''.join(wallet_address[:5])}..{''.join(wallet_address[-5:])}"
    return address


def get_time_left(target_timestamp):
    current_timestamp = int(datetime.now().timestamp())
    return target_timestamp - current_timestamp


def generate_new_eth_address():
    # Generate a new Ethereum account
    account = Account.create()
    # Return the address and private key
    return account.address


RPC_URL = 'https://rpc-mainnet.inichain.com'
BASE_URL = 'https://candyapi-mainnet.inichain.com/airdrop/api/v1'

# First test the RPC endpoint with a simple request
try:
    response = requests.post(
        RPC_URL, json={"jsonrpc": "2.0", "method": "eth_blockNumber", "params": [], "id": 1}, timeout=5)
    logging.info(f"RPC Response: {response.status_code}")
except Exception as e:
    raise Exception(f"Failed to connect to RPC: {e}")

# Then try Web3
try:
    web3 = Web3(Web3.HTTPProvider(RPC_URL))
    connected = web3.is_connected()
    logging.info(f"Web3 connected: {connected}")
except Exception as e:
    print(f"Web3 connection error: {e}")


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
            receipt = web3.eth.wait_for_transaction_receipt(tx_hash, timeout=200)

            if receipt['status'] == 1:
                logging.info(f"Account {short_address(sender_address)}: Transferred {amount_in_ether} INI to {receiver_address} successfully!")
                return tx_hash.hex()  # Return transaction hash if successful
            else:
                raise Exception(f"Account {short_address(sender_address)}: Transaction failed")

        except Exception as e:
            logging.warning(f"Account {short_address(sender_address)}: Transaction failed ({attempt}) with error: {str(e)}")

            if attempt < retries:
                gas_price = int(gas_price * 1.5)  # Increase gas price by 50% for the next attempt
                logging.info(f"Account {short_address(sender_address)}: Increasing gas price and retrying ({attempt + 1})...")
            else:
                logging.error(f"Account {short_address(sender_address)}: Max retries reached. Token send failed.")
                raise e  # Re-raise the exception if retries are exhausted


def list_tasks(wallet_address):
    url = f"{BASE_URL}/task/list"
    headers['address'] = wallet_address
    r = requests.get(url, headers=headers)
    if r.status_code == 200:
        data = r.json()['data']
        return data


def get_user_info(wallet_address):
    url = f'{BASE_URL}/user/userInfo?address={wallet_address}'
    headers['address'] = wallet_address
    r = requests.get(url, headers=headers)
    if r.status_code == 200:
        data = r.json()["data"]
        return data


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
    wallet_address = web3.eth.account.from_key(private_key).address
    print(list_tasks(wallet_address))
    additional_tasks = list_tasks(wallet_address)['tasks']['additional']
    for task in additional_tasks:
        tweet_id = task['link']
        task_title = task['title'].split(' ')[0].lower()
        is_performed_task = task['flag']

        if not is_performed_task:
            print(f"tweet_id: {tweet_id},"
                  f"task: {task_title},"
                  )

    # while True:
    #     try:


        #     additional_tasks_urls = [
        #         f'{BASE_URL}/twitter/like',
        #         f'{BASE_URL}twitter/retweet',
        #         f'{BASE_URL}/twitter/reply',
        #         f'{BASE_URL}/twitter/quote'
        #     ]
        #     additional_tasks = []
        #     tasks_and_urls = list(zip(additional_tasks, additional_tasks_urls))
        #     for task, url in tasks_and_urls:
        #         if not task:  # If the task is not yet performed
        #             perform_task(url, wallet_address)
        #         # else:
        #             # logging.info(f'Account {short_address(wallet_address)}: Task already completed')
        #     await asyncio.sleep(60 * 60 * 2)
        # except Exception as e:
        #     wallet_address = web3.eth.account.from_key(private_key).address
        #     logging.error(f'Account {short_address(wallet_address)}: Twitter additional tasks failed. {e}')


async def send_tokens(private_key):
    while True:
        try:
            wallet_address = web3.eth.account.from_key(private_key).address
            abridged_address = short_address(wallet_address)

            # get trades
            list_tasks_data = list_tasks(wallet_address)
            day_trading_count = int(list_tasks_data['dayTradingCount'])
            trades = list_tasks_data['tasks']['dailyTask'][0]['tag']
            trade_count = int(trades.split('/')[0])
            trade_left = day_trading_count - trade_count

            for _ in range(trade_left):
                new_address = generate_new_eth_address()
                try:
                    # points
                    points = get_user_info(wallet_address)['points']
                    logging.info(
                        f"Account {abridged_address}: Prepping to send tokens...Trades ({trades}). Points {points}")
                    tx = send_testnet_eth(private_key, new_address, 0.000001)
                    logging.info(f"Account {abridged_address}: Send Token Successful!")

                    await asyncio.sleep(60 * 1)
                    # get updated trades
                    trades = list_tasks(wallet_address)['tasks']['dailyTask'][0]['tag']
                except Exception as e:
                    logging.error(f"Account {abridged_address}: Error when sending token \n{e}")
                    await asyncio.sleep(30)
            # points
            points = get_user_info(wallet_address)['points']
            logging.info(f"Account {abridged_address}: Trading complete. Trades ({trades}). Points {points}")
            await asyncio.sleep(60 * 60 * 6)
        except Exception as e:
            logging.error(f"Account {abridged_address}: Error during trading {e}\nStarting all over")


def convert_time_left(time_left):
    """
    convert to human readable time
    :param time_left:
    :return:
    """

    hours = int(time_left / 3600)
    minutes = int((time_left % 3600) / 60)
    seconds = int(time_left % 60)

    display_time_left = f"{hours} Hours {minutes} Mins" if hours > 0 else \
        f"{minutes} Minutes {seconds} Secs" if minutes > 0 else \
            f"{seconds} Seconds"

    return display_time_left


# Run tasks for all private keys concurrently
async def run_all(private_keys: list):
    tasks = []  # Collect all tasks here
    for private_key in private_keys:
        tasks.append(asyncio.gather(

            send_tokens(private_key),
            # additional_task(private_key)
        ))

    # Run all tasks concurrently
    await asyncio.gather(*tasks)
