import logging
from web3 import Web3
from eth_account import Account
import asyncio
from headers import headers
from playwright.async_api import async_playwright
import json


try:
    # Load data from the JSON file
    with open('config.json', "r") as file:
        data = json.load(file)
except FileNotFoundError:
    raise FileNotFoundError(f"config.json file does not exist. Create one")
except json.JSONDecodeError:
    raise ValueError(f"The config file is not a valid JSON file.")


timeout_after_trades = data['timeout_after_trades']
timeout_within_trades = data['timeout_within_trades']
send_amount = data['send_amount']


RPC_URL = 'http://rpc-mainnet.inichain.com'
BASE_URL = 'https://candyapi-mainnet.inichain.com/airdrop/api/v1'

web3 = Web3(Web3.HTTPProvider(RPC_URL))


def short_address(wallet_address):
    address = f"{''.join(wallet_address[:5])}..{''.join(wallet_address[-5:])}"
    return address


def generate_new_eth_address():
    # Generate a new Ethereum account
    account = Account.create()
    # Return the address and private key
    return account.address


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


async def requests_via_playwright(url, wallet_address):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()

        # Set headers
        headers['address'] = wallet_address
        await page.set_extra_http_headers(headers)

        response = await page.goto(url)

        if response.status == 200:
            body = await response.body()
            data = json.loads(body)
            data = data['data']
            await browser.close()
            return data
        else:
            text = await response.text()
            await browser.close()
            raise Exception(f"Possible Cloudflare blockade")


async def list_tasks(wallet_address):
    url = f"{BASE_URL}/task/list?address={wallet_address}"
    response_data = await requests_via_playwright(url, wallet_address)
    return response_data


async def get_user_info(wallet_address):
    url = f'{BASE_URL}/user/userInfo?address={wallet_address}'
    response_data = await requests_via_playwright(url, wallet_address)
    return response_data


async def get_points_trades(wallet_address):
    # get trades
    list_tasks_data = await list_tasks(wallet_address)
    day_trading_count = int(list_tasks_data['dayTradingCount'])
    trades = list_tasks_data['tasks']['dailyTask'][0]['tag']
    trade_count = int(trades.split('/')[0])
    trade_left = day_trading_count - trade_count

    # points
    points = await get_user_info(wallet_address)
    points = points['points']

    return trade_left, trade_count, points


async def send_tokens(private_key):
    wallet_address = web3.eth.account.from_key(private_key).address
    abridged_address = short_address(wallet_address)
    while True:  # infinite loop
        try:
            wallet_address = web3.eth.account.from_key(private_key).address
            abridged_address = short_address(wallet_address)

            trade_left, trade_count, points = await get_points_trades(wallet_address)
            logging.info(f"Account {abridged_address}: Trades {trade_count}. Points {points}")

            for _ in range(trade_left):
                new_address = generate_new_eth_address()
                try:
                    logging.info(f"Account {abridged_address}: Prepping to send tokens...")
                    tx = send_testnet_eth(private_key, new_address, send_amount)
                    logging.info(f"Account {abridged_address}: Send Token Successful! Tx Hash: {tx}")
                    await asyncio.sleep(timeout_within_trades)

                except Exception as e:
                    logging.error(f"Account {abridged_address}: Error when sending token \n{e}")
                    await asyncio.sleep(30)

            trades, trade_count, points = await get_points_trades(wallet_address)
            logging.info(f"Account {abridged_address}: Trading complete. Trades ({trade_count}/10). Points {points}")
            logging.info(f"Account {abridged_address}: Waiting {timeout_after_trades} hrs till next trade")
            await asyncio.sleep(60 * 60 * timeout_after_trades)

        except Exception as e:
            logging.error(f"Account {abridged_address}: Error during trades. {e}. Restarting")


# Run tasks for all private keys concurrently
async def run_all(private_keys: list):
    tasks = []  # Collect all tasks here
    for private_key in private_keys:
        tasks.append(asyncio.gather(

            send_tokens(private_key),
        ))

    # Run all tasks concurrently
    await asyncio.gather(*tasks)
